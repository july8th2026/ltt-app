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

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core import credit
from platform_core.i18n import N_, _ as _t
from platform_core.models import Job
from platform_core.public_api import keys as devkeys, projects, usage
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


# The area's information architecture, in one place. `href=None` means the
# section is named but not built yet: EXT-08 owns the playground, EXT-09 the
# request logs, EXT-11 the notifications. Showing them greyed is honest about
# the shape of the area; a link that 404s is not. OAuth apps are absent rather
# than greyed, because D1 decided not to build them at all.
SECTIONS = (
    ("overview", "/developers", N_("Tổng quan")),
    ("projects", "/developers/projects", N_("Project")),
    ("keys", "/developers/keys", N_("Khóa API")),
    ("tools", "/developers/tools", N_("Công cụ & model")),
    ("playground", None, N_("Playground")),
    ("logs", None, N_("Nhật ký request")),
    ("jobs", "/developers/jobs", N_("Job")),
    ("usage", "/developers/usage", N_("Sử dụng & credit")),
    ("webhooks", "/developers/webhooks", N_("Webhook")),
    ("notifications", None, N_("Thông báo")),
    ("docs", "/developers/docs", N_("Tài liệu & SDK")),
    ("settings", "/developers/settings", N_("Cài đặt & bảo mật")),
)


def _nav(active: str) -> list:
    return [{"key": key, "href": href, "label": _t(label),
             "active": key == active}
            for key, href, label in SECTIONS]


def _title(active: str) -> str:
    for key, _href, label in SECTIONS:
        if key == active:
            return _t(label)
    return _t(N_("Tổng quan"))


def _base_context(request: Request, db: Session, user, active: str,
                  error: str = "") -> dict:
    """What every section needs: navigation, service state, CSRF."""
    config = _public_api_config(request)
    return {
        "csrf_token": issue_csrf_token(request),
        "api_enabled": config.enabled,
        "read_only": config.read_only,
        "nav": _nav(active),
        "section_title": _title(active),
        "error": error,
    }


def _projects_context(db: Session, user) -> dict:
    rows = projects.list_for(db, user_id=user.id)
    return {"projects": [
        {"id": project.id, "name": project.name, "slug": project.slug,
         "created_at": project.created_at,
         "key_count": len(projects.keys_of(db, project_id=project.id))}
        for project in rows]}


def _keys_context(db: Session, user, config) -> dict:
    now = datetime.now(timezone.utc)
    names = {project.id: project.name
             for project in projects.list_for(db, user_id=user.id,
                                              include_archived=True)}
    return {
        "keys": [
            {
                "key_id": key.key_id, "name": key.name,
                "status": key.status(now=now),
                "scopes": list(key.scopes or ()),
                "allowed_tools": list(key.allowed_tools or ()),
                "allowed_ips": list(key.allowed_ips or ()),
                "project": names.get(str(key.project_id or ""), ""),
                "created_at": key.created_at,
                "last_used_at": key.last_used_at,
                "expires_at": key.expires_at,
            }
            for key in devkeys.list_for_user(db, user.id)
        ],
        "scopes": sorted(KNOWN_SCOPES),
        "default_scopes": list(DEFAULT_SCOPES),
        "tools": [tool.name for tool in build_catalog(config)],
    }


def _usage_context(db: Session, user, config) -> dict:
    now = datetime.now(timezone.utc)
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "balance": credit.so_du(db, user.id),
        "usage_today": usage.usage_totals(db, user_id=user.id,
                                          since=window_start, until=now),
        "limits": {
            "request_rpm": config.request_rpm,
            "create_rpm": config.create_rpm,
            "max_active_jobs": config.max_active_jobs,
            "daily_credit_limit": config.daily_credit_limit,
        },
    }


