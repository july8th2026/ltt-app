"""Operations a webhook owner needs: resend, test, rotate, disable.

Each of these is a small function with one sharp rule behind it, and the rules
are what make them safe to offer at all.

**Resend never re-runs anything.** It queues the *same* event id with the *same*
payload for another delivery attempt. It does not touch the job, does not touch
the ledger, and cannot: nothing here reads or writes either. That matters because
a support conversation that ends in "just resend it" must not be a way to
re-charge a customer, and because the receiver's own idempotency key is the
event id — a resend carrying a fresh id would look like a second event and could
be processed twice on their side.

**A test event is clearly a test.** It has its own event type, no job id, and a
payload that says so. A receiver that treats it as a real completion is a
receiver whose author was misled, so the payload does not pretend.

**Rotation has a grace window.** Deliveries in flight were signed with the old
secret; a rotation that took effect instantly would fail every one of them at a
receiver that had already switched. So both signatures are sent during the
window, and the receiver may accept either.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from platform_core.public_api import webhooks
from platform_core.public_api.tables import (WEBHOOK_DEAD, WEBHOOK_FAILED,
                                             WEBHOOK_PENDING, WebhookDelivery,
                                             WebhookSubscription)

#: How many manual resends one account may ask for per hour. A resend is a
#: request *we* make to somebody else's server; an unbounded button is an
#: outbound amplifier pointed at whatever URL the customer configured.
RESEND_LIMIT_PER_HOUR = 20

#: Both secrets are accepted for this long after a rotation.
ROTATION_GRACE = timedelta(hours=24)

EVENT_TEST = "webhook.test"


class WebhookConsoleError(Exception):
    """Refusal a human caused and a human can fix."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value):
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(
        tzinfo=timezone.utc)


def owned_subscription(db, *, user_id: str, subscription_id: str):
    return db.execute(select(WebhookSubscription).where(
        WebhookSubscription.id == str(subscription_id or ""),
        WebhookSubscription.user_id == str(user_id or ""),
    )).scalar_one_or_none()


def owned_delivery(db, *, user_id: str, delivery_id: str):
    return db.execute(select(WebhookDelivery).where(
        WebhookDelivery.id == str(delivery_id or ""),
        WebhookDelivery.user_id == str(user_id or ""),
    )).scalar_one_or_none()


def deliveries_for(db, *, user_id: str, subscription_id: str = "",
                   status: str = "", limit: int = 50) -> list:
    statement = select(WebhookDelivery).where(
        WebhookDelivery.user_id == str(user_id or ""))
    if subscription_id:
        statement = statement.where(
            WebhookDelivery.subscription_id == str(subscription_id))
    if status:
        statement = statement.where(WebhookDelivery.status == str(status))
    return list(db.execute(
        statement.order_by(WebhookDelivery.created_at.desc())
        .limit(int(limit))).scalars().all())


def health(db, *, user_id: str) -> dict:
    """What the console shows at the top: is anything stuck."""
    rows = db.execute(
        select(WebhookDelivery.status, func.count(WebhookDelivery.id))
        .where(WebhookDelivery.user_id == str(user_id or ""))
        .group_by(WebhookDelivery.status)).all()
    counts = {str(status): int(total) for status, total in rows}
    return {"pending": counts.get(WEBHOOK_PENDING, 0),
            "delivered": counts.get("delivered", 0),
            "failed": counts.get(WEBHOOK_FAILED, 0),
            "dead": counts.get(WEBHOOK_DEAD, 0)}


def resend(db, delivery, *, now: datetime | None = None) -> WebhookDelivery:
    """Queue another attempt at the same event. Caller commits.

    The row is reused rather than copied: same id, same event id, same payload,
    attempts reset to zero and due immediately. A copy would be a second event
    to the receiver, and their deduplication — which is the event id — would not
    save them.
    """
    current = now or _now()
    if _recent_resends(db, user_id=delivery.user_id, since=current
                       - timedelta(hours=1)) >= RESEND_LIMIT_PER_HOUR:
        raise WebhookConsoleError(
            f"At most {RESEND_LIMIT_PER_HOUR} manual resends per hour.")

    delivery.status = WEBHOOK_PENDING
    delivery.attempts = 0
    delivery.next_attempt_at = current
    delivery.last_error = ""
    delivery.last_status_code = 0
    delivery.delivered_at = None
    # Audit trail: who asked, and when. Kept on the row rather than in a second
    # table, because the only question anyone asks is "was this one resent".
    payload = dict(delivery.payload or {})
    resends = int(payload.get("_resends") or 0) + 1
    payload["_resends"] = resends
    payload["_resent_at"] = current.isoformat()
    delivery.payload = payload
    return delivery


def _recent_resends(db, *, user_id: str, since: datetime) -> int:
    rows = db.execute(select(WebhookDelivery).where(
        WebhookDelivery.user_id == str(user_id or ""))).scalars().all()
    total = 0
    for row in rows:
        payload = row.payload or {}
        stamp = payload.get("_resent_at")
        if not stamp:
            continue
        try:
            when = datetime.fromisoformat(str(stamp))
        except ValueError:
            continue
        if _aware(when) >= since:
            total += int(payload.get("_resends") or 1)
    return total


def send_test(db, subscription, *, now: datetime | None = None) -> WebhookDelivery:
    """Queue a test event for this subscription. Caller commits.

    A distinct event type and no job id, so a receiver can tell instantly that
    nothing ran and nothing was charged. Wiring is exactly the real one: the
    same outbox row, the same worker, the same signature.
    """
    current = now or _now()
    event_id = webhooks.new_event_id()
    payload = {
        "id": event_id,
        "type": EVENT_TEST,
        "created_at": current.isoformat(),
        "data": {"message": "This is a test event. No job ran and no credit "
                            "moved.",
                 "subscription_id": subscription.id},
    }
    delivery = WebhookDelivery(
        id=str(uuid.uuid4()), subscription_id=subscription.id,
        user_id=subscription.user_id, event_id=event_id, event_type=EVENT_TEST,
        job_id="", payload=payload, status=WEBHOOK_PENDING,
        next_attempt_at=current, created_at=current)
    db.add(delivery)
    return delivery


def rotate_secret(db, subscription, *, now: datetime | None = None) -> str:
    """New signing secret, old one honoured for the grace window.

    Returns the plaintext **once**. The same encryption the subscription
    already uses (`platform_core.secretbox`) — the server has to reproduce this
    secret to sign, which is exactly why it is encrypted rather than hashed.
    """
    from platform_core import secretbox

    current = now or _now()
    previous = secretbox.giai_ma(subscription.secret_enc)
    fresh = webhooks.new_secret()
    subscription.secret_enc = secretbox.ma_hoa(fresh)
    subscription.previous_secret_enc = secretbox.ma_hoa(previous)
    subscription.previous_secret_until = current + ROTATION_GRACE
    return fresh


def grace_secret(subscription, *, now: datetime | None = None):
    """The old secret while it is still honoured, else None."""
    from platform_core import secretbox

    until = _aware(getattr(subscription, "previous_secret_until", None))
    if not until or until <= (now or _now()):
        return None
    blob = getattr(subscription, "previous_secret_enc", "") or ""
    return secretbox.giai_ma(blob) if blob else None
