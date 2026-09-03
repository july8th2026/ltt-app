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

    # ── Thêm 02/09/2026, sau một phép ĐO A/B, không phải theo linh cảm ──────
    #
    # Cách đo: sinh CÙNG một câu hai lần — một lần để nguyên viết tắt, một lần
    # tự tay giải ra — rồi cho ASR (faster-whisper `small`) nghe lại cả hai.
    # Viết tắt nào mà bản ĐỂ NGUYÊN bị nghe ra rác, còn bản ĐÃ GIẢI được nghe
    # đúng, thì mới vào bảng này.
    #
    #   HTTPS   de nguyen -> "hat TTFS"          da giai -> "HTTPS"      ✓
    #   MP3     de nguyen -> "muu phe 3"         da giai -> "MP3"        ✓
    #   WAV     de nguyen -> "5v kep AV"         da giai -> "Quap"       ✓
    #   HTTP    de nguyen -> "hat tro tim bi"    da giai -> "hat te te be" ✓
    "HTTPS": "hát tê tê pê ét",
    "HTTP": "hát tê tê pê",
    "MP3": "em pê ba",
    "WAV": "quáp",
}

#: 🔴 ĐÃ THỬ VÀ **LOẠI** — ghi lại để không ai "sửa" chúng lần nữa.
#:
#:    Cùng phép đo A/B ngày 02/09/2026, hai ứng viên dưới đây khiến kết quả
#:    **TỆ ĐI**, vì engine vốn đã đọc chúng đúng:
#:
#:      RTX    de nguyen -> "RTX 3090"  ✓     da giai ("a ro te ich") -> "AZTX"     ✗
#:      HTML   de nguyen -> "html"      ✓     da giai ("hat te em eo") -> "hat, kem L" ✗
#:
#: ⭐ Đây chính là lý do luật 1 tồn tại. Năm ứng viên, **hai** trong số đó sẽ
#:    làm hỏng một thứ đang chạy tốt — và cả hai đều "trông cần sửa" y hệt bốn
#:    cái kia. Không có phép đo thì không cách nào phân biệt.
#:
#: ⚠️ Và một cái bẫy của phép đo: ở bài `thuat_ngu` trong bộ đo tổng, ASR nghe
#:    `RTX` thành "otx" — nếu dừng ở đó thì đã kết luận RTX hỏng. Đo riêng một
#:    câu ngắn thì nó đúng. **Một lần nghe sai trong câu dài không đủ để kết
#:    tội một từ.**
DA_THU_VA_LOAI = ("RTX", "HTML")

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