def _overview_counts(db: Session, user) -> dict:
    """The numbers the overview answers "is anything wrong?" with."""
    from sqlalchemy import func

    from platform_core.public_api.tables import (WEBHOOK_DEAD, WEBHOOK_FAILED,
                                                 WebhookDelivery)

    now = datetime.now(timezone.utc)
    active_keys = sum(1 for key in devkeys.list_for_user(db, user.id)
                      if key.is_usable(now=now))
    failures = int(db.execute(
        select(func.count(WebhookDelivery.id)).where(
            WebhookDelivery.user_id == user.id,
            WebhookDelivery.status.in_((WEBHOOK_FAILED, WEBHOOK_DEAD)),
        )).scalar_one())
    since = now - timedelta(days=30)
    api_jobs = sum(1 for job in db.execute(
        select(Job).where(Job.user_id == user.id,
                          Job.created_at >= since)).scalars().all()
        if api_meta(job))
    return {
        "projects": len(projects.list_for(db, user_id=user.id)),
        "active_keys": active_keys,
        "webhooks": len(_webhooks(db, user.id)),
        "webhook_failures": failures,
        "api_jobs": api_jobs,
    }


def _render(request: Request, db: Session, user, active: str, template: str,
            **extra) -> HTMLResponse:
    context = _base_context(request, db, user, active,
                            error=str(extra.pop("error", "") or ""))
    context.update(extra)
    return templates.TemplateResponse(request, template, context)


def _keys_page(request: Request, db: Session, user, *, revealed: str = "",
               error: str = "", created_key=None) -> HTMLResponse:
    config = _public_api_config(request)
    return _render(request, db, user, "keys", "dev_keys.html",
                   error=error, revealed_secret=revealed,
                   created_key=created_key,
                   **_projects_context(db, user),
                   **_keys_context(db, user, config))


