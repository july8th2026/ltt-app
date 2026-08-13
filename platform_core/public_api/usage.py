"""Usage and balance — **derived** from the credit ledger, never stored twice.

The ledger (``credit_entries``) is the source of truth for money: append-only,
balance = sum of the book (Q5/H3). This module reads it and shapes the answer;
it does not keep a second copy.

Why no projection table: a projection is a cache, and a cache of money has to be
rebuilt, reconciled and explained when it disagrees. Computing from the ledger
means it *cannot* disagree, replaying an idempotent request cannot double-count
(there is only ever one hold), and "reconcile" is a check that the two readings
of one table match rather than a repair job on a second one. If a listing ever
outgrows this, add an index or a materialised view — and then the reconciliation
command in ``tools/reconcile_public_api_usage.py`` becomes load-bearing.

What this module deliberately does **not** report: provider cost. The platform
knows what it *charged the customer* (the ledger) and, per job, what the
provider run was estimated to cost — but there is no authoritative provider
invoice in this system, so publishing one would be inventing a number. Customer
credit usage and provider accounting are two different questions (Q84 keeps the
variance internal).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from platform_core.models import (CREDIT_HOLD, CREDIT_REFUND, CREDIT_SETTLE,
                                  CreditEntry, Job)

MAX_WINDOW_DAYS = 365
DEFAULT_WINDOW_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value):
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def balance(db, user_id: str) -> int:
    """The account's credit balance, straight from the ledger."""
    from platform_core import credit

    return credit.so_du(db, str(user_id))


def parse_window(since=None, until=None) -> tuple:
    """Validate a reporting window, with a bounded default.

    Bounded because an unbounded report over a growing ledger is the query that
    is fine for a year and then is not.
    """
    from platform_core.public_api.errors import invalid_request

    end = _parse_time(until, "until") or _now()
    start = _parse_time(since, "since") or (end - timedelta(days=DEFAULT_WINDOW_DAYS))
    if start >= end:
        raise invalid_request("since must be before until.")
    if end - start > timedelta(days=MAX_WINDOW_DAYS):
        raise invalid_request(f"The window must not exceed {MAX_WINDOW_DAYS} days.")
    return start, end


def _parse_time(value, field: str):
    from platform_core.public_api.errors import invalid_request

    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise invalid_request(f"{field} must be an ISO-8601 timestamp.",
                              field=field) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _ledger_by_job(db, user_id: str, job_ids) -> dict:
    """One grouped query for every job in the page — not one query per row."""
    if not job_ids:
        return {}
    rows = db.execute(
        select(CreditEntry.job_id, CreditEntry.kind,
               func.coalesce(func.sum(CreditEntry.delta), 0))
        .where(CreditEntry.user_id == str(user_id),
               CreditEntry.job_id.in_(list(job_ids)),
               CreditEntry.kind.in_((CREDIT_HOLD, CREDIT_SETTLE, CREDIT_REFUND)))
        .group_by(CreditEntry.job_id, CreditEntry.kind)
    ).all()
    totals: dict = {}
    for job_id, kind, amount in rows:
        totals.setdefault(job_id, {})[kind] = int(amount)
    return totals


def _line(job, ledger: dict) -> dict:
    from platform_core.public_api.invocation import api_meta

    held = -int(ledger.get(CREDIT_HOLD, 0))
    settled = int(ledger.get(CREDIT_SETTLE, 0))
    refunded = int(ledger.get(CREDIT_REFUND, 0))
    # Net is what the customer actually paid: held, less whatever came back
    # through settlement adjustment or a refund. A cancelled job nets zero.
    net = max(0, held - settled - refunded)
    meta = api_meta(job)
    return {
        "job_id": job.id,
        "tool": meta.get("tool") or None,
        "key_id": meta.get("key_id") or None,
        "status": job.status,
        "created_at": _aware(job.created_at).isoformat() if job.created_at else None,
        "finished_at": (_aware(job.finished_at).isoformat()
                        if job.finished_at else None),
        "credit": {"held": held, "refunded": max(0, refunded),
                   "net_charged": net},
    }


