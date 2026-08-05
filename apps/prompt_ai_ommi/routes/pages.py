"""Trang HTML va tuy chon hien thi cua nguoi dung."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _jobs, _models, _preference_payload, _preference_row, _production_rows, _render_workspace, _row, _user, _PREFERENCES_KIND, router, MANIFEST, templates, issue_csrf_token, require_login, get_db, is_operator, load_catalog)


@router.get("", response_class=HTMLResponse)
def page(request: Request, _identity: str = Depends(require_login)):
    """Cửa vào của app là workspace (2026-08-05).

    Trước đó là wizard 5 bước; giữ nó làm cửa vào cho tới khi workspace có đủ
    màn, vì chuyển sớm sẽ lấy mất Brief/Director/Export đang dùng được. Nay cả
    mười màn đã chạy nên đổi. Bản cũ còn ở `/classic` để lùi lại được mà không
    cần sửa mã; production có 0 project OMMI nên không ai mất dữ liệu.
    """
    return _render_workspace(request)


@router.get("/workspace", response_class=HTMLResponse)
def workspace(request: Request, _identity: str = Depends(require_login)):
    """Bí danh của cửa vào — giữ để link cũ không gãy."""
    return _render_workspace(request)


@router.get("/classic", response_class=HTMLResponse)
def classic_page(request: Request, _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    """Wizard 5 bước cũ. Giữ để lùi lại được nếu workspace lộ ra thiếu sót."""
    user = _user(request)
    projects = [_row(row) for row in _production_rows(db, user.id)]
    preference_row = _preference_row(db, user.id)
    return templates.TemplateResponse(request, "prompt_ai_ommi.html", {
        "user": user.email, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request), "projects": projects,
        "jobs": _jobs(db, user.id), "catalog": load_catalog(),
        "chat_models": _models("chat"), "image_models": _models("image"),
        "video_models": _models("video"), "operator": is_operator(request),
        "preferences": {**_preference_payload(preference_row),
                        "revision": preference_row.revision if preference_row else 0},
    })


@router.get("/api/preferences")
def get_preferences(request: Request, _identity: str = Depends(require_login),
                    db: Session = Depends(get_db)):
    user = _user(request); row = _preference_row(db, user.id)
    return {**_preference_payload(row), "revision": row.revision if row else 0}


@router.put("/api/preferences")
async def save_preferences(request: Request, _identity: str = Depends(require_login),
                           db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    theme = body.get("theme") if body.get("theme") in {"light", "dark"} else "light"
    payload = {"kind": _PREFERENCES_KIND, "version": 1, "theme": theme}
    row = _preference_row(db, user.id)
    from platform_core import app_projects
    if row is None:
        row = app_projects.create(db, user_id=user.id, app_slug=MANIFEST.slug,
                                  name="PROMPT AI OMMI preferences", schema_version=1,
                                  payload=payload)
    else:
        try:
            row = app_projects.save(db, project_id=row.id, user_id=user.id,
                                    app_slug=MANIFEST.slug,
                                    revision=int(body.get("revision") or 0),
                                    name=row.name, schema_version=1, payload=payload)
        except app_projects.ProjectConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"theme": theme, "revision": row.revision}
