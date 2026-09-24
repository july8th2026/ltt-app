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
from platform_core.workflow import (cau_noi, danh_thuc, may_trang_thai as mtt,
                                    moi_truong, nut_loi, su_kien, thi_hanh,
                                    thu_lai)
from platform_core.workflow.cong_cu import CongCu

log = logging.getLogger(__name__)

#: Trần cứng — PHẢI ngắn hơn `credit.TU_HOAN_SAU` (lập luận ở `dieu_phoi` cũ,
#: `test_965` ghim quan hệ này).
TRAN_RUN = timedelta(hours=20)
_KICH = {"DATA": frozenset({"SUCCEEDED"}),
         "CONTROL": frozenset({"SUCCEEDED"}),
         "ERROR": frozenset({"FAILED", "ABANDONED"})}

#: Spec §5.1: *"giới hạn 500 bước inline mỗi run mỗi vòng, vượt thì để vòng
#: sau — chống vòng vô hạn"*. Node inline không sinh job nên không có gì khác
#: chặn một chuỗi `if → if → if` dài; con số này là cái chặn đó.
TRAN_BUOC_INLINE = 500
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


def _nhanh_da_chon(db, run: WorkflowRun, nid: str) -> str:
    """Tên nhánh mà một node rẽ đã chọn (`core.if`/`core.switch`, §5.4).

    Rỗng cho mọi node KHÔNG rẽ nhánh — và đó là lý do luật dưới đây không đổi
    hành vi của đồ thị chỉ có node app: một cạnh không mang `condition` không
    bao giờ hỏi tới hàm này.
    """
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid)
    return str((anh.output_ref or {}).get(moi_truong.KHOA_NHANH, "")) if anh else ""


def _nguong_join(g: dict, nid: str, so_canh: int) -> int:
    """Bao nhiêu cạnh vào phải kích hoạt thì node này READY?

    Mặc định của đồ thị là **mọi cạnh** — tức `ALL`, và đó đã là một Join. Chỉ
    node `core.join` khai `ANY`/`N_OF_M` mới hạ ngưỡng.

    ⚠️ Một node không có cạnh vào nào (điểm bắt đầu) có ngưỡng 0 ⇒ READY ngay,
       y như trước. `all([])` cũ cũng cho đúng kết quả ấy; viết ra để lần đọc
       sau không phải suy lại.
    """
    node = next((n for n in g["nodes"] if n["id"] == nid), None)
    if node is None or str(node.get("type")) != "core.join":
        return so_canh
    p = node.get("params") or {}
    che_do = str(p.get("che_do") or "ALL")
    if che_do == "ANY":
        return 1 if so_canh else 0
    if che_do == "N_OF_M":
        return max(1, min(so_canh, int(p.get("can") or 1)))
    return so_canh


