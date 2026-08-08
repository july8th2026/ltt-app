"""Snapshot observability cho hàng đợi job, không phụ thuộc tên app."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from platform_core import job_events
from platform_core.models import JOB_DONE, JOB_ERROR, JOB_RUNNING, Job, JobEvent


def _seconds(start, end) -> float | None:
    if start is None or end is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(0.0, (end - start).total_seconds())


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return round(ordered[index], 3)


def snapshot(db: DbSession, *, now: datetime | None = None,
             days: int = 7, stale_minutes: int = 10) -> dict:
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=max(1, days))
    rows = list(db.execute(select(Job).where(Job.created_at >= cutoff)).scalars().all())
    finished = [job for job in rows if job.status in {JOB_DONE, JOB_ERROR}]
    success = sum(job.status == JOB_DONE for job in finished)
    queue_wait = [value for job in rows
                  if (value := _seconds(job.created_at, job.started_at)) is not None]
    runtime = [value for job in finished
               if (value := _seconds(job.started_at, job.finished_at)) is not None]
    event_counts = dict(db.execute(select(
        JobEvent.event_code, func.count(JobEvent.id),
    ).where(JobEvent.created_at >= cutoff).group_by(JobEvent.event_code)).all())
    stale_cutoff = current - timedelta(minutes=max(1, stale_minutes))
    stale = 0
    for job in rows:
        if job.status != JOB_RUNNING:
            continue
        heartbeat = job.heartbeat_at or job.started_at or job.created_at
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        stale += heartbeat < stale_cutoff
    total = len(finished)
    return {
        "window_days": max(1, days),
        "jobs_total": len(rows),
        "finished_total": total,
        "success_rate": round(success / total, 4) if total else 1.0,
        "queue_wait_p50_s": _percentile(queue_wait, 0.50),
        "queue_wait_p95_s": _percentile(queue_wait, 0.95),
        "runtime_p50_s": _percentile(runtime, 0.50),
        "runtime_p95_s": _percentile(runtime, 0.95),
        "retry_total": int(event_counts.get("retry_scheduled", 0)),
        "refund_total": int(event_counts.get("credit_refunded", 0)),
        "stale_jobs": int(stale),
        "event_write_failures": job_events.event_write_failures(),
    }


def alerts(metrics: dict) -> list[dict]:
    """Cảnh báo nền tối thiểu; ngưỡng SLO production được khóa ở Phase 4."""
    found = []
    if metrics.get("finished_total", 0) >= 5 and metrics.get("success_rate", 1) < 0.90:
        found.append({"code": "job_success_low", "level": "warning"})
    if metrics.get("stale_jobs", 0) > 0:
        found.append({"code": "job_stale", "level": "error"})
    if metrics.get("event_write_failures", 0) > 0:
        found.append({"code": "job_event_write_failed", "level": "error"})
    return found
