"""Login / logout routes (P3)."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.password_hashing import verify_password
from server.auth.rate_limit import RateLimiter
from server.auth.session import current_user, log_in, log_out
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
    return request.client.host if request.client else "unknown"


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if current_user(request):
        return RedirectResponse("/", status_code=303)
    token = issue_csrf_token(request)
    return templates.TemplateResponse(
        request, "login.html", {"csrf_token": token, "error": None},
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    settings = request.app.state.server_settings

    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "login.html",
            {"csrf_token": issue_csrf_token(request), "error": "Phiên đăng nhập đã hết hạn, thử lại."},
            status_code=400,
        )

    if not _limiter(request).allow(_client_key(request)):
        return templates.TemplateResponse(
            request, "login.html",
            {"csrf_token": issue_csrf_token(request), "error": "Quá nhiều lần thử — vui lòng đợi 1 phút."},
            status_code=429,
        )

    valid = (
        username == settings.admin_username
        and settings.admin_password_hash
        and verify_password(password, settings.admin_password_hash)
    )
    if not valid:
        return templates.TemplateResponse(
            request, "login.html",
            {"csrf_token": issue_csrf_token(request), "error": "Sai tên đăng nhập hoặc mật khẩu."},
            status_code=401,
        )

    _limiter(request).reset(_client_key(request))
    log_in(request, username)
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request):
    log_out(request)
    return RedirectResponse("/login", status_code=303)
