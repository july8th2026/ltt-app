"""Hạn mức của cửa trigger (spec §7.3) — đếm trên CSDL, không trong bộ nhớ.

🔴 VÌ SAO KHÔNG PHẢI MỘT BỘ ĐẾM TRONG TIẾN TRÌNH

Một `dict` đếm theo `trigger_id` là cách rẻ nhất và là cách **sai nhất ở đúng
lúc cần đúng**: web chạy nhiều worker, và mỗi worker sẽ cho qua trọn 60 lượt
của riêng nó. Hạn mức 60/phút thành 60×N/phút đúng vào lúc ai đó đang bắn dồn
— tức lúc duy nhất hạn mức có việc để làm. Bộ đếm cũng mất sạch mỗi lần
restart, và worker restart **13,6 lần/ngày** trên máy này.

⇒ Đếm thứ **đã có thật trong CSDL**: số `workflow_run` mà chính trigger này đã
  tạo trong 60 giây qua. Một truy vấn, đi vào `ix_workflow_run_owner_created`
  (`(owner_id, created_at)`), và mọi tiến trình thấy cùng một con số.

⚠️ Phép đếm này đếm **run đã tạo**, nên một cú gửi TRÙNG (khớp khoá khử trùng,
   không tạo run mới) **không** tốn hạn mức. Đúng như vậy: hạn mức tồn tại để
   chặn *tạo việc*, và một lần gửi lại không tạo việc nào.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from platform_core.models import WorkflowRun, WorkflowTrigger
from platform_core.workflow import trigger as _trigger

#: Cửa sổ trượt của hạn mức webhook. Spec §7.3 khai hạn theo **phút**.
CUA_SO_S = 60


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def dem_webhook_gan_day(db, t: WorkflowTrigger,
                        bay_gio: datetime | None = None) -> int:
    """Số run mà trigger này đã tạo trong `CUA_SO_S` giây qua."""
    tu = (bay_gio or _bay_gio()) - timedelta(seconds=CUA_SO_S)
    return int(db.execute(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.owner_id == t.owner_id,
            WorkflowRun.created_at >= tu,
            # Tiền tố khoá do `khoa_idem.khoa_webhook` sinh: `wh:<trigger_id>:`.
            # Lọc theo tiền tố chứ không theo `workflow_id`, vì một workflow có
            # thể mang nhiều trigger webhook và hạn mức là **của từng trigger**.
            WorkflowRun.idempotency_key.startswith(f"wh:{t.id}:"))).scalar() or 0)


def vuot_han_webhook(db, t: WorkflowTrigger,
                     bay_gio: datetime | None = None) -> bool:
    return dem_webhook_gan_day(db, t, bay_gio) >= \
        _trigger.WEBHOOK_MOI_PHUT_MOI_TRIGGER


__all__ = ["CUA_SO_S", "dem_webhook_gan_day", "vuot_han_webhook"]
