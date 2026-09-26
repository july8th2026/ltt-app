"""routes/bindings.py — endpoint the <-> variant (spec Sec 6.1).

CRUD mong: PUT ghi de TOAN BO danh sach binding cua (project, scene) — khong
phai them/bot tung cai. Xem services/bindings.py cho logic that.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _owned_production, _user, router, require_login, get_db)
from apps.prompt_ai_ommi.services import bindings as svc


def _row(binding) -> dict:
    return {"tag": binding.tag, "kind": binding.kind,
           "variant_id": binding.variant_id, "position": binding.position,
           "role": binding.role, "scene_id": binding.scene_id}


@router.get("/api/projects/{project_id}/bindings")
async def get_bindings(request: Request, project_id: str, scene_id: str = "",
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    user = _user(request)
    _owned_production(db, project_id, user.id)
    rows = svc.list_bindings(db, project_id=project_id, owner_id=user.id,
                             scene_id=(scene_id or None))
    return {"bindings": [_row(row) for row in rows]}


@router.put("/api/projects/{project_id}/bindings")
async def put_bindings(request: Request, project_id: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _owned_production(db, project_id, user.id)
    scene_id = body.get("scene_id") or None
    items = list(body.get("items") or [])
    try:
        created, changed = svc.replace_bindings(
            db, project_id=project_id, owner_id=user.id, scene_id=scene_id,
            items=items)
    except svc.BindingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return {"bindings": [_row(row) for row in created], "changed": changed}


@router.delete("/api/projects/{project_id}/bindings/{tag}")
async def delete_binding_route(request: Request, project_id: str, tag: str,
                               scene_id: str = "",
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    user = _user(request)
    _owned_production(db, project_id, user.id)
    try:
        remaining = svc.delete_binding(
            db, project_id=project_id, owner_id=user.id,
            scene_id=(scene_id or None), tag=tag)
    except svc.BindingNotFound as exc:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy binding.')) from exc
    db.commit()
    return {"bindings": [_row(row) for row in remaining]}
