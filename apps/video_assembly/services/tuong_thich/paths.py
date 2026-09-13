"""`ensure_dir` / `safe_name` — chữ ký của `bot_dungvideo/utils/paths.py`."""
from __future__ import annotations

import os

#: Ký tự Windows không cho trong tên tệp, cộng toàn bộ ký tự điều khiển.
#:
#: ⚠️ Viết bằng tập hợp chứ không bằng biểu thức chính quy, và đó không phải sở
#:    thích: một mẫu regex cho tập này cần bốn lớp thoát lồng nhau, và bản đầu
#:    của tệp này **đã sinh ra một byte null** vì đúng chuyện ấy. Tập hợp đọc
#:    được bằng mắt và không có gì để thoát.
CAM = set('<>:"/|?*' + chr(92)) | {chr(c) for c in range(32)}


def ensure_dir(duong: str) -> str:
    os.makedirs(duong, exist_ok=True)
    return duong


def safe_name(ten: str) -> str:
    """Tên tệp an toàn trên Windows.

    Giữ nguyên hành vi của bản legacy: thay ký tự cấm, gộp khoảng trắng, bỏ dấu
    chấm và khoảng trắng ở cuối (Windows không cho), và **không rỗng hoá** — một
    tên rỗng làm `os.path.join` trỏ vào chính thư mục cha, tức ghi đè lung tung.
    """
    s = "".join("_" if c in CAM else c for c in str(ten or "")).strip()
    s = " ".join(s.split()).rstrip(". ")
    return s or "khong_ten"
