"""
FastAPI application factory (P3).

No publishing behavior lives here yet (P4/P5). This module only builds the
authenticated dashboard shell + health/readiness endpoints. Must never
import gui.* or customtkinter — verified by test, same boundary as P1's
worker_main.py.
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from core.settings import Environment, load_settings
from server.auth.rate_limit import RateLimiter
from server.routes import accounts as accounts_routes
from server.routes import auth as auth_routes
from server.routes import dashboard as dashboard_routes
from server.routes import health as health_routes
from server.routes import manual as manual_routes
from server.routes import monitor as monitor_routes
from server.routes import oauth as oauth_routes
from server.routes import sheet as sheet_routes
from server.routes import settings as settings_routes
from server.routes import status as status_routes
from server.routes import workers as workers_routes
from server.settings import load_server_settings
from server.templating import templates


_ERROR_MESSAGES = {
    400: "Yêu cầu không hợp lệ.",
    401: "Bạn cần đăng nhập để xem trang này.",
    403: "Bạn không có quyền truy cập trang này.",
    404: "Không tìm thấy trang bạn yêu cầu.",
    429: "Bạn thao tác quá nhanh — vui lòng thử lại sau.",
    500: "Máy chủ gặp lỗi khi xử lý yêu cầu.",
}

SESSION_MAX_AGE_SECONDS = 8 * 60 * 60  # 8h idle expiry


# ── Maintenance daemon ─────────────────────────────────────────────────────────
# Only `gui/main_window.py` ever started this daemon. With the desktop gone,
# nothing would prune old content_history / page_health records or probe the
# Meta + TikTok app status, so retention (DATA_RETENTION_POLICY.md) would
# silently stop being enforced. The web app owns it now.


@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.maintenance = None
    cs = getattr(app.state, "core_settings", None)
    if cs is not None:
        try:
            from core.maintenance import MaintenanceDaemon
            daemon = MaintenanceDaemon(config=dict(cs.config))
            daemon.start()
            app.state.maintenance = daemon
        except Exception:
            # A failed sweep scheduler must not stop the dashboard from
            # serving — the operator needs it most when something is wrong.
            logging.getLogger(__name__).warning(
                "MaintenanceDaemon failed to start", exc_info=True)
    try:
        yield
    finally:
        daemon = getattr(app.state, "maintenance", None)
        if daemon is not None:
            daemon.stop()


def create_app(*, env: dict | None = None) -> FastAPI:
    server_settings = load_server_settings(env)

    # FastAPI's interactive docs enumerate every route and parameter. On a
    # public dashboard that is free reconnaissance for an attacker, so they
    # are development-only. Health endpoints stay open by design (the
    # reverse proxy and service manager probe them).
    expose_docs = server_settings.environment is Environment.DEVELOPMENT

    app = FastAPI(
        title="LTT AI Studio",
        lifespan=_lifespan,
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        openapi_url="/openapi.json" if expose_docs else None,
    )
    app.state.server_settings = server_settings
    # Per-app so separate app instances never share login-attempt counters.
    app.state.login_rate_limiter = RateLimiter(max_attempts=5, window_seconds=60.0)

    # Resolved synchronously at app-creation time (not a lifespan hook —
    # there's no async resource to wait on yet, and a sync check keeps
    # /health/ready correct immediately, including under TestClient
    # instances that are never entered as a context manager).
    try:
        app.state.core_settings = load_settings(env=env)
    except Exception:
        # /health/ready reports not_ready rather than raising here — an
        # operator can still reach the dashboard to see *why* (once a
        # settings/diagnostics view exists; for now this just keeps the
        # process able to start instead of crashing on an invalid config).
        app.state.core_settings = None

    # Phân quyền app (H1.4). Add TRƯỚC SessionMiddleware — trong Starlette,
    # middleware add trước là lớp trong, chạy SAU, nên nó đọc được
    # request.session mà SessionMiddleware đã dựng.
    from server.access_middleware import AccessControlMiddleware
    app.add_middleware(AccessControlMiddleware)

    app.add_middleware(
        SessionMiddleware,
        secret_key=server_settings.session_secret,
        https_only=server_settings.secure_cookies,
        same_site="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
    )

    @app.middleware("http")
    async def correlation_id_and_security_headers(request: Request, call_next):
        request.state.correlation_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id

        # Baseline hardening for a dashboard served on a public domain.
        # 'unsafe-inline' is required because the templates carry inline
        # <style> and one inline polling <script>; everything external is
        # still blocked, so an injected <script src=...> cannot load.
        # 'unsafe-inline' cần cho <style> nội tuyến và một <script> polling.
        # challenges.cloudflare.com được phép cho Turnstile (Q20): widget của
        # nó nạp một script và mở một iframe từ đó. Không có hai dòng
        # cloudflare này thì CSP chặn Turnstile ngay khi bật — một lỗi chỉ lộ
        # ra lúc production bật chống-bot, đúng lúc không muốn gỡ rối nhất.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "frame-src https://challenges.cloudflare.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"

        # KHÔNG để proxy/CDN (Cloudflare) cache BẤT KỲ response động/riêng-tư
        # nào — chỉ `/static/` (asset công khai) được phép cache.
        #
        # Trước đây chỉ chặn text/html. Hậu quả thật (phát hiện ở H5): ảnh output
        # per-user phục vụ ở URL đuôi `.png` bị Cloudflare cache theo phần mở
        # rộng (max-age mặc định) rồi TRẢ CHO NGƯỜI KHÔNG ĐĂNG NHẬP — origin đã
        # chặn (303) nhưng edge phục vụ bản cache, bỏ qua auth. Mặc định no-store
        # cho mọi thứ ngoài /static/ chặn cả lớp lỗi này.
        if not request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        # HSTS only outside development — development runs plain HTTP, and
        # a browser that caches HSTS for localhost is painful to undo.
        if server_settings.environment is not Environment.DEVELOPMENT:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    from server.routes import jobs as jobs_routes
    from server.routes import register as register_routes

    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(register_routes.router)
    app.include_router(jobs_routes.router)
    app.include_router(dashboard_routes.router)
    app.include_router(status_routes.router)
    app.include_router(accounts_routes.router)
    app.include_router(workers_routes.router)
    app.include_router(settings_routes.router)
    app.include_router(sheet_routes.router)
    app.include_router(manual_routes.router)
    app.include_router(monitor_routes.router)
    app.include_router(oauth_routes.router)

    # Thanh toán / nạp credit (H9)
    from server.routes import billing as billing_routes
    from server.routes import webhooks as webhooks_routes
    app.include_router(billing_routes.router)
    app.include_router(webhooks_routes.router)

    # File tĩnh (HTMX self-host — Q18). Self-host chứ không CDN: CSP chặn
    # script ngoài, và không phụ thuộc mạng để trang chạy.
    import os as _os
    from fastapi.staticfiles import StaticFiles
    _static = _os.path.join(_os.path.dirname(__file__), "static")
    if _os.path.isdir(_static):
        app.mount("/static", StaticFiles(directory=_static), name="static")

    # Mount mọi app trong apps/. Nền tảng không biết trước app nào tồn tại —
    # nó đọc apps/*/manifest.py. Thêm app = thêm folder, không sửa file này.
    from platform_core.registry import mount_all
    app.state.loaded_apps = mount_all(app)

    # Trang quan tri (H3-admin, Q15) o /admin. Chi admin vao duoc (AdminAuth).
    # Bo qua an toan khi thieu sqladmin (moi truong test khong cai) HOAC chua co
    # CSDL (nhieu test khong dung PostgreSQL) - admin chi co nghia khi co ca hai.
    app.state.admin_ready = False
    try:
        from server.admin import setup_admin
        app.state.admin_ready = setup_admin(
            app, session_secret=server_settings.session_secret)
    except Exception:
        logging.getLogger(__name__).info(
            "Bo qua trang quan tri (sqladmin chua san sang)")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        # require_login raises 303 + Location to bounce anonymous users to
        # /login; redirects must pass through, not render as an error page.
        if exc.status_code in (301, 302, 303, 307, 308):
            location = (exc.headers or {}).get("Location", "/login")
            return RedirectResponse(location, status_code=exc.status_code)

        # /health/* is probed by the reverse proxy and service manager —
        # those callers want JSON, not an HTML page.
        if request.url.path.startswith("/health"):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

        return templates.TemplateResponse(
            request, "error.html",
            {
                "code": exc.status_code,
                "message": _ERROR_MESSAGES.get(exc.status_code, str(exc.detail)),
                "correlation_id": getattr(request.state, "correlation_id", ""),
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        # W1.2: lỗi CHƯA BẮT (RuntimeError, KeyError...) trước đây rơi vào
        # ServerErrorMiddleware của Starlette → trả 500 TRẦN, không style, không
        # correlation id, và MẤT các header bảo mật/`no-store` (middleware headers
        # chỉ chạy khi call_next thành công, không chạy khi exception xuyên lên).
        # Đó là lỗ: một trang 500 bị Cloudflare cache có thể lộ chéo. Handler này
        # tự dựng trang lỗi + tự đặt lại no-store + header bảo mật.
        cid = getattr(request.state, "correlation_id", "")
        logging.getLogger(__name__).exception(
            "Loi chua bat [%s] %s %s", cid, request.method, request.url.path)
        if request.url.path.startswith("/health"):
            return JSONResponse({"detail": "internal error"}, status_code=500,
                                headers={"Cache-Control": "no-store"})
        resp = templates.TemplateResponse(
            request, "error.html",
            {"code": 500, "message": _ERROR_MESSAGES[500], "correlation_id": cid},
            status_code=500,
        )
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        if cid:
            resp.headers["X-Correlation-ID"] = cid
        return resp

    return app
