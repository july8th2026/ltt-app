"""``/developers`` — the portal where a customer manages their API keys.

This is the **session** surface, not the API one, and the difference is the
whole point:

* it authenticates with the platform's login session and therefore **must** have
  CSRF protection on every state-changing POST — a browser attaches session
  cookies to cross-site requests automatically. ``/api/v1`` is the opposite: it
  refuses cookies and needs no CSRF (see ``server/api/auth.py``);
* it is the only place a developer key is ever created, and the plaintext is
  shown **once**, on the response to the request that created it. A refresh
  cannot bring it back, because nothing on the server can reproduce it.

Deliberately not here: any provider credential. ``platform_core.api_keys`` holds
the platform's own keys for Gemini and friends; a customer has no business
seeing that they exist, let alone their preview.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core import credit
from platform_core.i18n import _ as _t
from platform_core.models import Job
from platform_core.public_api import keys as devkeys, usage
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.invocation import api_meta
from platform_core.public_api.scopes import DEFAULT_SCOPES, KNOWN_SCOPES
from platform_core.public_api.tables import WebhookSubscription
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

router = APIRouter(prefix="/developers", tags=["developers"])

# How many finished/queued API jobs the portal shows. Enough to answer "did my
# integration work"; not a job browser — that is what `/api/v1/jobs` is for.
RECENT_JOBS = 10


def require_account(request: Request):
    """The signed-in database user. The admin-env path has no account to bill.

    Declared **before** the database dependency on every route below, so an
    anonymous visitor is bounced to the login page instead of first opening a
    session — which on a server with no database configured turned a redirect
    into a 500.
    """
    require_login(request)
    user = user_hien_tai(request)
    if user is None:
        # Break-glass admin (Q29) has no `users` row, so no keys and no credit.
        raise _redirect("/login?next=/developers")
    return user


def _redirect(location: str, status_code: int = 303):
    from fastapi import HTTPException

    return HTTPException(status_code=status_code, headers={"Location": location})


def _webhooks(db: Session, user_id: str) -> list:
    return list(db.execute(select(WebhookSubscription).where(
        WebhookSubscription.user_id == user_id,
        WebhookSubscription.enabled.is_(True),
    ).order_by(WebhookSubscription.created_at.desc())).scalars().all())


def _recent_api_jobs(db: Session, user_id: str) -> list:
    """Jobs this account created through the API, newest first."""
    rows = db.execute(select(Job).where(Job.user_id == user_id)
                      .order_by(Job.created_at.desc()).limit(50)).scalars().all()
    found = []
    for job in rows:
        meta = api_meta(job)
        if not meta:
            continue        # made in the UI, not through the API
        found.append({"id": job.id, "tool": meta.get("tool") or "",
                      "status": job.status, "created_at": job.created_at,
                      "key_id": meta.get("key_id") or ""})
        if len(found) >= RECENT_JOBS:
            break
    return found


def _public_api_config(request: Request):
    """The configuration this application was mounted with.

    Read from app state rather than the environment: the portal must describe
    the API this process is actually serving, and an app built with an explicit
    env mapping (tests, a second instance) would otherwise be described by
    whatever the process environment happens to say.
    """
    config = getattr(request.app.state, "public_api", None)
    return config if config is not None else load_public_api_config()


def _page(request: Request, db: Session, user, *, revealed: str = "",
          error: str = "", created_key=None) -> HTMLResponse:
    config = _public_api_config(request)
    now = datetime.now(timezone.utc)
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return templates.TemplateResponse(
        request, "developers.html",
        {
            "csrf_token": issue_csrf_token(request),
            "api_enabled": config.enabled,
            "read_only": config.read_only,
            "keys": [
                {
                    "key_id": key.key_id, "name": key.name,
                    "status": key.status(now=now),
                    "scopes": list(key.scopes or ()),
                    "allowed_tools": list(key.allowed_tools or ()),
                    "created_at": key.created_at,
                    "last_used_at": key.last_used_at,
                    "expires_at": key.expires_at,
                }
                for key in devkeys.list_for_user(db, user.id)
            ],
            # Shown once, on this response only.
            "revealed_secret": revealed,
            "created_key": created_key,
            "error": error,
            "scopes": sorted(KNOWN_SCOPES),
            "default_scopes": list(DEFAULT_SCOPES),
            "tools": [tool.name for tool in build_catalog(config)],
            "balance": credit.so_du(db, user.id),
            "usage_today": usage.usage_totals(db, user_id=user.id,
                                              since=window_start, until=now),
            "limits": {
                "request_rpm": config.request_rpm,
                "create_rpm": config.create_rpm,
                "max_active_jobs": config.max_active_jobs,
                "daily_credit_limit": config.daily_credit_limit,
            },
            "webhooks": _webhooks(db, user.id),
            "recent_jobs": _recent_api_jobs(db, user.id),
        },
    )


@router.get("", response_class=HTMLResponse)
def developer_home(request: Request, user=Depends(require_account),
                   db: Session = Depends(get_db)):
    return _page(request, db, user)


@router.post("/keys", response_class=HTMLResponse)
def create_key(request: Request, name: str = Form(""),
               scopes: list[str] = Form(default=[]),
               allowed_tools: list[str] = Form(default=[]),
               csrf_token: str = Form(""), user=Depends(require_account),
               db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers")
    try:
        key, token = devkeys.issue(db, user_id=user.id, name=name,
                                   scopes=scopes, allowed_tools=allowed_tools)
    except Exception as exc:  # noqa: BLE001 - message is for this one customer
        from platform_core.public_api.scopes import ScopeError

        if not isinstance(exc, (devkeys.DeveloperKeyError, ScopeError)):
            raise
        return _page(request, db, user, error=str(exc))
    # The plaintext exists only in this response. Nothing stores it, and the
    # page below says so — a customer who closes the tab must create a new key.
    return _page(request, db, user, revealed=token, created_key=key.key_id)


@router.post("/keys/{key_id}/revoke")
def revoke_key(request: Request, key_id: str, csrf_token: str = Form(""),
               user=Depends(require_account), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers", status_code=303)
    key = devkeys.get_owned(db, user_id=user.id, key_id=key_id)
    if key is not None:
        devkeys.revoke(db, key)
    # Same redirect whether or not the key existed: a portal must not become a
    # way to find out which key ids belong to somebody else.
    return RedirectResponse("/developers", status_code=303)


@router.post("/keys/{key_id}/rotate", response_class=HTMLResponse)
def rotate_key(request: Request, key_id: str, csrf_token: str = Form(""),
               user=Depends(require_account), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers")
    key = devkeys.get_owned(db, user_id=user.id, key_id=key_id)
    if key is None:
        return _page(request, db, user, error=_t("Không tìm thấy khóa."))
    try:
        token = devkeys.rotate(db, key)
    except devkeys.DeveloperKeyError as exc:
        return _page(request, db, user, error=str(exc))
    return _page(request, db, user, revealed=token, created_key=key.key_id)
