"""Rieng tu: xem va xuat du lieu cua chinh minh."""
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
    _render, require_account, router)


@router.get("/privacy", response_class=HTMLResponse)
def developer_privacy(request: Request, user=Depends(require_account),
                      db: Session = Depends(get_db)):
    """What this area keeps about you, for how long, and why.

    Built from `governance.STORES` rather than written by hand, so the page
    cannot drift from the policy the worker actually enforces — a privacy page
    that describes a retention rule nobody runs is the worst kind of wrong.
    """
    from platform_core.public_api import governance

    # Translated here rather than in the template: a privacy page the reader
    # cannot read is not a disclosure.
    classes = [(klass, [governance.translated(store)
                        for store in governance.by_class(klass)])
               for klass in governance.CLASSES]
    return _render(request, db, user, "privacy", "dev_privacy.html",
                   classes=classes, legal=governance.LEGAL_LINKS)


@router.get("/privacy/export")
def developer_privacy_export(request: Request, user=Depends(require_account),
                             db: Session = Depends(get_db)):
    """The API area's data about this account, as a file.

    Scoped to this area on purpose. A whole-account export would have to speak
    for every app's tables as well, and promising that from here would be a
    promise this code cannot keep — so the page says what is and is not in it.

    Redacted with the same function the support trace uses: one definition of
    "what must never leave", applied in both directions.
    """
    import json

    from sqlalchemy import select
    from starlette.responses import Response

    from platform_core import credit
    from platform_core.models import CreditEntry, Job
    from platform_core.public_api import projects, request_log, support, usage
    from platform_core.public_api.invocation import api_meta
    from platform_core.public_api.tables import ApiBudget, WebhookSubscription

    keys = devkeys.list_for_user(db, user.id)
    jobs = [job for job in db.execute(
        select(Job).where(Job.user_id == user.id)
        .order_by(Job.created_at.desc()).limit(500)).scalars()
        if api_meta(job)]

    body = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "scope": _t("Khu API của tài khoản này. KHÔNG bao gồm nội dung do từng "
                    "app lưu (chat, storyboard, workflow…) — mỗi app giữ dữ "
                    "liệu của nó, và trang này không nói thay được."),
        "account": {"id": user.id, "email": user.email,
                    "created_at": user.created_at,
                    "credit_balance": credit.so_du(db, user.id)},
        "projects": [{"id": row.id, "name": row.name, "slug": row.slug,
                      "status": row.status, "created_at": row.created_at}
                     for row in projects.list_for(db, user_id=user.id,
                                                  include_archived=True)],
        # Public halves only. The secret half is not stored anywhere, so there
        # is nothing here to withhold.
        "api_keys": [{"key_id": row.key_id, "name": row.name,
                      "mode": getattr(row, "mode", "live"),
                      "status": row.status(), "created_at": row.created_at,
                      "last_used_at": row.last_used_at} for row in keys],
        "jobs": [{"id": job.id, "tool": api_meta(job).get("tool"),
                  "status": job.status, "created_at": job.created_at,
                  "finished_at": job.finished_at} for job in jobs],
        "credit_entries": [
            {"kind": row.kind, "delta": row.delta, "job_id": row.job_id,
             "note": row.note, "created_at": row.created_at}
            for row in db.execute(select(CreditEntry).where(
                CreditEntry.user_id == user.id)
                .order_by(CreditEntry.created_at)).scalars()],
        "budgets": [{"scope": row.scope, "period": row.period,
                     "amount": row.amount, "hard_cap": row.hard_cap}
                    for row in db.execute(select(ApiBudget).where(
                        ApiBudget.user_id == user.id)).scalars()],
        "webhooks": [{"url": row.url, "events": list(row.events or ()),
                      "enabled": row.enabled, "created_at": row.created_at}
                     for row in db.execute(select(WebhookSubscription).where(
                         WebhookSubscription.user_id == user.id)).scalars()],
        "recent_requests": [
            {"request_id": row.request_id, "method": row.method,
             "route": row.route, "status": row.status, "code": row.code,
             "created_at": row.created_at}
            for row in request_log.list_for(db, user_id=user.id, limit=200)],
    }

    name = f"ltt-api-data-{user.id[:8]}.json"
    return Response(
        json.dumps(support.redact(body), ensure_ascii=False, indent=2,
                   default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}"',
                 "Cache-Control": "no-store"})
