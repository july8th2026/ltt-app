"""Read model an toàn để mọi app dùng chung lịch sử job.

Không trả ``params``, ``result`` hay ``error``. Artifact tải qua opaque index ở
route Jobs; timeline chỉ gồm event customer. Nhờ vậy React/Jinja tool đều có
một contract thay vì tự đọc bảng và vô tình lộ payload của app khác.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from platform_core import job_events
from platform_core.models import CreditEntry, Job

STATUSES = {"queued", "running", "done", "error", "cancelled"}


def get_owned(db: DbSession, user_id: str, job_id: str) -> Job | None:
    return db.execute(select(Job).where(
        Job.id == job_id, Job.user_id == user_id,
    )).scalars().first()


def list_owned(
    db: DbSession, user_id: str, *, app_slug: str = "", status: str = "",
    start: datetime | None = None, end: datetime | None = None,
    cursor: str = "", limit: int = 50,
) -> tuple[list[Job], str]:
    stmt = select(Job).where(Job.user_id == user_id)
    if app_slug:
        stmt = stmt.where(Job.app_slug == app_slug[:64])
    if status in STATUSES:
        stmt = stmt.where(Job.status == status)
    if start is not None:
        stmt = stmt.where(Job.created_at >= start)
    if end is not None:
        stmt = stmt.where(Job.created_at <= end)
    if cursor:
        anchor = get_owned(db, user_id, cursor[:36])
        if anchor is not None:
            stmt = stmt.where(Job.created_at < anchor.created_at)
    size = max(1, min(int(limit), 100))
    rows = list(db.execute(
        stmt.order_by(Job.created_at.desc()).limit(size + 1)
    ).scalars().all())
    return rows[:size], (rows[size - 1].id if len(rows) > size else "")


def customer_payload(db: DbSession, job: Job, *, with_events: bool = False) -> dict:
    data = {
        "id": job.id,
        "app_slug": job.app_slug,
        "job_type": job.job_type,
        "status": job.status,
        "progress": max(0, min(100, int(job.progress or 0))),
        "attempts": int(job.attempts or 0),
        "max_attempts": int(job.max_attempts or 0),
        "retry_of_id": job.retry_of_id,
        "correlation_id": job.correlation_id,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }
    if with_events:
        data["events"] = [{
            "sequence": event.sequence,
            "code": event.event_code,
            "level": event.level,
            "message": event.public_message,
            "details": event.details,
            "created_at": event.created_at,
        } for event in job_events.timeline(db, job.id)]
    return data


def support_payload(db: DbSession, job: Job) -> dict:
    """Gói support operator-only, không chứa params/result/error/note/user PII."""
    events = job_events.timeline(db, job.id, include_internal=True, limit=500)
    ledger_rows = db.execute(select(
        CreditEntry.kind, func.sum(CreditEntry.delta), func.count(CreditEntry.id),
    ).where(CreditEntry.job_id == job.id).group_by(CreditEntry.kind)).all()
    return {
        "schema": "ltt.support-job.v1",
        "job": {
            "id": job.id,
            "app_slug": job.app_slug,
            "job_type": job.job_type,
            "status": job.status,
            "progress": max(0, min(100, int(job.progress or 0))),
            "attempts": int(job.attempts or 0),
            "max_attempts": int(job.max_attempts or 0),
            "retry_of_id": job.retry_of_id,
            "correlation_id": job.correlation_id,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        },
        "events": [{
            "sequence": row.sequence,
            "code": row.event_code,
            "level": row.level,
            "visibility": row.visibility,
            "message": job_events.redact_details(row.public_message),
            "details": job_events.redact_details(row.details),
            "created_at": row.created_at,
        } for row in events],
        "credit": {
            str(kind): {"delta": int(delta or 0), "entries": int(count or 0)}
            for kind, delta, count in ledger_rows
        },
    }
