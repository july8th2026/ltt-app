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


_WORKSPACE_MANIFEST = (Path(__file__).resolve().parents[2] / "server" / "static" /
                       "prompt-ai-ommi" / ".vite" / "manifest.json")


def _workspace_assets():
    """Đường dẫn bundle React đã build. Thiếu manifest thì trả rỗng.

    Không tự dựng một giao diện tạm khi thiếu bundle: template sẽ nói rõ và trỏ
    người dùng về trang đang chạy được, thay vì hiện một vỏ trống trông như hỏng.
    """
    try:
        manifest = json.loads(_WORKSPACE_MANIFEST.read_text(encoding="utf-8"))
        entry = manifest["src/main.tsx"]
        return ([f"/static/prompt-ai-ommi/{entry['file']}"],
                [f"/static/prompt-ai-ommi/{item}" for item in entry.get("css", [])])
    except (OSError, KeyError, ValueError):
        return [], []


@router.get("/workspace", response_class=HTMLResponse)
def workspace(request: Request, _identity: str = Depends(require_login)):
    """Workspace mới (Kho tài nguyên). Trang chính vẫn giữ nguyên cho tới khi
    đủ màn — chuyển sớm sẽ lấy mất Brief/Director/Export đang dùng được."""
    scripts, styles = _workspace_assets()
    return templates.TemplateResponse(request, "prompt_ai_ommi_workspace.html", {
        "user": _user(request).email, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "workspace_js": scripts, "workspace_css": styles,
    })


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


# ── Kho tài nguyên (R1) ─────────────────────────────────────────────────────
#
# Mọi handler dưới đây nhận `owner_id` từ PHIÊN ĐĂNG NHẬP, không bao giờ từ
# body hay query. Cho client gửi owner_id lên là trao luôn chìa khoá đọc dữ
# liệu người khác.
#
# Service ném `ResourceNotFound` cho cả "không có" lẫn "không phải của bạn";
# ở đây cả hai thành 404 giống hệt nhau.

def _resource_json(row, *, cover_key: str = "") -> dict:
    return {"id": row.id, "kind": row.kind, "name": row.name,
            "description": row.description, "prompt_text": row.prompt_text,
            "attributes": row.attributes or {},
            "cover_variant_id": row.cover_variant_id or "",
            "cover_key": cover_key,
            "is_catalog": row.owner_id is None,
            "archived": row.archived_at is not None,
            "updated_at": row.updated_at.isoformat()}


def _variant_json(row) -> dict:
    return {"id": row.id, "label": row.label, "storage_key": row.storage_key,
            "thumb_key": row.thumb_key, "width": row.width,
            "height": row.height, "bytes_size": row.bytes_size,
            "position": row.position}