def _lan_truyen(db, run: WorkflowRun, g: dict) -> tuple[dict[str, str], bool]:
    """Trả `(trang_thai_moi_node, co_doi)` — `co_doi` cho bên gọi biết pha này
    có tự chuyển node nào không (SKIPPED/READY), để quyết định có cần ghi một
    wakeup "tick" hay không (Important #2 — xem `xu_ly_run`)."""
    tt = {n["id"]: mtt.trang_thai_node(db, run.id, n["id"]) for n in g["nodes"]}
    vao: dict[str, list[dict]] = {n["id"]: [] for n in g["nodes"]}
    for e in g["edges"]:
        vao[e["target_node"]].append(e)
    # ⭐ §5.4: *"Cạnh CONTROL mang `condition = <tên nhánh>`; CHỈ cạnh khớp
    #    nhánh được kích hoạt."* Nên một cạnh có `condition` cần HAI điều kiện:
    #    nguồn kết thúc đúng kiểu, VÀ nhánh nguồn chọn khớp tên. Không khớp
    #    ⇒ cạnh CHẾT ⇒ đích SKIPPED qua đúng nhánh `chet` đã có sẵn dưới đây.
    nhanh: dict[str, str] = {}

    def _kich_hoat(e: dict, tt_nguon: str) -> bool:
        if tt_nguon not in _KICH.get(e["kind"], frozenset()):
            return False
        dk = str(e.get("condition") or "")
        if not dk:
            return True
        src = e["source_node"]
        if src not in nhanh:
            nhanh[src] = _nhanh_da_chon(db, run, src)
        return nhanh[src] == dk

    co_doi = False
    doi = True
    while doi:
        doi = False
        for nid in g["thu_tu"]:
            if tt[nid] != "PENDING":
                continue
            canh = vao[nid]
            kich = [_kich_hoat(e, tt[e["source_node"]]) for e in canh]
            chet = [tt[e["source_node"]] in mtt.NODE_KET_THUC and not k
                    for e, k in zip(canh, kich, strict=True)]
            # ⭐ `core.join` đổi NGƯỠNG, không đổi luật. Mặc định của đồ thị là
            #    `ALL` (mọi cạnh vào phải kích hoạt) — đó đã là một Join, nên
            #    node `core.join` chế độ ALL không thêm gì. `ANY`/`N_OF_M` chỉ
            #    hạ ngưỡng xuống, và ngưỡng ấy sống Ở ĐÂY chứ không trong bộ thi
            #    hành của node: một node chỉ được chạy KHI ĐÃ READY, nên một
            #    luật READY nằm trong bộ thi hành là một luật không bao giờ tới.
            can = _nguong_join(g, nid, len(canh))
            du = sum(1 for k in kich if k)
            con_co_the = du + sum(1 for e, k in zip(canh, kich, strict=True)
                                  if not k
                                  and tt[e["source_node"]] not in mtt.NODE_KET_THUC)
            if du >= can:
                mtt.chuyen_node(db, run.id, nid, sang="READY", mo_ta="du dau vao")
                tt[nid] = "READY"
                doi = True
                co_doi = True
            elif con_co_the < can or (can == len(canh) and any(chet)):
                mtt.chuyen_node(db, run.id, nid, sang="SKIPPED",
                                mo_ta="nguon khong kich hoat")
                tt[nid] = "SKIPPED"
                doi = True
                co_doi = True
    return tt, co_doi


def _ket_run(db, run: WorkflowRun, g: dict, tt: dict[str, str]) -> Optional[str]:
    if not all(s in mtt.NODE_KET_THUC for s in tt.values()):
        return None
    co_nhanh_loi = {e["source_node"] for e in g["edges"] if e["kind"] == "ERROR"}
    # ⭐ F4 (final-review.md): CANCELLED phải đếm là "hỏng" giống FAILED/
    # ABANDONED. Trước fix, một node bị huỷ TỪ NGOÀI (vd admin huỷ đúng một
    # job đang chạy — không đi qua `huy_run`, cái đó huỷ CẢ run trước rồi mới
    # huỷ node nên không đụng nhánh này) khiến `_ket_run` báo SUCCEEDED cho
    # một run có một node CHƯA BAO GIỜ chạy xong — sai đúng chữ khách hàng và
    # support đọc. Không thu tiền quá (node CANCELLED không viết `cost_credit`
    # — `test_1718::test_job_loi_khong_tinh_tien`), nên đây là lỗi TRUNG THỰC,
    # không phải lỗi SỔ SÁCH; nhưng "trung thực" vẫn là bất biến phải giữ.
    #
    # Chọn FAILED cho run (không phải một run-status CANCELLED riêng cho
    # trường hợp này): một node CANCELLED nghĩa là "phần việc đó không hoàn
    # thành như dự định" — cùng bản chất với FAILED/ABANDONED, chỉ khác NGUỒN
    # gây dừng (ngoại lực thay vì lỗi provider). Tái dùng đúng đường FAILED đã
    # kiểm kỹ (sự kiện `WorkflowFailed`, `ket_so` xử lý FAILED như bất kỳ kết
    # thúc lỗi nào) an toàn hơn là mở một đường run-CANCELLED-từ-node-lẻ mới,
    # thứ sẽ cần tự kiểm lại toàn bộ ma trận chuyển trạng thái + settlement.
    # `huy_run` (huỷ CẢ run, người dùng bấm nút Huỷ) vẫn đi thẳng
    # `chuyen_run(sang="CANCELLED")`, không qua hàm này — ý nghĩa "khách tự
    # huỷ" và "một node bị dừng ngoài ý muốn giữa một run vẫn đang chạy" là
    # hai chuyện khác nhau, và chỉ chuyện thứ hai đi qua `_ket_run`.
    hong = [n for n, s in tt.items()
            if s in ("FAILED", "ABANDONED", "CANCELLED") and n not in co_nhanh_loi]
    sang = "FAILED" if hong else "SUCCEEDED"
    if run.status == "QUEUED":
        mtt.chuyen_run(db, run.id, sang="RUNNING")
    su_kien.ghi(db, run.id, "WorkflowFailed" if hong else "WorkflowCompleted",
                du_lieu={"status": sang, "node_hong": hong})
    mtt.chuyen_run(db, run.id, sang=sang, ly_do="moi node ket thuc")
    return sang



