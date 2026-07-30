"""
Handler job của app demo — hàm này là thứ worker gọi.

Hợp đồng của một handler (mọi app đều theo đúng khuôn này):

    def handle(params: dict, ctx: JobContext) -> dict

    params  : tham số người dùng gửi lên, đã được validate ở routes.py
    ctx     : tiện ích do worker cấp — báo tiến độ, đọc/ghi file
    trả về  : dict kết quả, sẽ được lưu vào job và hiện cho người dùng

Ba quy tắc bắt buộc, và đều xuất phát từ chuyện tiền:

1. **Idempotent.** Worker có thể gọi lại cùng một job (mất mạng giữa đường,
   worker chết rồi job hết hạn khoá). Gọi hai lần không được tạo ra hai lần
   tính phí hay hai lần gọi API.
2. **Báo tiến độ.** Job dài mà không báo gì thì người dùng tưởng treo, bấm
   lại, và bạn trả tiền API hai lần.
3. **Ném exception khi thất bại, đừng trả về dict rỗng.** Nền tảng dựa vào
   exception để hoàn credit đã giữ. Trả về êm ru nghĩa là job "thành công" và
   tiền vẫn bị trừ.
"""
from __future__ import annotations


def handle(params: dict, ctx=None) -> dict:
    """Đảo ngược chuỗi ký tự. Cố tình tầm thường — xem docstring manifest."""
    text = str(params.get("text", ""))
    if not text.strip():
        # Ném lỗi để nền tảng hoàn lại credit đã giữ.
        raise ValueError("Chưa nhập nội dung để xử lý.")

    if ctx is not None:
        ctx.progress(50, "đang xử lý")

    reversed_text = text[::-1]

    if ctx is not None:
        ctx.progress(100, "xong")

    return {
        "input_length": len(text),
        "output": reversed_text,
        "words": len(text.split()),
    }