def _resource_error(exc: Exception) -> HTTPException:
    """Chỉ dịch lỗi CỦA NGƯỜI DÙNG. Mọi thứ khác để nguyên cho 500.

    Bản đầu bắt `Exception` rồi trả 400 cho tất cả. Hậu quả thấy ngay trên
    browser: bảng CSDL chưa tồn tại — lỗi máy chủ — lại báo "yêu cầu không hợp
    lệ", nên người dùng đi sửa thứ họ gõ trong khi hỏng nằm ở máy chủ, và log
    không ghi gì vì 400 được coi là bình thường.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    if isinstance(exc, rsvc.ResourceNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, rsvc.ResourceError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.get("/api/resources")
def list_resources(request: Request, kind: str = "", q: str = "",
                   catalog: bool = False, archived: bool = False,
                   limit: int = 40, offset: int = 0,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    user = _user(request)
    try:
        rows, total = rsvc.list_resources(
            db, user.id, kind=kind, query=q, include_catalog=bool(catalog),
            include_archived=bool(archived),
            limit=_as_int(limit, 40, 1, rsvc.PAGE_MAX),
            offset=_as_int(offset, 0, 0, 1_000_000))
    except Exception as exc:
        raise _resource_error(exc) from exc
    return {"items": [_resource_json(row) for row in rows], "total": total,
            "limit": _as_int(limit, 40, 1, rsvc.PAGE_MAX),
            "offset": _as_int(offset, 0, 0, 1_000_000),
            "counts": rsvc.count_by_kind(db, user.id),
            "kinds": list(rsvc.RESOURCE_KINDS)}


@router.post("/api/resources", status_code=201)
async def create_resource(request: Request, _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = rsvc.create(db, owner_id=user.id, kind=body.get("kind", ""),
                          name=body.get("name", ""),
                          description=body.get("description", ""),
                          prompt_text=body.get("prompt_text", ""),
                          attributes=body.get("attributes"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _resource_json(row)


@router.get("/api/resources/{resource_id}")
def get_resource(request: Request, resource_id: str,
                 _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    user = _user(request)
    try:
        row = rsvc.get_visible(db, resource_id, user.id)
        payload = _resource_json(row)
        payload["variants"] = [_variant_json(v)
                               for v in rsvc.variants(db, resource_id, user.id)]
        payload["tags"] = [t.name for t in rsvc.tags_of(db, resource_id, user.id)]
    except Exception as exc:
        raise _resource_error(exc) from exc
    return payload


@router.put("/api/resources/{resource_id}")
async def update_resource(request: Request, resource_id: str,
                          _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    fields = {key: body[key] for key in
              ("name", "kind", "description", "prompt_text", "attributes")
              if key in body}
    try:
        row = rsvc.update(db, resource_id=resource_id, owner_id=user.id, **fields)
        if isinstance(body.get("tags"), list):
            rsvc.set_tags(db, resource_id=resource_id, owner_id=user.id,
                          names=body["tags"])
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _resource_json(row)


@router.post("/api/resources/{resource_id}/archive")
async def archive_resource(request: Request, resource_id: str,
                           _identity: str = Depends(require_login),
                           db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = rsvc.archive(db, resource_id=resource_id, owner_id=user.id,
                           archived=bool(body.get("archived", True)))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _resource_json(row)


@router.post("/api/resources/{resource_id}/clone", status_code=201)
async def clone_resource(request: Request, resource_id: str,
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = rsvc.clone_from_catalog(db, resource_id=resource_id, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _resource_json(row)


@router.get("/api/resources/{resource_id}/usage")
def resource_usage(request: Request, resource_id: str,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    user = _user(request)
    try:
        rows = rsvc.usage(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc
    return {"items": [{"project_id": r.project_id, "scene_ref": r.scene_ref}
                      for r in rows], "total": len(rows)}


# ── Ảnh của tài nguyên (R1.3) ──────────────────────────────────────────────
#
# Hai đường, cùng một kết quả:
#   1. Có R2 và CORS đã bật  -> trả vé presigned, trình duyệt PUT THẲNG lên R2.
#      Ảnh không đi qua tunnel nên không đụng trần 100 MB của Cloudflare.
#   2. Chưa có               -> nhận multipart qua route, giới hạn nhỏ hơn.
#
# Dù đi đường nào, `confirm` mới là chỗ ghi vào CSDL, và nó luôn kiểm quyền sở
# hữu tài nguyên trước. Không có đường nào ghi ảnh vào tài nguyên người khác.

_RESOURCE_IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg",
                         "image/webp": ".webp"}
_RESOURCE_IMAGE_CAP = 20 * 1024 * 1024


def _browser_direct_upload_enabled() -> bool:
    """Presigned PUT chỉ chạy sau khi luật CORS của bucket đã được kiểm.

    Mặc định tắt để không tạo ra một lỗi CORS chắc chắn rồi mới rơi về
    multipart — người dùng thấy lỗi đỏ trước khi thấy nó tự chữa.
    """
    return os.environ.get("LTT_R2_BROWSER_UPLOAD_ENABLED", "").strip() == "1"


def _image_key(user_id: str, resource_id: str, content_type: str):
    """Khoá lưu trữ, giữ NGẮN có chủ đích.

    Windows giới hạn đường dẫn 260 ký tự và `LocalStorage` còn thêm hậu tố
    `.part<pid>` khi ghi. Bản đầu dùng
    `prompt_ai_ommi/{uuid}/resources/{uuid}/{32 hex}` ≈ 145 ký tự và đã vỡ thật
    khi thư mục gốc dài — `FileNotFoundError` chứ không phải lỗi nói rõ là quá
    dài, nên rất khó đoán. Production hiện có gốc ngắn nên chưa vỡ; đó là may,
    không phải thiết kế.

    Vẫn giữ ĐỦ `user_id` và `resource_id` vì `confirm` dựa vào tiền tố này để
    buộc khoá thuộc đúng người gọi và đúng tài nguyên.
    """
    ct = (content_type or "").split(";")[0].strip().lower()
    ext = _RESOURCE_IMAGE_TYPES.get(ct)
    if ext is None:
        raise HTTPException(status_code=400,
                            detail="Chỉ nhận ảnh PNG, JPEG hoặc WebP.")
    return f"ommi/{user_id}/{resource_id}/{uuid.uuid4().hex[:16]}{ext}", ct


@router.post("/api/resources/{resource_id}/images/ticket")
async def resource_image_ticket(request: Request, resource_id: str,
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    """Xin chỗ để tải ảnh lên. Kiểm quyền TRƯỚC khi cấp vé."""
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.storage import get_storage
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        rsvc.get_owned(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc

    key, ct = _image_key(user.id, resource_id, body.get("content_type", ""))
    target = None
    if _browser_direct_upload_enabled():
        try:
            target = get_storage().put_url(key, ttl_s=3600, content_type=ct)
        except Exception:  # noqa: BLE001
            target = None
    if target is None:
        return {"mode": "local", "key": key, "max_bytes": _RESOURCE_IMAGE_CAP}
    return {"mode": "direct", "key": target.key, "url": target.url,
            "method": target.method, "headers": target.headers or {}}


@router.post("/api/resources/{resource_id}/images", status_code=201)
async def upload_resource_image(request: Request, resource_id: str,
                                file: UploadFile = File(...),
                                csrf_token: str = Form(""),
                                label: str = Form(""),
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    """Đường dự phòng: nhận multipart khi chưa bật upload thẳng lên R2."""
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.storage import get_storage
    _csrf(request, {"csrf_token": csrf_token}); user = _user(request)
    try:
        rsvc.get_owned(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc

    key, ct = _image_key(user.id, resource_id, file.content_type or "")
    data = await file.read(_RESOURCE_IMAGE_CAP + 1)
    if len(data) > _RESOURCE_IMAGE_CAP:
        raise HTTPException(status_code=413, detail="Ảnh vượt 20 MB.")
    if not data:
        raise HTTPException(status_code=400, detail="File rỗng.")
    get_storage().put(key, io.BytesIO(data), content_type=ct)
    try:
        row = rsvc.add_variant(db, resource_id=resource_id, owner_id=user.id,
                               storage_key=key, label=label,
                               bytes_size=len(data))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _variant_json(row)


@router.post("/api/resources/{resource_id}/images/confirm", status_code=201)
async def confirm_resource_image(request: Request, resource_id: str,
                                 _identity: str = Depends(require_login),
                                 db: Session = Depends(get_db)):
    """Ghi nhận ảnh đã PUT thẳng lên storage.

    Kiểm ba việc trước khi ghi: tài nguyên là của người gọi, khoá nằm ĐÚNG
    trong thư mục của người gọi, và file có thật trên storage. Thiếu kiểm thứ
    hai thì client gửi khoá của người khác là gắn được ảnh người ta vào tài
    nguyên của mình.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.storage import get_storage
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        rsvc.get_owned(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc

    key = str(body.get("key") or "").strip()
    prefix = f"ommi/{user.id}/{resource_id}/"
    if not key.startswith(prefix):
        raise HTTPException(status_code=400, detail="Khoá lưu trữ không hợp lệ.")
    storage = get_storage()
    if not storage.exists(key):
        raise HTTPException(status_code=400, detail="Chưa thấy file trên kho lưu trữ.")
    try:
        row = rsvc.add_variant(db, resource_id=resource_id, owner_id=user.id,
                               storage_key=key, label=str(body.get("label") or ""),
                               width=_as_int(body.get("width"), 0, 0, 20000),
                               height=_as_int(body.get("height"), 0, 0, 20000),
                               bytes_size=storage.size(key))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _variant_json(row)


@router.delete("/api/resources/{resource_id}/images/{variant_id}")
async def delete_resource_image(request: Request, resource_id: str,
                                variant_id: str,
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    _csrf(request); user = _user(request)
    try:
        rsvc.remove_variant(db, variant_id=variant_id, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return {"ok": True}


@router.get("/api/resources/{resource_id}/images/{variant_id}/url")
def resource_image_url(request: Request, resource_id: str, variant_id: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    """URL xem ảnh.

    KHÔNG dùng `storage.download_token`: token nằm trong RAM của TỪNG tiến
    trình, mà worker (tạo ảnh) và web (phục vụ ảnh) là hai tiến trình khác nhau
    — token cấp ở đây tiến trình kia không biết. Bản đầu trả token và ảnh 404
    trên browser đúng vì lý do đó. App tự phục vụ file qua `/f/{key}` và kiểm
    sở hữu theo khoá, giống các app ảnh khác.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    user = _user(request)
    try:
        found = [v for v in rsvc.variants(db, resource_id, user.id)
                 if v.id == variant_id]
    except Exception as exc:
        raise _resource_error(exc) from exc
    if not found:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    return {"url": f"{MANIFEST.route_prefix}/f/{found[0].storage_key}"}


@router.get("/f/{key:path}")
def resource_image_file(request: Request, key: str,
                        _identity: str = Depends(require_login)):
    """Phục vụ ảnh tài nguyên, kiểm sở hữu NGAY TRÊN KHOÁ.

    Khoá có dạng `ommi/{owner_id}/{resource_id}/...`, nên chỉ cần so đoạn thứ
    hai với người đang đăng nhập là đủ chặn đọc chéo — không phải tra CSDL.
    Ảnh do `taoanh.generate` sinh nằm ngoài tiền tố này và được phục vụ bởi
    chính app Tạo ảnh.
    """
    from fastapi.responses import RedirectResponse, StreamingResponse
    from platform_core.storage import StorageError, get_storage
    user = _user(request)
    segments = key.split("/")
    if len(segments) < 3 or segments[0] != "ommi" or segments[1] != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    storage = get_storage()
    try:
        direct = storage.url_for(key)
    except Exception:  # noqa: BLE001
        direct = None
    if direct:
        return RedirectResponse(direct, status_code=302)
    try:
        stream = storage.open(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.") from None
    kind = "image/png" if key.endswith(".png") else (
        "image/webp" if key.endswith(".webp") else "image/jpeg")
    return StreamingResponse(stream, media_type=kind)


# ── Sinh ảnh cho tài nguyên (R1.5) ─────────────────────────────────────────
#
# OMMI sở hữu ĐIỀU PHỐI và trải nghiệm; lời gọi provider dùng lại job
# `taoanh.generate` của app Tạo ảnh. Người dùng không rời OMMI.
#
# Vì sao không dựng engine riêng: phần có giá trị trong `image_gen` của module
# nguồn (3.269 dòng) là sinh hàng loạt theo cảnh, chèn ảnh tham chiếu để giữ
# nhất quán nhân vật, và phiên bản theo cảnh — tất cả nằm TRÊN lời gọi provider,
# không phải bên trong nó. `image.generate` đã nhận `image_keys`, tức cơ chế
# nhất quán đã có sẵn. Dựng engine thứ hai chỉ nhân đôi tích hợp provider, xoay
# khoá, retry và bảng giá.
#
# Cơ chế cho phép điều này, đã kiểm: worker phân việc theo `job_type` chứ không
# theo `app_slug` (`platform_core/jobs.py`), và giá tra theo `job_type`
# (`platform_core/job_submit.py`). Nên OMMI nộp `taoanh.generate` là hợp lệ và
# tính đúng giá của Tạo ảnh.

_IMAGE_JOB_TYPE = "taoanh.generate"


def _reference_keys(db, *, resource_id: str, owner_id: str,
                    variant_ids: list) -> list:
    """Ảnh tham chiếu để giữ nhất quán nhân vật giữa các lần sinh.

    Chỉ chọn trong ảnh CỦA CHÍNH tài nguyên này. Client gửi ID lạ — của người
    khác hay của tài nguyên khác — thì ID đó rơi ra, không có đường nào ép
    provider đọc ảnh riêng tư của người khác.

    Phép so `owner_id` bên dưới là phòng thủ lớp hai chứ không phải lớp chính:
    `variants()` đã lọc qua tài nguyên, và caller luôn gọi `get_owned` trước.
    Nó chỉ có tác dụng nếu sau này có ai cho phép tham chiếu ảnh của mẫu
    catalog (owner NULL) — giữ lại để lúc đó không phải nhớ ra.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    wanted = {str(v) for v in (variant_ids or [])[:4] if v}
    if not wanted:
        return []
    keys = []
    for variant in rsvc.variants(db, resource_id, owner_id):
        if variant.id in wanted and variant.owner_id == owner_id:
            keys.append(variant.storage_key)
    return keys


def _image_params(request_body: dict, *, resource, owner_id: str,
                  reference_keys: list) -> dict:
    prompt = str(request_body.get("prompt") or resource.prompt_text
                 or resource.description or resource.name).strip()
    if len(prompt) < 8:
        raise HTTPException(status_code=422,
                            detail="Mô tả ảnh quá ngắn — tối thiểu 8 ký tự.")
    params = {
        "prompt": prompt[:4000],
        "aspect_ratio": str(request_body.get("aspect_ratio") or "1:1"),
        "count": _as_int(request_body.get("count"), 1, 1, 4),
        "owner_id": owner_id,
    }
    model = str(request_body.get("model") or "").strip()
    if model:
        params["model"] = model
    if reference_keys:
        params["image_keys"] = reference_keys
    return params


@router.post("/api/resources/{resource_id}/images/generate")
async def generate_resource_image(request: Request, resource_id: str,
                                  _identity: str = Depends(require_login),
                                  db: Session = Depends(get_db)):
    """Báo giá, rồi chạy khi `confirmed` là true.

    Một endpoint làm hai việc để giá người dùng thấy và giá bị trừ được tính
    bằng ĐÚNG một đoạn mã. Tách đôi là mở đường cho hai công thức lệch nhau.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.registry import credit_for
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        resource = rsvc.get_owned(db, resource_id, user.id)
        refs = _reference_keys(db, resource_id=resource_id, owner_id=user.id,
                               variant_ids=body.get("reference_variant_ids") or [])
    except HTTPException:
        raise
    except Exception as exc:
        raise _resource_error(exc) from exc

    params = _image_params(body, resource=resource, owner_id=user.id,
                           reference_keys=refs)
    estimate = int(credit_for(_IMAGE_JOB_TYPE, params))
    if not body.get("confirmed"):
        return {"credit": estimate, "count": params["count"],
                "reference_count": len(refs), "authoritative": True,
                "confirmed": False}

    _require_run_enabled(user)
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    try:
        job = submit_with_credit(
            db, user_id=user.id, app_slug=MANIFEST.slug,
            job_type=_IMAGE_JOB_TYPE, params=params,
            dedupe_key=dedupe_key_for(_IMAGE_JOB_TYPE, params))
        db.commit()
    except (credit.ThieuCreditError, RegistryError) as exc:
        db.rollback()
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"id": job.id, "status": job.status, "credit": estimate,
            "resource_id": resource_id, "job_url": f"/jobs/{job.id}"}


@router.post("/api/resources/{resource_id}/images/from-job", status_code=201)
async def attach_generated_images(request: Request, resource_id: str,
                                  _identity: str = Depends(require_login),
                                  db: Session = Depends(get_db)):
    """Gắn ảnh một job đã sinh vào tài nguyên.

    Quyền ở đây suy từ CHÍNH job (`job.user_id`), không suy từ tiền tố khoá như
    `confirm`: ảnh do `taoanh.generate` sinh nằm trong namespace của app Tạo
    ảnh, không nằm trong thư mục OMMI của người dùng. Hai đường kiểm khác nhau
    vì nguồn tin cậy khác nhau — nới lỏng luật tiền tố của `confirm` để dùng
    chung sẽ mở đúng lỗ hổng mà luật đó đang bịt.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.models import JOB_DONE, Job
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        rsvc.get_owned(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc

    job = db.get(Job, str(body.get("job_id") or ""))
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    if job.status != JOB_DONE:
        raise HTTPException(status_code=409, detail="Job chưa chạy xong.")
    if job.job_type != _IMAGE_JOB_TYPE:
        raise HTTPException(status_code=400, detail="Job này không sinh ảnh.")

    keys = [k for k in ((job.result or {}).get("image_keys") or []) if k][:4]
    if not keys:
        raise HTTPException(status_code=400, detail="Job không trả về ảnh nào.")

    made = []
    try:
        for index, key in enumerate(keys):
            made.append(rsvc.add_variant(
                db, resource_id=resource_id, owner_id=user.id, storage_key=key,
                label=str(body.get("label") or f"AI {index + 1}")))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return {"variants": [_variant_json(row) for row in made]}


# ── Thư viện: meta prompt / đoạn prompt / phong cách (R2) ───────────────────
#
# Một bộ endpoint cho cả ba loại, phân biệt bằng `{kind}` trong đường dẫn. Ba
# bộ giống nhau chỉ khác tên bảng là ba chỗ để quên sửa khi luật đổi — module
# nguồn có ba manager riêng và chúng đã lệch nhau thật.

def _library_error(exc: Exception) -> HTTPException:
    """Giống `_resource_error`: chỉ dịch lỗi của người dùng, còn lại để 500."""
    from apps.prompt_ai_ommi.services import library as lsvc
    if isinstance(exc, lsvc.LibraryNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, lsvc.LibraryError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


def _library_json(kind: str, row) -> dict:
    payload = {"id": row.id, "kind": kind, "name": row.name, "body": row.body,
               "is_catalog": row.owner_id is None,
               "cloned_from_id": row.cloned_from_id or "",
               "archived": row.archived_at is not None,
               "updated_at": row.updated_at.isoformat()}
    if kind == "meta":
        payload |= {"purpose": row.purpose, "variables": row.variables or {},
                    "version": row.version}
    elif kind == "snippet":
        payload |= {"category": row.category, "version": row.version}
    elif kind == "style":
        payload |= {"negative": row.negative, "attributes": row.attributes or {}}
    return payload


@router.get("/api/library/{kind}")
def list_library(request: Request, kind: str, q: str = "", catalog: bool = False,
                 archived: bool = False, limit: int = 40, offset: int = 0,
                 _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import library as lsvc
    user = _user(request)
    try:
        rows, total = lsvc.list_items(
            db, kind, user.id, catalog=bool(catalog), query=q,
            include_archived=bool(archived),
            limit=_as_int(limit, 40, 1, lsvc.PAGE_MAX),
            offset=_as_int(offset, 0, 0, 1_000_000))
    except Exception as exc:
        raise _library_error(exc) from exc
    return {"items": [_library_json(kind, row) for row in rows], "total": total,
            "catalog": bool(catalog), "counts": lsvc.counts(db, user.id)}


@router.post("/api/library/{kind}", status_code=201)
async def create_library_item(request: Request, kind: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = lsvc.create(db, kind, owner_id=user.id, name=body.get("name", ""),
                          body=body.get("body", ""),
                          purpose=body.get("purpose"),
                          category=body.get("category"),
                          negative=body.get("negative"),
                          variables=body.get("variables"),
                          attributes=body.get("attributes"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


@router.get("/api/library/{kind}/{item_id}")
def get_library_item(request: Request, kind: str, item_id: str,
                     _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import library as lsvc
    user = _user(request)
    try:
        row = lsvc.get_visible(db, kind, item_id, user.id)
        payload = _library_json(kind, row)
        # Lịch sử chỉ có với bản riêng; mẫu catalog không thuộc về ai để mà có.
        payload["versions"] = ([] if row.owner_id is None else
                               [{"version": v.version, "note": v.note,
                                 "created_at": v.created_at.isoformat()}
                                for v in lsvc.versions(db, kind, item_id, user.id)])
    except Exception as exc:
        raise _library_error(exc) from exc
    return payload


@router.put("/api/library/{kind}/{item_id}")
async def update_library_item(request: Request, kind: str, item_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    fields = {key: body[key] for key in
              ("name", "body", "purpose", "category", "negative", "variables",
               "attributes", "note") if key in body}
    try:
        row = lsvc.update(db, kind, item_id=item_id, owner_id=user.id, **fields)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


@router.post("/api/library/{kind}/{item_id}/archive")
async def archive_library_item(request: Request, kind: str, item_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = lsvc.archive(db, kind, item_id=item_id, owner_id=user.id,
                           archived=bool(body.get("archived", True)))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


@router.post("/api/library/{kind}/{item_id}/clone", status_code=201)
async def clone_library_item(request: Request, kind: str, item_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    """"Dùng mẫu này" — chỉ áp dụng cho mẫu catalog."""
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = lsvc.clone_from_catalog(db, kind, item_id=item_id, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


@router.post("/api/library/{kind}/{item_id}/publish", status_code=201)
async def publish_library_item(request: Request, kind: str, item_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    """Đưa một mục thành mẫu catalog. Quyền admin lấy từ CSDL, không từ body."""
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    if getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403,
                            detail="Chỉ admin được publish mẫu vào catalog.")
    try:
        row = lsvc.publish_to_catalog(db, kind, item_id=item_id,
                                      owner_id=user.id, is_admin=True)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


# ── Storyboard (R3) ────────────────────────────────────────────────────────
#
# Chỗ hai lớp trước gặp nhau: mỗi cảnh lấy tài nguyên để giữ nhất quán nhân vật
# và lấy phong cách từ thư viện để giữ giọng chung. Sinh ảnh vẫn đi qua
# `taoanh.generate` theo phương án đã chốt — OMMI sở hữu điều phối, không sở
# hữu engine.

def _storyboard_error(exc: Exception) -> HTTPException:
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    if isinstance(exc, ssvc.StoryboardNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ssvc.StoryboardError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


def _board_json(row) -> dict:
    return {"id": row.id, "project_id": row.project_id, "name": row.name,
            "meta_prompt_id": row.meta_prompt_id or "",
            "style_id": row.style_id or "", "aspect_ratio": row.aspect_ratio,
            "archived": row.archived_at is not None,
            "updated_at": row.updated_at.isoformat()}


def _scene_json(row) -> dict:
    return {"id": row.id, "storyboard_id": row.storyboard_id,
            "position": row.position, "title": row.title, "prompt": row.prompt,
            "camera": row.camera, "continuity": row.continuity,
            "resource_ids": list(row.resource_ids or []),
            "image_key": row.image_key, "version": row.version}


@router.get("/api/storyboards")
def list_storyboards(request: Request, project_id: str = "",
                     archived: bool = False,
                     _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    user = _user(request)
    rows = ssvc.list_boards(db, user.id, project_id=project_id,
                            include_archived=bool(archived))
    return {"items": [_board_json(row) for row in rows], "total": len(rows)}


@router.post("/api/storyboards", status_code=201)
async def create_storyboard(request: Request,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    project_id = str(body.get("project_id") or "")
    # Chỉ cho gắn vào project CỦA CHÍNH mình — nếu không, biết ID là gắn
    # storyboard vào project người khác.
    _owned_production(db, project_id, user.id)
    try:
        row = ssvc.create_board(db, owner_id=user.id, project_id=project_id,
                                name=body.get("name", "Storyboard mới"),
                                aspect_ratio=str(body.get("aspect_ratio") or "16:9"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _board_json(row)


@router.get("/api/storyboards/{board_id}")
def get_storyboard(request: Request, board_id: str,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    user = _user(request)
    try:
        board = ssvc.get_owned_board(db, board_id, user.id)
        rows = ssvc.scenes(db, board_id, user.id)
    except Exception as exc:
        raise _storyboard_error(exc) from exc
    return {**_board_json(board), "scenes": [_scene_json(row) for row in rows]}


@router.put("/api/storyboards/{board_id}")
async def update_storyboard(request: Request, board_id: str,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    fields = {key: body[key] for key in
              ("name", "aspect_ratio", "meta_prompt_id", "style_id") if key in body}
    try:
        row = ssvc.update_board(db, board_id=board_id, owner_id=user.id, **fields)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _board_json(row)


@router.post("/api/storyboards/{board_id}/scenes", status_code=201)
async def add_storyboard_scene(request: Request, board_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = ssvc.add_scene(db, board_id=board_id, owner_id=user.id,
                             title=body.get("title", ""),
                             prompt=body.get("prompt", ""),
                             camera=body.get("camera", ""),
                             resource_ids=body.get("resource_ids"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _scene_json(row)


@router.put("/api/scenes/{scene_id}")
async def update_scene_route(request: Request, scene_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    fields = {key: body[key] for key in
              ("title", "prompt", "camera", "continuity", "resource_ids")
              if key in body}
    try:
        row = ssvc.update_scene(db, scene_id=scene_id, owner_id=user.id, **fields)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _scene_json(row)


@router.delete("/api/scenes/{scene_id}")
async def delete_scene_route(request: Request, scene_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    _csrf(request); user = _user(request)
    try:
        ssvc.delete_scene(db, scene_id=scene_id, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return {"ok": True}


@router.post("/api/storyboards/{board_id}/reorder")
async def reorder_scenes(request: Request, board_id: str,
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        rows = ssvc.reorder(db, board_id=board_id, owner_id=user.id,
                            scene_ids=body.get("scene_ids") or [])
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return {"scenes": [_scene_json(row) for row in rows]}


@router.get("/api/scenes/{scene_id}/versions")
def scene_versions(request: Request, scene_id: str,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    user = _user(request)
    try:
        rows = ssvc.versions(db, scene_id, user.id)
    except Exception as exc:
        raise _storyboard_error(exc) from exc
    return {"items": [{"version": row.version, "image_key": row.image_key,
                       "job_id": row.job_id,
                       "created_at": row.created_at.isoformat()} for row in rows]}


@router.post("/api/scenes/{scene_id}/restore/{version}")
async def restore_scene_version(request: Request, scene_id: str, version: int,
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = ssvc.restore_version(db, scene_id=scene_id, owner_id=user.id,
                                   version=int(version))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _scene_json(row)


@router.post("/api/scenes/{scene_id}/render")
async def render_scene(request: Request, scene_id: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    """Báo giá rồi chạy MỘT cảnh. Cảnh khác không bị đụng và không bị tính tiền."""
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    from platform_core.registry import credit_for
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        scene = ssvc.get_owned_scene(db, scene_id, user.id)
        board = ssvc.get_owned_board(db, scene.storyboard_id, user.id)
        prompt = ssvc.compose_prompt(db, scene_id=scene_id, owner_id=user.id)
        refs = ssvc.reference_keys(db, scene_id=scene_id, owner_id=user.id)
    except Exception as exc:
        raise _storyboard_error(exc) from exc
    if len(prompt.strip()) < 8:
        raise HTTPException(status_code=422,
                            detail="Cảnh chưa đủ mô tả để sinh ảnh.")

    params = {"prompt": prompt[:4000], "aspect_ratio": board.aspect_ratio,
              "count": 1, "owner_id": user.id}
    if refs:
        params["image_keys"] = refs
    model = str(body.get("model") or "").strip()
    if model:
        params["model"] = model

    estimate = int(credit_for(_IMAGE_JOB_TYPE, params))
    if not body.get("confirmed"):
        return {"credit": estimate, "scene_id": scene_id,
                "reference_count": len(refs), "prompt_preview": prompt[:400],
                "confirmed": False}

    _require_run_enabled(user)
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    try:
        job = submit_with_credit(
            db, user_id=user.id, app_slug=MANIFEST.slug,
            job_type=_IMAGE_JOB_TYPE, params=params,
            dedupe_key=dedupe_key_for(_IMAGE_JOB_TYPE, params))
        db.commit()
    except (credit.ThieuCreditError, RegistryError) as exc:
        db.rollback()
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"id": job.id, "status": job.status, "credit": estimate,
            "scene_id": scene_id}


@router.post("/api/scenes/{scene_id}/attach/{job_id}", status_code=201)
async def attach_scene_render(request: Request, scene_id: str, job_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    """Gắn ảnh job đã sinh vào cảnh và ghi một phiên bản mới."""
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    from platform_core.models import JOB_DONE, Job
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        ssvc.get_owned_scene(db, scene_id, user.id)
    except Exception as exc:
        raise _storyboard_error(exc) from exc

    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    if job.status != JOB_DONE:
        raise HTTPException(status_code=409, detail="Job chưa chạy xong.")
    keys = [k for k in ((job.result or {}).get("image_keys") or []) if k]
    if not keys:
        raise HTTPException(status_code=400, detail="Job không trả về ảnh nào.")
    try:
        ssvc.record_version(db, scene_id=scene_id, owner_id=user.id,
                            image_key=keys[0], job_id=job_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _scene_json(ssvc.get_owned_scene(db, scene_id, user.id))