def _chay_mot_inline(db, run: WorkflowRun, g: dict, node: dict) -> str:
    """Thi hành MỘT node inline. Trả trạng thái mới, hoặc `"DUNG:<tt>"` nếu nó
    dừng cả run.

    ⛔ Không hàng đợi, không lease, không bút toán — `dieu_khien.py` nói vì sao:
       *"một job là một bút toán. Rẽ nhánh tạo một dòng trong sổ tiền, dù nó chỉ
       so sánh hai giá trị."*
    """
    nid = str(node["id"])
    ham = nut_loi.bo_thi_hanh(str(node["type"]))
    if ham is None:
        # Cùng hạng lỗi với `cau_noi.nop_job` khi tool biến mất khỏi registry:
        # nói thẳng ra bằng một FAILED có mã, thay vì để node đứng READY tới
        # khi `TRAN_RUN` (20 giờ) tự hết hạn.
        mtt.chuyen_node(db, run.id, nid, sang="FAILED",
                        mo_ta="khong co bo thi hanh inline",
                        error=f"loi_he_thong: {node['type']!r} khong co bo thi hanh")
        return "FAILED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid)
    lan = int(anh.attempt_number if anh else 1)
    try:
        kq = ham(db, run, node,
                 moi_truong=moi_truong.moi_truong_run(db, run, g, nid), g=g)
    except Exception as loi:                      # noqa: BLE001
        # Một node inline ngã KHÔNG được kéo theo cả lượt `mot_vong` (cùng hình
        # dạng Important #1): ghi FAILED cho chính nó, run đi tiếp theo nhánh
        # ERROR nếu có.
        log.exception("dong co: node inline %s cua run %s nga", nid, run.id)
        mtt.chuyen_node(db, run.id, nid, sang="FAILED", mo_ta="node inline nga",
                        error=f"loi_he_thong: {type(loi).__name__}",
                        attempt_number=lan)
        return "FAILED"
    ra = dict(kq.output or {})
    if kq.nhanh:
        ra[moi_truong.KHOA_NHANH] = kq.nhanh
    mtt.chuyen_node(db, run.id, nid, sang=kq.sang, mo_ta="node inline",
                    error=kq.error, attempt_number=lan, output_ref=ra)
    if kq.dung_run and kq.sang == "SUCCEEDED":
        return "DUNG:" + kq.dung_run
    return kq.sang


