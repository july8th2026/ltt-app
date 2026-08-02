"""Thin app-owned seam over the shared Agent executor."""
from __future__ import annotations

from sqlalchemy.orm import Session

from platform_core.agent import executor


def advance(db: Session, *, run_id: str, user_id: str):
    """Advance one orchestration tick; called by the CSRF-protected progress POST."""
    return executor.tick(db, run_id=run_id, user_id=user_id)
