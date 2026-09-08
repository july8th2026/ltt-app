"""Hệ con `finally`: kết sổ credit và nhả giữ chỗ — ĐÚNG MỘT LẦN.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §6`.

🔴 **Vì sao hệ con này tồn tại — một con số đo được trên production:**

    145 dong "GIU CHO TREO: <n> khoan, <n> credit cua khach dang bi giu"
        trong 28 ngay log worker            (`01 §A`, `G16` -> `G32`)

Khoản giữ chỗ treo là **tiền của khách bị giam**: số dư hiển thị thấp hơn thực
tế, và không lệnh nào của khách gỡ được. Nó không gây lỗi, không gây cảnh báo —
nó chỉ **im lặng** cho tới khi ai đó đọc log.

⭐ Nguyên nhân là **hình dạng**, không phải sự cẩu thả: hôm nay `_terminal_status`
   ghi trạng thái ở một chỗ, `budget.settle` kết sổ ở chỗ khác, và giữa hai chỗ
   là một cửa sổ. Worker restart **13,6 lần/ngày** (`01 §A.6`) nên cửa sổ ấy
   được thử 13,6 lần mỗi ngày.

⇒ Bản vá không phải "nhớ gọi settle" mà là **gộp hai thao tác vào một
  transaction**: `may_trang_thai.chuyen_run()` gọi thẳng vào đây. Không còn cửa
  sổ nào để một lần restart lọt vào.
"""
from __future__ import annotations

from datetime import datetime, timezone

from platform_core.models import WorkflowRun


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def da_ket_so(db, run_id: str) -> bool:
    run = db.get(WorkflowRun, run_id)
    return bool(run is not None and run.ket_so_luc is not None)


def ket_so(db, run_id: str, *, ly_do: str = "") -> bool:
    """Kết sổ một run đã kết thúc. Trả `True` nếu lượt này thật sự kết sổ.

    **Luỹ đẳng.** Gọi lại — bởi bộ dọn nền, bởi một lượt thử lại, bởi người vận
    hành — không làm gì thêm và không trả `True` lần thứ hai. Đó là điều kiện
    để có thể gọi nó ở **nhiều** chỗ mà vẫn an toàn, và một hệ con chỉ an toàn ở
    một chỗ thì sớm muộn cũng bị bỏ sót ở chỗ thứ hai.

    ⛔ KHÔNG commit. Bên gọi commit cùng lần chuyển trạng thái — đó chính là
       điều làm `M10` đạt được, nên đừng "tiện tay" thêm `db.commit()` vào đây.

    ## Ba việc, theo thứ tự

    1. **Chốt chi phí thật** = tổng `cost_credit` của các ảnh chụp **hợp lệ**.
       Hàng `is_valid=False` là một lần chuyển *không xảy ra* — tính tiền cho nó
       là thu tiền một việc chưa từng chạy.
    2. **Lỗi CỦA TA thì không thu.** `SYSTEM_FAILURE` ⇒ `actual_cost = 0`. Đây
       là lý do trạng thái ấy phải tách khỏi `FAILED` (`G21`): lỗi nghiệp vụ thì
       khách đã tiêu tài nguyên thật và vẫn thu phần đã dùng.
    3. **Nhả giữ chỗ.** `hold_id = ""`.
    """
    run = db.get(WorkflowRun, run_id)
    if run is None:
        return False
    from platform_core.workflow.may_trang_thai import (RUN_KET_THUC,
                                                       RUN_LOI_CUA_TA,
                                                       tong_chi_phi_hop_le)
    if run.status not in RUN_KET_THUC:
        return False
    if run.ket_so_luc is not None:
        return False

    run.actual_cost = (0 if run.status in RUN_LOI_CUA_TA
                       else tong_chi_phi_hop_le(db, run_id))
    run.hold_id = ""
    run.ket_so_luc = _bay_gio()
    run.ly_do_ket_so = (ly_do or f"run -> {run.status}")[:200]
    db.flush()
    return True