def _dung_run(db, run: WorkflowRun, g: dict, sang: str, ly_do: str) -> str:
    """`core.stop`: mọi node chưa kết thúc thành SKIPPED, rồi run kết thúc.

    ⭐ SKIPPED chứ không CANCELLED: `_ket_run` đếm CANCELLED là "hỏng" (F4), và
       một node không chạy vì luồng đã rẽ đi chỗ khác **không hỏng**. Đây đúng
       nghĩa `SKIPPED` mà §5.5 đã định.
    """
    for n in g["nodes"]:
        if mtt.trang_thai_node(db, run.id, n["id"]) not in mtt.NODE_KET_THUC:
            mtt.chuyen_node(db, run.id, n["id"], sang="SKIPPED", mo_ta=ly_do)
    if run.status == "QUEUED":
        mtt.chuyen_run(db, run.id, sang="RUNNING")
    su_kien.ghi(db, run.id,
                "WorkflowFailed" if sang == "FAILED" else "WorkflowCompleted",
                du_lieu={"status": sang, "ly_do": ly_do})
    mtt.chuyen_run(db, run.id, sang=sang, ly_do=ly_do)
    return sang


def _pha_inline(db, run: WorkflowRun, g: dict) -> Optional[str]:
    """Chạy MỌI node inline sẵn sàng, liên tiếp, tới khi hết (spec §5.1).

    Trả trạng thái kết thúc run nếu một `core.stop` dừng nó, ngược lại `None`.

    ⛔ `TRAN_BUOC_INLINE` là chặn trên của MỘT vòng, không phải của cả run:
       *"vượt thì để vòng sau"*. Ném ở đây thì một đồ thị hợp lệ mà dài sẽ chết
       thay vì chạy chậm.
    """
    inline = {str(n["id"]): n for n in g["nodes"]
              if str(n.get("thi_hanh")) == "inline"}
    if not inline:
        return None
    for _ in range(TRAN_BUOC_INLINE):
        tt, _doi = _lan_truyen(db, run, g)
        san_sang = [nid for nid in g["thu_tu"]
                    if nid in inline and tt[nid] == "READY"]
        if not san_sang:
            return None
        for nid in san_sang:
            ket = _chay_mot_inline(db, run, g, inline[nid])
            if ket.startswith("DUNG:"):
                return _dung_run(db, run, g, ket[5:], f"core.stop tai {nid}")
    return None


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
    # ⭐ Retry cấp node (spec §5.6): `RETRY_SCHEDULED` đã tới hạn quay về READY
    #    TRƯỚC vòng lan truyền, để nó được nộp lại ngay trong lượt này thay vì
    #    phải đợi thêm một lượt động cơ nữa.
    thu_lai.den_han(db, run.id, g["nodes"])
    # ⭐ Node inline chạy LIÊN TIẾP trong cùng vòng (spec §5.1) — trước vòng nộp
    #    job, để một `if` vừa rẽ xong là nhánh của nó được nộp ngay lượt này.
    dung = _pha_inline(db, run, g)
    if dung:
        return dung
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
        if str(node.get("thi_hanh")) != "job":
            # ⛔ Node inline KHÔNG bao giờ được rơi vào vòng nộp job: `nop_job`
            #    tra registry công cụ bằng `type[4:]`, nên `core.if` thành
            #    `".if"` và node FAILED `cong_cu_khong_con`. `_pha_inline` đã
            #    chạy hết phần inline trước đó; cái gì còn READY ở đây là một
            #    node inline KHÔNG có bộ thi hành, và `_chay_mot_inline` đã nói
            #    ra điều đó bằng một FAILED có mã.
            continue
        if cau_noi.nop_job(db, run, node, cong_cu=cong_cu):
            dang += 1
    dung = _pha_inline(db, run, g)          # node inline mở ra sau vòng nộp
    if dung:
        return dung
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


