"""Provider OAuth routes (W5) — replaces the desktop's localhost HTTPServer.

Both callbacks require an authenticated session, so a stray hit on the URL
cannot write into the token store. The provider only ever redirects the
operator's own browser here, which already carries that session.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.services import oauth_service
from server.services.oauth_service import OAuthError
from server.templating import templates
from utils.logger import BotLogger

router = APIRouter(tags=["oauth"])

_ACCOUNTS_PAGE = {"facebook": "/facebook", "tiktok": "/tiktok"}


def _config(request: Request) -> dict:
    cs = getattr(request.app.state, "core_settings", None)
    return dict(cs.config) if cs else {}


def _base_url(request: Request) -> str:
    """The public origin of this app as the operator's browser sees it.

    Starlette derives this from the X-Forwarded-Proto/Host headers Caddy
    sets, so it is the https://app.lttstudios.com origin, not the loopback
    address the proxy dialled.
    """
    return str(request.base_url).rstrip("/")


def _result(request: Request, provider: str, ok: bool, title: str, detail: str):
    return templates.TemplateResponse(request, "oauth_result.html", {
        "user": request.session.get("user", ""),
        "nav": provider, "provider": provider, "ok": ok,
        "title": title, "detail": detail,
        "back_url": _ACCOUNTS_PAGE[provider],
    }, status_code=200 if ok else 400)


# ── Facebook ───────────────────────────────────────────────────────────────

@router.post("/oauth/facebook/start")
def facebook_start(
    request: Request,
    csrf_token: str = Form(...),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/facebook", status_code=303)
    try:
        url = oauth_service.facebook_start(
            _config(request), _base_url(request), request.session)
    except OAuthError as exc:
        return _result(request, "facebook", False, "Chưa thể bắt đầu kết nối", str(exc))
    return RedirectResponse(url, status_code=303)


@router.get("/oauth/facebook/callback", response_class=HTMLResponse)
def facebook_callback(request: Request, user: str = Depends(require_login)):
    params = dict(request.query_params)

    denied = oauth_service.provider_error_message(params)
    if denied:
        return _result(request, "facebook", False,
                       "Facebook đã từ chối hoặc bạn đã huỷ", denied)
    try:
        account = oauth_service.facebook_finish(
            _config(request), params.get("state", ""), params.get("code", ""),
            request.session)
    except OAuthError as exc:
        return _result(request, "facebook", False, "Callback không hợp lệ", str(exc))
    except Exception as exc:
        BotLogger().error(f"OAuth Facebook thất bại: {type(exc).__name__}: {exc}")
        return _result(request, "facebook", False, "Đổi token thất bại",
                       f"{type(exc).__name__}: {exc}")

    pages = len(account.get_pages_list())
    return _result(request, "facebook", True, f"Đã kết nối: {account.name}",
                   f"Lấy được {pages} page. Vào Tài khoản FB để chọn page "
                   f"nào được phép đăng.")


# ── TikTok ─────────────────────────────────────────────────────────────────

@router.get("/oauth/tiktok/disclosure", response_class=HTMLResponse)
def tiktok_disclosure(request: Request, user: str = Depends(require_login)):
    """Mandatory pre-authorize consent screen.

    TikTok's audit requires the app to state which scopes it asks for and why
    BEFORE redirecting. The desktop showed this as a modal
    (gui/tiktok_oauth_disclosure.py); it stays on the critical path here — the
    only way to reach /oauth/tiktok/start is through this page.
    """
    config = _config(request)
    from server.services.audit_service import SCOPE_EXPLAIN, SCOPE_UNKNOWN

    scopes = [{"scope": s, "explain": SCOPE_EXPLAIN.get(s, SCOPE_UNKNOWN)}
              for s in oauth_service.tiktok_scopes(config)]
    return templates.TemplateResponse(request, "oauth_tiktok_disclosure.html", {
        "user": user, "nav": "tiktok", "scopes": scopes,
        "app_name": str(config.get("app_name", "") or "LTT AI Studio"),
        "csrf_token": issue_csrf_token(request),
    })


@router.post("/oauth/tiktok/start")
def tiktok_start(
    request: Request,
    csrf_token: str = Form(...),
    consent: str = Form(""),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/tiktok", status_code=303)
    if consent != "yes":
        # Never redirect to TikTok without recorded consent — that is the
        # compliance requirement, not a UI nicety.
        return _result(request, "tiktok", False, "Chưa xác nhận quyền truy cập",
                       "Bạn cần tích vào ô đồng ý trước khi kết nối TikTok.")
    try:
        url = oauth_service.tiktok_start(
            _config(request), _base_url(request), request.session)
    except OAuthError as exc:
        return _result(request, "tiktok", False, "Chưa thể bắt đầu kết nối", str(exc))
    return RedirectResponse(url, status_code=303)


@router.get("/oauth/tiktok/callback", response_class=HTMLResponse)
def tiktok_callback(request: Request, user: str = Depends(require_login)):
    params = dict(request.query_params)

    denied = oauth_service.provider_error_message(params)
    if denied:
        return _result(request, "tiktok", False,
                       "TikTok đã từ chối hoặc bạn đã huỷ", denied)
    try:
        account = oauth_service.tiktok_finish(
            _config(request), params.get("state", ""), params.get("code", ""),
            request.session)
    except OAuthError as exc:
        return _result(request, "tiktok", False, "Callback không hợp lệ", str(exc))
    except Exception as exc:
        BotLogger().error(f"OAuth TikTok thất bại: {type(exc).__name__}: {exc}")
        return _result(request, "tiktok", False, "Đổi token thất bại",
                       f"{type(exc).__name__}: {exc}")

    return _result(request, "tiktok", True,
                   f"Đã kết nối: {account.display_name}",
                   "Scope được cấp: " + ", ".join(account.scopes))
