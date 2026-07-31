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

from cryptography.fernet import Fernet, InvalidToken

# Salt riêng cho kho API key — KHÁC salt của token FB/TikTok (fb_bot_token_salt).
_SALT = b"ltt_api_key_salt_v1_2026"


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


def _fernet() -> Fernet:
    digest = hashlib.sha256(_material() + _SALT).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


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


def preview(plaintext: str) -> str:
    """4 ký tự cuối để hiển thị an toàn (không lộ secret). Rỗng nếu quá ngắn."""
    p = plaintext or ""
    return f"...{p[-4:]}" if len(p) >= 4 else "..."
