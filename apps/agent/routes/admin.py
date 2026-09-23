"""Man hinh van hanh cho quan tri: lan chay, so lieu, huy."""
from __future__ import annotations

from __future__ import annotations
from platform_core.i18n import _ as _t
import hashlib
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from platform_core.agent import budget, metrics, runs
from platform_core.registry import discover
from platform_core.models import AGENT_AWAITING_APPROVAL, AGENT_RUNNING, AgentRun, Job
from server.auth.session import require_login
from server.deps import get_db

from apps.agent.routes._shared import (
    _require_admin_user, _verify_json_csrf, router)


@router.get("/api/admin/runs")
def agent_admin_runs(request: Request, _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    """Read-only operational audit without exposing goals, params or user PII."""
    _require_admin_user(request)
    rows = db.query(AgentRun).order_by(AgentRun.created_at.desc()).limit(100).all()
    return JSONResponse({"items": [{
        "id": row.id, "user_ref": hashlib.sha256(row.user_id.encode()).hexdigest()[:12],
        "status": row.status, "version": row.version, "estimated": row.estimated,
        "actual": row.actual, "step_count": len((row.plan or {}).get("steps") or []),
        "events": [str(item.get("event", "")) for item in (row.decision_log or [])],
    } for row in rows]})


@router.get("/api/admin/metrics")
def agent_admin_metrics(request: Request, _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    _require_admin_user(request)
    rows = db.query(AgentRun).all()
    statuses: dict[str, int] = {}
    retries = verifies = refunds = 0
    for row in rows:
        statuses[row.status] = statuses.get(row.status, 0) + 1
        retries += sum(1 for item in (row.decision_log or [])
                       if item.get("event") == "verify" and item.get("attempt", 0))
        verifies += sum(1 for item in (row.decision_log or []) if item.get("event") == "verify")
        refunds += sum(int(item.get("refunded", 0)) for item in (row.decision_log or [])
                       if item.get("event") == "settle")
    estimated = sum(row.estimated for row in rows)
    actual = sum(row.actual for row in rows)
    terminal = sum(count for status, count in statuses.items()
                   if status in {"done", "error", "cancelled"})
    run_success_rate = statuses.get("done", 0) / terminal if terminal else 0
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
    return JSONResponse({"runs": len(rows), "statuses": statuses, "retries": retries,
                         "verifications": verifies, "estimated": estimated,
                         "actual": actual, "actual_estimated_ratio": actual / estimated if estimated else 0,
                         "refunded": refunds, "run_success_rate": run_success_rate,
                         "worker_wait_by_capability": worker_wait,
                         "live": metrics.snapshot()})


@router.post("/api/admin/runs/{run_id}/cancel")
async def agent_admin_cancel(request: Request, run_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    _require_admin_user(request)
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy run.'))
    if run.status in (AGENT_AWAITING_APPROVAL, AGENT_RUNNING):
        actual = runs.actual_cost(run, runs.children(db, run)) if run.status == AGENT_RUNNING else 0
        run = budget.cancel(db, run_id=run.id, user_id=run.user_id, actual=actual)
    return JSONResponse({"id": run.id, "status": run.status,
                         "estimated": run.estimated, "actual": run.actual})
