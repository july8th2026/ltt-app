"""CRUD workflow va ban chup theo phien ban."""
from __future__ import annotations

from __future__ import annotations
from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from platform_core.agent import workflows
from platform_core.models import AgentWorkflow
from server.auth.session import require_login
from server.deps import get_db

from apps.agent.routes._shared import (
    _user, _verify_json_csrf, _workflow_json, _workflow_response, router)


@router.get("/api/workflows")
def workflow_list(request: Request, _identity: str = Depends(require_login),
                  db: Session = Depends(get_db)):
    user = _user(request)
    rows = db.query(AgentWorkflow).filter_by(user_id=user.id).order_by(
        AgentWorkflow.updated_at.desc()).all()
    return JSONResponse({"items": [_workflow_json(row, include_canvas=False) for row in rows]})


@router.post("/api/workflows")
async def workflow_create(request: Request, _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        row = workflows.create(db, user_id=user.id, name=str(body.get("name", "")),
                               canvas=body.get("canvas"))
    except workflows.WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _workflow_response(row, status_code=201)


@router.get("/api/workflows/{workflow_id}")
def workflow_get(request: Request, workflow_id: str,
                 _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    return _workflow_response(row)


@router.put("/api/workflows/{workflow_id}")
async def workflow_save(request: Request, workflow_id: str,
                        _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        revision = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
        row = workflows.save(db, workflow_id=workflow_id, user_id=user.id,
                             revision=revision, name=str(body.get("name", "")),
                             canvas=body.get("canvas"))
    except workflows.WorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    except (KeyError, TypeError, ValueError, workflows.WorkflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _workflow_response(row)
