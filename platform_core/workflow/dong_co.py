"""Động cơ Workflow V2 — MỘT runtime (spec §5.1).

Không I/O: chỉ đọc/ghi CSDL. Việc có mạng/GPU/tiền đi thành job (`cau_noi`).
`mot_vong` mở MỖI RUN MỘT TRANSACTION, khoá hàng run `SKIP LOCKED` — nhiều
worker chạy job động cơ cùng lúc vẫn an toàn (`jobs.submit` chỉ khử trùng job
CHƯA kết thúc bằng một `SELECT` thường, không có chỉ mục duy nhất, nên hai job
động cơ có thể tồn tại cùng lúc — khoá hàng ở đây, không phải một bảng khoá
mới, là thứ giữ cho hai lượt `mot_vong` chồng nhau vẫn an toàn).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy import select

from platform_core import jobs
from platform_core.models import Job, Wakeup, WorkflowRun, WorkflowVersion
from platform_core.workflow import cau_noi, danh_thuc, may_trang_thai as mtt, su_kien
from platform_core.workflow.cong_cu import CongCu

log = logging.getLogger(__name__)

#: Trần cứng — PHẢI ngắn hơn `credit.TU_HOAN_SAU` (lập luận ở `dieu_phoi` cũ,
#: `test_965` ghim quan hệ này).
TRAN_RUN = timedelta(hours=20)
_KICH = {"DATA": frozenset({"SUCCEEDED"}),
         "ERROR": frozenset({"FAILED", "ABANDONED"})}
_CAI_CACHE: dict[str, dict] = {}


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _do_thi(db, version_id: str) -> dict:
    g = _CAI_CACHE.get(version_id)
    if g is None:
        g = db.get(WorkflowVersion, version_id).graph   # bất biến ⇒ cache an toàn
        if len(_CAI_CACHE) > 512:
            _CAI_CACHE.clear()
        _CAI_CACHE[version_id] = g
    return g


def _lan_truyen(db, run: WorkflowRun, g: dict) -> tuple[dict[str, str], bool]:
    """Trả `(trang_thai_moi_node, co_doi)` — `co_doi` cho bên gọi biết pha này
    có tự chuyển node nào không (SKIPPED/READY), để quyết định có cần ghi một
    wakeup "tick" hay không (Important #2 — xem `xu_ly_run`)."""
    tt = {n["id"]: mtt.trang_thai_node(db, run.id, n["id"]) for n in g["nodes"]}
    vao: dict[str, list[dict]] = {n["id"]: [] for n in g["nodes"]}
    for e in g["edges"]:
        vao[e["target_node"]].append(e)
    co_doi = False
    doi = True
    while doi:
        doi = False
        for nid in g["thu_tu"]:
            if tt[nid] != "PENDING":
                continue
            canh = vao[nid]
            kich = [tt[e["source_node"]] in _KICH.get(e["kind"], frozenset())
                    for e in canh]
            chet = [tt[e["source_node"]] in mtt.NODE_KET_THUC and not k
                    for e, k in zip(canh, kich, strict=True)]
            if any(chet):
                mtt.chuyen_node(db, run.id, nid, sang="SKIPPED",
                                mo_ta="nguon khong kich hoat")
                tt[nid] = "SKIPPED"
                doi = True
                co_doi = True
            elif all(kich):
                mtt.chuyen_node(db, run.id, nid, sang="READY", mo_ta="du dau vao")
                tt[nid] = "READY"
                doi = True
                co_doi = True
    return tt, co_doi


def _ket_run(db, run: WorkflowRun, g: dict, tt: dict[str, str]) -> Optional[str]:
    if not all(s in mtt.NODE_KET_THUC for s in tt.values()):
        return None
    co_nhanh_loi = {e["source_node"] for e in g["edges"] if e["kind"] == "ERROR"}
    hong = [n for n, s in tt.items()
            if s in ("FAILED", "ABANDONED") and n not in co_nhanh_loi]
    sang = "FAILED" if hong else "SUCCEEDED"
    if run.status == "QUEUED":
        mtt.chuyen_run(db, run.id, sang="RUNNING")
    su_kien.ghi(db, run.id, "WorkflowFailed" if hong else "WorkflowCompleted",
                du_lieu={"status": sang, "node_hong": hong})
    mtt.chuyen_run(db, run.id, sang=sang, ly_do="moi node ket thuc")
    return sang


def xu_ly_run(db, run_id: str, *,
              cong_cu: Optional[dict[str, CongCu]] = None) -> str:
    run = db.get(WorkflowRun, run_id)
    if run is None or run.status in mtt.RUN_KET_THUC:
        return run.status if run else "MISSING"
    g = _do_thi(db, run.version_id)
    if run.status == "QUEUED":
        mtt.chuyen_run(db, run.id, sang="RUNNING")
    for n in g["nodes"]:
        cau_noi.ap_ket_qua(db, run, n["id"], cong_cu=cong_cu)
    tt, _ = _lan_truyen(db, run, g)
    ket = _ket_run(db, run, g, tt)
    if ket:
        return ket
    dang = sum(1 for s in tt.values() if s in mtt.NODE_DANG_CHAY)
    tran = int(g["settings"].get("max_concurrency", 4))
    for nid in g["thu_tu"]:
        if dang >= tran:
            break
        if tt[nid] != "READY":
            continue
        node = next(n for n in g["nodes"] if n["id"] == nid)
        if cau_noi.nop_job(db, run, node, cong_cu=cong_cu):
            dang += 1
    tt, co_doi = _lan_truyen(db, run, g)    # node FAILED lúc nộp ⇒ lan tiếp
    ket = _ket_run(db, run, g, tt)
    if ket:
        return ket
    # ⭐ Important #2 (review round 1): nếu vòng lan truyền THỨ HAI này (chạy
    # SAU vòng nộp job) vừa tự chuyển một node — vd node bị `nop_job` từ chối
    # (vượt trần báo giá / tham số không giải được, xem `cau_noi.nop_job`)
    # làm một cạnh ERROR kích hoạt đích thành READY — thì đích đó KHÔNG được
    # nộp trong lượt này (vòng nộp đã chạy xong phía trên) và không có job nào
    # sinh wakeup cho nó. Không có gì khác đưa run này quay lại trước hạn TTL
    # 20 giờ ⇒ tự ghi một wakeup "tick" ngay bây giờ, trừ khi run đã có sẵn
    # một wakeup khác đang chờ (mot_vong sẽ tự đến, không cần ghi thêm).
    if co_doi:
        con_wakeup = db.execute(select(Wakeup.id).where(
            Wakeup.run_id == run.id, Wakeup.claimed_at.is_(None))
            .limit(1)).scalar()
        if con_wakeup is None:
            danh_thuc.hen(db, run_id=run.id, kind="tick", due_at=_bay_gio())
    return run.status


def huy_run(db, run_id: str, ly_do: str) -> bool:
    # ⭐ Important #4 (review round 1): khoá HÀNG run (chặn, không skip_locked)
    # trước khi soi trạng thái — nếu không, một lượt `mot_vong` đang giữ khoá
    # này có thể nộp job MỚI ngay sau khi vòng huỷ đã quét xong
    # `Job.plan_id == run.id`, và job đó sống sót qua lần huỷ (tiền thật chạy
    # trên một run khách đã huỷ). Khoá tại đây ép `mot_vong` (dùng cùng khoá
    # `with_for_update` trên hàng run) đợi lượt huỷ xong trước khi nộp job kế.
    run = db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id)
                     .with_for_update()).scalars().first()
    if run is None or run.status in mtt.RUN_KET_THUC:
        return False
    g = _do_thi(db, run.version_id)
    for n in g["nodes"]:
        if mtt.trang_thai_node(db, run.id, n["id"]) not in mtt.NODE_KET_THUC:
            mtt.chuyen_node(db, run.id, n["id"], sang="CANCELLED", mo_ta=ly_do)
    for job in db.execute(select(Job).where(Job.plan_id == run.id)).scalars():
        jobs.cancel(db, job)                 # chỉ đổi job queued/running
    su_kien.ghi(db, run.id, "WorkflowCancelled", du_lieu={"ly_do": ly_do})
    return mtt.chuyen_run(db, run.id, sang="CANCELLED", ly_do=ly_do)


