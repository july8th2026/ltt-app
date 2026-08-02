"""
usage_rate_limit.py — rate-limit per-USER cho endpoint ứng dụng (chống script/lạm dụng).

Khác `auth/rate_limit.py` (giới hạn ĐĂNG NHẬP theo IP). Đây giới hạn số POST mỗi user
để một dev không script hạ endpoint tạo / endpoint MIỄN PHÍ (translate/estimate/preview/
upload-url — đốt quota provider, mint presigned vô hạn). Trung tâm ở middleware → KHÔNG
sửa từng app, tự áp cho mọi app hiện có + tương lai.

In-memory, một tiến trình web (ADR-005). Khoá theo user (sid/username), fallback IP.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from server.auth.rate_limit import RateLimiter

# Đuôi path "miễn phí / đốt quota ngoài" — siết chặt hơn (dễ bị script lạm dụng nhất).
_EXPENSIVE_SUFFIXES = ("/translate", "/preview", "/estimate", "/upload-url",
                       "/plan", "/approve", "/runs", "/again")

# Path KHÔNG áp (có limiter riêng theo IP, hoặc là auth flow) — tránh double-limit.
_EXEMPT_PREFIXES = ("/login", "/register", "/logout", "/forgot-password",
                    "/reset-password", "/health")


def _user_key(request) -> str:
    try:
        s = request.session
        uid = s.get("sid") or s.get("user")
        if uid:
            return f"u:{uid}"
    except Exception:  # noqa: BLE001
        pass
    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


class UsageRateLimitMiddleware(BaseHTTPMiddleware):
    """Giới hạn POST/user. General cho mọi POST app; tight cho endpoint miễn phí."""

    def __init__(self, app, *, general_per_min: int = 120, expensive_per_min: int = 30):
        super().__init__(app)
        self._general = RateLimiter(max_attempts=general_per_min, window_seconds=60.0)
        self._expensive = RateLimiter(max_attempts=expensive_per_min, window_seconds=60.0)

    async def dispatch(self, request, call_next):
        if request.method != "POST":
            return await call_next(request)
        path = request.url.path
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)
        key = _user_key(request)
        expensive = path.endswith(_EXPENSIVE_SUFFIXES)
        limiter = self._expensive if expensive else self._general
        if not limiter.allow(f"{key}|{'exp' if expensive else 'gen'}"):
            return JSONResponse(
                {"ok": False, "error": "Bạn thao tác quá nhanh — thử lại sau ít giây."},
                status_code=429)
        return await call_next(request)