def ttl(db_factory: Callable) -> int:
    """Quét TTL — MỖI RUN QUÁ HẠN MỘT TRANSACTION RIÊNG, khoá hàng run
    `SKIP LOCKED` giống `mot_vong` (⭐ F3, final-review.md).

    ⛔ Bản cũ chạy CẢ vòng TTL trong MỘT transaction dùng chung với vòng gom
       wakeup của `mot_vong`, không khoá hàng nào. Đây là đường ĐỘNG CƠ DUY
       NHẤT không khoá — hai lượt `mot_vong` song song (thiết kế CHO PHÉP
       điều này, `jobs.submit` chỉ khử trùng bằng `SELECT` thường) có thể
       cùng đọc một run RUNNING quá hạn, cùng chuyển nó sang TIMED_OUT, cùng
       ghi sự kiện `WorkflowFailed` — `UNIQUE(run_id, seq)` làm LƯỢT THUA
       ném `IntegrityError`, sập NGUYÊN transaction TTL đó, kéo theo quyết
       định TTL của MỌI run khác trong cùng lượt (không phải chỉ run va
       chạm). Tiền vẫn an toàn (`_khoa_ket_so_job` + `_ket_qua_da_chot` tự
       khoá ở tầng settlement) — đây là lỗi sống còn/nhiễu, không phải sổ
       sách, nhưng "một run va chạm chặn hết các run khác" đúng hình dạng lỗi
       `mot_vong` đã né cho vòng nộp job (Important #1 review round 1).

    ⇒ Gom ứng viên (không khoá) trước, rồi khoá + xử lý + commit TỪNG RUN
       MỘT giống hệt vòng lặp chính của `mot_vong`: lượt thua `SKIP LOCKED`
       bỏ qua (không chờ, không sập), lượt lỗi khác cuộn riêng transaction
       của nó rồi đi tiếp — không chặn các run còn lại trong lượt quét này.
       Điều kiện lọc trạng thái được lặp lại NGAY TRONG câu khoá (không chỉ
       ở vòng gom ứng viên) để tự tái kiểm trạng thái SAU khi khoá được: run
       đã kết thúc bằng đường khác (vd `mot_vong` xử lý xong) giữa hai bước
       sẽ không khớp `WHERE` nữa và bị bỏ qua đúng cách, không cần đọc lại
       thêm một câu riêng.
    """
    dem = 0
    luc = _bay_gio()
    db0 = db_factory()
    try:
        ung_vien = list(db0.execute(select(WorkflowRun.id).where(
            WorkflowRun.status.in_(("QUEUED", "RUNNING", "WAITING")),
            WorkflowRun.started_at.is_not(None))).scalars())
    finally:
        db0.close()
    for rid in ung_vien:
        db = db_factory()
        try:
            run = db.execute(select(WorkflowRun).where(
                WorkflowRun.id == rid,
                WorkflowRun.status.in_(("QUEUED", "RUNNING", "WAITING")),
                WorkflowRun.started_at.is_not(None))
                .with_for_update(skip_locked=True)).scalars().first()
            if run is None:
                db.rollback()
                continue
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
            db.commit()
        except Exception:
            # Cùng hình dạng Important #1 (review round 1) của vòng nộp job:
            # một run lỗi cuộn riêng transaction của nó, ghi log, đi tiếp —
            # không chặn quyết định TTL của các run khác trong lượt này.
            db.rollback()
            log.exception("dong co: ttl run %s loi, bo qua luot nay", rid)
        finally:
            db.close()
    return dem


def mot_vong(db_factory: Callable, *, gioi_han: int = 50) -> dict:
    db = db_factory()
    try:
        run_ids = list(dict.fromkeys(db.execute(
            select(Wakeup.run_id).where(Wakeup.claimed_at.is_(None),
                                        Wakeup.due_at <= _bay_gio())
            .order_by(Wakeup.due_at).limit(gioi_han * 4)).scalars()))[:gioi_han]
        db.commit()
    finally:
        db.close()
    so = ttl(db_factory)
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


__all__ = ["TRAN_BUOC_INLINE", "TRAN_RUN", "mot_vong", "xu_ly_run",
           "huy_run", "ttl"]