def ttl(db) -> int:
    dem = 0
    luc = _bay_gio()
    for run in db.execute(select(WorkflowRun).where(
            WorkflowRun.status.in_(("QUEUED", "RUNNING", "WAITING")),
            WorkflowRun.started_at.is_not(None))).scalars():
        g = _do_thi(db, run.version_id)
        han = min(timedelta(seconds=int(g["settings"].get("timeout_s", 21600))),
                  TRAN_RUN)
        # `WorkflowRun.started_at` là cột `DateTime(timezone=True)` — SQLite
        # trả về naive (bất kể khai báo), nhưng PostgreSQL thật trả về AWARE
        # (session TZ, thường là UTC). `_bay_gio()` luôn naive UTC theo quy
        # ước chung của module này (8 chỗ khác cùng định nghĩa) — so sánh
        # trực tiếp aware với naive ném `TypeError` ngay trên PostgreSQL thật,
        # chưa từng lộ trên SQLite (phát hiện bằng `tests/test_1720_wf_dong_co_pg.py`
        # chạy thật, Task 11 fix round 3). Bỏ tzinfo trước khi so — an toàn vì
        # giả định session TZ = UTC đã ngầm có sẵn ở MỌI chỗ khác ghi
        # `_bay_gio()` vào chính cột này.
        bat_dau = run.started_at.replace(tzinfo=None) if run.started_at.tzinfo else run.started_at
        if bat_dau <= luc - han:
            for job in db.execute(select(Job).where(Job.plan_id == run.id)).scalars():
                jobs.cancel(db, job)
            su_kien.ghi(db, run.id, "WorkflowFailed",
                        du_lieu={"status": "TIMED_OUT"})
            if mtt.chuyen_run(db, run.id, sang="TIMED_OUT", ly_do="qua han"):
                dem += 1
    return dem


