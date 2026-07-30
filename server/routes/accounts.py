"""
Facebook / TikTok account pages.

Ported from `gui/account_tab.py` and `gui/tiktok_account_tab.py`. The
operations are wired up: System-User token import, token test, page
selection, TikTok refresh/revoke, disconnect. The OAuth buttons post to
`server/routes/oauth.py`, which receives the provider callback in this app
instead of on a localhost port the way the desktop did.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.services import oauth_service
from server.services import ui_constants as UI
from server.services.accounts import list_facebook_accounts, list_tiktok_accounts
from server.services.accounts_actions import (
    disconnect_facebook,
    disconnect_tiktok,
    import_system_user_token,
    refresh_tiktok_token,
    set_page_selected,
    test_facebook_token,
)
from server.templating import templates

router = APIRouter(tags=["accounts"])


def _config(request: Request) -> dict:
    cs = getattr(request.app.state, "core_settings", None)
    return dict(cs.config) if cs else {}


def _context(request: Request, user: str, platform: str, **extra) -> dict:
    cfg = _config(request)
    if platform == "facebook":
        listing = list_facebook_accounts()
        title, shows_pages = "Facebook Bot", True
    else:
        listing = list_tiktok_accounts()
        title, shows_pages = "TikTok Bot", False

    ctx = {
        "user": user,
        "nav": platform,
        "platform": platform,
        "title": title,
        "listing": listing,
        "shows_pages": shows_pages,
        "colors": UI.COLORS,
        "csrf_token": issue_csrf_token(request),
        "callback_uri": oauth_service.callback_url(
            str(request.base_url).rstrip("/"), platform),
        "audit_approved": str(cfg.get("tiktok_audit_approved", "")).lower()
                          in ("true", "1", "yes"),
        "action_ok": "",
        "action_err": "",
    }
    ctx.update(extra)
    return ctx


def _render(request: Request, user: str, platform: str,
            status_code: int = 200, **extra):
    return templates.TemplateResponse(
        request, "accounts.html", _context(request, user, platform, **extra),
        status_code=status_code,
    )


@router.get("/facebook", response_class=HTMLResponse)
def facebook_accounts(request: Request, user: str = Depends(require_login)):
    return _render(request, user, "facebook")


@router.get("/tiktok", response_class=HTMLResponse)
def tiktok_accounts(request: Request, user: str = Depends(require_login)):
    return _render(request, user, "tiktok")


@router.post("/facebook/system-token", response_class=HTMLResponse)
def fb_import_system_token(
    request: Request,
    csrf_token: str = Form(...),
    token: str = Form(""),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, "facebook", 400,
                       action_err="Phiên đã hết hạn, tải lại trang.")
    ok, msg = import_system_user_token(_config(request), token)
    key = "action_ok" if ok else "action_err"
    return _render(request, user, "facebook", 200 if ok else 400, **{key: msg})


@router.post("/facebook/test", response_class=HTMLResponse)
def fb_test(
    request: Request,
    csrf_token: str = Form(...),
    account_id: str = Form(...),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, "facebook", 400,
                       action_err="Phiên đã hết hạn, tải lại trang.")
    ok, msg = test_facebook_token(_config(request), account_id)
    key = "action_ok" if ok else "action_err"
    return _render(request, user, "facebook", **{key: msg})


@router.post("/facebook/page", response_class=HTMLResponse)
def fb_toggle_page(
    request: Request,
    csrf_token: str = Form(...),
    account_id: str = Form(...),
    page_id: str = Form(...),
    selected: str = Form("1"),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, "facebook", 400,
                       action_err="Phiên đã hết hạn, tải lại trang.")
    ok, msg = set_page_selected(account_id, page_id, selected == "1")
    key = "action_ok" if ok else "action_err"
    return _render(request, user, "facebook", **{key: msg})


@router.post("/facebook/disconnect", response_class=HTMLResponse)
def fb_disconnect(
    request: Request,
    csrf_token: str = Form(...),
    account_id: str = Form(...),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, "facebook", 400,
                       action_err="Phiên đã hết hạn, tải lại trang.")
    ok, msg = disconnect_facebook(account_id)
    key = "action_ok" if ok else "action_err"
    return _render(request, user, "facebook", **{key: msg})


@router.post("/tiktok/refresh", response_class=HTMLResponse)
def tt_refresh(
    request: Request,
    csrf_token: str = Form(...),
    account_id: str = Form(...),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, "tiktok", 400,
                       action_err="Phiên đã hết hạn, tải lại trang.")
    ok, msg = refresh_tiktok_token(_config(request), account_id)
    key = "action_ok" if ok else "action_err"
    return _render(request, user, "tiktok", **{key: msg})


@router.post("/tiktok/disconnect", response_class=HTMLResponse)
def tt_disconnect(
    request: Request,
    csrf_token: str = Form(...),
    account_id: str = Form(...),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, "tiktok", 400,
                       action_err="Phiên đã hết hạn, tải lại trang.")
    ok, msg = disconnect_tiktok(_config(request), account_id)
    key = "action_ok" if ok else "action_err"
    return _render(request, user, "tiktok", **{key: msg})
