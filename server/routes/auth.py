"""Login / logout routes (P3)."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.password_hashing import verify_password
from server.auth.rate_limit import RateLimiter
from server.auth.session import (client_ip, current_identity_optional, log_in,
                                 log_in_db, log_out, safe_next)
from server.deps import mo_db_optional
from server.templating import templates

router = APIRouter(tags=["auth"])


def _limiter(request: Request) -> RateLimiter:
    """Per-application limiter, created by create_app() and held on
    app.state.

    Deliberately not module-level: module state is shared by every app
    instance in a process, so two apps would share login-attempt counters
    (and a test that exhausts the limit would silently lock out unrelated
    tests). Within one running server there is still exactly one limiter,
    which is what ADR-005's single-process model wants.
    """
    return request.app.state.login_rate_limiter


def _client_key(request: Request) -> str:
    # IP THẬT sau Cloudflare Tunnel (CF-Connecting-IP), không phải 127.0.0.1 của
    # loopback — nếu không rate-limit sẽ khoá nhầm toàn hệ thống. Xem client_ip.
    return client_ip(request)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: str = ""):
    # Đã đăng nhập bằng đường nào (admin-env hoặc phiên CSDL) đều khỏi hiện form.
    # PHẢI xác thực đồng nhất với require_login (current_identity_optional có
    # RESOLVE sid với CSDL), không chỉ kiểm sự hiện diện của sid. Nếu chỉ kiểm
    # hiện diện: phiên có sid nhưng đã bị thu hồi/hết hạn sẽ khiến /login đá sang
    # trang trong khi require_login đá ngược về /login → vòng lặp vô tận
    # (ERR_TOO_MANY_REDIRECTS). `next` (H6): quay lại đúng trang, lọc open-redirect.
    if current_identity_optional(request):
        return RedirectResponse(safe_next(next), status_code=303)
    token = issue_csrf_token(request)
    return templates.TemplateResponse(
        request, "login.html", {"csrf_token": token, "error": None, "next": next},
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    next: str = Form(""),
):
    settings = request.app.state.server_settings

    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "login.html",
            {"csrf_token": issue_csrf_token(request), "error": "Phiên đăng nhập đã hết hạn, thử lại.", "next": next},
            status_code=400,
        )

    if not _limiter(request).allow(_client_key(request)):
        return templates.TemplateResponse(
            request, "login.html",
            {"csrf_token": issue_csrf_token(request), "error": "Quá nhiều lần thử — vui lòng đợi 1 phút.", "next": next},
            status_code=429,
        )

    # Đường 1 — người dùng trong CSDL (email + mật khẩu). Thử trước.
    # `username` cũng là ô nhập email; đường CSDL im lặng bỏ qua khi chưa có DB.
    with mo_db_optional() as db:
        if db is not None:
            from platform_core.users import tao_phien, xac_thuc
            user = xac_thuc(db, email=username, password=password)
            if user is not None:
                sid = tao_phien(
                    db, user,
                    user_agent=request.headers.get("user-agent", ""),
                    ip=_client_key(request),
                )
                _limiter(request).reset(_client_key(request))
                log_in_db(request, sid)
                return RedirectResponse(safe_next(next), status_code=303)

    # Đường 2 — admin-từ-biến-môi-trường (đường lui, luôn còn kể cả khi DB hỏng).
    valid = (
        username == settings.admin_username
        and settings.admin_password_hash
        and verify_password(password, settings.admin_password_hash)
    )
    if not valid:
        return templates.TemplateResponse(
            request, "login.html",
            {"csrf_token": issue_csrf_token(request), "error": "Sai tên đăng nhập hoặc mật khẩu.", "next": next},
            status_code=401,
        )

    _limiter(request).reset(_client_key(request))
    log_in(request, username)
    return RedirectResponse(safe_next(next), status_code=303)


@router.post("/logout")
def logout(request: Request):
    log_out(request)
    return RedirectResponse("/login", status_code=303)