def mot_vong(db_factory: Callable, *, gioi_han: int = 50) -> dict:
    db = db_factory()
    try:
        run_ids = list(dict.fromkeys(db.execute(
            select(Wakeup.run_id).where(Wakeup.claimed_at.is_(None),
                                        Wakeup.due_at <= _bay_gio())
            .order_by(Wakeup.due_at).limit(gioi_han * 4)).scalars()))[:gioi_han]
        so = ttl(db)
        db.commit()
    finally:
        db.close()
    da = 0
    loi = 0
    for rid in run_ids:
        db = db_factory()
        try:
            run = db.execute(select(WorkflowRun).where(WorkflowRun.id == rid)
                             .with_for_update(skip_locked=True)).scalars().first()
            if run is None:
                db.rollback()
                continue
            ws = list(db.execute(select(Wakeup).where(
                Wakeup.run_id == rid, Wakeup.claimed_at.is_(None),
                Wakeup.due_at <= _bay_gio()).with_for_update(skip_locked=True))
                .scalars())
            xu_ly_run(db, rid)
            for w in ws:
                w.claimed_at = _bay_gio()
            db.commit()
            da += 1
        except Exception:
            # ⭐ Important #1 (review round 1): MỘT run lỗi không được chặn
            # những run khác trong cùng lượt — `run_ids` sắp theo `due_at`, nên
            # nếu ném tiếp thì đúng run hỏng này sẽ luôn đứng đầu mọi lượt sau
            # (nghẽn vĩnh viễn). Cuộn transaction CỦA RIÊNG run này, ghi log
            # (không lộ bí mật — chỉ id + tên lỗi), để wakeup của nó CHƯA
            # CLAIM (thử lại đúng lượt sau), và đếm vào `loi` thay vì `raise`.
            db.rollback()
            loi += 1
            log.exception("dong co: run %s loi, bo qua luot nay", rid)
        finally:
            db.close()
    db = db_factory()
    try:
        # ⭐ Important #3 (review round 1): `con_viec` chỉ dựa trên wakeup CHƯA
        # NHẶN — một run không-kết-thúc nhưng không còn wakeup nào là run
        # ĐANG ĐỖ có chủ đích (chờ webhook/delay dài); watchdog `bao_tri` (60s)
        # + wakeup lúc job xong sẽ tự đưa nó về, không cần động cơ tự nộp lại
        # mỗi 2 giây mãi mãi.
        ke = db.execute(select(Wakeup.due_at).where(Wakeup.claimed_at.is_(None))
                        .order_by(Wakeup.due_at).limit(1)).scalar()
    finally:
        db.close()
    return {"run_da_xu_ly": da, "timed_out": so, "loi": loi,
            "con_viec": ke is not None, "han_ke_tiep": ke}


__all__ = ["TRAN_RUN", "mot_vong", "xu_ly_run", "huy_run", "ttl"]
