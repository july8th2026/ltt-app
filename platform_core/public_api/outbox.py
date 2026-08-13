"""The webhook outbox: enqueue in the job's transaction, deliver from the worker.

Enqueueing is a database insert next to the job's terminal state, so it inherits
that transaction: if the job commits, the event exists; if the job rolls back,
so does the event. No message broker, no "send after commit" hook that a crash
can skip.

Delivery is the worker's job, on its own schedule, with its own retries. Nothing
in the settlement path waits for it — Q84's exactly-once settle must not depend
on somebody else's HTTP endpoint being up.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from platform_core.public_api import webhooks
from platform_core.public_api.tables import (WEBHOOK_DEAD, WEBHOOK_DELIVERED,
                                             WEBHOOK_FAILED, WEBHOOK_PENDING,
                                             WebhookDelivery, WebhookSubscription)

log = logging.getLogger("ltt.public_api.webhooks")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def enqueue_for_job(db, job) -> int:
    """Queue a terminal-state event for every matching subscription.

    Idempotent by construction: the event id is derived from the job and its
    status, and ``(subscription_id, event_id)`` is unique — so a reclaimed job,
    a retried settlement or a double call all produce one delivery.
    """
    event_type = webhooks.job_event_type(job.status)
    if not event_type or not job.user_id:
        return 0

    subscriptions = db.execute(select(WebhookSubscription).where(
        WebhookSubscription.user_id == job.user_id,
        WebhookSubscription.enabled.is_(True),
    )).scalars().all()
    if not subscriptions:
        return 0

    from platform_core.public_api.invocation import api_meta

    tool = api_meta(job).get("tool") or ""
    # Deterministic: the same job in the same terminal state is the same event,
    # whoever asks and however often.
    event_id = uuid.uuid5(uuid.NAMESPACE_URL,
                          f"ltt:job:{job.id}:{job.status}").hex
    payload = webhooks.build_payload(
        event_id=event_id, event_type=event_type, job_id=job.id, tool=tool,
        status=event_type.split(".", 1)[-1])

    queued = 0
    for subscription in subscriptions:
        wanted = list(subscription.events or ())
        if wanted and event_type not in wanted:
            continue
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()), subscription_id=subscription.id,
            user_id=job.user_id, event_id=event_id, event_type=event_type,
            job_id=job.id, payload=payload, status=WEBHOOK_PENDING,
            next_attempt_at=_now(), created_at=_now())
        db.add(delivery)
        try:
            db.flush()
        except IntegrityError:
            # Already queued for this subscription: that is the dedupe working.
            db.rollback()
            continue
        queued += 1
    return queued


def claim_due(db, *, limit: int = 20, now: datetime | None = None) -> list:
    """Deliveries whose backoff has elapsed, oldest first."""
    current = now or _now()
    return list(db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.status.in_((WEBHOOK_PENDING, WEBHOOK_FAILED)),
               WebhookDelivery.next_attempt_at <= current)
        .order_by(WebhookDelivery.next_attempt_at)
        .limit(max(1, min(int(limit), 200)))
    ).scalars().all())


def record_success(db, delivery, *, status_code: int,
                   now: datetime | None = None) -> None:
    delivery.status = WEBHOOK_DELIVERED
    delivery.attempts += 1
    delivery.last_status_code = int(status_code)
    delivery.last_error = ""
    delivery.delivered_at = now or _now()
    db.flush()


def record_failure(db, delivery, *, status_code: int = 0, error: str = "",
                   jitter: float = 0.0, now: datetime | None = None) -> None:
    """Schedule the next attempt, or give up and mark the delivery dead.

    A dead delivery is kept, not deleted: "we tried six times and your endpoint
    refused" is exactly what a customer needs to see, and deleting the evidence
    turns a receiver outage into a mystery.
    """
    delivery.attempts += 1
    delivery.last_status_code = int(status_code or 0)
    # Truncated and free of the URL: an error string from an HTTP client can
    # carry the full target, and a target can carry a token in its query.
    delivery.last_error = str(error or "")[:500]
    if delivery.attempts >= webhooks.MAX_ATTEMPTS:
        delivery.status = WEBHOOK_DEAD
    else:
        delivery.status = WEBHOOK_FAILED
        delivery.next_attempt_at = webhooks.next_attempt_at(
            delivery.attempts, now=now, jitter=jitter)
    db.flush()


def deliver_due(db, *, sender=None, limit: int = 20,
                now: datetime | None = None, jitter: float = 0.0) -> dict:
    """Send what is due. Returns a small report for the worker log.

    ``sender`` is injected so tests can run the whole loop — schedule, signing,
    retry, dead state — against a fake receiver without a socket.
    """
    from platform_core.public_api.delivery import send_delivery

    send = sender or send_delivery
    report = {"attempted": 0, "delivered": 0, "failed": 0, "dead": 0}
    for delivery in claim_due(db, limit=limit, now=now):
        subscription = db.get(WebhookSubscription, delivery.subscription_id)
        if subscription is None or not subscription.enabled:
            record_failure(db, delivery, error="subscription disabled",
                           jitter=jitter, now=now)
            report["failed"] += 1
            continue
        report["attempted"] += 1
        try:
            status_code = send(subscription, delivery)
        except Exception as exc:  # noqa: BLE001 - one bad receiver must not
            # stop the loop for every other customer.
            record_failure(db, delivery, error=f"{type(exc).__name__}",
                           jitter=jitter, now=now)
            report["dead" if delivery.status == WEBHOOK_DEAD else "failed"] += 1
            log.warning("webhook delivery failed delivery=%s attempt=%s reason=%s",
                        delivery.id[:8], delivery.attempts, type(exc).__name__)
            continue
        if 200 <= int(status_code) < 300:
            record_success(db, delivery, status_code=status_code, now=now)
            report["delivered"] += 1
        else:
            record_failure(db, delivery, status_code=status_code,
                           error=f"HTTP {status_code}", jitter=jitter, now=now)
            report["dead" if delivery.status == WEBHOOK_DEAD else "failed"] += 1
    return report
