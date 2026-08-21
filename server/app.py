"""
FastAPI application factory (P3).

No publishing behavior lives here yet (P4/P5). This module only builds the
authenticated dashboard shell + health/readiness endpoints. Must never
import gui.* or customtkinter — verified by test, same boundary as P1's
worker_main.py.
"""
from __future__ import annotations

import logging
import threading
import re
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


def _json_error_detail(value):
    """Make framework/app error details serializable without echoing input.

    Pydantic error dictionaries can contain the original request under
    ``input`` and exception objects under ``ctx``. Neither belongs in a public
    response: one may expose customer content and the other breaks json.dumps.

    The rule itself lives in ``platform_core.public_api.errors.scrub_detail`` so
    the Q88 contract here and the RFC 9457 contract on ``/api/v1`` cannot drift
    apart; this name stays because routes and tests already use it.
    """
    from platform_core.public_api.errors import scrub_detail

    return scrub_detail(value)

SESSION_MAX_AGE_SECONDS = 8 * 60 * 60  # 8h idle expiry
_HASHED_FRONTEND_ASSET = re.compile(
    r"^/static/(?:agent-canvas|autosub-studio)/assets/.+-[A-Za-z0-9_-]{8,}\.(?:js|css)$"
)


# ── Maintenance daemon ─────────────────────────────────────────────────────────
# Only `gui/main_window.py` ever started this daemon. With the desktop gone,
# nothing would prune old content_history / page_health records or probe the
# Meta + TikTok app status, so retention (DATA_RETENTION_POLICY.md) would
# silently stop being enforced. The web app owns it now.


#: Chu kỳ xả bộ đếm của tiến trình web. Là hằng số module để test rút ngắn được
#: — một luồng nền chỉ chạy sau 60 giây thì trên thực tế là một luồng không có
#: test nào đi qua.
METRICS_FLUSH_INTERVAL_S = 60.0


def _xa_metrics_web(dung) -> None:
    """Đưa bộ đếm của tiến trình WEB xuống CSDL.

    Bộ đếm sống trong tiến trình. Worker đã có đường xả từ trước, nhưng phần lớn
    con số đáng xem lại phát sinh **ở đây** — số request, lỗi xác thực, lần bị
    chặn nhịp — nên trước khi có hàm này, trang vận hành cộng lại được mọi thứ
    trừ chính thứ nó cần nhất.
    """
    import time as _time

    from platform_core.db import get_session
    from platform_core.public_api import metrics

    log = logging.getLogger(__name__)
    while not dung.wait(METRICS_FLUSH_INTERVAL_S):
        try:
            gen = get_session()
            db = next(gen)
            try:
                metrics.flush(db, prefix=metrics.WEB_PREFIX)
                db.commit()
            finally:
                try:
                    next(gen)
                except StopIteration:
                    pass
        except Exception:                   # noqa: BLE001
            # Không xả được số liệu là chuyện phải chịu được; nó không được
            # làm sập tầng web đang phục vụ khách.
            log.warning("khong xa duoc metrics web", exc_info=True)


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
    dung_metrics = threading.Event()
    luong_metrics = threading.Thread(
        target=_xa_metrics_web, args=(dung_metrics,),
        name="xa-metrics-web", daemon=True)
    luong_metrics.start()
    try:
        yield
    finally:
        dung_metrics.set()
        luong_metrics.join(timeout=5)
        daemon = getattr(app.state, "maintenance", None)
        if daemon is not None:
            daemon.stop()


def _socialbot_routes_enabled(env: dict | None = None) -> bool:
    """Có gắn 43 route bảng điều khiển FB/TikTok cũ không (H22.10).

    Mặc định BẬT. Chọn mặc định bật chứ không tắt vì tắt sẵn là để bảng điều
    khiển cũ biến mất **lặng lẽ** với người còn đang dùng, ngay lần deploy tới —
    một quyết định sản phẩm không nên nằm trong một lần refactor.
    """
    import os
    raw = (env or os.environ).get("LTT_SOCIALBOT_ROUTES")
    if raw is None:
        return True
    return str(raw).strip().lower() not in {"0", "false", "no", "off", ""}


