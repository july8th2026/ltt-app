"""
image_input.py — kiểm ảnh người dùng tải lên, dùng chung cho mọi app.

Vì sao nằm ở `platform_core` chứ không ở một app: ba app cần đúng phép kiểm
này, và trước 2026-08-06 hai trong số đó **import thẳng vào module nội bộ của
app thứ ba**. App gọi vào ruột app khác nghĩa là gỡ hay đổi tên app đó sẽ làm
gãy hai app không liên quan.

Đây là kiểm **an toàn**, không phải nghiệp vụ của riêng app nào: MIME khai báo
phải khớp nội dung file thật. Trình duyệt gửi `Content-Type` gì cũng được, nên
tin nó là để lọt file không phải ảnh vào đường xử lý ảnh.
"""
from __future__ import annotations

import io

MAX_REFERENCE_BYTES = 8 * 1024 * 1024
MAX_REFERENCE_PIXELS = 24_000_000
ALLOWED_REFERENCE_MIME = {"image/png", "image/jpeg", "image/webp"}


def validate_reference(data: bytes, content_type: str) -> tuple[str, tuple[int, int]]:
    """Kiểm ảnh đã giải mã, KHÔNG chỉ tin MIME của trình duyệt.

    Trả về (MIME thật, (rộng, cao)). Ném `ValueError` kèm thông báo tiếng Việt
    đọc được cho người dùng — caller đưa thẳng ra giao diện.
    """
    if not data:
        raise ValueError("Ảnh tham chiếu rỗng.")
    if len(data) > MAX_REFERENCE_BYTES:
        raise ValueError("Ảnh tham chiếu vượt giới hạn 8 MB.")
    mime = (content_type or "").lower()
    if mime not in ALLOWED_REFERENCE_MIME:
        raise ValueError("Ảnh tham chiếu chỉ nhận PNG, JPEG hoặc WebP.")
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            actual = Image.MIME.get(image.format, "").lower()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("File tham chiếu không phải ảnh hợp lệ.") from exc
    if actual not in ALLOWED_REFERENCE_MIME or actual != mime:
        raise ValueError("MIME ảnh tham chiếu không khớp nội dung file.")
    if width < 64 or height < 64 or width * height > MAX_REFERENCE_PIXELS:
        raise ValueError("Kích thước ảnh tham chiếu không hợp lệ.")
    return actual, (width, height)
