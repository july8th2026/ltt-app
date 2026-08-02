"""State/checkpoint/fan-out service for AgentRun (P3)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from platform_core import jobs
from platform_core.models import (
    AGENT_AWAITING_APPROVAL, AGENT_CANCELLED, AGENT_DONE, AGENT_ERROR,
    AGENT_PLANNING, AGENT_RUNNING, JOB_DONE, JOB_ERROR, AgentRun, Job,
    User,
)

MAX_ACTIVE_RUNS_PER_USER = 3


class AgentRunError(ValueError):
    pass


_TRANSITIONS = {
    AGENT_PLANNING: {AGENT_AWAITING_APPROVAL, AGENT_ERROR},
    # awaiting -> running is deliberately absent: only budget.approve may cross
    # the money/approval boundary after creating the hold atomically.
    AGENT_AWAITING_APPROVAL: {AGENT_CANCELLED, AGENT_ERROR},
    AGENT_RUNNING: {AGENT_DONE, AGENT_CANCELLED, AGENT_ERROR},
    AGENT_DONE: set(),
    AGENT_CANCELLED: set(),
    AGENT_ERROR: set(),
}


def create_run(db: DbSession, *, user_id: str, goal: str,
               plan: dict | None = None, budget_max: int = 0) -> AgentRun:
    run = AgentRun(user_id=user_id, goal=(goal or "").strip(), plan=plan or {},
                   checkpoint={}, budget_max=max(0, int(budget_max or 0)))
    db.add(run)
    db.flush()
    return run


def create_run_capped(db: DbSession, *, user_id: str, goal: str,
                      plan: dict | None = None, budget_max: int = 0) -> AgentRun:
    """Serialize on the user row so concurrent requests cannot bypass the cap."""
    user = db.execute(select(User).where(User.id == user_id).with_for_update()).scalars().first()
    if user is None:
        raise AgentRunError("Không tìm thấy người dùng.")
    active = db.execute(select(AgentRun.id).where(
        AgentRun.user_id == user_id,
        AgentRun.status.in_((AGENT_PLANNING, AGENT_AWAITING_APPROVAL, AGENT_RUNNING)),
    )).all()
    if len(active) >= MAX_ACTIVE_RUNS_PER_USER:
        raise AgentRunError(f"Chỉ được có tối đa {MAX_ACTIVE_RUNS_PER_USER} run đang hoạt động.")
    return create_run(db, user_id=user_id, goal=goal, plan=plan, budget_max=budget_max)


def get_owned(db: DbSession, run_id: str, user_id: str, *, lock: bool = False) -> AgentRun:
    stmt = select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user_id)
    if lock:
        stmt = stmt.with_for_update()
    run = db.execute(stmt).scalars().first()
    if run is None:
        raise AgentRunError("Không tìm thấy AgentRun thuộc người dùng.")
    return run


def transition(db: DbSession, run: AgentRun, target: str) -> AgentRun:
    if target not in _TRANSITIONS.get(run.status, set()):
        raise AgentRunError(f"Chuyển trạng thái không hợp lệ: {run.status} -> {target}")
    run.status = target
    if target in (AGENT_DONE, AGENT_CANCELLED, AGENT_ERROR):
        run.finished_at = datetime.now(timezone.utc)
    db.flush()
    return run


def _mark_approved_running(db: DbSession, run: AgentRun) -> AgentRun:
    """Internal half of budget.approve; callers must already hold the row."""
    if run.status != AGENT_AWAITING_APPROVAL or run.approved_at is None:
        raise AgentRunError("Thiếu approval hợp lệ để bắt đầu AgentRun.")
    run.status = AGENT_RUNNING
    db.flush()
    return run


def checkpoint_step(db: DbSession, run: AgentRun, step_id: str, data: dict) -> None:
    if not step_id or not isinstance(data, dict):
        raise AgentRunError("Checkpoint step không hợp lệ.")
    updated = dict(run.checkpoint or {})
    updated[step_id] = dict(data)
    run.checkpoint = updated
    db.flush()


def append_decision(db: DbSession, run: AgentRun, event: dict) -> None:
    if not isinstance(event, dict):
        raise AgentRunError("Decision event phải là object.")
    log = list(run.decision_log or [])
    log.append(dict(event))
    run.decision_log = log
    db.flush()


def submit_child(db: DbSession, run: AgentRun, *, step_id: str, app_slug: str,
                 job_type: str, params: dict, parent_id: str = "",
                 dedupe_key: str = "", max_attempts: int = 3) -> Job:
    if run.status != AGENT_RUNNING:
        raise AgentRunError("Chỉ AgentRun running mới được tạo child job.")
    return jobs.submit(
        db, user_id=run.user_id, app_slug=app_slug, job_type=job_type,
        params=params, dedupe_key=dedupe_key, max_attempts=max_attempts,
        parent_id=parent_id, plan_id=run.id, step_id=step_id,
    )


def children(db: DbSession, run: AgentRun, *, step_id: str = "") -> list[Job]:
    stmt = select(Job).where(Job.plan_id == run.id, Job.user_id == run.user_id)
    if step_id:
        stmt = stmt.where(Job.step_id == step_id)
    return list(db.execute(stmt.order_by(Job.created_at, Job.id)).scalars())


def child_summary(db: DbSession, run: AgentRun, *, step_id: str = "") -> dict:
    rows = children(db, run, step_id=step_id)
    return {
        "total": len(rows),
        "done": sum(row.status == JOB_DONE for row in rows),
        "error": sum(row.status == JOB_ERROR for row in rows),
        "pending": sum(row.status not in (JOB_DONE, JOB_ERROR) for row in rows),
    }