def create_app(*, env: dict | None = None) -> FastAPI:
    server_settings = load_server_settings(env)
    from server.telemetry import init_sentry
    init_sentry(env)

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

    # Rate-limit per-user cho endpoint app (chống script/lạm dụng) — thêm TRƯỚC
    # SessionMiddleware để đọc được request.session (giống AccessControl).
    from server.usage_rate_limit import UsageRateLimitMiddleware
    app.add_middleware(UsageRateLimitMiddleware)

    from server.request_body_limit import AgentBodyLimitMiddleware
    app.add_middleware(AgentBodyLimitMiddleware)

    # Ngôn ngữ (H24). Vị trí quan trọng, thêm SAU ba cái trên và TRƯỚC
    # SessionMiddleware, để nó nằm giữa hai lớp:
    #   - NGOÀI phân quyền/rate-limit → chúng thấy đường dẫn ĐÃ bóc tiền tố,
    #     nên luật của chúng khỏi phải biết `/en/` tồn tại;
    #   - TRONG SessionMiddleware → đọc được `request.session` để lấy ngôn ngữ
    #     đã lưu ở hồ sơ tài khoản.
    from server.i18n_middleware import I18nMiddleware
    app.add_middleware(I18nMiddleware)

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
            "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com "
            "https://static.cloudflareinsights.com; "
            "style-src 'self' 'unsafe-inline'; "
            # img-src thêm R2: app ảnh (chat AI, và app khác) phục vụ ảnh output qua
            # presigned URL (redirect 302 sang R2) → 'self' chặn cross-origin. Cho phép
            # host R2 để ảnh hiện được (song song media-src/connect-src của app video).
            "img-src 'self' data: https://*.r2.cloudflarestorage.com; "
            # media-src cho app VIDEO (taovideo/autosubvideo/upscale sau này):
            #   blob:  — đọc metadata video client-side (thời lượng → ước tính credit)
            #   *.r2…  — phát video output do R2 phục vụ qua presigned URL (redirect
            #            302 từ /v/{key}); không có dòng này thì default-src 'self'
            #            chặn cả blob lẫn video R2. Đây là hợp đồng chung của nhóm
            #            app ffmpeg/gpu, không phải vá riêng một app.
            "media-src 'self' blob: https://*.r2.cloudflarestorage.com; "
            # connect-src cho upload THẲNG browser→R2 (presigned PUT, P1): XHR/fetch
            # tới R2 là connect-src; thiếu thì default-src 'self' chặn. 'self' cho
            # các fetch nội bộ (/upload-url, /queue, HTMX).
            "connect-src 'self' https://*.r2.cloudflarestorage.com "
            "https://cloudflareinsights.com; "
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
        if _HASHED_FRONTEND_ASSET.fullmatch(request.url.path):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.url.path.startswith(("/static/agent-canvas/",
                                          "/static/autosub-studio/")):
            response.headers["Cache-Control"] = "no-store"
        elif not request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        # HSTS only outside development — development runs plain HTTP, and
        # a browser that caches HSTS for localhost is painful to undo.
        if server_settings.environment is not Environment.DEVELOPMENT:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    from server.routes import developer as developer_routes
    from server.routes import jobs as jobs_routes
    from server.routes import register as register_routes

    app.include_router(health_routes.router)
    from server.routes import ngon_ngu as ngon_ngu_routes
    app.include_router(ngon_ngu_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(register_routes.router)
    app.include_router(jobs_routes.router)
    app.include_router(dashboard_routes.router)
    app.include_router(status_routes.router)
    # Trang tải LTT Nexus (Model B, Q101: web = hướng dẫn/tải) + version.json.
    # Công khai, không phụ thuộc cờ LTT_NEXUS (tải/hướng dẫn không lộ gì).
    from server import nexus_download as nexus_download_routes
    app.include_router(nexus_download_routes.router)
    # Developer portal: session + CSRF surface where API keys are created. It is
    # mounted unconditionally so a customer can prepare keys before an operator
    # turns the API itself on; the page says plainly when `/api/v1` is off.
    app.include_router(developer_routes.router)

    # ── Nexus: bề mặt cho AGENT trên máy khách (Q93) ─────────────────────────
    #
    # Gắn KHÔNG điều kiện, và các route tự trả 404 khi `LTT_NEXUS` tắt. Cố ý làm
    # vậy chứ không gác ở đây: `registry.mount_all()` đã cho thấy một cờ chỉ được
    # đọc ở chỗ mount là một cờ **không đóng được URL** — nó chỉ ẩn khỏi catalog.
    # Đặt phép kiểm trong route nghĩa là chỉ có một chỗ để quên, và có test chốt
    # rằng chỗ đó không bị quên.
    #
    # Không nằm dưới `route_prefix` của app nào: agent không phải trình duyệt, và
    # một app không mount được path ngoài prefix của nó (`AGENTS.md` 8.4).
    from server import nexus as nexus_agent_routes
    app.include_router(nexus_agent_routes.router)

    # ── Bảng điều khiển FB/TikTok cũ (H22.10) ────────────────────────────────
    #
    # Bảy router này là bản port từ GUI desktop của sản phẩm socialbot — app đó
    # đã **đóng băng, không phát triển thêm**. Chúng chiếm **43/69 = 62% route
    # công khai** của nền tảng, trong khi nền tảng giờ bán công cụ AI theo
    # credit. Mỗi route là một chỗ phải xét lại mỗi lần rà bảo mật, cho một
    # nghiệp vụ không còn bán.
    #
    # Gắn sau một cờ để tắt được mà KHÔNG xoá code — socialbot đóng băng chứ
    # chưa khai tử, nên xoá là quyết định sản phẩm, còn tắt thì bật lại được
    # bằng một biến môi trường.
    #
    # Mặc định giữ BẬT: tắt sẵn nghĩa là nếu còn ai đang dùng bảng điều khiển
    # cũ thì nó biến mất lặng lẽ sau lần deploy tới. Đổi `LTT_SOCIALBOT_ROUTES=0`
    # khi đã xác nhận không còn ai dùng.
    if _socialbot_routes_enabled(env):
        app.include_router(accounts_routes.router)
        app.include_router(workers_routes.router)
        app.include_router(settings_routes.router)
        app.include_router(sheet_routes.router)
        app.include_router(manual_routes.router)
        app.include_router(monitor_routes.router)
        app.include_router(oauth_routes.router)
    else:
        logging.getLogger(__name__).info(
            "LTT_SOCIALBOT_ROUTES=0 — khong gan 43 route bang dieu khien FB/TikTok cu")

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

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return RedirectResponse("/static/favicon.svg", status_code=307)

    # Mount mọi app trong apps/. Nền tảng không biết trước app nào tồn tại —
    # nó đọc apps/*/manifest.py. Thêm app = thêm folder, không sửa file này.
    from platform_core.registry import mount_all
    app.state.loaded_apps = mount_all(app)

    # Public API `/api/v1` (Q92). Đây KHÔNG phải một app: một app không mount
    # được path ngoài `route_prefix` của nó và không được biết app khác, nên
    # bề mặt máy-gọi-máy phải nằm ở nền tảng. Mặc định TẮT — không bật cờ
    # `LTT_PUBLIC_API` thì router không được dựng và bề mặt route y hệt hôm nay.
    from server.api import mount_public_api
    app.state.public_api = mount_public_api(app, env=env)

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

        path = request.url.path

        # Public API owns a stricter contract (RFC 9457) than Q88's JSON body,
        # and it must apply even when the surface is disabled — otherwise a
        # client discovers the switch by receiving an HTML page. Checked first
        # because `/api/v1/...` also matches the `/api/` test below.
        from server.api.errors import is_public_api_path, status_problem_response
        if is_public_api_path(path):
            return status_problem_response(request, exc.status_code, exc.detail)

        # Health probes and app APIs need a machine-readable contract. App
        # routes are mounted below their slug (for example ``/<slug>/api``),
        # so checking only a root ``/api`` prefix silently returned an HTML
        # error page to fetch clients and hid the actionable validation detail.
        if path.startswith("/health") or path.startswith("/api/") or "/api/" in path:
            body = {"detail": _json_error_detail(exc.detail)}
            cid = getattr(request.state, "correlation_id", "")
            if cid:
                body["correlation_id"] = cid
            return JSONResponse(body, status_code=exc.status_code,
                                headers={"Cache-Control": "no-store"})

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
        # An API caller gets the same problem document as for any other error,
        # with a fixed detail: the exception text can carry provider secrets or
        # customer data, and a stack trace is free reconnaissance.
        from server.api.errors import is_public_api_path, status_problem_response
        if is_public_api_path(request.url.path):
            return status_problem_response(request, 500)
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