@router.get("", response_class=HTMLResponse)
def developer_overview(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    config = _public_api_config(request)
    return _render(request, db, user, "overview", "dev_overview.html",
                   counts=_overview_counts(db, user),
                   **_usage_context(db, user, config))


@router.get("/projects", response_class=HTMLResponse)
def developer_projects(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    return _render(request, db, user, "projects", "dev_projects.html",
                   **_projects_context(db, user))


@router.get("/keys", response_class=HTMLResponse)
def developer_keys(request: Request, user=Depends(require_account),
                   db: Session = Depends(get_db)):
    return _keys_page(request, db, user)


@router.get("/tools", response_class=HTMLResponse)
def developer_tools(request: Request, user=Depends(require_account),
                    db: Session = Depends(get_db)):
    from platform_core.public_api.catalog import build_models

    config = _public_api_config(request)
    catalog = build_catalog(config)
    return _render(request, db, user, "tools", "dev_tools.html",
                   catalog=[{"name": tool.name, "description": tool.description,
                             "capability": tool.capability,
                             "execution_mode": tool.execution_mode,
                             "scopes": list(tool.scopes)}
                            for tool in catalog],
                   models=[model.to_public_dict()
                           for model in build_models(catalog)])


@router.get("/jobs", response_class=HTMLResponse)
def developer_jobs(request: Request, user=Depends(require_account),
                   db: Session = Depends(get_db)):
    return _render(request, db, user, "jobs", "dev_jobs.html",
                   recent_jobs=_recent_api_jobs(db, user.id))


@router.get("/usage", response_class=HTMLResponse)
def developer_usage(request: Request, user=Depends(require_account),
                    db: Session = Depends(get_db)):
    config = _public_api_config(request)
    return _render(request, db, user, "usage", "dev_usage.html",
                   **_usage_context(db, user, config))


@router.get("/webhooks", response_class=HTMLResponse)
def developer_webhooks(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    return _render(request, db, user, "webhooks", "dev_webhooks.html",
                   webhooks=_webhooks(db, user.id))


@router.get("/docs", response_class=HTMLResponse)
def developer_docs(request: Request, user=Depends(require_account),
                   db: Session = Depends(get_db)):
    # The origin as the caller's browser sees it, so the copyable curl example
    # works on a laptop, behind the tunnel and in a test alike.
    return _render(request, db, user, "docs", "dev_docs.html",
                   base_url=str(request.base_url).rstrip("/"))


@router.get("/settings", response_class=HTMLResponse)
def developer_settings(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    return _render(request, db, user, "settings", "dev_settings.html")


@router.post("/keys", response_class=HTMLResponse)
def create_key(request: Request, name: str = Form(""),
               scopes: list[str] = Form(default=[]),
               allowed_tools: list[str] = Form(default=[]),
               project_id: str = Form(""), allowed_ips: str = Form(""),
               expires_in_days: str = Form(""),
               csrf_token: str = Form(""), user=Depends(require_account),
               db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/keys")
    try:
        project = (projects.get_owned(db, user_id=user.id, project_id=project_id)
                   if project_id else projects.default_for(db, user_id=user.id))
        if project is None or not project.is_active():
            # Ownership is resolved from the session user, so a forged id
            # simply does not resolve — it never reaches the key.
            return _keys_page(request, db, user,
                              error=_t("Không tìm thấy project."))
        expiry = _expiry_from_days(expires_in_days)
        key, token = devkeys.issue(
            db, user_id=user.id, name=name, scopes=scopes,
            allowed_tools=allowed_tools, project_id=project.id,
            allowed_ips=_split_ips(allowed_ips), expires_at=expiry)
    except Exception as exc:  # noqa: BLE001 - message is for this one customer
        from platform_core.public_api.scopes import ScopeError

        if not isinstance(exc, (devkeys.DeveloperKeyError, ScopeError,
                                projects.ProjectError)):
            raise
        db.rollback()
        return _keys_page(request, db, user, error=str(exc))
    # The plaintext exists only in this response. Nothing stores it, and the
    # page below says so — a customer who closes the tab must create a new key.
    return _keys_page(request, db, user, revealed=token,
                      created_key=key.key_id)


@router.post("/keys/{key_id}/revoke")
def revoke_key(request: Request, key_id: str, csrf_token: str = Form(""),
               user=Depends(require_account), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/keys", status_code=303)
    key = devkeys.get_owned(db, user_id=user.id, key_id=key_id)
    if key is not None:
        devkeys.revoke(db, key)
    # Same redirect whether or not the key existed: a portal must not become a
    # way to find out which key ids belong to somebody else.
    return RedirectResponse("/developers/keys", status_code=303)


@router.post("/keys/{key_id}/rotate", response_class=HTMLResponse)
def rotate_key(request: Request, key_id: str, csrf_token: str = Form(""),
               user=Depends(require_account), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/keys")
    key = devkeys.get_owned(db, user_id=user.id, key_id=key_id)
    if key is None:
        return _keys_page(request, db, user, error=_t("Không tìm thấy khóa."))
    try:
        token = devkeys.rotate(db, key)
    except devkeys.DeveloperKeyError as exc:
        return _keys_page(request, db, user, error=str(exc))
    return _keys_page(request, db, user, revealed=token,
                      created_key=key.key_id)


def _split_ips(value: str) -> list:
    """Accept commas, newlines or spaces — people paste all three."""
    raw = str(value or "").replace("\n", ",").replace(" ", ",")
    return [part.strip() for part in raw.split(",") if part.strip()]


def _expiry_from_days(value: str):
    """Turn "90" into a timestamp, or nothing at all.

    A key with no expiry is the default because most integrations run for years
    and a surprise expiry at 3am is worse than a long-lived key that can be
    revoked in one click. An expiry is offered because a key handed to a
    contractor should stop working on its own.
    """
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        days = int(raw)
    except ValueError as exc:
        raise devkeys.DeveloperKeyError(
            _t("Số ngày hết hạn phải là một số nguyên.")) from exc
    if days <= 0:
        raise devkeys.DeveloperKeyError(
            _t("Số ngày hết hạn phải lớn hơn 0."))
    return datetime.now(timezone.utc) + timedelta(days=days)


@router.post("/projects", response_class=HTMLResponse)
def create_project(request: Request, name: str = Form(""),
                   csrf_token: str = Form(""), user=Depends(require_account),
                   db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/projects")
    try:
        projects.create(db, user_id=user.id, name=name)
    except projects.ProjectError as exc:
        db.rollback()
        return _render(request, db, user, "projects", "dev_projects.html",
                       error=str(exc), **_projects_context(db, user))
    db.commit()
    raise _redirect("/developers/projects")


@router.post("/projects/{project_id}/archive")
def archive_project(request: Request, project_id: str,
                    csrf_token: str = Form(""), user=Depends(require_account),
                    db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/projects", status_code=303)
    project = projects.get_owned(db, user_id=user.id, project_id=project_id)
    if project is not None:
        # Archiving revokes the project's keys and touches nothing else: jobs,
        # ledger entries and usage rows record money that moved, and retiring an
        # integration cannot make them untrue.
        projects.archive(db, project)
        db.commit()
    return RedirectResponse("/developers/projects", status_code=303)
