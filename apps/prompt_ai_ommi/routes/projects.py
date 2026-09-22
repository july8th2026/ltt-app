"""Vong doi du an: CRUD, ban chup, bao gia va chay AI Director."""
from __future__ import annotations

from platform_core.i18n import _ as _t
from platform_core.llm import canonical as _C
import copy

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from platform_core.jobs import loi_cho_khach

from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _models, _owned_production, _production_rows, _require_run_enabled, _row, _user, router, MANIFEST, require_login, get_db, SCHEMA_VERSION, clean_project, empty_project, prompt_job_params)


def _prompt_context(db: Session, user_id: str, payload: dict) -> dict:
    """Resolve user-visible catalog choices into bounded generation guidance.

    Projects persist stable IDs only. Resolving at preview/run time means catalog
    updates are visible, private ownership is enforced, and stale IDs fail with
    a useful 422 instead of silently producing a different prompt.
    """
    from apps.prompt_ai_ommi.services import library as lsvc
    from apps.prompt_ai_ommi.services.composer import load_catalog

    brief = payload["brief"]
    context = {"style_override": "", "style_negative": "", "meta_prompt": "",
               "snippets": [], "selection_names": {"snippets": []}}
    simple_styles = {str(item.get("id") or "") for item in
                     load_catalog().get("styles", [])}

    style_id = str(brief.get("style_id") or "cinematic")
    if not brief.get("style_custom") and style_id not in simple_styles:
        try:
            row = lsvc.get_visible(db, "style", style_id, user_id)
        except lsvc.LibraryNotFound as exc:
            raise HTTPException(status_code=422,
                                detail=_t('Phong cách đã chọn không còn khả dụng.')) from exc
        context["style_override"] = row.body
        context["style_negative"] = row.negative or ""
        context["selection_names"]["style"] = row.name

    meta_id = str(brief.get("meta_prompt_id") or "")
    if meta_id:
        try:
            row = lsvc.get_visible(db, "meta", meta_id, user_id)
        except lsvc.LibraryNotFound as exc:
            raise HTTPException(status_code=422,
                                detail=_t('Meta Director đã chọn không còn khả dụng.')) from exc
        context["meta_prompt"] = row.body
        context["selection_names"]["meta"] = row.name

    for snippet_id in brief.get("snippet_ids") or []:
        try:
            row = lsvc.get_visible(db, "snippet", snippet_id, user_id)
        except lsvc.LibraryNotFound as exc:
            raise HTTPException(status_code=422,
                                detail=_t('Một khối prompt đã chọn không còn khả dụng.')) from exc
        context["snippets"].append(row.body)
        context["selection_names"]["snippets"].append(row.name)
    return context


@router.get("/api/projects")
def list_projects(request: Request, archived: bool = False,
                  _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request)
    return {"items": [_row(row) for row in _production_rows(
        db, user.id, include_archived=archived)]}


