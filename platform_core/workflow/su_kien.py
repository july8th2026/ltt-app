"""Nhật ký cấp run — `workflow_event`, CHỈ THÊM (spec §5.11).

Cấp node KHÔNG ghi ở đây: `node_run_snapshot` đã là nhật ký của node.

⚠️ `seq` = max + 1. Bên gọi phải đang giữ khoá hàng `workflow_run` (động cơ)
   hoặc là bên vừa tạo run (`tao_run`); `UNIQUE(run_id, seq)` là chốt cuối.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select

from platform_core import job_events
from platform_core.models import WorkflowEvent

LOAI = frozenset({
    "WorkflowStarted", "TriggerReceived", "NodeResumed", "WaitpointOpened",
    "WaitpointSignalled", "BudgetChecked", "SupervisorDecision",
    "WorkflowCompleted", "WorkflowFailed", "WorkflowCancelled",
})


def ghi(db, run_id: str, loai: str, *, node_id: str = "",
        du_lieu: Optional[dict] = None) -> WorkflowEvent:
    if loai not in LOAI:
        raise ValueError(f"loai su kien khong hop le: {loai!r}")
    cuoi = db.execute(select(func.max(WorkflowEvent.seq))
                      .where(WorkflowEvent.run_id == run_id)).scalar()
    ev = WorkflowEvent(run_id=run_id, seq=int(cuoi or 0) + 1, loai=loai,
                       node_id=node_id or "",
                       du_lieu=job_events.redact_details(dict(du_lieu or {})))
    db.add(ev)
    db.flush()
    return ev


def doc(db, run_id: str, *, sau: int = 0) -> list[WorkflowEvent]:
    return list(db.execute(
        select(WorkflowEvent)
        .where(WorkflowEvent.run_id == run_id, WorkflowEvent.seq > int(sau))
        .order_by(WorkflowEvent.seq)).scalars())


__all__ = ["LOAI", "ghi", "doc"]
