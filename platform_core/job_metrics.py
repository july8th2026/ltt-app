"""Snapshot observability cho hàng đợi job, không phụ thuộc tên app."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from platform_core import job_events
from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR, JOB_QUEUED,
                                  JOB_RUNNING, CreditEntry, ExecutionLease, Job,
                                  JobEvent)

EXTERNAL_STARVATION_S = 300.0


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
             days: int = 7, stale_minutes: int = 10,
             lease_stale_minutes: int = 20,
             app_slug: str = "") -> dict:
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=max(1, days))
    jobs_stmt = select(Job).where(Job.created_at >= cutoff)
    if app_slug:
        jobs_stmt = jobs_stmt.where(Job.app_slug == app_slug[:64])
    rows = list(db.execute(jobs_stmt).scalars().all())
    finished = [job for job in rows if job.status in {JOB_DONE, JOB_ERROR}]
    success = sum(job.status == JOB_DONE for job in finished)
    queue_wait = [value for job in rows
                  if (value := _seconds(job.created_at, job.started_at)) is not None]
    admission_delay = [value for job in rows
                       if (value := _seconds(job.created_at, job.admitted_at))
                       is not None]
    runtime = [value for job in finished
               if (value := _seconds(job.started_at, job.finished_at)) is not None]
    from platform_core.job_scheduler import normalize_priority

    lifecycle_by_priority = {
        priority: {
            "started": sum(normalize_priority(job.priority_class) == priority and
                           job.started_at is not None for job in rows),
            "completed": sum(normalize_priority(job.priority_class) == priority and
                             job.status == JOB_DONE for job in rows),
            "failed": sum(normalize_priority(job.priority_class) == priority and
                          job.status == JOB_ERROR for job in rows),
            "cancelled": sum(normalize_priority(job.priority_class) == priority and
                             job.status == JOB_CANCELLED for job in rows),
        }
        for priority in ("internal", "external")
    }
    events_stmt = select(
        JobEvent.event_code, func.count(JobEvent.id),
    ).where(JobEvent.created_at >= cutoff)
    if app_slug:
        events_stmt = events_stmt.where(JobEvent.app_slug == app_slug[:64])
    event_counts = dict(db.execute(
        events_stmt.group_by(JobEvent.event_code)).all())
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
    done_ids = [job.id for job in finished if job.status == JOB_DONE]
    credit_spent = 0
    if done_ids:
        net_rows = db.execute(select(
            CreditEntry.job_id, func.sum(CreditEntry.delta),
        ).where(CreditEntry.job_id.in_(done_ids)).group_by(
            CreditEntry.job_id)).all()
        credit_spent = sum(max(0, -int(delta or 0)) for _job_id, delta in net_rows)
    successful = len(done_ids)

    # Queue hiện tại không bị giới hạn bởi cửa sổ báo cáo: một job chờ tám ngày
    # vẫn phải hiện trên dashboard hôm nay, nếu không chính job kẹt lâu nhất lại
    # biến mất khỏi số liệu.
    queued_stmt = select(Job).where(Job.status == JOB_QUEUED)
    if app_slug:
        queued_stmt = queued_stmt.where(Job.app_slug == app_slug[:64])
    queued_rows = list(db.execute(queued_stmt).scalars().all())
    queue_depth_by_resource: dict[str, int] = {}
    oldest_by_resource: dict[str, float] = {}
    queue_depth_by_resource_priority: dict[str, dict[str, int]] = {}
    oldest_by_resource_priority: dict[str, dict[str, float]] = {}
    waits_by_resource_priority: dict[str, dict[str, list[float]]] = {}
    for job in queued_rows:
        resource = job.admission_resource or "unclassified"
        priority = normalize_priority(job.priority_class)
        queue_depth_by_resource[resource] = queue_depth_by_resource.get(resource, 0) + 1
        age = _seconds(job.created_at, current) or 0.0
        oldest_by_resource[resource] = max(oldest_by_resource.get(resource, 0.0), age)
        by_priority = queue_depth_by_resource_priority.setdefault(resource, {})
        by_priority[priority] = by_priority.get(priority, 0) + 1
        oldest_priority = oldest_by_resource_priority.setdefault(resource, {})
        oldest_priority[priority] = max(oldest_priority.get(priority, 0.0), age)
        waits_by_resource_priority.setdefault(resource, {}).setdefault(
            priority, []).append(age)

    lease_stmt = select(ExecutionLease)
    if app_slug:
        lease_stmt = lease_stmt.join(
            Job, ExecutionLease.job_id == Job.id).where(
                Job.app_slug == app_slug[:64])
    lease_rows = list(db.execute(lease_stmt).scalars().all())
    active_leases_by_resource: dict[str, int] = {}
    lease_stale_cutoff = current - timedelta(
        minutes=max(1, int(lease_stale_minutes)))
    expired_lease_candidates = 0
    for lease in lease_rows:
        heartbeat = lease.heartbeat_at
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        if heartbeat < lease_stale_cutoff:
            expired_lease_candidates += 1
            continue
        active_leases_by_resource[lease.resource] = (
            active_leases_by_resource.get(lease.resource, 0) + 1)

    return {
        "app_slug": app_slug[:64],
        "window_days": max(1, days),
        "jobs_total": len(rows),
        "finished_total": total,
        "success_rate": round(success / total, 4) if total else 1.0,
        "queue_wait_p50_s": _percentile(queue_wait, 0.50),
        "queue_wait_p95_s": _percentile(queue_wait, 0.95),
        "admission_delay_p50_s": _percentile(admission_delay, 0.50),
        "admission_delay_p95_s": _percentile(admission_delay, 0.95),
        "runtime_p50_s": _percentile(runtime, 0.50),
        "runtime_p95_s": _percentile(runtime, 0.95),
        "lifecycle_by_priority": lifecycle_by_priority,
        "retry_total": int(event_counts.get("retry_scheduled", 0)),
        "refund_total": int(event_counts.get("credit_refunded", 0)),
        "resource_wait_total": int(event_counts.get("resource_wait", 0)),
        "provider_dispatched_total": int(event_counts.get("provider_dispatched", 0)),
        "provider_rejected_total": int(event_counts.get("provider_rejected", 0)),
        "ambiguous_provider_total": int(event_counts.get("ambiguous_provider", 0)),
        "scheduler_priority_override_total": int(
            event_counts.get("scheduler_priority_override", 0)),
        "scheduler_fair_rotation_total": int(
            event_counts.get("scheduler_fair_rotation", 0)),
        "queue_depth": len(queued_rows),
        "queue_depth_by_resource": dict(sorted(queue_depth_by_resource.items())),
        "queue_depth_by_resource_priority": {
            resource: dict(sorted(values.items()))
            for resource, values in sorted(queue_depth_by_resource_priority.items())},
        "oldest_queued_age_s": round(max(oldest_by_resource.values(), default=0.0), 3),
        "oldest_queued_age_s_by_resource": {
            key: round(value, 3) for key, value in sorted(oldest_by_resource.items())},
        "oldest_queued_age_s_by_resource_priority": {
            resource: {priority: round(value, 3)
                       for priority, value in sorted(values.items())}
            for resource, values in sorted(oldest_by_resource_priority.items())},
        "queue_wait_s_by_resource_priority": {
            resource: {
                priority: {"p50": _percentile(values, 0.50),
                           "p95": _percentile(values, 0.95)}
                for priority, values in sorted(classes.items())
            }
            for resource, classes in sorted(waits_by_resource_priority.items())},
        "active_execution_leases": sum(active_leases_by_resource.values()),
        "active_execution_leases_by_resource": dict(
            sorted(active_leases_by_resource.items())),
        "execution_lease_rows": len(lease_rows),
        "expired_execution_lease_candidates": int(expired_lease_candidates),
        "stale_jobs": int(stale),
        "event_write_failures": job_events.event_write_failures(),
        "credit_spent_total": int(credit_spent),
        "credit_per_successful_job": (
            round(credit_spent / successful, 3) if successful else 0.0),
    }


def slo_budget(requires: tuple | list | set = ()) -> dict:
    """Budget generic theo loại executor, không biết tên app cụ thể."""
    needs = set(requires or ())
    if "browser" in needs:
        queue_max = 300.0
        profile = "browser"
    elif needs.intersection({"gpu", "ffmpeg"}):
        queue_max = 120.0
        profile = "compute"
    else:
        queue_max = 30.0
        profile = "api"
    return {
        "profile": profile,
        "minimum_finished": 20,
        "success_rate_min": 0.90,
        "queue_wait_p95_s_max": queue_max,
        "stale_jobs_max": 0,
        "event_write_failures_max": 0,
    }


def evaluate_slo(metrics: dict, budget: dict) -> dict:
    """Đánh giá SLO; ít hơn 20 mẫu là insufficient, không giả PASS."""
    checks = {
        "success_rate": float(metrics.get("success_rate", 0)) >=
                        float(budget["success_rate_min"]),
        "queue_wait_p95": float(metrics.get("queue_wait_p95_s", 0)) <=
                          float(budget["queue_wait_p95_s_max"]),
        "stale_jobs": int(metrics.get("stale_jobs", 0)) <=
                      int(budget["stale_jobs_max"]),
        "event_write_failures": int(metrics.get("event_write_failures", 0)) <=
                                int(budget["event_write_failures_max"]),
    }
    hard_failure = not checks["stale_jobs"] or not checks["event_write_failures"]
    enough = int(metrics.get("finished_total", 0)) >= int(budget["minimum_finished"])
    if hard_failure:
        state = "fail"
    elif not enough:
        state = "insufficient_data"
    else:
        state = "pass" if all(checks.values()) else "fail"
    return {"state": state, "checks": checks, "budget": budget,
            "sample_finished": int(metrics.get("finished_total", 0))}


def alerts(metrics: dict) -> list[dict]:
    """Cảnh báo nền tối thiểu; ngưỡng SLO production được khóa ở Phase 4."""
    found: list[dict[str, object]] = []
    if metrics.get("finished_total", 0) >= 5 and metrics.get("success_rate", 1) < 0.90:
        found.append({"code": "job_success_low", "level": "warning"})
    if metrics.get("stale_jobs", 0) > 0:
        found.append({"code": "job_stale", "level": "error"})
    if metrics.get("event_write_failures", 0) > 0:
        found.append({"code": "job_event_write_failed", "level": "error"})
    for resource, classes in metrics.get(
            "oldest_queued_age_s_by_resource_priority", {}).items():
        age = float(classes.get("external", 0.0) or 0.0)
        if age >= EXTERNAL_STARVATION_S:
            found.append({"code": "external_queue_starvation",
                          "level": "warning", "resource": resource,
                          "oldest_wait_seconds": age})
    return found
