"""Đường tiền của một lượt chạy — **MỘT khoản giữ chỗ cho cả run**.

Nguồn: `23_24` dòng 33, và nó viết thẳng ra con số:

    QUOTE ──► trần chi phí tất định ──► APPROVAL ──► HOLD (1 lần/run)

## ⛔ VÌ SAO "1 LẦN/RUN" LÀ RÀNG BUỘC CHỨ KHÔNG PHẢI GỢI Ý

Mỗi node của một workflow rồi sẽ sinh một job, và **đường job đã thu tiền**
(`server/api/jobs.py` giữ chỗ theo báo giá của từng tool). Nếu run cũng giữ và
node cũng giữ thì khách trả **hai lần** cho cùng một việc.

Hôm nay chưa hỏng — `dieu_phoi.attempt()` mới ghi lượt thử, **chưa nộp job**.
Nên đây là lúc duy nhất đặt được cái rào trước khi cầu nối node→job ra đời:
`tests/test_965` chốt rằng một run có **đúng một** bút toán `CREDIT_HOLD`.

## 🔴 CÁI BẪY ĐÃ ĐO ĐƯỢC KHI NỐI VÀO SỔ

Sổ credit khoá theo `job_id`, và ta đưa `run_id` vào đó (cột là `String(36)`
không khoá ngoại, nên hợp lệ về cấu trúc). Nhưng `credit.giu_cho_treo` — bộ dò
**tiền treo**, thứ tồn tại vì *145 khoản treo / 28 ngày* — hỏi

    SELECT id FROM jobs WHERE id IN (khoa) AND status IN (QUEUED, RUNNING)

để biết khoá nào **còn sống**. Một `run_id` không nằm trong bảng `jobs`, nên
mọi lượt chạy **đang chạy bình thường** sẽ bị báo là tiền treo.

⇒ Nối sổ mà không dạy bộ dò biết `WorkflowRun` là biến một công cụ chẩn đoán
  thành một máy phát báo động giả — và nó sẽ kêu to nhất đúng lúc hệ chạy đúng
  nhất. `credit.khoa_con_song()` là chỗ vá.
"""
from __future__ import annotations

from platform_core import credit
from platform_core.models import WorkflowRun

__all__ = ["giu_cho_run", "ket_so_tien"]


def giu_cho_run(db, run: WorkflowRun) -> bool:
    """Giữ chỗ `estimated_max` cho cả lượt. Trả `True` nếu lượt này thật sự giữ.

    **Luỹ đẳng** theo `hold_id`: gọi lại không giữ thêm lần nữa. Đó là điều kiện
    để gọi được nó từ nhiều đường (API, giao diện, trigger) mà không phải nhớ
    đường nào đã gọi.

    ⚠️ KHÔNG commit — bên gọi commit cùng lần tạo run. Giữ chỗ và run phải cùng
       sống hoặc cùng chết; một khoản giữ không có run là đúng thứ `G16` mô tả.

    Ném `credit.ThieuCreditError` khi không đủ số dư, và ném **trước** khi có
    bất cứ gì được ghi — nên bên gọi rollback là sạch.
    """
    if run.hold_id:
        return False
    so = max(0, int(run.estimated_max or 0))
    if so == 0:
        # Trần 0 = không có gì để giữ. Vẫn KHÔNG đặt `hold_id`: `hold_id` nghĩa
        # là "có một khoản đang giữ", và đặt nó cho một khoản không tồn tại làm
        # `ket_so` đi quyết toán một thứ rỗng.
        return False
    credit.giu_cho(db, run.owner_id, so, run.id)
    # Khoá sổ CHÍNH LÀ `run.id`. Không sinh một id thứ hai: một khoá phái sinh
    # là một khoá có thể lệch khỏi thứ nó trỏ tới, và `String(36)` vừa khít một
    # uuid — thêm tiền tố nào cũng tràn cột (bài học `M-1`, 08/09).
    run.hold_id = run.id
    db.flush()
    return True


def ket_so_tien(db, run: WorkflowRun) -> bool:
    """Quyết toán hoặc hoàn khoản giữ của một run **đã kết thúc**.

    Gọi từ `ket_so.ket_so()` **trước** khi `hold_id` bị xoá — thứ tự ấy là toàn
    bộ vấn đề: xoá dấu trước rồi mới quyết toán thì một lần crash ở giữa để lại
    một khoản giữ **không còn ai biết nó thuộc về đâu**.

    ⭐ `SYSTEM_FAILURE` ⇒ **hoàn toàn bộ**. Đó là lý do trạng thái ấy phải tách
       khỏi `FAILED` (`G21`): lỗi nghiệp vụ thì khách đã tiêu tài nguyên thật và
       vẫn trả phần đã dùng; lỗi **của ta** thì không được bắt khách trả.
    """
    from platform_core.workflow.may_trang_thai import RUN_LOI_CUA_TA

    if not run.hold_id:
        return False
    if run.status in RUN_LOI_CUA_TA:
        credit.hoan(db, run.owner_id, run.id)
    else:
        # `quyet_toan` tự chặn thu quá phần đã giữ, và tự luỹ đẳng theo khoá.
        # Không kiểm lại ở đây: hai chỗ cùng cưỡng chế một luật là hai chỗ có
        # thể lệch nhau.
        credit.quyet_toan(db, run.owner_id, run.id, int(run.actual_cost or 0))
    return True
