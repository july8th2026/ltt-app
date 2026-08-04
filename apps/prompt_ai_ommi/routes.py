"""Tenant-safe web/API surface for PROMPT AI OMMI."""
from __future__ import annotations

import copy
import io
import json
import os
import uuid
import zipfile
from pathlib import Path, PurePath

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Request,
                     UploadFile)
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.manifest import MANIFEST
from apps.prompt_ai_ommi.project_schema import (SCHEMA_VERSION, clean_project,
                                                empty_project, prompt_job_params)
from apps.prompt_ai_ommi.services.composer import load_catalog
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, is_operator, user_hien_tai
from server.templating import templates

router = APIRouter(tags=["prompt-ai-ommi"])
_ASSET_CAP = {"image": 20 * 1024 * 1024, "video": 60 * 1024 * 1024,
              "audio": 20 * 1024 * 1024}
_PREFERENCES_KIND = "preferences"


def _run_mode() -> str:
    configured = os.environ.get("LTT_PROMPT_AI_OMMI_ROLLOUT")
    if configured is not None:
        mode = configured.strip().lower()
        return mode if mode in {"off", "admin", "allowlist", "public"} else "off"
    return "off" if os.environ.get("LTT_ENV", "").strip().lower() in {
        "production", "prod"} else "public"


def _require_run_enabled(user) -> None:
    mode = _run_mode()
    allowed = {value.strip() for value in os.environ.get(
        "LTT_PROMPT_AI_OMMI_USER_IDS", "").split(",") if value.strip()}
    enabled = (mode == "public" or
               mode == "admin" and getattr(user, "role", "") == "admin" or
               mode == "allowlist" and (getattr(user, "role", "") == "admin" or
                                         str(getattr(user, "id", "")) in allowed))
    if not enabled:
        raise HTTPException(status_code=503, detail="Tạo job PROMPT AI OMMI đang tạm khóa.")


def _user(request: Request):
    user = user_hien_tai(request)
    if user is None:
        raise HTTPException(status_code=403,
                            detail="Cần tài khoản người dùng trong CSDL để sử dụng app.")
    return user


