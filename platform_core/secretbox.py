"""
secretbox.py — mã hoá AT-REST cho secret của nền tảng (API key, H8).

Dùng Fernet (AES-128-CBC + HMAC-SHA256), khoá DẪN XUẤT từ
`LTT_TOKEN_ENCRYPTION_KEY` — CÙNG khoá at-rest của nền tảng như token FB/TikTok
(`core/token_store.py`), nhưng **salt RIÊNG** nên hai kho không dùng chung khoá
Fernet: lộ một kho không mở được kho kia.

Vì sao có file này (thay vì gọi vào core/token_store): giữ `platform_core` độc
lập với `core/` (miền FB/TikTok). Đây chỉ là lớp mã hoá thuần, không biết gì về
app nào.

**Production PHẢI đặt `LTT_TOKEN_ENCRYPTION_KEY`** (đã đặt trong secrets/app.env)
để secret sống sau khi cài lại máy. Khi không đặt (một số test/dev), khoá suy từ
định danh máy — vẫn round-trip được trong cùng tiến trình, nhưng KHÔNG bền qua
cài lại (đúng như thiết kế token_store).
"""
from __future__ import annotations

import base64
import hashlib
import os
import platform
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

# Salt riêng cho kho API key — KHÁC salt của token FB/TikTok (fb_bot_token_salt).
_SALT = b"ltt_api_key_salt_v1_2026"

#: Env mang các khoá **ĐỜI CŨ**, mới nhất trước, ngăn bằng `,` hoặc xuống dòng.
#: `_FILE` cùng nghĩa, để khoá không phải đi qua bảng env của tiến trình.
ENV_KHOA_CU = "LTT_TOKEN_ENCRYPTION_KEYS_CU"
ENV_KHOA_CU_FILE = "LTT_TOKEN_ENCRYPTION_KEYS_CU_FILE"


class SecretBoxError(Exception):
    pass


def _material() -> bytes:
    """Nguyên liệu khoá: ưu tiên LTT_TOKEN_ENCRYPTION_KEY (env hoặc _FILE), rồi
    mới đến định danh máy (chỉ hợp dev). Không bao giờ log."""
    raw = os.environ.get("LTT_TOKEN_ENCRYPTION_KEY", "").strip()
    if raw:
        return raw.encode("utf-8")
    key_file = os.environ.get("LTT_TOKEN_ENCRYPTION_KEY_FILE", "").strip()
    if key_file and os.path.exists(key_file):
        material = Path(key_file).read_bytes().strip()
        if material:
            return material
    return f"{platform.node()}_{platform.system()}_{platform.machine()}".encode("utf-8")


def _materials_cu() -> list[bytes]:
    """Nguyên liệu của các khoá ĐỜI CŨ, theo thứ tự mới → cũ.

    ⭐ Xoay khoá cần **một khoảng chồng lấn**: khoá mới đứng đầu để mọi lần ghi
       dùng nó, còn khoá cũ vẫn phải đọc được hàng chưa kịp mã hoá lại. Bỏ khoá
       cũ ra ngay lúc đổi là tự xoá dữ liệu của chính mình.
    """
    tho = os.environ.get(ENV_KHOA_CU, "")
    duong = os.environ.get(ENV_KHOA_CU_FILE, "").strip()
    if not tho.strip() and duong and os.path.exists(duong):
        tho = Path(duong).read_text(encoding="utf-8")
    ra: list[bytes] = []
    for dong in tho.replace(",", chr(10)).splitlines():
        d = dong.strip()
        if d and not d.startswith("#") and d.encode("utf-8") not in ra:
            ra.append(d.encode("utf-8"))
    return ra


def _khoa_fernet(material: bytes) -> Fernet:
    """⛔ Dẫn xuất KHÔNG ĐỔI so với bản một-khoá: hàng đã ghi trước 24/09/2026
    phải đọc được y nguyên, nếu không việc "nâng cấp" chính là mất dữ liệu."""
    digest = hashlib.sha256(material + _SALT).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _fernet() -> MultiFernet:
    """`MultiFernet` — ADOPT `cryptography`, ⛔ không tự viết vòng thử khoá.

    Tài liệu `cryptography` (`fernet.rst`, lớp `MultiFernet`): ghi **luôn** bằng
    khoá đầu tiên, đọc thì thử lần lượt cả danh sách, và `rotate()` giải mã bằng
    bất kỳ khoá nào rồi mã hoá lại bằng khoá đầu **giữ nguyên dấu thời gian**.
    Đó đúng là ba thứ một lần xoay khoá cần, nên không có lý do viết lại.
    """
    khoa = [_khoa_fernet(_material())]
    khoa += [_khoa_fernet(m) for m in _materials_cu()]
    return MultiFernet(khoa)


def so_khoa() -> int:
    """Số khoá đang nạp (1 = chưa có đời cũ nào). Không lộ khoá nào cả."""
    return 1 + len(_materials_cu())


def ma_hoa(plaintext: str) -> str:
    """Mã hoá một secret → chuỗi token Fernet (an toàn lưu DB)."""
    if plaintext is None:
        raise SecretBoxError("khong the ma hoa None")
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def giai_ma(token: str) -> str:
    """Giải mã token Fernet → secret thô. Ném SecretBoxError nếu sai khoá/hỏng."""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError) as e:
        raise SecretBoxError(f"giai ma that bai: {type(e).__name__}")


def xoay(token: str) -> str:
    """Mã hoá lại một token bằng khoá ĐỜI MỚI (khoá đầu danh sách).

    ⛔ Không phải `giai_ma` rồi `ma_hoa`: `MultiFernet.rotate` giữ nguyên dấu
       thời gian của token gốc, và bản rõ không bao giờ thành một biến Python
       của nơi gọi.
    """
    try:
        return _fernet().rotate(token.encode("utf-8")).decode("ascii")
    except (InvalidToken, ValueError, TypeError) as e:
        raise SecretBoxError(f"xoay khoa that bai: {type(e).__name__}")


def preview(plaintext: str) -> str:
    """4 ký tự cuối để hiển thị an toàn (không lộ secret). Rỗng nếu quá ngắn."""
    p = plaintext or ""
    return f"...{p[-4:]}" if len(p) >= 4 else "..."
