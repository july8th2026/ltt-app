"""Chia se workflow qua link va nhan ban tu link."""
from __future__ import annotations

from __future__ import annotations
from platform_core.i18n import _ as _t
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from platform_core.agent import workflows
from platform_core.models import AgentWorkflow, AgentWorkflowShare
from server.auth.session import require_login
from server.deps import get_db

from apps.agent.routes._shared import (
    _active_share, _user, _verify_json_csrf, _workflow_json,
    _workflow_response, router)


@router.get("/api/workflows/{workflow_id}/shares")
def workflow_shares(request: Request, workflow_id: str,
                    _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request)
    try: workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    rows = db.query(AgentWorkflowShare).filter_by(workflow_id=workflow_id, owner_id=user.id).order_by(
        AgentWorkflowShare.created_at.desc()).all()
    return {"items": [{"id": row.id, "permission": row.permission,
                        "expires_at": row.expires_at.isoformat(),
                        "revoked": row.revoked_at is not None} for row in rows]}


@router.post("/api/workflows/{workflow_id}/shares")
async def workflow_share_create(request: Request, workflow_id: str,
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body); user = _user(request)
    try: workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy workflow.')) from None
    permission = str(body.get("permission") or "view")
    if permission not in {"view", "clone"}:
        raise HTTPException(status_code=422, detail=_t('Quyền share không hợp lệ.'))
    hours = max(1, min(int(body.get("expires_hours", 24)), 168))
    token = secrets.token_urlsafe(32)
    row = AgentWorkflowShare(workflow_id=workflow_id, owner_id=user.id,
                             token_hash=hashlib.sha256(token.encode()).hexdigest(),
                             permission=permission,
                             expires_at=datetime.now(timezone.utc) + timedelta(hours=hours))
    db.add(row); db.flush()
    return JSONResponse({"id": row.id, "permission": permission,
                         "path": f"/agent/shared/{token}", "expires_at": row.expires_at.isoformat()},
                        status_code=201)


@router.get("/shared/{token}")
def workflow_shared_view(request: Request, token: str,
                         _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    share = _active_share(db, token); row = db.get(AgentWorkflow, share.workflow_id)
    if row is None:
        raise HTTPException(status_code=404, detail=_t('Workflow không còn tồn tại.'))
    return {"permission": share.permission, "workflow": _workflow_json(row)}


@router.post("/shared/{token}/clone")
async def workflow_shared_clone(request: Request, token: str,
                                _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body); user = _user(request)
    share = _active_share(db, token)
    if share.permission != "clone":
        raise HTTPException(status_code=403, detail=_t('Share chỉ có quyền xem.'))
    source = db.get(AgentWorkflow, share.workflow_id)
    if source is None:
        raise HTTPException(status_code=404, detail=_t('Workflow không còn tồn tại.'))
    row = workflows.create(db, user_id=user.id, name=f"{source.name} — shared clone",
                           canvas=workflows.as_canvas(source), source_workflow_id=source.id)
    return _workflow_response(row, status_code=201)


@router.post("/api/workflows/{workflow_id}/shares/{share_id}/revoke")
async def workflow_share_revoke(request: Request, workflow_id: str, share_id: str,
                                _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body); user = _user(request)
    row = db.query(AgentWorkflowShare).filter_by(id=share_id, workflow_id=workflow_id,
                                                owner_id=user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy share.'))
    row.revoked_at = datetime.now(timezone.utc)
    return {"id": row.id, "revoked": True}
