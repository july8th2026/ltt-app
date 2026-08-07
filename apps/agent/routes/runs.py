"""Vong doi lan chay canvas: tao, duyet, tick, huy, artifact, bundle."""
from __future__ import annotations

from __future__ import annotations
from platform_core.i18n import _ as _t
import json
import mimetypes
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from apps.agent import jobs
from platform_core import credit
from platform_core.agent import budget, executor, metrics, runs, workflows
from platform_core.models import AGENT_AWAITING_APPROVAL, AGENT_RUNNING, AgentRun
from server.auth.session import require_login
from server.deps import get_db

from apps.agent.routes._shared import (
    _artifact_key, _cancel_advance_jobs, _enqueue_advance, _owned,
    _prepare_run, _run_json, _run_summary, _schedule_at, _scheduled_datetime,
    _user, _verify_json_csrf, _workflow_response, router)


@router.post("/api/workflows/{workflow_id}/runs")
async def workflow_create_run(request: Request, workflow_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    """Snapshot an exact validated Canvas revision into an immutable AgentRun."""
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
        expected = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
        if row.revision != expected:
            raise workflows.WorkflowConflict("Workflow đã được sửa; cần báo giá lại.")
        canvas = workflows.as_canvas(row)
        plan = workflows.canvas_to_plan(canvas)
        targets, scope = workflows.scope_targets(canvas, body.get("scope") or {"mode": "full"})
        scoped_plan = workflows.scope_plan(plan, targets)
        run = _prepare_run(db, user=user, plan=scoped_plan,
                           source={"workflow_id": row.id, "workflow_revision": row.revision,
                                   "scope": scope,
                                   "use_cache": bool(body.get("use_cache", True)),
                                   "correlation_id": getattr(request.state, "correlation_id", "")})
    except workflows.WorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    except (KeyError, TypeError, ValueError, workflows.WorkflowError,
            budget.BudgetError, runs.AgentRunError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return JSONResponse(_run_json(run), status_code=201)


@router.post("/api/runs/{run_id}/approve")
async def workflow_approve_run(request: Request, run_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user, run = _owned(db, request, run_id)
    if str(body.get("quote_hash", "")) != _run_json(run)["quote_hash"]:
        metrics.record_approval(success=False)
        raise HTTPException(status_code=409, detail=_t('Báo giá đã thay đổi.'))
    approval_success = False
    try:
        scheduled_at = _schedule_at(body.get("scheduled_at"))
        run = budget.approve(db, run_id=run.id, user_id=user.id, approved_by=user.id,
                             expected_version=int(body.get("version", 0)))
        _enqueue_advance(db, run, scheduled_at)
        approval_success = True
    except credit.ThieuCreditError:
        raise HTTPException(status_code=402, detail=_t('Không đủ credit.')) from None
    except (ValueError, budget.BudgetError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    finally:
        metrics.record_approval(success=approval_success)
    return JSONResponse(_run_json(run))


@router.post("/api/runs/{run_id}/restore-workflow")
async def workflow_restore_run(request: Request, run_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user, source = _owned(db, request, run_id)
    try:
        canvas = workflows.plan_to_canvas(dict(source.plan))
        row = workflows.create(db, user_id=user.id,
                               name=str(body.get("name") or f"Khôi phục {source.goal[:80]}"),
                               canvas=canvas)
    except workflows.WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _workflow_response(row, status_code=201)


@router.get("/api/runs")
def workflow_run_list(request: Request, _identity: str = Depends(require_login),
                      db: Session = Depends(get_db)):
    user = _user(request)
    rows = db.query(AgentRun).filter_by(user_id=user.id).order_by(
        AgentRun.created_at.desc()).limit(20).all()
    return JSONResponse({"items": [_run_summary(row) for row in rows]})


@router.get("/api/runs/{run_id}")
def workflow_run_get(request: Request, run_id: str,
                     _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    _user_row, run = _owned(db, request, run_id)
    return JSONResponse(_run_json(run))


@router.post("/api/runs/{run_id}/again")
async def workflow_run_again(request: Request, run_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user, source = _owned(db, request, run_id)
    try:
        run = _prepare_run(db, user=user, plan=dict(source.plan),
                           source={"source_run_id": source.id,
                                   "source_run_version": source.version,
                                   "correlation_id": getattr(request.state, "correlation_id", "")})
    except (workflows.WorkflowError, budget.BudgetError, runs.AgentRunError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return JSONResponse(_run_json(run), status_code=201)


@router.post("/api/runs/{run_id}/tick")
async def workflow_tick_run(request: Request, run_id: str,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user, run = _owned(db, request, run_id)
    scheduled = _scheduled_datetime(run)
    if run.status == AGENT_RUNNING and (scheduled is None or
                                        scheduled <= datetime.now(timezone.utc)):
        run = jobs.advance(db, run_id=run.id, user_id=user.id)
    return JSONResponse(_run_json(run))


@router.post("/api/runs/{run_id}/cancel")
async def workflow_cancel_run(request: Request, run_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user, run = _owned(db, request, run_id)
    if run.status in (AGENT_AWAITING_APPROVAL, AGENT_RUNNING):
        actual = executor.actual_cost(run, runs.children(db, run)) if run.status == AGENT_RUNNING else 0
        run = budget.cancel(db, run_id=run.id, user_id=user.id, actual=actual)
        _cancel_advance_jobs(db, run)
    return JSONResponse(_run_json(run))


@router.get("/api/runs/{run_id}/artifacts/{step_id}/{index}")
def workflow_artifact(request: Request, run_id: str, step_id: str, index: int,
                      _identity: str = Depends(require_login),
                      db: Session = Depends(get_db)):
    """Owned, short-lived artifact delivery; R2 redirects, local streams."""
    _user_row, run = _owned(db, request, run_id)
    key = _artifact_key(run, step_id, index)
    from platform_core.storage import StorageError, get_storage
    storage = get_storage()
    try:
        direct = storage.url_for(key)
        if direct:
            return RedirectResponse(direct, status_code=307)
        stream = storage.open(key)
    except (OSError, StorageError):
        raise HTTPException(status_code=404, detail=_t('Artifact không còn tồn tại.')) from None
    media_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    return StreamingResponse(stream, media_type=media_type,
                             headers={"Cache-Control": "private, no-store"})


@router.get("/api/runs/{run_id}/bundle")
def workflow_run_bundle(request: Request, run_id: str,
                        _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    """Owned ZIP containing the immutable scoped plan and available artifacts."""
    _user_row, run = _owned(db, request, run_id)
    from platform_core.storage import StorageError, get_storage
    storage = get_storage(); artifact_rows = list(_run_json(run).get("artifacts") or [])
    keys = []
    for item in artifact_rows:
        try:
            key = _artifact_key(run, str(item["step_id"]),
                                sum(1 for prior in keys if prior[0] == item["step_id"]))
            keys.append((str(item["step_id"]), key))
        except HTTPException:
            continue
    total = sum(storage.size(key) for _step, key in keys if storage.exists(key))
    if total > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail=_t('Bundle vượt 200 MB; tải từng artifact.'))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        source = next((item for item in reversed(run.decision_log or [])
                       if item.get("event") == "workflow_source"), {})
        archive.writestr("manifest.json", json.dumps({
            "format": "ltt-agent-run-bundle", "version": 1, "run_id": run.id,
            "status": run.status, "scope": source.get("scope", {"mode": "full"}),
            "plan": run.plan, "artifacts": artifact_rows,
        }, ensure_ascii=False, indent=2))
        for index, (step_id, key) in enumerate(keys, 1):
            if not storage.exists(key):
                continue
            try:
                with storage.open(key) as stream:
                    archive.writestr(f"artifacts/{step_id}/{index:03d}-{Path(key).name}", stream.read())
            except (OSError, StorageError):
                continue
    output.seek(0)
    return StreamingResponse(output, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="ltt-run-{run.id[:8]}.zip"',
        "Cache-Control": "private, no-store"})
