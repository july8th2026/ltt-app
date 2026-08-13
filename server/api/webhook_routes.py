"""``/api/v1/webhooks`` — subscriptions and delivery history.

The secret is returned **once**, at creation, like the developer key: from then
on the platform can still use it (it is encrypted, not hashed — it has to sign
with it) but the API never shows it again, so a leaked listing is not a leaked
signing key.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Body, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core import secretbox
from platform_core.public_api import webhooks
from platform_core.public_api.errors import invalid_request, not_found
from platform_core.public_api.pagination import Page, PageRequest
from platform_core.public_api.principal import Principal
from platform_core.public_api.scopes import SCOPE_WEBHOOKS_MANAGE
from platform_core.public_api.tables import (WebhookDelivery,
                                             WebhookSubscription)
from server.api.auth import require_scope
from server.deps import get_db

_NO_STORE = {"Cache-Control": "no-store"}
MAX_SUBSCRIPTIONS = 5


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.isoformat()


def _public_subscription(subscription, *, secret: str = "") -> dict:
    body = {
        "id": subscription.id,
        "url": subscription.url,
        "events": list(subscription.events or ()),
        "enabled": bool(subscription.enabled),
        "created_at": _iso(subscription.created_at),
    }
    if secret:
        body["secret"] = secret
        body["secret_note"] = "Store this now; it is not shown again."
    return body


def _public_delivery(delivery) -> dict:
    return {
        "id": delivery.id,
        "subscription_id": delivery.subscription_id,
        "event_id": delivery.event_id,
        "event_type": delivery.event_type,
        "job_id": delivery.job_id or None,
        "status": delivery.status,
        "attempts": int(delivery.attempts or 0),
        "last_status_code": int(delivery.last_status_code or 0),
        "next_attempt_at": _iso(delivery.next_attempt_at),
        "delivered_at": _iso(delivery.delivered_at),
    }


def register_webhook_routes(api, config, tag: str) -> None:

    @api.post("/webhooks", tags=[tag], summary="Subscribe to job events",
              description=("Registers an https endpoint for terminal job events. "
                           "The signing secret is returned once."))
    def create_subscription(
        body: dict = Body(...),
        principal: Principal = Depends(require_scope(SCOPE_WEBHOOKS_MANAGE)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        payload = body or {}
        require_https = not getattr(config, "allow_http_webhooks", False)
        url = webhooks.validate_target(str(payload.get("url") or ""),
                                       require_https=require_https)

        wanted = [str(event) for event in (payload.get("events") or ())]
        unknown = sorted(set(wanted) - set(webhooks.TERMINAL_EVENTS))
        if unknown:
            raise invalid_request(
                f"Unknown event type(s): {', '.join(unknown)}.",
                supported=list(webhooks.TERMINAL_EVENTS))

        existing = db.execute(select(WebhookSubscription).where(
            WebhookSubscription.user_id == principal.user_id,
            WebhookSubscription.enabled.is_(True))).scalars().all()
        if len(existing) >= MAX_SUBSCRIPTIONS:
            raise invalid_request(
                f"This account already has {MAX_SUBSCRIPTIONS} webhooks.")

        secret = webhooks.new_secret()
        subscription = WebhookSubscription(
            id=str(uuid.uuid4()), user_id=principal.user_id,
            key_id=principal.key_id, url=url,
            secret_enc=secretbox.ma_hoa(secret),
            events=wanted or list(webhooks.TERMINAL_EVENTS), enabled=True,
            created_at=datetime.now(timezone.utc))
        db.add(subscription)
        db.flush()
        return JSONResponse(_public_subscription(subscription, secret=secret),
                            status_code=201, headers=_NO_STORE)

    @api.get("/webhooks", tags=[tag], summary="List webhook subscriptions",
             description="Owner-scoped. Secrets are never included.")
    def list_subscriptions(
        principal: Principal = Depends(require_scope(SCOPE_WEBHOOKS_MANAGE)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        rows = db.execute(select(WebhookSubscription).where(
            WebhookSubscription.user_id == principal.user_id
        ).order_by(WebhookSubscription.created_at.desc())).scalars().all()
        return JSONResponse({"items": [_public_subscription(row) for row in rows]},
                            headers=_NO_STORE)

    @api.delete("/webhooks/{webhook_id}", tags=[tag],
                summary="Delete a webhook subscription",
                description="Owner-scoped and safe to repeat.")
    def delete_subscription(
        webhook_id: str = Path(...),
        principal: Principal = Depends(require_scope(SCOPE_WEBHOOKS_MANAGE)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        subscription = db.execute(select(WebhookSubscription).where(
            WebhookSubscription.id == str(webhook_id),
            WebhookSubscription.user_id == principal.user_id,
        )).scalar_one_or_none()
        if subscription is None:
            raise not_found("Not found.")
        subscription.enabled = False
        subscription.disabled_at = datetime.now(timezone.utc)
        db.flush()
        return JSONResponse({"id": subscription.id, "enabled": False},
                            headers=_NO_STORE)

    @api.get("/webhooks/deliveries", tags=[tag],
             summary="List webhook delivery attempts",
             description=("Owner-scoped delivery history, newest first — what "
                          "was sent, how often it was retried and why it failed."))
    def list_deliveries(
        status: str = Query(default=""),
        limit: int = Query(default=None),
        offset: int = Query(default=None),
        principal: Principal = Depends(require_scope(SCOPE_WEBHOOKS_MANAGE)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        page_request = PageRequest.parse(limit, offset)
        statement = select(WebhookDelivery).where(
            WebhookDelivery.user_id == principal.user_id)
        if status:
            statement = statement.where(WebhookDelivery.status == str(status))
        rows = db.execute(
            statement.order_by(WebhookDelivery.created_at.desc())
            .offset(page_request.offset).limit(page_request.fetch_limit)
        ).scalars().all()
        page = Page.of([_public_delivery(row) for row in rows], page_request)
        return JSONResponse(page.to_dict(), headers=_NO_STORE)
