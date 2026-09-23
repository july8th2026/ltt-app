"""Nhật ký cấp run — `workflow_event`, CHỈ THÊM (spec §5.11).

Cấp node KHÔNG ghi ở đây: `node_run_snapshot` đã là nhật ký của node.

⚠️ `seq` = max + 1. Bên gọi phải đang giữ khoá hàng `workflow_run` (động cơ)
   hoặc là bên vừa tạo run (`tao_run`); `UNIQUE(run_id, seq)` là chốt cuối.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select

from platform_core import job_events
from platform_core.models import WorkflowEvent, WorkflowRun

#: TTL 90 ngay cho run DA KET THUC (spec Sec5.11) — khong dung cho run con
#: dang chay, du created_at cu den may.
RETENTION_DAYS = 90

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


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def purge_expired(db, *, days: int = RETENTION_DAYS,
                  now: datetime | None = None) -> int:
    """Xoa `workflow_event` cua nhung run DA KET SO qua `days` ngay (spec Sec5.11).

    Chi xoa theo `ket_so_luc` (dau KET SO trong `ket_so.py`) — KHONG theo
    `created_at` cua chinh su kien. Mot run con dang chay khong bao gio bi don,
    du su kien dau tien cua no da 90 ngay tuoi (workflow cho lau, hoac paused).
    """
    cutoff = (now or _bay_gio()) - timedelta(days=max(1, int(days)))
    run_ids = db.execute(
        select(WorkflowRun.id)
        .where(WorkflowRun.ket_so_luc.is_not(None),
               WorkflowRun.ket_so_luc < cutoff)).scalars().all()
    if not run_ids:
        return 0
    rows = db.execute(
        select(WorkflowEvent)
        .where(WorkflowEvent.run_id.in_(run_ids))).scalars().all()
    for row in rows:
        db.delete(row)
    return len(rows)


__all__ = ["LOAI", "RETENTION_DAYS", "ghi", "doc", "purge_expired"]
