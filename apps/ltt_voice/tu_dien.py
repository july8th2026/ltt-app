"""
tu_dien.py — từ điển phát âm cấp sản phẩm.

⭐ VÌ SAO CẦN, VÀ CON SỐ ĐỨNG SAU NÓ.

   Upstream issue #168, người dùng báo trực tiếp: *"phát âm `ch` -> `tr` và ngược
   lại: ví dụ như 'chưởng môn' -> 'trưởng môn'"*. Đó không phải một lỗi ta sửa
   được ở tầng âm vị — `sea-g2p` đã làm đúng việc của nó, chỗ trượt nằm trong
   model. Thứ ta làm được là **viết lại đầu vào** cho những từ đã biết là hay
   trượt.

⛔ BA LUẬT KHI THÊM MỘT MỤC:

   1. **Chỉ thêm khi đã NGHE THẤY sai**, không thêm theo linh cảm. Mỗi mục là một
      phép thay không thể tắt cho mọi khách; thêm nhầm là làm hỏng một từ vốn
      đang đúng.
   2. **Ghi lý do**, kèm ngày nghe thấy. Một bảng thay thế không có lý do sẽ
      không bao giờ xoá được, vì không ai dám.
   3. **Khớp theo BIÊN TỪ**, không khớp chuỗi con. Không có `\\b` thì "cha" trong
      "chai" cũng bị thay.

⚠️ Đây là bảng CHUNG cho mọi khách. Từ điển riêng của một người (tên công ty, tên
   nhân vật) đi qua tham số `them=` — nó không được lẫn vào đây.
"""
from __future__ import annotations

import re

#: `mẫu (đã hạ chữ) -> cách viết lại`. Thêm mục thì đọc ba luật ở docstring.
#:
#: Bảng khởi điểm cố ý **rỗng phần đoán**: mỗi mục dưới đây phải chờ V1 nghe thật
#: rồi mới được thêm. Để sẵn khuôn để lần sau không ai phải nghĩ lại định dạng.
BANG_CHUNG: dict = {
    # "chưởng môn": ("chưởng môn", "2026-08-30 #168: nghe ra 'trưởng môn'"),
}

#: Viết tắt kỹ thuật hay gặp trong kịch bản sáng tạo. Đây **không** phải đoán:
#: một chuỗi viết hoa không có cách đọc mặc định, model sẽ đánh vần hoặc bịa.
VIET_TAT: dict = {
    "AI": "ây ai",
    "API": "ây pi ai",
    "CPU": "xi pi diu",
    "GPU": "gi pi diu",
    "USB": "diu ét bi",
    "PDF": "pi đi ép",
    "URL": "diu a eo",
    "TV": "ti vi",
    "OK": "ô kê",
}

_CACHE: dict = {}


def _mau(tu: str) -> re.Pattern:
    m = _CACHE.get(tu)
    if m is None:
        m = re.compile(r"(?<!\w)" + re.escape(tu) + r"(?!\w)", re.IGNORECASE)
        _CACHE[tu] = m
    return m


def ap_dung(text: str, *, them: dict | None = None) -> str:
    """Thay theo bảng chung + bảng riêng của khách. Bảng riêng thắng."""
    t = text or ""

    for tu, thay in VIET_TAT.items():
        # Viết tắt khớp PHÂN BIỆT HOA-THƯỜNG: "AI" là viết tắt, "ai" là đại từ
        # tiếng Việt và tuyệt đối không được đọc thành "ây ai".
        t = re.sub(r"(?<!\w)" + re.escape(tu) + r"(?!\w)", thay, t)

    for tu, muc in BANG_CHUNG.items():
        thay = muc[0] if isinstance(muc, (tuple, list)) else muc
        t = _mau(tu).sub(thay, t)

    for tu, thay in (them or {}).items():
        if not tu:
            continue
        t = _mau(str(tu)).sub(str(thay), t)

    return t
