"""Man hinh van hanh cho quan tri: so lieu hang doi cua job con.

🗑️ 23/09/2026 (plan 01b Task 9, spec §17.3+§17.5) — hai cua `/api/admin/runs`
   va `/api/admin/runs/{id}/cancel` da bi go cung bang `agent_runs`. Chung
   khong lam gi khac ngoai doc/ghi bang do, nen chung chet cung no.

⭐ `/api/admin/metrics` thi O LAI, va day la ly do — no la hai menh de chu
   khong phai mot:

   1. nua "runs" (dem theo trang thai, estimated/actual, ti le thanh cong,
      so lan hoan) doc THANG tu `AgentRun` ⇒ chet cung bang;
   2. nua `worker_wait_by_capability` do **job con** doi bao lau truoc khi
      worker nhat — va job con VAN duoc sinh ra: `platform_core/workflow/
      cau_noi.py` dat `parent_id` cho moi waitpoint cua dong co v2.

   Go ca cua nay la go luon menh de thu hai, thu duy nhat con do mot duong
   dang song. Nen no duoc CHUYEN, khong bi xoa.

⚠️ `live` (`metrics.snapshot()`) la bo dem trong tien trinh cua `planner`, khong
   phai cua runtime v1 — `apps/agent/routes/assistant.py` con goi `plan_once()`.
"""
from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from platform_core.agent import metrics
from platform_core.models import Job
from platform_core.registry import discover
from server.auth.session import require_login
from server.deps import get_db

from apps.agent.routes._shared import _require_admin_user, router


@router.get("/api/admin/metrics")
def agent_admin_metrics(request: Request, _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    """Read-only operational audit without exposing goals, params or user PII."""
    _require_admin_user(request)
    requirements = {item.slug: tuple(item.manifest.requires) for item in discover()}
    waits: dict[str, list[float]] = {}
    for job in db.query(Job).filter(Job.parent_id != "").all():
        if job.started_at is None:
            continue
        seconds = max(0.0, job.started_at.timestamp() - job.created_at.timestamp())
        for capability in requirements.get(job.app_slug, ("api",)):
            waits.setdefault(capability, []).append(seconds)
    worker_wait = {name: {"count": len(values), "avg_s": sum(values) / len(values),
                          "max_s": max(values)} for name, values in waits.items()}
    return JSONResponse({"worker_wait_by_capability": worker_wait,
                         "live": metrics.snapshot()})
