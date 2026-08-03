"""App-owned orchestration jobs over the shared Agent executor."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from platform_core.agent import executor
from platform_core.db import get_session
from platform_core.models import AGENT_RUNNING


def advance(db: Session, *, run_id: str, user_id: str):
    """Advance one orchestration tick; called by the CSRF-protected progress POST."""
    return executor.tick(db, run_id=run_id, user_id=user_id)


def handle(params: dict, ctx=None) -> dict:
    """Advance once, then durably enqueue the next tick while the run is active."""
    run_id, user_id = str(params.get("run_id", "")), str(params.get("user_id", ""))
    if not run_id or not user_id:
        raise ValueError("Thiếu run_id/user_id cho agent.advance.")
    gen = get_session(); db = next(gen)
    try:
        from platform_core import jobs as job_queue
        from platform_core.agent import runs
        run = runs.get_owned(db, run_id, user_id, lock=True)
        if run.status == AGENT_RUNNING:
            run = advance(db, run_id=run.id, user_id=user_id)
        if run.status == AGENT_RUNNING:
            suffix = getattr(ctx, "job_id", "manual")
            followup = job_queue.submit(
                db, user_id=user_id, app_slug="agent", job_type="agent.advance",
                params={"run_id": run_id, "user_id": user_id},
                dedupe_key=f"agent:advance:{run_id}:after:{suffix}", max_attempts=3,
            )
            followup.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=2)
        db.commit()
        return {"run_id": run.id, "status": run.status}
    finally:
        db.close()
