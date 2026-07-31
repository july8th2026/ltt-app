"""
access_middleware.py — chặn quyền app ở tầng route (H1.4).

Vì sao là middleware chứ không phải dependency gắn từng route: chặn phải phủ
**mọi** đường vào một app, kể cả khi người dùng gõ thẳng URL, và phải làm được
mà **không sửa từng app** (giữ hợp đồng: nền tảng không biết trước app nào tồn
tại). Một middleware đọc registry rồi ánh xạ path → app làm đúng điều đó cho cả
app mount động lẫn các route đặc cách của socialbot.

Thứ tự middleware: lớp này phải chạy **sau** SessionMiddleware để đọc được
`request.session`. Trong Starlette, middleware thêm TRƯỚC là lớp trong (chạy
sau) — nên `create_app` add lớp này trước khi add SessionMiddleware.

Fail-open có chủ ý: khi chưa có CSDL, không tra được user, hay bất kỳ lỗi nào,
middleware **cho qua**. Ở giai đoạn này mặc định quyền là "mở" (Q25) nên cho
qua = đúng mặc định; và admin-env (đường lui khi DB hỏng) không bao giờ bị lớp
này chặn. Chốt chặn tiền thật vẫn là credit, không phải lớp này.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from server.templating import templates


class AccessControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        chan = self._kiem_tra(request)
        if chan is not None:
            return chan
        return await call_next(request)

    def _kiem_tra(self, request: Request):
        # Chỉ quan tâm request thuộc về một app. Mọi thứ khác cho qua ngay.
        try:
            loaded = getattr(request.app.state, "loaded_apps", None) or []
            from platform_core.app_access import app_cho_path
            slug = app_cho_path(request.url.path, loaded)
        except Exception:
            return None
        if slug is None:
            return None

        # admin-env (đường lui) là admin → không bao giờ bị chặn ở đây.
        try:
            session = request.session
        except Exception:
            return None
        if session.get("user"):
            return None
        sid = session.get("sid")
        if not sid:
            return None      # ẩn danh → require_login của route lo phần đăng nhập

        # Tra user CSDL. Bất kỳ trục trặc nào → fail-open.
        try:
            from platform_core.app_access import HIDDEN, LOCKED, muc_quyen
            from platform_core.db import get_session
            from platform_core.users import lay_user_tu_phien
            gen = get_session()
            db = next(gen)
            try:
                user = lay_user_tu_phien(db, sid)
                if user is None:
                    return None
                level = muc_quyen(db, user, slug)
                db.commit()
            finally:
                try:
                    next(gen)
                except StopIteration:
                    pass
        except Exception:
            return None

        if level == HIDDEN:
            # Ẩn nghĩa là "không tồn tại với người này" → 404, không 403.
            # 403 xác nhận app có thật; 404 thì không tiết lộ gì.
            return self._trang_loi(request, 404,
                                   "Không tìm thấy trang bạn yêu cầu.")
        if level == LOCKED:
            return self._trang_loi(request, 403,
                                   "Công cụ này chưa mở cho tài khoản của bạn.")
        return None

    def _trang_loi(self, request: Request, code: int, message: str) -> Response:
        return templates.TemplateResponse(
            request, "error.html",
            {"code": code, "message": message,
             "correlation_id": getattr(request.state, "correlation_id", "")},
            status_code=code,
        )
