"""Thao tac tren workflow: nhat ky, kiem, nhan ban, luu tru, xuat/nhap."""
from __future__ import annotations

from __future__ import annotations
from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from platform_core.agent import workflows
from platform_core.models import AgentWorkflowShare, WORKFLOW_ARCHIVED
from server.auth.session import require_login
from server.deps import get_db

from apps.agent.routes._shared import (
    _user, _verify_json_csrf, _workflow_json, _workflow_response, router)


@router.get("/api/workflows/{workflow_id}/activity")
def workflow_activity(request: Request, workflow_id: str,
                      _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request)
    try: snapshots = workflows.snapshots(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    events = [{"event": "snapshot", "revision": item.revision, "reason": item.reason,
               "at": item.created_at.isoformat()} for item in snapshots]
    shares = db.query(AgentWorkflowShare).filter_by(workflow_id=workflow_id, owner_id=user.id).all()
    events.extend({"event": "share_revoked" if item.revoked_at else "share_created",
                   "permission": item.permission,
                   "at": (item.revoked_at or item.created_at).isoformat()} for item in shares)
    return {"items": sorted(events, key=lambda item: item["at"], reverse=True)[:100]}


@router.post("/api/workflows/{workflow_id}/validate")
async def workflow_validate(request: Request, workflow_id: str,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
        expected = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
        if row.revision != expected:
            raise workflows.WorkflowConflict("Workflow đã được sửa ở phiên khác.")
        result = workflows.validate(db, row, user=user)
    except workflows.WorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    response = _workflow_json(row)
    response["validation"] = {"valid": result.valid,
                              "estimated_max_credit": result.estimated_max_credit,
                              "issues": [issue.__dict__ for issue in result.issues],
                              "step_costs": list(result.step_costs)}
    return JSONResponse(response, headers={"ETag": f'"{row.revision}"'})


@router.post("/api/workflows/{workflow_id}/clone")
async def workflow_clone(request: Request, workflow_id: str,
                         _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        source = workflows.get_owned(db, workflow_id, user.id)
        row = workflows.create(db, user_id=user.id,
                               name=str(body.get("name") or f"{source.name} — bản sao"),
                               canvas=workflows.as_canvas(source), source_workflow_id=source.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    return _workflow_response(row, status_code=201)


@router.post("/api/workflows/{workflow_id}/archive")
async def workflow_archive(request: Request, workflow_id: str,
                           _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    if row.status != WORKFLOW_ARCHIVED:
        row.status = WORKFLOW_ARCHIVED; row.revision += 1
    return _workflow_response(row)


@router.get("/api/workflows/{workflow_id}/export")
def workflow_export(request: Request, workflow_id: str,
                    _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    return JSONResponse({"format": "ltt-agent-workflow", "version": 1,
                         "name": row.name, "canvas": workflows.as_canvas(row)},
                        headers={"Content-Disposition":
                                 f'attachment; filename="workflow-{row.id}.json"'})


@router.get("/api/workflows/{workflow_id}/frames/{frame_id}/export")
def workflow_frame_export(request: Request, workflow_id: str, frame_id: str,
                          _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
        canvas = workflows.as_canvas(row)
        targets, scope = workflows.scope_targets(canvas, {"mode": "frame", "frame_id": frame_id})
        plan = workflows.scope_plan(workflows.canvas_to_plan(canvas), targets)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    except workflows.WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return JSONResponse({"format": "ltt-agent-workflow", "version": 1,
                         "name": f"{row.name} · {scope['frame_name']}",
                         "canvas": workflows.plan_to_canvas(plan), "scope": scope})


@router.post("/api/workflows/import")
async def workflow_import(request: Request, _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    if body.get("format") != "ltt-agent-workflow" or body.get("version") != 1:
        raise HTTPException(status_code=422, detail=_t('Định dạng workflow không hỗ trợ.'))
    user = _user(request)
    try:
        row = workflows.create(db, user_id=user.id, name=str(body.get("name", "")),
                               canvas=body.get("canvas"))
    except workflows.WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _workflow_response(row, status_code=201)
