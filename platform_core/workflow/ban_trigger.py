"""Bắn trigger — MỘT vòng, MỘT cửa tạo run (spec §8.1).

⭐ *"`tao_run.tao_run` — một hàm, ba cửa gọi: API, trigger, Canvas"*. Mô-đun
   này là cửa **trigger**, và nó không được có đường tạo run riêng: trần credit,
   khoản giữ chỗ, hạn mức run đồng thời và `WorkflowStarted` đều sống trong
   `tao_run`. Một cửa thứ hai là một cửa không có những thứ đó.

## Ba luật, mỗi luật là một sự cố của người khác

1. **Khoá khử trùng mang MỐC LỊCH, không mang lúc bắn** (`khoa_idem.khoa_cron`).
   n8n `#17187` — *"Scheduled tasks executing multiple times at once"*. Hai
   tiến trình cùng thấy một trigger tới hạn là chuyện **bình thường**; chốt
   cuối là chỉ mục `ux_workflow_run_idem`, không phải một câu `SELECT` cẩn thận.

2. **Lỡ lịch phải có CHÍNH SÁCH, không có mặc định ngầm.** n8n `#34628` /
   `#23906` — *"Missed schedule trigger can cause unexpectedly long delays"*.
   `chay_mot_lan` ⇒ **một** run cho mốc lỡ **gần nhất** (⛔ không bù 3 ngày =
   3 run: đó là 3 lần tiêu credit cho một việc đã lỡ). `bo_qua` ⇒ không run,
   **nhưng `next_fire_at` vẫn phải tiến** — nếu không, trigger đứng ở một mốc
   quá khứ và mỗi vòng quét lại nhặt nó lên.

3. **Một trigger hỏng không được chặn trigger lành**, và phải **tự tắt**.
   Cùng hình dạng `dong_co.mot_vong` Important #1: `den_han()` sắp theo
   `next_fire_at`, nên một hàng hỏng luôn đứng đầu mọi lượt sau — nghẽn vĩnh
   viễn. Và spec §11.4: *"5 lần lỗi liên tiếp ⇒ tự tắt trigger"*.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from platform_core.models import Workflow, WorkflowTrigger
from platform_core.workflow import khoa_idem, tao_run, trigger as _trigger
# ⭐ Import vi HIEU UNG PHU: `poll_connector` goi `trigger.dang_ky(PiecePoll())`
#    luc import. Mot mo-dun dang ky ma khong ai import la mot mo-dun CHET — va
#    `trigger.tao()` se tu choi kind `PIECE_POLL` voi cau "loai chua dang ky".
from platform_core.workflow import poll_connector as _poll  # noqa: F401

log = logging.getLogger(__name__)

#: Spec §11.4. ⛔ Không tự tắt = một trigger hỏng gọi `tao_run` mỗi vòng động
#: cơ, mãi mãi — và mỗi lần gọi là một lần chạm CSDL của production.
TRAN_LOI_LIEN_TIEP = 5

#: Chính sách lỡ lịch. ⛔ Danh sách ĐÓNG: một chuỗi lạ ở đây sẽ rơi vào nhánh
#: mặc định và người soạn không bao giờ biết lịch của họ đang chạy kiểu nào.
BO_LO = ("chay_mot_lan", "bo_qua")


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _moc_ban(mo_dun, t: WorkflowTrigger,
             bay_gio: datetime) -> tuple[Optional[datetime], bool]:
    """`(mốc nên bắn, có phải BÙ không)`. `None` = loại này không tự bắn."""
    gan_nhat = getattr(mo_dun, "moc_gan_nhat", None)
    if not callable(gan_nhat):
        # Loại không có lịch (`MANUAL`/`API`/`WEBHOOK`) — `den_han()` không bao
        # giờ trả về chúng vì `next_fire_at` của chúng là `NULL`, nhưng nói ra
        # vẫn rẻ hơn là để một loại thứ tư im lặng bắn theo mốc sai.
        return None, False
    moc = gan_nhat(t.config or {}, bay_gio)
    if moc is None:
        return None, False
    # "BÙ" = mốc gần nhất đã đi QUA mốc mà lịch hẹn ⇒ có mốc bị lỡ ở giữa.
    return moc, bool(t.next_fire_at is not None and moc > t.next_fire_at)


def ban_mot(db, t: WorkflowTrigger, *, bay_gio: datetime) -> str:
    """Bắn MỘT trigger. Trả `"ban"` · `"bo_qua"` · `"khong"`.

    ⚠️ Không `commit()`: bên gọi quyết định ranh giới transaction. Cùng quy ước
       với `tao_run` (*"Một transaction… Không commit"*).
    """
    mo_dun = _trigger.SO_DANG_KY.get(t.kind)
    if mo_dun is None:
        raise ValueError(f"loai trigger chua dang ky: {t.kind!r}")
    moc, la_bu = _moc_ban(mo_dun, t, bay_gio)
    ke = mo_dun.lan_ke_tiep(t.config or {}, bay_gio)

    bo_lo = str((t.config or {}).get("bo_lo") or "chay_mot_lan")
    if bo_lo not in BO_LO:
        raise ValueError(f"`bo_lo` phai la mot trong {list(BO_LO)}: {bo_lo!r}")

    if moc is None or (la_bu and bo_lo == "bo_qua"):
        # ⛔ Vẫn phải đẩy lịch: đứng yên ở một mốc quá khứ nghĩa là mỗi vòng
        #    quét lại nhặt chính hàng này lên, mãi mãi.
        t.next_fire_at = ke
        db.flush()
        return "bo_qua" if moc is not None else "khong"

    # ⭐ HỢP ĐỒNG MỞ RỘNG (plan wf-v2 P6): một loại trigger tự tạo run của nó.
    #
    #    Mặc định ở dưới là *"một mốc lịch ⇒ MỘT run"*, và đó là hình dạng của
    #    CRON/SCHEDULE. Trigger **poll** của piece thì một mốc ra **N** run
    #    (N = số bản ghi mới), và N chỉ biết được SAU khi đã gọi ra ngoài.
    #
    # ⛔ Đó là một hình dạng khác, không phải một tham số khác — nên lõi hỏi
    #    mô-đun loại *"anh có tự bắn không"* thay vì mọc một nhánh
    #    `if kind == "PIECE_POLL"`. Đúng `G42`: thêm loại thứ bảy vẫn không
    #    sửa tệp này.
    ban_rieng = getattr(mo_dun, "ban", None)
    if callable(ban_rieng):
        ban_rieng(db, t, moc=moc, la_bu=la_bu)
        t.next_fire_at = ke
        t.last_fired_at = bay_gio
        t.loi_lien_tiep = 0
        db.flush()
        return "ban"

    wf = db.get(Workflow, t.workflow_id)
    if wf is None:
        raise ValueError(f"workflow {t.workflow_id!r} khong con")
    tao_run.tao_run(db, workflow=wf, owner_id=t.owner_id,
                    trigger_kind="cron" if t.kind == "CRON" else t.kind.lower(),
                    idempotency_key=khoa_idem.khoa_cron(t.id, moc),
                    inputs={"fired_at": moc.isoformat(), "bu": la_bu})
    t.next_fire_at = ke
    t.last_fired_at = bay_gio
    t.loi_lien_tiep = 0
    db.flush()
    return "ban"


def ban_den_han(db, *, gioi_han: int = 200,
                bay_gio: Optional[datetime] = None) -> dict:
    """Bắn MỌI trigger đã tới hạn. Một truy vấn gom, rồi từng hàng một.

    ⛔ Mỗi trigger được bọc `begin_nested()` RIÊNG: một hàng ném không được
       cuộn mất những hàng đã bắn trước nó trong cùng lượt — và trên PostgreSQL
       một câu vỡ đưa transaction vào trạng thái abort, nên "bắt rồi đi tiếp"
       mà không có savepoint là một transaction chết đi tiếp.
    """
    luc = bay_gio or _bay_gio()
    ra = {"da_ban": 0, "bo_qua": 0, "loi": 0}
    for t in _trigger.den_han(db, gioi_han=gioi_han, bay_gio=luc):
        try:
            with db.begin_nested():
                ket = ban_mot(db, t, bay_gio=luc)
        except Exception:                                # noqa: BLE001
            ra["loi"] += 1
            log.exception("trigger %s ban loi, bo qua luot nay", t.id)
            # ⚠️ Ghi bộ đếm SAU khi savepoint của chính lượt này đã cuộn: cuộn
            #    về một savepoint chỉ gỡ những gì ghi SAU nó, nên lần ghi ở đây
            #    sống sót — và savepoint của trigger KẾ TIẾP cũng không đụng
            #    tới nó. (Trên PostgreSQL, `ROLLBACK TO` còn là thứ đưa
            #    transaction ra khỏi trạng thái abort để câu này chạy được.)
            t.loi_lien_tiep = int(t.loi_lien_tiep or 0) + 1
            if t.loi_lien_tiep >= TRAN_LOI_LIEN_TIEP:
                t.enabled = False
                log.error("trigger %s tu tat sau %s lan loi lien tiep",
                          t.id, t.loi_lien_tiep)
            db.flush()
            continue
        if ket == "ban":
            ra["da_ban"] += 1
        elif ket == "bo_qua":
            ra["bo_qua"] += 1
    return ra


# ── `trigger.event` (spec §8.4) ─────────────────────────────────────────────

#: Ba dòng `workflow_event` nghĩa là *"một run đã kết thúc"* — và spec §8.4
#: chốt rằng đó là **toàn bộ** nguồn sự kiện trong phạm vi.
LOAI_KET_THUC = ("WorkflowCompleted", "WorkflowFailed", "WorkflowCancelled")


def _con_tro_cua(t: WorkflowTrigger) -> Optional[tuple]:
    """`(created_at, id)` đã xử lý tới, hoặc `None`.

    ⚠️ Con trỏ là một CẶP, không phải `created_at` một mình: nhiều run kết
       thúc trong cùng một micro-giây là chuyện thường trên máy nhanh, và một
       con trỏ chỉ có thời gian sẽ **bỏ sót** dòng thứ hai hoặc **lặp** dòng
       thứ nhất mãi mãi. Spec §8.4 khai đúng cặp này.
    """
    ct = t.con_tro or {}
    luc = ct.get("created_at")
    if not luc:
        return None
    try:
        goc = datetime.fromisoformat(str(luc))
    except ValueError:
        return None
    if goc.tzinfo is not None:
        goc = goc.replace(tzinfo=None)
    return goc, str(ct.get("id") or "")


def _khop(loc: str, ev) -> bool:
    from platform_core.workflow import ngon_ngu

    if not loc:
        return True
    du = ev.du_lieu or {}
    return bool(ngon_ngu.tinh(loc, {"event": {
        "id": ev.id, "run_id": ev.run_id, "loai": ev.loai,
        "status": str(du.get("status") or ""),
        "outputs": dict(du.get("outputs") or {})}}))


def ban_su_kien(db, *, gioi_han: int = 200) -> dict:
    """Quét `workflow_event` cho mọi `trigger.event` đang bật (spec §8.4).

    ⛔ **Không nghe sự kiện của chính workflow mình.** Một workflow bật
       `trigger.event` trên chính nó là một vòng có **tiền thật**: mỗi run sinh
       một sự kiện kết thúc, sự kiện ấy sinh một run. Không có phép chặn này
       thì một lần cấu hình nhầm tiêu sạch credit của khách trong một đêm.

    ⭐ HAI chốt khử trùng, và cần cả hai:
       - con trỏ keyset `(created_at, id)` — để không quét lại;
       - khoá `evt:<trigger_id>:<event_id>` — để một con trỏ **mất** (khôi phục
         CSDL, sửa tay) không thành một loạt run trùng.
    """
    from sqlalchemy import ColumnElement, select, tuple_

    from platform_core.models import WorkflowEvent

    ra = {"da_ban": 0, "bo_qua": 0, "loi": 0}
    triggers = list(db.execute(
        select(WorkflowTrigger).where(
            WorkflowTrigger.enabled.is_(True),
            WorkflowTrigger.kind == "EVENT")).scalars())
    for t in triggers:
        # Khai kieu TONG QUAT: mypy suy `list[BinaryExpression]` tu phan tu
        # dau, nhung danh sach nay con nhan mot so sanh `tuple_(...)` —
        # do la `ColumnElement[bool]`. Chu thich hep hon thuc te thi loi
        # bao o CHO THEM VAO, khong phai cho khai sai.  (gate 24/09)
        dk: list[ColumnElement[bool]] = [
            WorkflowEvent.loai.in_(LOAI_KET_THUC)]
        ct = _con_tro_cua(t)
        if ct is not None:
            dk.append(tuple_(WorkflowEvent.created_at, WorkflowEvent.id)
                      > tuple_(ct[0], ct[1]))
        hang = list(db.execute(
            select(WorkflowEvent).where(*dk)
            .order_by(WorkflowEvent.created_at, WorkflowEvent.id)
            .limit(max(1, int(gioi_han)))).scalars())
        if not hang:
            continue
        loc = str((t.config or {}).get("loc") or "")
        wf = db.get(Workflow, t.workflow_id)
        for ev in hang:
            try:
                with db.begin_nested():
                    _ban_mot_su_kien(db, t, wf, ev, loc=loc, ra=ra)
            except Exception:                            # noqa: BLE001
                ra["loi"] += 1
                log.exception("trigger %s: su kien %s loi", t.id, ev.id)
            # ⭐ Con trỏ tiến KỂ CẢ khi dòng này lỗi hay không khớp: đứng lại ở
            #    một dòng hỏng nghĩa là mọi dòng sau nó không bao giờ tới lượt.
            t.con_tro = {"created_at": _iso(ev.created_at), "id": ev.id}
        db.flush()
    return ra


def _ban_mot_su_kien(db, t: WorkflowTrigger, wf, ev, *, loc: str,
                     ra: dict) -> None:
    from platform_core.models import WorkflowRun

    if wf is None:
        return
    # ⛔ Sự kiện của CHÍNH workflow này ⇒ bỏ. Xem docstring `ban_su_kien`.
    nguon = db.get(WorkflowRun, ev.run_id)
    if nguon is not None and nguon.workflow_id == t.workflow_id:
        ra["bo_qua"] += 1
        return
    if not _khop(loc, ev):
        ra["bo_qua"] += 1
        return
    _run, moi = tao_run.tao_run(
        db, workflow=wf, owner_id=t.owner_id, trigger_kind="event",
        idempotency_key=khoa_idem.khoa_event(t.id, ev.id),
        inputs={"event": {"id": ev.id, "run_id": ev.run_id, "loai": ev.loai}})
    if moi:
        ra["da_ban"] += 1
        t.last_fired_at = _bay_gio()
    else:
        ra["bo_qua"] += 1


def _iso(luc: datetime) -> str:
    return (luc.replace(tzinfo=None) if luc.tzinfo else luc).isoformat()


__all__ = ["BO_LO", "LOAI_KET_THUC", "TRAN_LOI_LIEN_TIEP", "ban_den_han",
           "ban_mot", "ban_su_kien"]
