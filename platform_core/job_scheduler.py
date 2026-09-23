"""Canonical Scheduler V1 ranking, queue snapshot and honest ETA.

The durable queue remains :class:`platform_core.models.Job`.  This module owns
only ordering and derived read models; it never commits, moves credit, acquires
a lease or changes a job state.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import aliased

from platform_core.models import JOB_DONE, JOB_QUEUED, JOB_RUNNING, Job


PRIORITY_INTERNAL = "internal"
PRIORITY_EXTERNAL = "external"

ORIGIN_INTERNAL_RUNTIME = "internal_runtime"
ORIGIN_AGENT = "agent"
ORIGIN_WORKFLOW = "workflow"
ORIGIN_PUBLIC_API = "public_api"
ORIGIN_WEB = "web"
ORIGIN_CODEX = "codex"
ORIGIN_CLI = "cli"
ORIGIN_WORKER = "worker"
ORIGIN_UNKNOWN = "unknown"

_ORIGINS = {
    ORIGIN_INTERNAL_RUNTIME, ORIGIN_AGENT, ORIGIN_WORKFLOW, ORIGIN_PUBLIC_API,
    ORIGIN_WEB, ORIGIN_CODEX, ORIGIN_CLI, ORIGIN_WORKER, ORIGIN_UNKNOWN,
}
_HISTORY_LIMIT = 200


def normalize_priority(value: object) -> str:
    """Unknown or missing values are external; callers cannot fail open."""
    return (PRIORITY_INTERNAL if str(value or "").strip().lower()
            == PRIORITY_INTERNAL else PRIORITY_EXTERNAL)


def normalize_origin(value: object) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if candidate in _ORIGINS else ORIGIN_UNKNOWN


def _priority_rank(column):  # noqa: ANN001 - SQLAlchemy expression
    return case((column == PRIORITY_INTERNAL, 0), else_=1)


def order_expressions(job_entity, *, now: datetime, peer_entity=None,
                      include_eligibility: bool = False) -> tuple:
    """The one ordering contract used by claim and every queue projection.

    ``include_eligibility`` is for a snapshot containing future retry rows.
    Claim already filters to due rows, so the expression would be constant
    there. Priority remains strict among jobs that are eligible together.
    """
    from platform_core.jobs import FAIR_AGING

    peer = peer_entity if peer_entity is not None else aliased(Job)
    job_priority = _priority_rank(job_entity.priority_class)
    peer_priority = _priority_rank(peer.priority_class)
    last_account_claim = (
        select(func.max(peer.last_claimed_at))
        .where(peer.user_id == job_entity.user_id,
               peer.admission_resource == job_entity.admission_resource,
               peer_priority == job_priority)
        .correlate(job_entity)
        .scalar_subquery()
    )
    aged_first = case(
        (job_entity.created_at <= now - FAIR_AGING, 0), else_=1)
    never_served_first = case((last_account_claim.is_(None), 0), else_=1)
    order: list[Any] = []
    if include_eligibility:
        order.append(case((job_entity.next_run_at <= now, 0), else_=1))
    order.extend((job_priority, aged_first, never_served_first,
                  last_account_claim, job_entity.created_at, job_entity.id))
    return tuple(order)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _duration_seconds(job: Job) -> float | None:
    start = _aware(job.admitted_at or job.started_at)
    finish = _aware(job.finished_at)
    if start is None or finish is None:
        return None
    return max(0.0, (finish - start).total_seconds())


def historical_duration(db, *, resource: str, job_type: str) -> float | None:
    """Bounded rolling median for one resource/job type; no invented default."""
    rows = list(db.execute(
        select(Job).where(
            Job.status == JOB_DONE,
            Job.admission_resource == str(resource or ""),
            Job.job_type == str(job_type or ""),
            Job.finished_at.is_not(None),
        ).order_by(Job.finished_at.desc()).limit(_HISTORY_LIMIT)
    ).scalars().all())
    measured = [value for row in rows
                if (value := _duration_seconds(row)) is not None]
    return float(median(measured)) if measured else None


def _ranked_queue(resource: str, now: datetime):
    candidate = aliased(Job, name="scheduler_candidate")
    peer = aliased(Job, name="scheduler_peer")
    priority = _priority_rank(candidate.priority_class).label("priority_rank")
    return select(
        candidate.id.label("job_id"),
        candidate.job_type.label("job_type"),
        priority,
        func.row_number().over(order_by=order_expressions(
            candidate, now=now, peer_entity=peer,
            include_eligibility=True)).label("position"),
    ).where(
        candidate.status == JOB_QUEUED,
        candidate.admission_resource == str(resource or ""),
    ).cte("scheduler_ranked_queue")


def _estimate_wait(db, job: Job, *, ranked, position: int,
                   now: datetime) -> float | None:
    resource = str(job.admission_resource or "")
    slots = max(0, int(job.admission_slots or 0))
    running = list(db.execute(select(Job).where(
        Job.status == JOB_RUNNING,
        Job.admission_resource == resource,
    )).scalars().all())

    workload = 0.0
    for active in running:
        typical = historical_duration(
            db, resource=resource, job_type=active.job_type)
        started = _aware(active.admitted_at or active.started_at)
        if typical is None or started is None:
            return None
        workload += max(0.0, typical - max(0.0, (now - started).total_seconds()))

    ahead = db.execute(select(
        ranked.c.job_type, func.count(ranked.c.job_id)
    ).where(ranked.c.position < position).group_by(ranked.c.job_type)).all()
    for job_type, count in ahead:
        typical = historical_duration(
            db, resource=resource, job_type=str(job_type))
        if typical is None:
            return None
        workload += typical * int(count)

    if workload == 0:
        return 0.0
    if slots <= 0:
        return None
    return round(workload / slots, 3)


def queue_snapshot(db, job: Job, *, now: datetime | None = None) -> dict | None:
    """Return a dynamic owner-safe queue snapshot, or ``None`` if not queued."""
    if job.status != JOB_QUEUED:
        return None
    current = now or datetime.now(timezone.utc)
    ranked = _ranked_queue(str(job.admission_resource or ""), current)
    subject = db.execute(select(
        ranked.c.position, ranked.c.priority_rank
    ).where(ranked.c.job_id == job.id)).first()
    if subject is None:
        return None
    position = int(subject.position)
    jobs_ahead = max(0, position - 1)
    higher = int(db.execute(select(func.count()).select_from(ranked).where(
        ranked.c.position < position,
        ranked.c.priority_rank < int(subject.priority_rank),
    )).scalar_one())
    estimate = _estimate_wait(
        db, job, ranked=ranked, position=position, now=current)
    next_run = _aware(job.next_run_at)
    eligible = next_run is None or next_run <= current
    return {
        "resource": str(job.admission_resource or "unclassified"),
        "priority_class": normalize_priority(job.priority_class),
        "position": position,
        "jobs_ahead": jobs_ahead,
        "higher_priority_ahead": higher,
        "same_priority_ahead": max(0, jobs_ahead - higher),
        "eligible": bool(eligible),
        "retry_at": next_run.isoformat() if not eligible and next_run else None,
        "estimated_wait_seconds": estimate,
        "estimated_start_at": (
            (current + timedelta(seconds=estimate)).isoformat()
            if estimate is not None else None),
        "updated_at": current.isoformat(),
    }