def _csrf(request: Request, body: dict | None = None) -> None:
    token = request.headers.get("X-CSRF-Token", "") or str((body or {}).get("csrf_token") or "")
    if not verify_csrf_token(request, token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn — tải lại trang.")


def _as_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


def _row(row) -> dict:
    return {"id": row.id, "name": row.name, "revision": row.revision,
            "schema_version": row.schema_version, "status": row.status,
            "payload": row.payload or {}, "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat()}


def _production_rows(db: Session, user_id: str, *, include_archived: bool = False):
    from platform_core.models import APP_PROJECT_ACTIVE, AppProject
    stmt = select(AppProject).where(AppProject.user_id == user_id,
                                    AppProject.app_slug == MANIFEST.slug)
    if not include_archived:
        stmt = stmt.where(AppProject.status == APP_PROJECT_ACTIVE)
    rows = db.execute(stmt.order_by(AppProject.updated_at.desc()).limit(120)).scalars().all()
    return [row for row in rows if (row.payload or {}).get("kind") == "production"]


def _owned_production(db: Session, project_id: str, user_id: str):
    from platform_core import app_projects
    try:
        row = app_projects.get_owned(db, project_id, user_id, MANIFEST.slug)
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy project.") from None
    if (row.payload or {}).get("kind") != "production":
        raise HTTPException(status_code=404, detail="Không tìm thấy project.")
    return row


def _models(category: str) -> list[dict]:
    from platform_core import providers
    return providers.model_options(category, ("gemini",) if category in {"chat", "image"} else None)


def _preference_row(db: Session, user_id: str):
    from platform_core.models import AppProject
    rows = db.execute(select(AppProject).where(
        AppProject.user_id == user_id, AppProject.app_slug == MANIFEST.slug
    ).order_by(AppProject.updated_at.desc()).limit(160)).scalars().all()
    return next((row for row in rows if (row.payload or {}).get("kind") == _PREFERENCES_KIND), None)


def _preference_payload(row) -> dict:
    raw = (row.payload or {}) if row is not None else {}
    return {"theme": raw.get("theme") if raw.get("theme") in {"light", "dark"} else "light"}


def _jobs(db: Session, user_id: str) -> list[dict]:
    from platform_core.models import Job
    rows = db.execute(select(Job).where(
        Job.user_id == user_id, Job.app_slug == MANIFEST.slug
    ).order_by(Job.created_at.desc()).limit(30)).scalars().all()
    return [{"id": row.id, "status": row.status, "progress": row.progress,
             "progress_msg": row.progress_msg, "error": row.error,
             "operation": str((row.params or {}).get("operation") or "director"),
             "project_id": str((row.params or {}).get("project_id") or ""),
             "created_at": row.created_at.isoformat()} for row in rows]


@router.get("", response_class=HTMLResponse)
def page(request: Request, _identity: str = Depends(require_login),
         db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=409, detail="Project không ở trạng thái lưu trữ.")
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
        raise HTTPException(status_code=404, detail="Không tìm thấy snapshot.") from None
    if ((snap.payload or {}).get("kind") != "snapshot" or
            (snap.payload or {}).get("source_project_id") != project_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy snapshot.")
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
    return preview(payload)


def _chat_model(value: str) -> str:
    allowed = {item["value"] for item in _models("chat")}
    if value in allowed:
        return value
    return next(iter(allowed), "gemini-2.5-flash")


@router.post("/api/projects/{project_id}/quote")
async def quote_project(request: Request, project_id: str,
                        _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    row = _owned_production(db, project_id, user.id)
    payload = clean_project(body.get("payload") or row.payload)
    operation = str(body.get("operation") or "director")
    params = prompt_job_params(payload, operation=operation,
                               model=_chat_model(str(body.get("model") or "")))
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
    params = prompt_job_params(payload, operation=operation,
                               model=_chat_model(str(body.get("model") or "")))
    if len(params["story"].strip()) < 20:
        raise HTTPException(status_code=422, detail="Nội dung brief tối thiểu 20 ký tự.")
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
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    return {"id": row.id, "app_slug": row.app_slug, "job_type": row.job_type,
            "status": row.status, "progress": row.progress,
            "progress_msg": row.progress_msg, "error": row.error,
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
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả job.")
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


def _tool(tool_name: str):
    from platform_core.agent.tools import discover_tools
    from platform_core.registry import discover
    loaded = discover(); spec = discover_tools(apps=loaded).get(tool_name)
    if spec is None:
        raise HTTPException(status_code=503, detail="Công cụ handoff chưa khả dụng.")
    owner = next((item for item in loaded if any(t.name == tool_name for t in item.manifest.tools)), None)
    if owner is None:
        raise HTTPException(status_code=503, detail="Không xác định được app nhận handoff.")
    return loaded, spec, owner


def _handoff_params(project, scene: dict, kind: str, body: dict) -> tuple[str, dict]:
    if kind == "image":
        tool_name = "image.generate"
        params = {"prompt": str(scene.get("prompt") or "")[:4000],
                  "model": str(body.get("model") or next(
                      (item["value"] for item in _models("image")), "gemini-2.5-flash-image")),
                  "aspect_ratio": str((project.payload or {}).get("brief", {}).get(
                      "aspect_ratio") or "16:9"),
                  "count": _as_int(body.get("count"), 1, 1, 4)}
    elif kind == "video":
        tool_name = "video.generate"
        params = {"prompt": str(scene.get("prompt") or "")[:10000],
                  "model": str(body.get("model") or "seedance-2.0-mini"),
                  "resolution": str(body.get("resolution") or "480p"),
                  "duration": _as_int(body.get("duration") or scene.get("duration_seconds"),
                                      5, 1, 60),
                  "aspect_ratio": str((project.payload or {}).get("brief", {}).get(
                      "aspect_ratio") or "16:9"),
                  "generate_audio": bool(body.get("generate_audio", True)),
                  "camera": "", "motion": "cinematic", "visual_style": "cinematic",
                  "refs": []}
    else:
        raise HTTPException(status_code=404, detail="Loại handoff không hỗ trợ.")
    from platform_core import providers
    capabilities = providers.model_capabilities(params["model"])
    if kind == "image":
        aspects = list(capabilities.get("aspects") or ["16:9", "9:16", "1:1", "4:3", "3:4"])
        if params["aspect_ratio"] not in aspects:
            params["aspect_ratio"] = "16:9" if "16:9" in aspects else aspects[0]
    else:
        durations = [int(value) for value in capabilities.get("durations", [])]
        if durations and params["duration"] not in durations:
            params["duration"] = min(durations, key=lambda value: abs(value - params["duration"]))
        resolutions = list(capabilities.get("resolutions") or [])
        if resolutions and params["resolution"] not in resolutions:
            params["resolution"] = resolutions[0]
        aspects = list(capabilities.get("aspects") or [])
        if aspects and params["aspect_ratio"] not in aspects:
            params["aspect_ratio"] = "16:9" if "16:9" in aspects else aspects[0]
    return tool_name, params


@router.post("/api/projects/{project_id}/handoff/{kind}", status_code=201)
async def handoff(request: Request, project_id: str, kind: str,
                  _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    project = _owned_production(db, project_id, user.id)
    scenes = list((project.payload or {}).get("scenes") or [])
    scene = next((item for item in scenes if item.get("id") == body.get("scene_id")), None)
    if scene is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảnh.")
    tool_name, params = _handoff_params(project, scene, kind, body)
    loaded, spec, owner = _tool(tool_name)
    from platform_core.agent.tools import ToolParamsError, validate_tool_params
    try:
        clean = validate_tool_params(tool_name, params, apps=loaded)
    except ToolParamsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    clean["owner_id"] = user.id
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError, credit_for
    quote = credit_for(spec.job_type, clean)
    if not bool(body.get("confirmed")):
        return JSONResponse({"confirmed": False, "credit": quote,
                             "tool": tool_name, "authoritative": True}, status_code=200)
    try:
        job = submit_with_credit(db, user_id=user.id, app_slug=owner.slug,
                                 job_type=spec.job_type, params=clean,
                                 dedupe_key=dedupe_key_for(spec.job_type, clean))
    except (credit.ThieuCreditError, RegistryError) as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"confirmed": True, "credit": quote, "id": job.id,
            "app_slug": owner.slug, "job_url": f"/jobs/{job.id}"}


@router.post("/api/projects/{project_id}/handoff-batch/image", status_code=201)
async def handoff_image_batch(request: Request, project_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    project = _owned_production(db, project_id, user.id)
    requested = set(str(value) for value in list(body.get("scene_ids") or [])[:20])
    scenes = [scene for scene in list((project.payload or {}).get("scenes") or [])
              if scene.get("id") in requested]
    if not scenes:
        raise HTTPException(status_code=422, detail="Chưa chọn cảnh hợp lệ để tạo frame.")
    loaded, spec, owner = _tool("image.generate")
    from platform_core.agent.tools import ToolParamsError, validate_tool_params
    prepared = []
    for scene in scenes:
        _, params = _handoff_params(project, scene, "image", body)
        try:
            clean = validate_tool_params("image.generate", params, apps=loaded)
        except ToolParamsError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        clean["owner_id"] = user.id; prepared.append((scene["id"], clean))
    from platform_core.registry import credit_for
    total = sum(credit_for(spec.job_type, params) for _, params in prepared)
    if not bool(body.get("confirmed")):
        return JSONResponse({"confirmed": False, "credit": total,
                             "count": len(prepared), "authoritative": True}, status_code=200)
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    jobs = []
    try:
        for scene_id, params in prepared:
            job = submit_with_credit(db, user_id=user.id, app_slug=owner.slug,
                                     job_type=spec.job_type, params=params,
                                     dedupe_key=dedupe_key_for(spec.job_type, params))
            jobs.append({"scene_id": scene_id, "id": job.id, "status": job.status})
    except (credit.ThieuCreditError, RegistryError) as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"confirmed": True, "credit": total, "count": len(jobs), "jobs": jobs}


@router.get("/api/admin/health")
def admin_health(request: Request, _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    user = _user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin được xem vận hành.")
    from sqlalchemy import func
    from platform_core.models import AppProject, Job
    projects = db.execute(select(func.count()).select_from(AppProject).where(
        AppProject.app_slug == MANIFEST.slug)).scalar_one()
    statuses = dict(db.execute(select(Job.status, func.count()).where(
        Job.app_slug == MANIFEST.slug).group_by(Job.status)).all())
    return {"app_slug": MANIFEST.slug, "projects": int(projects),
            "jobs": {str(key): int(value) for key, value in statuses.items()},
            "provider": "gemini", "secret_values_exposed": False}


@router.post("/api/assets", status_code=201)
async def upload_asset(request: Request, file: UploadFile = File(...),
                       kind: str = Form("image"), name: str = Form(""),
                       description: str = Form(""),
                       _identity: str = Depends(require_login)):
    _csrf(request); user = _user(request)
    content_type = str(file.content_type or "").lower()
    detected = "image" if content_type.startswith("image/") else (
        "video" if content_type.startswith("video/") else (
            "audio" if content_type.startswith("audio/") else ""))
    if not detected:
        raise HTTPException(status_code=415, detail="Chỉ nhận ảnh, video hoặc audio.")
    data = await file.read(_ASSET_CAP[detected] + 1)
    if not data or len(data) > _ASSET_CAP[detected]:
        raise HTTPException(status_code=413, detail="File rỗng hoặc vượt giới hạn.")
    if detected == "image":
        try:
            from PIL import Image
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        except Exception:
            raise HTTPException(status_code=422, detail="File ảnh không hợp lệ.") from None
    safe_name = PurePath(str(file.filename or "asset").replace("\\", "/")).name[:120]
    suffix = Path(safe_name).suffix.lower()[:10]
    key = f"prompt_ai_ommi/{user.id}/assets/{uuid.uuid4().hex}{suffix}"
    from platform_core.storage import get_storage
    stored = get_storage().put(key, io.BytesIO(data), content_type=content_type)
    return {"id": f"res_{uuid.uuid4().hex[:12]}",
            "kind": kind if kind in {"character", "location", "prop", "style"} else detected,
            "name": str(name or safe_name)[:120], "description": str(description)[:1200],
            "storage_key": stored.key, "content_type": content_type, "size": stored.size}


@router.get("/api/projects/{project_id}/export/{fmt}")
def export_project(request: Request, project_id: str, fmt: str,
                   _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request); row = _owned_production(db, project_id, user.id)
    payload = clean_project(row.payload)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in row.name)[:80] or "prompt-ai-ommi"
    if fmt == "json":
        data = json.dumps({"format": "ltt-prompt-ai-ommi", "version": 1,
                           "name": row.name, "project": payload}, ensure_ascii=False,
                          indent=2).encode("utf-8")
        return Response(data, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{safe}.json"'})
    lines = [f"# {payload['brief']['title']}", "", payload["brief"]["story"], ""]
    for scene in payload["scenes"]:
        lines += [f"## {scene['order'] + 1}. {scene['title']}", "",
                  scene["summary"], "", "### Prompt", "", scene["prompt"], "",
                  "### Negative prompt", "", scene["negative_prompt"], ""]
    markdown = "\n".join(lines).encode("utf-8")
    if fmt == "md":
        return Response(markdown, media_type="text/markdown; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{safe}.md"'})
    if fmt == "zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(f"{safe}.md", markdown)
            archive.writestr(f"{safe}.json", json.dumps(
                {"format": "ltt-prompt-ai-ommi", "version": 1, "name": row.name,
                 "project": payload}, ensure_ascii=False, indent=2))
        return Response(buf.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{safe}.zip"'})
    raise HTTPException(status_code=404, detail="Định dạng export không hỗ trợ.")


@router.post("/api/import", status_code=201)
async def import_project(request: Request, _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if len(raw) > 900_000:
        raise HTTPException(status_code=413, detail="Package vượt giới hạn 900 KiB.")
    if body.get("format") != "ltt-prompt-ai-ommi" or body.get("version") != 1:
        raise HTTPException(status_code=422, detail="Package không đúng định dạng.")
    payload = clean_project(body.get("project") or {})
    # Không nhập storage key từ package khác: asset binary phải upload lại.
    for item in payload["resources"]:
        item["storage_key"] = ""; item["size"] = 0; item["content_type"] = ""
    from platform_core import app_projects
    row = app_projects.create(db, user_id=user.id, app_slug=MANIFEST.slug,
                              name=str(body.get("name") or payload["brief"]["title"])[:160],
                              schema_version=SCHEMA_VERSION, payload=payload)
    return _row(row)


@router.get("/api/catalog")
def catalog(request: Request, _identity: str = Depends(require_login),
            db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services.composer import load_catalog
    from platform_core.models import APP_PROJECT_ACTIVE, AppProject
    rows = db.execute(select(AppProject).where(
        AppProject.app_slug == MANIFEST.slug, AppProject.status == APP_PROJECT_ACTIVE
    ).order_by(AppProject.updated_at.desc()).limit(100)).scalars().all()
    published = [{"id": row.id, "name": row.name,
                  "item": (row.payload or {}).get("item", {})}
                 for row in rows if (row.payload or {}).get("kind") == "published_catalog" and
                 (row.payload or {}).get("published") is True]
    return {"built_in": load_catalog(), "published": published}


@router.post("/api/admin/catalog", status_code=201)
async def admin_catalog(request: Request, _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin được publish catalog.")
    item = body.get("item") if isinstance(body.get("item"), dict) else {}
    payload = {"kind": "published_catalog", "version": 1, "published": True,
               "item": {"type": str(item.get("type") or "template")[:40],
                        "label": str(item.get("label") or "Mẫu LTT")[:120],
                        "description": str(item.get("description") or "")[:1000],
                        "content": str(item.get("content") or "")[:12000],
                        "provenance": str(item.get("provenance") or "LTT")[:300]}}
    from platform_core import app_projects
    row = app_projects.create(db, user_id=user.id, app_slug=MANIFEST.slug,
                              name=payload["item"]["label"], schema_version=1,
                              payload=payload)
    return _row(row)
