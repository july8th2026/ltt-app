"""Alerts a developer sees, with the deduplication that keeps them worth seeing.

An alerting feature fails in one of two directions and both are bad. Too quiet
and the customer finds out from their invoice. Too loud and they filter the
whole channel, which is the same as too quiet but harder to notice.

So every alert has a **subject** — the specific thing it is about, like one key
id or one threshold of one budget — and a **cooldown**. The same subject cannot
raise the same alert twice inside its cooldown, and crossing 80% does not send
80% again tomorrow if nothing changed. Deduplication is on the row, not in the
sender: any code path that emits gets it.

Channels are the ones the platform already has: a row a portal page reads, plus
email through ``platform_core.mailer``. No SMS, no push, no third service to
own — COMMON_RULES §6, and the same reasoning that kept Redis out.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from platform_core.public_api.tables import ApiNotification

# What can be raised. Each is a thing the customer can act on; nothing here is
# informational-only, because an alert nobody can act on is noise by definition.
LOW_CREDIT = "credit.low"
BUDGET_THRESHOLD = "budget.threshold"
BUDGET_EXCEEDED = "budget.exceeded"
QUOTA_NEAR = "quota.near"
QUOTA_EXCEEDED = "quota.exceeded"
KEY_EXPIRING = "key.expiring"
WEBHOOK_FAILING = "webhook.failing"
PROJECT_SUSPENDED = "project.suspended"

KINDS = (LOW_CREDIT, BUDGET_THRESHOLD, BUDGET_EXCEEDED, QUOTA_NEAR,
         QUOTA_EXCEEDED, KEY_EXPIRING, WEBHOOK_FAILING, PROJECT_SUSPENDED)

#: How long the same subject stays quiet after being raised. Long enough that a
#: customer is not paged by a condition they have already seen; short enough
#: that a condition still true tomorrow is raised again.
COOLDOWN = {
    LOW_CREDIT: timedelta(days=1),
    BUDGET_THRESHOLD: timedelta(days=1),
    BUDGET_EXCEEDED: timedelta(days=1),
    QUOTA_NEAR: timedelta(hours=6),
    QUOTA_EXCEEDED: timedelta(hours=6),
    KEY_EXPIRING: timedelta(days=3),
    WEBHOOK_FAILING: timedelta(hours=12),
    PROJECT_SUSPENDED: timedelta(days=7),
}
DEFAULT_COOLDOWN = timedelta(days=1)

#: Which alerts are worth an email as well as a page a customer may not visit.
#: The test is simple: would they want to be interrupted? Money and credentials,
#: yes; a threshold they set themselves to be informative, on the page only.
EMAIL_KINDS = frozenset({LOW_CREDIT, BUDGET_EXCEEDED, QUOTA_EXCEEDED,
                         KEY_EXPIRING, PROJECT_SUSPENDED})

RETENTION_DAYS = 90


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value):
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(
        tzinfo=timezone.utc)


def raise_alert(db, *, user_id: str, kind: str, subject: str = "",
                title: str = "", body: str = "", now: datetime | None = None):
    """Record an alert unless the same subject is still in cooldown.

    Returns the row, or ``None`` when it was suppressed. Callers may run on a
    schedule and re-detect the same condition every pass; suppression here is
    what makes that safe.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown notification kind: {kind}")
    current = now or _now()
    since = current - COOLDOWN.get(kind, DEFAULT_COOLDOWN)
    recent = db.execute(select(ApiNotification).where(
        ApiNotification.user_id == str(user_id or ""),
        ApiNotification.kind == kind,
        ApiNotification.subject == str(subject or ""),
        ApiNotification.created_at >= since,
    )).scalars().first()
    if recent is not None:
        return None

    row = ApiNotification(
        id=str(uuid.uuid4()), user_id=str(user_id or ""), kind=kind,
        subject=str(subject or "")[:120], title=str(title or "")[:200],
        body=str(body or "")[:1000], created_at=current)
    db.add(row)
    return row


def list_for(db, *, user_id: str, unread_only: bool = False,
             limit: int = 50) -> list:
    statement = select(ApiNotification).where(
        ApiNotification.user_id == str(user_id or ""))
    if unread_only:
        statement = statement.where(ApiNotification.read_at.is_(None))
    return list(db.execute(
        statement.order_by(ApiNotification.created_at.desc())
        .limit(int(limit))).scalars().all())


def unread_count(db, *, user_id: str) -> int:
    from sqlalchemy import func

    return int(db.execute(select(func.count(ApiNotification.id)).where(
        ApiNotification.user_id == str(user_id or ""),
        ApiNotification.read_at.is_(None))).scalar_one())


def mark_all_read(db, *, user_id: str, now: datetime | None = None) -> int:
    rows = list_for(db, user_id=user_id, unread_only=True, limit=500)
    current = now or _now()
    for row in rows:
        row.read_at = current
    return len(rows)


def send_email_for(db, row, *, mailer=None) -> bool:
    """Email the ones worth interrupting somebody for. Best effort.

    A failed email must not lose the alert: the row is already stored and the
    portal shows it either way, so this returns False rather than raising.
    """
    if row is None or row.kind not in EMAIL_KINDS:
        return False

    from platform_core.i18n import _ as _t
    from platform_core.mailer import Email, get_mailer
    from platform_core.models import User

    user = db.get(User, row.user_id)
    if user is None or not user.email:
        return False
    body = f"{row.title}\n\n{row.body}\n\nhttps://app.lttstudios.com/developers/notifications"
    try:
        (mailer or get_mailer()).send(Email(
            to=user.email, subject=row.title,
            html=f"<p>{row.body}</p>"
                 f'<p><a href="https://app.lttstudios.com/developers/'
                 f'notifications">{_t("Mở khu API")}</a></p>',
            text=body))
        return True
    except Exception:                            # noqa: BLE001 - see docstring
        import logging

        logging.getLogger(__name__).warning(
            "could not email notification %s", row.kind, exc_info=True)
        return False


def purge_expired(db, *, days: int = RETENTION_DAYS,
                  now: datetime | None = None) -> int:
    from sqlalchemy import delete

    cutoff = (now or _now()) - timedelta(days=int(days))
    result = db.execute(
        delete(ApiNotification).where(ApiNotification.created_at < cutoff))
    return int(result.rowcount or 0)
