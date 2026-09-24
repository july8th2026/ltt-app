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


__all__ = ["BO_LO", "TRAN_LOI_LIEN_TIEP", "ban_den_han", "ban_mot"]
