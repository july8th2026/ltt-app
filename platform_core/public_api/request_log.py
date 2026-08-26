"""One row per public API request, so a developer can debug their own calls.

Why a table when there is already a log line
--------------------------------------------

``ltt.public_api.access`` writes a structured line per request, and that is
enough for an operator with shell access. It is not enough for the person who
actually needs it: a customer cannot grep our disk, cannot filter by their own
account, and — most importantly — the calls they most need to understand never
reach anything else that is stored. A job explains a job; nothing explains the
401 that stopped them, the 403 that named a scope they thought they had, or the
429 that arrived when their queue backed up.

What is deliberately **not** stored
-----------------------------------

* **No request or response body.** Not truncated, not "just the first 200
  characters" — none. Payloads are where customer content and prompts live, and
  a debugging table is the last place that should quietly become a copy of them.
* **No `detail` string.** Validation details can echo a caller's own input back;
  the stable ``code`` is what a client branches on anyway.
* **No credential.** ``key_id`` is the public half and is already what a support
  conversation refers to.

What that leaves is the skeleton of a call — who, what, how it ended, how long
it took, what it cost — which is exactly what makes a request explainable
without becoming a second copy of the request.

Retention is part of the design rather than a later prompt's problem: this table
grows with every request, and the platform already learned that lesson from
``webhook_deliveries``, which had no policy until an audit found it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from platform_core.public_api.tables import ApiRequestLog

#: How long a customer can still look a request up. Long enough to debug last
#: week's incident, short enough that the table is not an archive.
RETENTION_DAYS = 30

#: A single page of history. Same ceiling as the API's own listings.
MAX_PAGE = 100


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record(db, *, request_id: str, user_id: str, key_id: str = "",
           project_id: str = "", method: str = "", route: str = "",
           status: int = 0, code: str = "", latency_ms: float = 0.0,
           tool: str = "", job_id: str = "", credit_delta: int = 0,
           now: datetime | None = None) -> ApiRequestLog:
    """Write one request row. Caller commits.

    Deliberately tolerant about missing pieces: an unauthenticated failure has
    no key, no project and no tool, and it is precisely the row a developer
    needs most.
    """
    row = ApiRequestLog(
        id=str(uuid.uuid4()),
        request_id=str(request_id or "")[:64],
        user_id=str(user_id or ""),
        key_id=str(key_id or "")[:48],
        project_id=str(project_id or "")[:36],
        method=str(method or "")[:8],
        route=str(route or "")[:200],
        status=int(status or 0),
        code=str(code or "")[:48],
        latency_ms=int(max(0.0, latency_ms)),
        tool=str(tool or "")[:64],
        job_id=str(job_id or "")[:36],
        credit_delta=int(credit_delta or 0),
        created_at=now or _now(),
    )
    db.add(row)
    return row


def list_for(db, *, user_id: str, since: datetime | None = None,
             until: datetime | None = None, status: str = "", code: str = "",
             tool: str = "", key_id: str = "", request_id: str = "",
             failures_only: bool = False, limit: int = 50,
             offset: int = 0) -> list:
    """This account's requests, newest first.

    Ownership is in the query rather than checked afterwards, for the same
    reason it is everywhere else on this surface: a filter that is applied by
    the caller is a filter somebody eventually forgets.
    """
    statement = select(ApiRequestLog).where(
        ApiRequestLog.user_id == str(user_id or ""))
    if since is not None:
        statement = statement.where(ApiRequestLog.created_at >= since)
    if until is not None:
        statement = statement.where(ApiRequestLog.created_at <= until)
    if request_id:
        statement = statement.where(
            ApiRequestLog.request_id == str(request_id).strip())
    if code:
        statement = statement.where(ApiRequestLog.code == str(code).strip())
    if tool:
        statement = statement.where(ApiRequestLog.tool == str(tool).strip())
    if key_id:
        statement = statement.where(ApiRequestLog.key_id == str(key_id).strip())
    if status:
        text = str(status).strip()
        if text.endswith("xx") and text[:1].isdigit():
            # "4xx" is how a person thinks about a class of failures.
            first = int(text[0])
            statement = statement.where(
                ApiRequestLog.status >= first * 100,
                ApiRequestLog.status < (first + 1) * 100)
        elif text.isdigit():
            statement = statement.where(ApiRequestLog.status == int(text))
    if failures_only:
        statement = statement.where(ApiRequestLog.status >= 400)
    statement = statement.order_by(ApiRequestLog.created_at.desc())
    return list(db.execute(
        statement.limit(min(int(limit), MAX_PAGE)).offset(max(0, int(offset)))
    ).scalars().all())


def get_owned(db, *, user_id: str, request_id: str):
    return db.execute(select(ApiRequestLog).where(
        ApiRequestLog.user_id == str(user_id or ""),
        ApiRequestLog.request_id == str(request_id or ""),
    ).order_by(ApiRequestLog.created_at.desc())).scalars().first()


def timeline(db, row) -> dict:
    """Everything reachable from one request, assembled for a detail page.

    Nothing new is stored to make this possible: the job, its events, the ledger
    entries and the webhook deliveries already exist and already carry the ids
    that connect them. A request log that duplicated them would be a second copy
    to keep true.
    """
    from platform_core.models import CreditEntry, Job, JobEvent
    from platform_core.public_api import media
    from platform_core.public_api.tables import WebhookDelivery

    found: dict = {"job": None, "events": [], "credit": [], "artifacts": [],
                   "webhooks": []}
    if not row or not row.job_id:
        return found

    job = db.execute(select(Job).where(
        Job.id == row.job_id, Job.user_id == row.user_id)).scalar_one_or_none()
    if job is None:
        return found
    found["job"] = job
    found["events"] = list(db.execute(
        select(JobEvent).where(
            JobEvent.job_id == job.id,
            # Operator-only lines stay operator-only, even for the job's owner.
            JobEvent.visibility == "customer",
        ).order_by(JobEvent.sequence)).scalars().all())
    found["credit"] = list(db.execute(
        select(CreditEntry).where(
            CreditEntry.job_id == job.id,
            CreditEntry.user_id == row.user_id,
        ).order_by(CreditEntry.created_at)).scalars().all())
    found["webhooks"] = list(db.execute(
        select(WebhookDelivery).where(
            WebhookDelivery.job_id == job.id,
            WebhookDelivery.user_id == row.user_id,
        ).order_by(WebhookDelivery.created_at)).scalars().all())

    tool = None
    if row.tool:
        from platform_core.public_api.catalog import build_catalog
        from platform_core.public_api.config import load_public_api_config

        config = load_public_api_config({"LTT_PUBLIC_API": "1",
                                         "LTT_PUBLIC_API_TOOLS": row.tool})
        for candidate in build_catalog(config):
            if candidate.name == row.tool:
                tool = candidate
                break
    if tool is not None:
        found["artifacts"] = media.artifacts_of(job, tool)
    return found


def daily(db, *, user_id: str, since: datetime,
          until: datetime | None = None) -> list:
    """Requests, failures and credit bucketed by calendar day (UTC).

    Read-only, and deliberately bucketed in Python rather than with a
    ``GROUP BY date(...)``: the two databases in play (SQLite in the harness,
    PostgreSQL in production) disagree on how ``date()`` treats a timezone-aware
    column, and a chart is the last place to discover that. The window is capped
    at the retention horizon, the query is served by
    ``ix_public_api_requests_owner_time``, and every day in range is emitted —
    **including the empty ones** — so a gap reads as "no calls that day", not as
    a line the renderer had to guess through.
    """
    end = _aware(until) if until is not None else _now()
    start = _aware(since)
    rows = db.execute(select(
        ApiRequestLog.created_at, ApiRequestLog.status,
        ApiRequestLog.credit_delta,
    ).where(ApiRequestLog.user_id == str(user_id or ""),
            ApiRequestLog.created_at >= start,
            ApiRequestLog.created_at <= end)).all()

    buckets: dict = {}
    for created_at, status, credit_delta in rows:
        day = _aware(created_at).date()
        acc = buckets.setdefault(day, {"requests": 0, "failures": 0,
                                       "credit": 0})
        acc["requests"] += 1
        if int(status or 0) >= 400:
            acc["failures"] += 1
        acc["credit"] += abs(int(credit_delta or 0))

    out = []
    day = start.date()
    last = end.date()
    while day <= last:
        acc = buckets.get(day, {"requests": 0, "failures": 0, "credit": 0})
        out.append({"date": day, "requests": acc["requests"],
                    "failures": acc["failures"], "credit": acc["credit"]})
        day += timedelta(days=1)
    return out


def _aware(value: datetime) -> datetime:
    """A timezone-aware copy — SQLite hands back naive datetimes."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def counts(db, *, user_id: str, since: datetime) -> dict:
    """A small summary for the top of the page: total, failures, spend."""
    rows = db.execute(select(
        func.count(ApiRequestLog.id),
        func.sum(func.abs(ApiRequestLog.credit_delta)),
    ).where(ApiRequestLog.user_id == str(user_id or ""),
            ApiRequestLog.created_at >= since)).one()
    failures = int(db.execute(select(func.count(ApiRequestLog.id)).where(
        ApiRequestLog.user_id == str(user_id or ""),
        ApiRequestLog.created_at >= since,
        ApiRequestLog.status >= 400)).scalar_one())
    return {"requests": int(rows[0] or 0), "failures": failures,
            "credit": int(rows[1] or 0)}


def purge_expired(db, *, days: int = RETENTION_DAYS,
                  now: datetime | None = None) -> int:
    """Delete rows past the retention window. Returns how many went."""
    cutoff = (now or _now()) - timedelta(days=int(days))
    result = db.execute(
        delete(ApiRequestLog).where(ApiRequestLog.created_at < cutoff))
    return int(result.rowcount or 0)
