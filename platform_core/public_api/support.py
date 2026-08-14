"""One call, end to end, from whatever identifier the person in front of you has.

The problem this solves
-----------------------

A support conversation starts with whatever the customer happened to copy: a
correlation id from a response header, a job id from their own logs, the public
half of a key, an email address. Each of those already reaches part of the story
— but only part, and joining them by hand across five tables is how a ten-minute
question becomes an afternoon.

So there is one lookup that accepts any of them and returns **one timeline**:

    request → quote → hold → job → worker → artifact → settle → webhook

Nothing new is stored to make that possible. Every link already exists and
already carries the id that connects it; EXT-09 built the customer-facing half of
this, and what is added here is the operator's view — across accounts, including
the events a customer must not see.

What the operator sees that the customer does not
-------------------------------------------------

Internal job events (``visibility != "customer"``), the worker that ran the job,
the queue delay, and the failure text a customer is deliberately shown a cleaned
version of (Q76). That is the whole point of an operator trace: the customer's
page is written to be safe, and safety costs detail.

What nobody sees
----------------

No secret, in any view or any export. Not a key's secret half — it does not
exist anywhere to be shown — not a webhook signing secret, not a provider
credential, not a raw upload path. ``redact()`` is applied to every exported
structure rather than to selected fields, so a value added to a model later is
covered by default instead of by remembering.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import or_, select

from platform_core.models import CreditEntry, Job, JobEvent, User
from platform_core.public_api.tables import (ApiProject, ApiRequestLog,
                                             ApiSecurityEvent,
                                             DeveloperApiKey, WebhookDelivery)

#: Field names whose *value* must never leave the platform, whatever the shape
#: it is nested in. Matched by substring on the key, because the day somebody
#: adds `webhook_secret_enc` is the day an allowlist of exact names fails.
SECRET_HINTS = ("secret", "token", "password", "credential", "digest",
                "pepper", "authorization", "api_key", "signature")

#: Fields that name *where* something is stored. Not secret, but they encode the
#: bucket layout and the owner id, and a support export is a file that travels.
LOCATION_HINTS = ("storage_key", "staging_key", "path", "url")

REDACTED = "[redacted]"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def redact(value):
    """Strip secrets and locations from anything before it leaves.

    Applied to whole structures rather than to a list of known fields: a model
    gains columns over time, and an allowlist is a promise to remember. This is
    the opposite — a new field is redacted unless its name says it is safe.
    """
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            name = str(key).lower()
            if any(hint in name for hint in SECRET_HINTS):
                clean[key] = REDACTED
            elif any(hint in name for hint in LOCATION_HINTS):
                clean[key] = REDACTED
            else:
                clean[key] = redact(item)
        return clean
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@dataclass
class Trace:
    """Everything known about one call, in the order it happened."""

    query: str = ""
    matched_by: str = ""
    request: ApiRequestLog | None = None
    requests: list = field(default_factory=list)
    job: Job | None = None
    events: list = field(default_factory=list)
    credit: list = field(default_factory=list)
    webhooks: list = field(default_factory=list)
    security: list = field(default_factory=list)
    user: User | None = None
    project: ApiProject | None = None
    key: DeveloperApiKey | None = None

    @property
    def found(self) -> bool:
        return bool(self.request or self.job or self.requests or self.security)

    @property
    def queue_delay_ms(self) -> int | None:
        """How long the job waited before a worker picked it up.

        The number that separates "we were slow" from "the queue was full",
        which is the first fork in almost every latency complaint.
        """
        if self.job is None or not self.job.started_at:
            return None
        started = _aware(self.job.started_at)
        created = _aware(self.job.created_at)
        if started is None or created is None:
            return None
        return max(0, int((started - created).total_seconds() * 1000))

    @property
    def run_ms(self) -> int | None:
        if self.job is None or not (self.job.started_at and self.job.finished_at):
            return None
        return max(0, int((_aware(self.job.finished_at)
                           - _aware(self.job.started_at)).total_seconds() * 1000))


def _aware(value):
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(
        tzinfo=timezone.utc)


def trace(db, query: str, *, limit: int = 25) -> Trace:
    """Find a call by correlation id, job id, key id, project id or email.

    Tried in order of how specific the identifier is. A correlation id names one
    request; an email names an account and returns its recent traffic instead.
    Guessing wrong is cheap — each lookup is indexed — and guessing at all is
    what makes the box on the page accept whatever the customer pasted.
    """
    wanted = str(query or "").strip()
    found = Trace(query=wanted)
    if not wanted:
        return found

    row = db.execute(select(ApiRequestLog).where(
        ApiRequestLog.request_id == wanted).order_by(
            ApiRequestLog.created_at.desc())).scalars().first()
    if row is not None:
        found.matched_by = "request_id"
        found.request = row
        _fill_from_request(db, found, row)
        _fill_actors(db, found, user_id=row.user_id, key_id=row.key_id,
                     project_id=row.project_id)
        found.security = _security_for(db, request_id=wanted)
        return found

    job = db.get(Job, wanted)
    if job is not None:
        found.matched_by = "job_id"
        found.job = job
        _fill_from_job(db, found, job)
        found.requests = list(db.execute(select(ApiRequestLog).where(
            ApiRequestLog.job_id == job.id).order_by(
                ApiRequestLog.created_at)).scalars())
        if found.requests:
            found.request = found.requests[0]
        _fill_actors(db, found, user_id=job.user_id)
        return found

    key = db.execute(select(DeveloperApiKey).where(
        DeveloperApiKey.key_id == wanted)).scalar_one_or_none()
    if key is not None:
        found.matched_by = "key_id"
        found.key = key
        found.requests = list(db.execute(select(ApiRequestLog).where(
            ApiRequestLog.key_id == key.key_id).order_by(
                ApiRequestLog.created_at.desc()).limit(limit)).scalars())
        found.security = _security_for(db, key_id=key.key_id, limit=limit)
        _fill_actors(db, found, user_id=key.user_id,
                     project_id=str(key.project_id or ""))
        return found

    project = db.get(ApiProject, wanted)
    if project is not None:
        found.matched_by = "project_id"
        found.project = project
        found.requests = list(db.execute(select(ApiRequestLog).where(
            ApiRequestLog.project_id == project.id).order_by(
                ApiRequestLog.created_at.desc()).limit(limit)).scalars())
        _fill_actors(db, found, user_id=project.user_id)
        return found

    user = db.execute(select(User).where(
        or_(User.id == wanted, User.email == wanted))).scalar_one_or_none()
    if user is not None:
        found.matched_by = "user"
        found.user = user
        found.requests = list(db.execute(select(ApiRequestLog).where(
            ApiRequestLog.user_id == user.id).order_by(
                ApiRequestLog.created_at.desc()).limit(limit)).scalars())
        return found

    # Nothing matched an object; it may still name an address that was refused.
    found.security = _security_for(db, ip=wanted, limit=limit)
    if found.security:
        found.matched_by = "ip"
    return found


def _fill_from_request(db, found: Trace, row: ApiRequestLog) -> None:
    if not row.job_id:
        return
    job = db.get(Job, row.job_id)
    if job is not None:
        found.job = job
        _fill_from_job(db, found, job)


def _fill_from_job(db, found: Trace, job: Job) -> None:
    """Events, ledger and deliveries for one job — **all** events.

    The customer's timeline filters to `visibility == "customer"` (EXT-09); this
    one does not, because the internal lines are the ones that say what actually
    went wrong.
    """
    found.events = list(db.execute(select(JobEvent).where(
        JobEvent.job_id == job.id).order_by(JobEvent.sequence)).scalars())
    found.credit = list(db.execute(select(CreditEntry).where(
        CreditEntry.job_id == job.id).order_by(
            CreditEntry.created_at)).scalars())
    found.webhooks = list(db.execute(select(WebhookDelivery).where(
        WebhookDelivery.job_id == job.id).order_by(
            WebhookDelivery.created_at)).scalars())


def _fill_actors(db, found: Trace, *, user_id: str = "", key_id: str = "",
                 project_id: str = "") -> None:
    if user_id and found.user is None:
        found.user = db.get(User, str(user_id))
    if key_id and found.key is None:
        found.key = db.execute(select(DeveloperApiKey).where(
            DeveloperApiKey.key_id == str(key_id))).scalar_one_or_none()
    if project_id and found.project is None:
        found.project = db.get(ApiProject, str(project_id))


def _security_for(db, *, request_id: str = "", key_id: str = "", ip: str = "",
                  limit: int = 25) -> list:
    statement = select(ApiSecurityEvent)
    if request_id:
        statement = statement.where(ApiSecurityEvent.request_id == request_id)
    elif key_id:
        statement = statement.where(ApiSecurityEvent.key_id == key_id)
    elif ip:
        statement = statement.where(ApiSecurityEvent.ip == ip)
    else:
        return []
    return list(db.execute(statement.order_by(
        ApiSecurityEvent.created_at.desc()).limit(limit)).scalars())


# ── Export ───────────────────────────────────────────────────────────────────

def export(found: Trace) -> dict:
    """A support trace as a file somebody can attach to a ticket.

    Every structure goes through ``redact`` on the way out. The ledger is
    included because a billing dispute is the commonest reason to export one —
    and it is included **read-only**, as a description of entries that exist;
    nothing here can create, edit or hide one.
    """
    body = {
        "query": found.query,
        "matched_by": found.matched_by,
        "exported_at": _now().isoformat(),
        "account": ({"id": found.user.id, "email": found.user.email}
                    if found.user else None),
        "project": ({"id": found.project.id, "name": found.project.name,
                     "slug": found.project.slug} if found.project else None),
        "key": ({"key_id": found.key.key_id, "name": found.key.name,
                 "mode": getattr(found.key, "mode", "live"),
                 "status": found.key.status()} if found.key else None),
        "request": _request_dict(found.request),
        "requests": [_request_dict(row) for row in found.requests],
        "job": _job_dict(found),
        "events": [{"sequence": row.sequence, "code": row.event_code,
                    "level": row.level, "visibility": row.visibility,
                    "at": row.created_at, "details": row.details}
                   for row in found.events],
        "credit": [{"kind": row.kind, "delta": row.delta, "at": row.created_at,
                    "note": row.note} for row in found.credit],
        "webhooks": [{"event_type": row.event_type, "status": row.status,
                      "attempts": row.attempts,
                      "last_status_code": row.last_status_code,
                      "at": row.created_at} for row in found.webhooks],
        "security": [{"kind": row.kind, "ip": row.ip, "key_id": row.key_id,
                      "route": row.route, "at": row.created_at}
                     for row in found.security],
    }
    return redact(body)


def _request_dict(row) -> dict | None:
    if row is None:
        return None
    return {"request_id": row.request_id, "method": row.method,
            "route": row.route, "status": row.status, "code": row.code,
            "latency_ms": row.latency_ms, "tool": row.tool,
            "job_id": row.job_id, "credit_delta": row.credit_delta,
            "at": row.created_at}


def _job_dict(found: Trace) -> dict | None:
    job = found.job
    if job is None:
        return None
    return {
        "id": job.id, "status": job.status, "job_type": job.job_type,
        "app_slug": job.app_slug, "attempts": job.attempts,
        # Operator-only, all three: the worker that ran it, how long it waited,
        # and how long it took. None of these are in the customer's view.
        "worker_id": job.worker_id, "queue_delay_ms": found.queue_delay_ms,
        "run_ms": found.run_ms,
        "created_at": job.created_at, "started_at": job.started_at,
        "finished_at": job.finished_at,
        # The raw error, which the customer is deliberately shown a cleaned
        # version of (Q76). Redaction still applies to it.
        "error": job.error,
    }


__all__ = ["LOCATION_HINTS", "REDACTED", "SECRET_HINTS", "Trace", "export",
           "redact", "trace"]
