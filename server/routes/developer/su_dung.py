"""Su dung, ngan sach, viec da chay, nhat ky, thong bao."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core import credit
from platform_core.i18n import N_, _ as _t
from platform_core.models import Job
from platform_core.public_api import keys as devkeys, projects, sandbox, usage
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.invocation import api_meta
from platform_core.public_api.scopes import DEFAULT_SCOPES, KNOWN_SCOPES
from platform_core.public_api.tables import WebhookSubscription
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

from server.routes.developer._chung import (  # noqa: F401
    STATUS_CHOICES, _public_api_config, _recent_api_jobs, _redirect, _render, _usage_page, require_account, router)


@router.get("/logs", response_class=HTMLResponse)
def developer_logs(request: Request, request_id: str = "", status: str = "",
                   tool: str = "", key_id: str = "",
                   user=Depends(require_account),
                   db: Session = Depends(get_db)):
    """This account's own API calls — including the ones that never ran.

    A job explains a job. Nothing else explained the 401 that stopped an
    integration, the 403 that named a scope the developer thought they had, or
    the 429 that arrived when their queue backed up; those are exactly the calls
    somebody needs to look up, and until now only an operator could.
    """
    from platform_core.public_api import request_log

    config = _public_api_config(request)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = request_log.list_for(db, user_id=user.id, request_id=request_id,
                                status=status, tool=tool, key_id=key_id,
                                limit=100)
    return _render(
        request, db, user, "logs", "dev_logs.html",
        rows=rows,
        counts=request_log.counts(db, user_id=user.id, since=since),
        retention_days=request_log.RETENTION_DAYS,
        tools=[item.name for item in build_catalog(config)],
        keys=[{"key_id": key.key_id, "name": key.name}
              for key in devkeys.list_for_user(db, user.id)],
        status_choices=[(value, _t(label)) for value, label in STATUS_CHOICES],
        filters={"request_id": request_id, "status": status, "tool": tool,
                 "key_id": key_id,
                 "any": bool(request_id or status or tool or key_id)})


@router.get("/logs/{wanted_id}", response_class=HTMLResponse)
def developer_log_detail(request: Request, wanted_id: str,
                         user=Depends(require_account),
                         db: Session = Depends(get_db)):
    """One request, and everything reachable from it.

    Assembled from rows that already exist — the job, its customer-visible
    events, the ledger entries, the artifacts, the webhook deliveries. Storing a
    second copy of any of that would be a second thing to keep true.
    """
    from platform_core.public_api import request_log
    from platform_core.public_api.error_registry import REGISTRY

    row = request_log.get_owned(db, user_id=user.id, request_id=wanted_id)
    if row is None:
        # Same 404 a request that never existed gets: a log page must not
        # confirm that somebody else's request id is real.
        raise _redirect("/developers/logs", status_code=404)
    spec = REGISTRY.get(row.code)
    names = {project.id: project.name
             for project in projects.list_for(db, user_id=user.id,
                                              include_archived=True)}
    return _render(
        request, db, user, "logs", "dev_log_detail.html",
        section_title=row.request_id[:8],
        row=row, timeline=request_log.timeline(db, row),
        project_name=names.get(row.project_id, ""),
        advice=({"action": spec.action, "retry": spec.retry,
                 "reuse_idempotency_key": spec.reuse_idempotency_key}
                if spec is not None else None))


@router.get("/jobs", response_class=HTMLResponse)
def developer_jobs(request: Request, user=Depends(require_account),
                   db: Session = Depends(get_db)):
    return _render(request, db, user, "jobs", "dev_jobs.html",
                   recent_jobs=_recent_api_jobs(db, user.id))


@router.get("/usage", response_class=HTMLResponse)
def developer_usage(request: Request, tool: str = "", key_id: str = "",
                    status: str = "", user=Depends(require_account),
                    db: Session = Depends(get_db)):
    return _usage_page(request, db, user, tool=tool, key_id=key_id,
                       status=status)


@router.post("/budgets", response_class=HTMLResponse)
def developer_create_budget(request: Request, amount: str = Form(""),
                            period: str = Form("month"),
                            project_id: str = Form(""),
                            hard_cap: str = Form(""),
                            csrf_token: str = Form(""),
                            user=Depends(require_account),
                            db: Session = Depends(get_db)):
    from platform_core.public_api import budgets as budget_mod

    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/usage")
    scope = (budget_mod.SCOPE_PROJECT if project_id
             else budget_mod.SCOPE_ACCOUNT)
    try:
        budget_mod.create(db, user_id=user.id, amount=amount, period=period,
                          scope=scope, project_id=project_id,
                          hard_cap=bool(hard_cap))
    except budget_mod.BudgetError as exc:
        db.rollback()
        return _usage_page(request, db, user, error=str(exc))
    db.commit()
    raise _redirect("/developers/usage")


@router.post("/budgets/{budget_id}/delete")
def developer_delete_budget(request: Request, budget_id: str,
                            csrf_token: str = Form(""),
                            user=Depends(require_account),
                            db: Session = Depends(get_db)):
    from platform_core.public_api import budgets as budget_mod

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/usage", status_code=303)
    budget = budget_mod.get_owned(db, user_id=user.id, budget_id=budget_id)
    if budget is not None:
        db.delete(budget)
        db.commit()
    return RedirectResponse("/developers/usage", status_code=303)


@router.get("/notifications", response_class=HTMLResponse)
def developer_notifications(request: Request, user=Depends(require_account),
                            db: Session = Depends(get_db)):
    from platform_core.public_api import notifications

    return _render(request, db, user, "notifications",
                   "dev_notifications.html",
                   rows=notifications.list_for(db, user_id=user.id))


@router.post("/notifications/read")
def developer_notifications_read(request: Request, csrf_token: str = Form(""),
                                 user=Depends(require_account),
                                 db: Session = Depends(get_db)):
    from platform_core.public_api import notifications

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/notifications", status_code=303)
    notifications.mark_all_read(db, user_id=user.id)
    db.commit()
    return RedirectResponse("/developers/notifications", status_code=303)