@router.post("/api/projects", status_code=201)
async def create_project(request: Request, _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    name = str(body.get("name") or "Dự án mới")[:160]
    payload = clean_project(body.get("payload") or empty_project(name))
    from platform_core import app_projects
    try:
        row = app_projects.create(db, user_id=user.id, app_slug=MANIFEST.slug,
                                  name=payload["brief"]["title"] or name,
                                  schema_version=SCHEMA_VERSION, payload=payload)
    except app_projects.ProjectError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _row(row)


@router.get("/api/projects/{project_id}")
def get_project(request: Request, project_id: str,
                _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    return _row(_owned_production(db, project_id, _user(request).id))


@router.put("/api/projects/{project_id}")
async def save_project(request: Request, project_id: str,
                       _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    current = _owned_production(db, project_id, user.id)
    payload = clean_project(body.get("payload"))
    from platform_core import app_projects
    try:
        row = app_projects.save(
            db, project_id=project_id, user_id=user.id, app_slug=MANIFEST.slug,
            revision=int(body.get("revision") or 0),
            name=payload["brief"]["title"], schema_version=SCHEMA_VERSION,
            payload=payload)
    except app_projects.ProjectConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except app_projects.ProjectError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if current.id != row.id:  # pragma: no cover - defensive invariant
        raise HTTPException(status_code=409, detail="Project identity conflict.")
    return _row(row)


@router.post("/api/projects/{project_id}/clone", status_code=201)
async def clone_project(request: Request, project_id: str,
                        _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    source = _owned_production(db, project_id, user.id)
    from platform_core import app_projects
    name = str(body.get("name") or f"{source.name} — bản sao")[:160]
    payload = clean_project(copy.deepcopy(source.payload)); payload["brief"]["title"] = name
    return _row(app_projects.create(db, user_id=user.id, app_slug=MANIFEST.slug,
                                    name=name, schema_version=SCHEMA_VERSION,
                                    payload=payload))


@router.post("/api/projects/{project_id}/archive")
async def archive_project(request: Request, project_id: str,
                          _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    from platform_core import app_projects
    row = _owned_production(db, project_id, user.id)
    return _row(app_projects.archive(db, row))


@router.post("/api/projects/{project_id}/unarchive")
async def unarchive_project(request: Request, project_id: str,
                            _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    row = _owned_production(db, project_id, user.id)
    from datetime import datetime, timezone
    from platform_core.models import APP_PROJECT_ACTIVE, APP_PROJECT_ARCHIVED
    if row.status != APP_PROJECT_ARCHIVED:
        raise HTTPException(status_code=409, detail=_t('Project không ở trạng thái lưu trữ.'))
    row.status = APP_PROJECT_ACTIVE; row.revision += 1
    row.updated_at = datetime.now(timezone.utc); db.flush()
    return _row(row)


@router.post("/api/projects/{project_id}/snapshot", status_code=201)
async def snapshot_project(request: Request, project_id: str,
                           _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    source = _owned_production(db, project_id, user.id)
    payload = {"kind": "snapshot", "version": 1, "source_project_id": source.id,
               "source_revision": source.revision, "project": copy.deepcopy(source.payload)}
    from platform_core import app_projects
    row = app_projects.create(db, user_id=user.id, app_slug=MANIFEST.slug,
                              name=f"Snapshot — {source.name}"[:160], schema_version=1,
                              payload=payload)
    return _row(row)


@router.get("/api/projects/{project_id}/snapshots")
def list_snapshots(request: Request, project_id: str,
                   _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request); _owned_production(db, project_id, user.id)
    from platform_core.models import AppProject
    rows = db.execute(select(AppProject).where(
        AppProject.user_id == user.id, AppProject.app_slug == MANIFEST.slug
    ).order_by(AppProject.created_at.desc()).limit(100)).scalars().all()
    return {"items": [_row(row) for row in rows if
                      (row.payload or {}).get("kind") == "snapshot" and
                      (row.payload or {}).get("source_project_id") == project_id]}


@router.post("/api/projects/{project_id}/restore/{snapshot_id}")
async def restore_snapshot(request: Request, project_id: str, snapshot_id: str,
                           _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    current = _owned_production(db, project_id, user.id)
    from platform_core import app_projects
    try:
        snap = app_projects.get_owned(db, snapshot_id, user.id, MANIFEST.slug)
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy snapshot.')) from None
    if ((snap.payload or {}).get("kind") != "snapshot" or
            (snap.payload or {}).get("source_project_id") != project_id):
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy snapshot.'))
    payload = clean_project((snap.payload or {}).get("project") or {})
    try:
        row = app_projects.save(db, project_id=project_id, user_id=user.id,
                                app_slug=MANIFEST.slug,
                                revision=int(body.get("revision") or current.revision),
                                name=payload["brief"]["title"],
                                schema_version=SCHEMA_VERSION, payload=payload)
    except app_projects.ProjectConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _row(row)


@router.post("/api/projects/{project_id}/preview")
async def preview_project(request: Request, project_id: str,
                          _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    row = _owned_production(db, project_id, user.id)
    payload = clean_project(body.get("payload") or row.payload)
    from apps.prompt_ai_ommi.services.composer import preview
    return preview(payload, **_prompt_context(db, user.id, payload))


def _chat_model(value: str) -> str:
    allowed = {item["value"] for item in _models("chat")}
    if value in allowed:
        return value
    # Bí danh model NHÀ, không phải tên một hãng đã ngừng. Nhánh này chỉ chạy
    # khi `allowed` rỗng — tức lúc registry chưa nạp — nên nó ít khi nổ, và
    # một giá trị sai ở đây sống rất lâu mà không ai thấy.
    # D09: mac dinh la model NOI BO app khai, khong phai mac dinh cua khach.
    return next(iter(allowed), _C.model_noi_bo_cua("prompt_ai_ommi"))


@router.post("/api/projects/{project_id}/quote")
async def quote_project(request: Request, project_id: str,
                        _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    row = _owned_production(db, project_id, user.id)
    payload = clean_project(body.get("payload") or row.payload)
    operation = str(body.get("operation") or "director")
    params = prompt_job_params(
        payload, operation=operation,
        model=_chat_model(str(body.get("model") or "")),
        prompt_context=_prompt_context(db, user.id, payload))
    params["project_id"] = project_id
    from platform_core.registry import credit_for
    return {"operation": params["operation"], "credit": credit_for(
        "prompt_ai_ommi.generate", params), "authoritative": True,
        "scene_count": params["scene_count"], "model": params["model"]}


@router.post("/api/projects/{project_id}/generate", status_code=201)
async def generate_project(request: Request, project_id: str,
                           _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    row = _owned_production(db, project_id, user.id)
    payload = clean_project(body.get("payload") or row.payload)
    operation = str(body.get("operation") or "director")
    params = prompt_job_params(
        payload, operation=operation,
        model=_chat_model(str(body.get("model") or "")),
        prompt_context=_prompt_context(db, user.id, payload))
    if len(params["story"].strip()) < 20:
        raise HTTPException(status_code=422, detail=_t('Nội dung brief tối thiểu 20 ký tự.'))
    params["project_id"] = project_id; params["owner_id"] = user.id
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    try:
        job = submit_with_credit(
            db, user_id=user.id, app_slug=MANIFEST.slug,
            job_type="prompt_ai_ommi.generate", params=params,
            dedupe_key=dedupe_key_for("prompt_ai_ommi.generate", params))
    except (credit.ThieuCreditError, RegistryError) as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"id": job.id, "status": job.status, "progress": job.progress,
            "job_url": f"/jobs/{job.id}"}


@router.get("/api/jobs/{job_id}")
def job_status(request: Request, job_id: str, _identity: str = Depends(require_login),
               db: Session = Depends(get_db)):
    user = _user(request)
    from platform_core.models import Job
    row = db.get(Job, job_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
    return {"id": row.id, "app_slug": row.app_slug, "job_type": row.job_type,
            "status": row.status, "progress": row.progress,
            "progress_msg": row.progress_msg, "error": loi_cho_khach(row),
            "result": row.result if row.status == "done" else None}


@router.post("/api/projects/{project_id}/apply/{job_id}")
async def apply_job(request: Request, project_id: str, job_id: str,
                    _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    project = _owned_production(db, project_id, user.id)
    from platform_core.models import JOB_DONE, Job
    job = db.get(Job, job_id)
    if (job is None or job.user_id != user.id or job.app_slug != MANIFEST.slug or
            job.status != JOB_DONE or (job.params or {}).get("project_id") != project_id):
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy kết quả job.'))
    package = (job.result or {}).get("prompt_package") or {}
    payload = clean_project(copy.deepcopy(project.payload))
    payload["scenes"] = package.get("scenes") or []
    payload["job_refs"] = list(dict.fromkeys([*payload.get("job_refs", []), job.id]))[-80:]
    payload["ui"]["active_step"] = "storyboard"
    if (job.result or {}).get("operation") == "storyboard":
        payload["storyboard"]["frames"] = [{
            "scene_id": scene["id"], "image_job_id": "", "image_key": "",
            "prompt": scene.get("prompt", "")[:4000], "status": "prompt_ready"
        } for scene in payload["scenes"]]
    from platform_core import app_projects
    try:
        row = app_projects.save(db, project_id=project_id, user_id=user.id,
                                app_slug=MANIFEST.slug,
                                revision=int(body.get("revision") or 0),
                                name=payload["brief"]["title"],
                                schema_version=SCHEMA_VERSION, payload=payload)
    except app_projects.ProjectConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _row(row)
