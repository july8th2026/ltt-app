"""
turnstile.py — kiểm tra Cloudflare Turnstile phía máy chủ (Q20).

Turnstile chống bot đăng ký hàng loạt để ăn credit dùng thử. Widget ở trình
duyệt sinh một token; token đó **phải được máy chủ xác minh lại** với Cloudflare
— nếu chỉ tin widget hiển thị là xong thì bot bỏ qua widget, gửi thẳng form.

Bỏ qua có kiểm soát: khi chưa đặt `TURNSTILE_SECRET_KEY` (máy phát triển,
test), `bat_buoc()` trả False và `xac_minh()` cho qua. Nhờ vậy luồng đăng ký
chạy và test được mà không cần khoá thật; ở production đặt khoá vào là bật.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

_TIMEOUT_S = 10.0
_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def site_key() -> str:
    """Khoá công khai, nhúng vào trang. Rỗng nghĩa là chưa bật Turnstile."""
    return (os.environ.get("TURNSTILE_SITE_KEY") or "").strip()


def bat_buoc() -> bool:
    """True khi Turnstile đã cấu hình đủ (có cả khoá bí mật) và phải kiểm."""
    return bool((os.environ.get("TURNSTILE_SECRET_KEY") or "").strip())


def xac_minh(token: str, *, remote_ip: str = "") -> bool:
    """Xác minh token với Cloudflare.

    - Chưa cấu hình khoá bí mật → True (bỏ qua có kiểm soát, xem docstring module).
    - Có cấu hình mà token rỗng/sai/lỗi mạng → False (từ chối, an toàn mặc định).
    """
    secret = (os.environ.get("TURNSTILE_SECRET_KEY") or "").strip()
    if not secret:
        return True
    if not token:
        return False

    import httpx

    data = {"secret": secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        resp = httpx.post(_VERIFY_URL, data=data, timeout=_TIMEOUT_S)
        return bool(resp.json().get("success"))
    except Exception as exc:
        # Lỗi mạng tới Cloudflare → từ chối. Cho qua khi không xác minh được
        # nghĩa là vô hiệu hoá Turnstile đúng lúc cần nó nhất.
        log.warning("Turnstile verify loi: %s", type(exc).__name__)
        return False