def usage_lines(db, *, user_id: str, since: datetime, until: datetime,
                tool: str = "", key_id: str = "", limit: int = 20,
                offset: int = 0) -> list:
    """One line per job in the window, newest first."""
    jobs = db.execute(
        select(Job).where(Job.user_id == str(user_id),
                          Job.created_at >= since, Job.created_at <= until)
        .order_by(Job.created_at.desc()).offset(int(offset)).limit(int(limit))
    ).scalars().all()

    ledger = _ledger_by_job(db, user_id, [job.id for job in jobs])
    lines = [_line(job, ledger.get(job.id, {})) for job in jobs]
    if tool:
        lines = [line for line in lines if line["tool"] == tool]
    if key_id:
        lines = [line for line in lines if line["key_id"] == key_id]
    return lines


def usage_totals(db, *, user_id: str, since: datetime, until: datetime) -> dict:
    """Window totals straight from the ledger, independent of the page above.

    Computed from the ledger rather than by summing the returned lines: a total
    that only counts what fits on one page is a bug that looks like an answer.
    """
    rows = db.execute(
        select(CreditEntry.kind, func.coalesce(func.sum(CreditEntry.delta), 0))
        .where(CreditEntry.user_id == str(user_id),
               CreditEntry.created_at >= since, CreditEntry.created_at <= until,
               CreditEntry.kind.in_((CREDIT_HOLD, CREDIT_SETTLE, CREDIT_REFUND)))
        .group_by(CreditEntry.kind)
    ).all()
    totals = {kind: int(amount) for kind, amount in rows}
    held = -int(totals.get(CREDIT_HOLD, 0))
    settled = int(totals.get(CREDIT_SETTLE, 0))
    refunded = int(totals.get(CREDIT_REFUND, 0))
    return {
        "held_credit": held,
        "returned_credit": max(0, settled + refunded),
        "net_charged_credit": max(0, held - settled - refunded),
    }


def reconcile(db, *, user_id: str = "", since: datetime | None = None,
              until: datetime | None = None) -> dict:
    """Check the two readings of the ledger against each other.

    Line-by-line net (per job) versus the window aggregate. They come from the
    same table by different routes, so a mismatch means a bug in this module or
    an entry with no job attached — both worth knowing about before a customer
    finds them on an invoice.
    """
    end = until or _now()
    start = since or (end - timedelta(days=DEFAULT_WINDOW_DAYS))
    statement = select(Job).where(Job.created_at >= start, Job.created_at <= end)
    if user_id:
        statement = statement.where(Job.user_id == str(user_id))
    jobs = db.execute(statement).scalars().all()

    per_owner: dict = {}
    for job in jobs:
        per_owner.setdefault(job.user_id, []).append(job)

    mismatches = []
    checked = 0
    for owner, owner_jobs in per_owner.items():
        ledger = _ledger_by_job(db, owner, [job.id for job in owner_jobs])
        line_total = sum(_line(job, ledger.get(job.id, {}))["credit"]["net_charged"]
                         for job in owner_jobs)
        window_total = usage_totals(db, user_id=owner, since=start,
                                    until=end)["net_charged_credit"]
        checked += 1
        if line_total != window_total:
            mismatches.append({"user_id": owner, "lines": line_total,
                               "window": window_total})

    orphan_entries = int(db.execute(
        select(func.count(CreditEntry.id)).where(
            CreditEntry.created_at >= start, CreditEntry.created_at <= end,
            CreditEntry.kind == CREDIT_HOLD, CreditEntry.job_id == "")
    ).scalar_one())

    return {"accounts_checked": checked, "jobs": len(jobs),
            "mismatches": mismatches, "holds_without_job": orphan_entries,
            "ok": not mismatches and orphan_entries == 0}
