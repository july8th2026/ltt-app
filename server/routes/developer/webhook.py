"""Dang ky webhook: thu, xoay khoa ky, tat, gui lai."""
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
    SECRET_ONCE_KEY, VERIFY_SNIPPET, _all_webhooks, _render, require_account, router)


@router.get("/webhooks", response_class=HTMLResponse)
def developer_webhooks(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    from platform_core.public_api import webhook_console, webhooks as hooks

    catalog = [
        (hooks.EVENT_JOB_SUCCEEDED, _t("Job kết thúc thành công.")),
        (hooks.EVENT_JOB_FAILED, _t("Job hỏng — credit đã được hoàn.")),
        (hooks.EVENT_JOB_CANCELLED, _t("Job bị hủy — credit đã được hoàn.")),
        (webhook_console.EVENT_TEST,
         _t("Bạn bấm Gửi thử. Không job nào chạy, không credit nào chuyển.")),
    ]
    return _render(
        request, db, user, "webhooks", "dev_webhooks.html",
        subscriptions=_all_webhooks(db, user.id),
        deliveries=webhook_console.deliveries_for(db, user_id=user.id),
        health=webhook_console.health(db, user_id=user.id),
        event_catalog=catalog, payload_version=hooks.SIGNATURE_VERSION,
        headers={"signature": hooks.SIGNATURE_HEADER,
                 "timestamp": hooks.TIMESTAMP_HEADER,
                 "event": hooks.EVENT_HEADER},
        verify_snippet=VERIFY_SNIPPET,
        tolerance_s=300,
        grace_hours=int(webhook_console.ROTATION_GRACE.total_seconds() // 3600),
        # Popped: shown on exactly one render, and gone even if the page is
        # reloaded or shared.
        revealed_secret=request.session.pop(SECRET_ONCE_KEY, ""))


@router.post("/webhooks/{subscription_id}/test")
def developer_webhook_test(request: Request, subscription_id: str,
                           csrf_token: str = Form(""),
                           user=Depends(require_account),
                           db: Session = Depends(get_db)):
    """Queue a test event. Nothing runs and nothing is charged."""
    from platform_core.public_api import webhook_console

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/webhooks", status_code=303)
    subscription = webhook_console.owned_subscription(
        db, user_id=user.id, subscription_id=subscription_id)
    if subscription is not None and subscription.enabled:
        webhook_console.send_test(db, subscription)
        db.commit()
    return RedirectResponse("/developers/webhooks", status_code=303)


@router.post("/webhooks/{subscription_id}/rotate")
def developer_webhook_rotate(request: Request, subscription_id: str,
                             csrf_token: str = Form(""),
                             user=Depends(require_account),
                             db: Session = Depends(get_db)):
    from platform_core.public_api import webhook_console

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/webhooks", status_code=303)
    subscription = webhook_console.owned_subscription(
        db, user_id=user.id, subscription_id=subscription_id)
    if subscription is None:
        return RedirectResponse("/developers/webhooks", status_code=303)
    secret = webhook_console.rotate_secret(db, subscription)
    db.commit()
    # Handed over through the session, not the URL: a query string ends up in
    # browser history, in the Referer of the next click and in every access log
    # between here and the browser. The next render pops it.
    request.session[SECRET_ONCE_KEY] = secret
    return RedirectResponse("/developers/webhooks", status_code=303)


@router.post("/webhooks/{subscription_id}/disable")
def developer_webhook_disable(request: Request, subscription_id: str,
                              csrf_token: str = Form(""),
                              user=Depends(require_account),
                              db: Session = Depends(get_db)):
    from datetime import datetime as _dt

    from platform_core.public_api import webhook_console

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/webhooks", status_code=303)
    subscription = webhook_console.owned_subscription(
        db, user_id=user.id, subscription_id=subscription_id)
    if subscription is not None:
        # Disabled, not deleted: the delivery history is the evidence of what
        # this endpoint was told, and deleting the subscription would orphan it.
        subscription.enabled = False
        subscription.disabled_at = _dt.now(timezone.utc)
        db.commit()
    return RedirectResponse("/developers/webhooks", status_code=303)


@router.post("/webhooks/deliveries/{delivery_id}/resend")
def developer_webhook_resend(request: Request, delivery_id: str,
                             csrf_token: str = Form(""),
                             user=Depends(require_account),
                             db: Session = Depends(get_db)):
    """Try the same event again — same id, same payload, no job, no credit."""
    from platform_core.public_api import webhook_console

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/webhooks", status_code=303)
    delivery = webhook_console.owned_delivery(db, user_id=user.id,
                                              delivery_id=delivery_id)
    if delivery is None:
        return RedirectResponse("/developers/webhooks", status_code=303)
    try:
        webhook_console.resend(db, delivery)
        db.commit()
    except webhook_console.WebhookConsoleError:
        db.rollback()
    return RedirectResponse("/developers/webhooks", status_code=303)
