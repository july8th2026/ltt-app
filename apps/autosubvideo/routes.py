"""
UI app `autosubvideo` (Đợt B). Upload video LỚN đi thẳng browser→R2 (presigned
PUT, P1) để né trần 100MB Cloudflare; transcript nhỏ nạp kèm khi submit. Router
KHÔNG tự viết prefix (nền tảng gắn theo manifest).
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import uuid
import json
import os
import copy
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse,
                               Response, StreamingResponse)
from sqlalchemy.orm import Session

from apps.autosubvideo import cost
from apps.autosubvideo.features import render_preflight
from apps.autosubvideo.manifest import MANIFEST
from platform_core.frontend_bundle import bundle_assets
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.deps import get_db
from server.templating import templates

router = APIRouter(tags=["autosubvideo"])

# Preset (nhãn hiển thị) — khớp 8 preset trong style_registry.
_PRESETS = [
    ("default", "Mặc định"), ("tiktok_bold", "TikTok đậm"),
    ("reels_clean", "Reels gọn"), ("cinematic", "Điện ảnh"),
    ("meme_punch", "Meme"), ("kids_color", "Trẻ em"),
    ("punchline", "Punchline"), ("word_emphasis", "Nhấn từ"),
]
_SEGMENTS = [("sentence", "Theo câu"), ("phrase", "Theo cụm"),
             ("short_form", "Ngắn (dọc)"), ("punchline", "Punchline"),
             ("word_emphasis", "Nhấn từng từ")]
_QUALITY = [("draft", "Nháp"), ("standard", "Chuẩn"), ("high", "Cao")]
_FORMATS = ["mp4", "mkv", "webm"]
_TRANSCRIPT_MAX = 8 * 1024 * 1024      # 8MB transcript là quá đủ
_LOCAL_VIDEO_MAX = 90 * 1024 * 1024    # fallback Local: dưới trần 100MB CF
_PROJECT_VIDEO_MAX = 2 * 1024 * 1024 * 1024
_VIDEO_TYPES = ("video/mp4", "video/quicktime", "video/x-m4v",
                "video/webm", "video/x-matroska", "video/x-msvideo")


def _studio_enabled() -> bool:
    configured = os.environ.get("LTT_AUTOSUB_STUDIO_ROLLOUT")
    # AS9 da PASS va Studio da duoc chot la giao dien public mac dinh (Q50).
    # Sau reset/update, bien optional co the bi mat hoac rong; khong duoc vi the
    # am tham quay khach hang ve form legacy. Chi gia tri `off`/gia tri sai duoc
    # xem la lenh rollback co chu y. Bundle thieu van duoc `_render()` fail-safe.
    if configured is None or not configured.strip():
        return True
    return configured.strip().lower() == "public"


def _browser_direct_upload_enabled() -> bool:
    return os.environ.get("LTT_R2_BROWSER_UPLOAD_ENABLED", "").strip() == "1"


def _render(request: Request, user: str, *, error: str = "", status_code: int = 200):
    enabled = _studio_enabled()
    studio_js, studio_css = bundle_assets("autosub-studio") if enabled else ([], [])
    # A missing production bundle is not silently replaced with a half-built
    # editor. Roll back to the proven legacy form until the release is complete.
    enabled = enabled and bool(studio_js)
    return templates.TemplateResponse(request, "autosubvideo.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "presets": _PRESETS, "segments": _SEGMENTS, "qualities": _QUALITY,
        "formats": _FORMATS, "jobs": _jobs_cua_toi(request), "error": error,
        "studio_enabled": enabled, "studio_js": studio_js, "studio_css": studio_css,
    }, status_code=status_code)


def _jobs_cua_toi(request: Request):
    u = user_hien_tai(request)
    if u is None:
        return []
    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        rows = db.execute(
            select(Job).where(Job.user_id == u.id, Job.app_slug == MANIFEST.slug)
            .order_by(Job.created_at.desc()).limit(12)
        ).scalars().all()
        out = []
        for j in rows:
            r = j.result or {}
            out.append({"id": j.id, "status": j.status, "progress": j.progress,
                        "progress_msg": j.progress_msg, "error": j.error,
                        "video_key": r.get("video_key"), "srt_key": r.get("srt_key"),
                        "ass_key": r.get("ass_key"), "duration_s": r.get("duration_s"),
                        "font_warning": r.get("font_warning")})
        return out
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("", response_class=HTMLResponse)
def page(request: Request, user: str = Depends(require_login)):
    return _render(request, user)


@router.get("/api/styles")
def studio_styles(_identity: str = Depends(require_login)):
    from apps.autosubvideo.style_registry import list_presets
    return {"items": [item.model_dump(mode="json") for item in list_presets()]}


def _api_user(request: Request):
    current = user_hien_tai(request)
    if current is None:
        raise HTTPException(status_code=403, detail=_t('Cần tài khoản người dùng.'))
    return current


def _verify_json_csrf(request: Request, body: dict) -> None:
    token = request.headers.get("X-CSRF-Token", "") or str(body.get("csrf_token", ""))
    if not verify_csrf_token(request, token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))


def _validated_project_payload(value) -> dict:
    from pydantic import ValidationError
    from apps.autosubvideo.schemas import StudioProjectV1
    try:
        return StudioProjectV1.model_validate(value).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from None


def _project_json(row, *, include_payload: bool = True) -> dict:
    out = {"id": row.id, "name": row.name, "app_slug": row.app_slug,
           "schema_version": row.schema_version, "revision": row.revision,
           "status": row.status, "created_at": row.created_at.isoformat(),
           "updated_at": row.updated_at.isoformat()}
    if include_payload:
        from apps.autosubvideo.schemas import StudioProjectV1
        out["payload"] = StudioProjectV1.model_validate(row.payload).model_dump(mode="json")
    return out


def _project_response(row, *, status_code: int = 200, source_expired: bool = False):
    body = _project_json(row)
    if source_expired:
        body["source_expired"] = True
    return JSONResponse(body, status_code=status_code,
                        headers={"ETag": f'"{row.revision}"'})


@router.get("/api/projects")
def project_list(request: Request, _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    from platform_core.models import AppProject
    current = _api_user(request)
    rows = db.query(AppProject).filter_by(user_id=current.id, app_slug=MANIFEST.slug).order_by(
        AppProject.updated_at.desc()).limit(100).all()
    return {"items": [_project_json(row, include_payload=False) for row in rows]}


@router.post("/api/projects")
async def project_create(request: Request, _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    from platform_core import app_projects
    from apps.autosubvideo.schemas import empty_studio_project
    body = await request.json(); _verify_json_csrf(request, body)
    current = _api_user(request)
    payload = _validated_project_payload(body.get("payload", empty_studio_project()))
    try:
        row = app_projects.create(db, user_id=current.id, app_slug=MANIFEST.slug,
                                  name=str(body.get("name", "")), schema_version=1,
                                  payload=payload)
    except app_projects.ProjectError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _project_response(row, status_code=201)


@router.get("/api/projects/{project_id}")
def project_get(request: Request, project_id: str,
                _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    from apps.autosubvideo.services import source_drafts
    from platform_core import app_projects
    from platform_core.storage import get_storage
    current = _api_user(request)
    try:
        row = app_projects.get_owned(db, project_id, current.id, MANIFEST.slug)
        row, expired = source_drafts.refresh(
            db, get_storage(), row, user_id=current.id, app_slug=MANIFEST.slug)
        return _project_response(row, source_expired=expired)
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None


@router.post("/api/uploads")
async def project_upload_ticket(request: Request,
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    from apps.autosubvideo.services import source_drafts
    from platform_core import upload_sessions
    from platform_core.storage import get_storage
    body = await request.json(); _verify_json_csrf(request, body)
    current = _api_user(request)
    try:
        return source_drafts.create_ticket(
            db, get_storage(), user_id=current.id, app_slug=MANIFEST.slug,
            filename=str(body.get("filename", "")),
            content_type=str(body.get("content_type", "video/mp4")),
            expected_size=body.get("expected_size", 0),
            direct_enabled=_browser_direct_upload_enabled(),
            max_size=_PROJECT_VIDEO_MAX, local_max=_LOCAL_VIDEO_MAX,
            allowed_types=_VIDEO_TYPES)
    except upload_sessions.UploadSessionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.put("/api/projects/{project_id}")
async def project_save(request: Request, project_id: str,
                       _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    from platform_core import app_projects
    body = await request.json(); _verify_json_csrf(request, body)
    current = _api_user(request)
    try:
        revision = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
        payload = _validated_project_payload(body.get("payload"))
        row = app_projects.save(db, project_id=project_id, user_id=current.id,
                                app_slug=MANIFEST.slug, revision=revision,
                                name=str(body.get("name", "")), schema_version=1,
                                payload=payload)
    except app_projects.ProjectConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None
    except (KeyError, TypeError, ValueError, app_projects.ProjectError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _project_response(row)


@router.post("/api/projects/{project_id}/archive")
async def project_archive(request: Request, project_id: str,
                          _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    from platform_core import app_projects
    body = await request.json(); _verify_json_csrf(request, body)
    current = _api_user(request)
    try:
        row = app_projects.get_owned(db, project_id, current.id, MANIFEST.slug)
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None
    return _project_response(app_projects.archive(db, row))


@router.post("/api/projects/{project_id}/import")
async def project_import_transcript(
        request: Request, project_id: str, transcript: UploadFile = File(...),
        language: str = Form("vi"), track_name: str = Form("Transcript"),
        revision: int = Form(...), csrf_token: str = Form(""),
        _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    from platform_core import app_projects
    from apps.autosubvideo.parsers import parse_transcript
    if not verify_csrf_token(request, request.headers.get("X-CSRF-Token", "") or csrf_token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))
    current = _api_user(request)
    raw = await transcript.read()
    if not raw or len(raw) > _TRANSCRIPT_MAX:
        raise HTTPException(status_code=422, detail=_t('Transcript rỗng hoặc quá lớn (>8MB).'))
    try:
        segments = parse_transcript(transcript.filename or "", raw)
        row = app_projects.get_owned(db, project_id, current.id, MANIFEST.slug)
        payload = dict(row.payload)
        track = {"id": "track-source", "kind": "source", "language": language[:24],
                 "name": track_name[:120] or "Transcript", "visible": True,
                 "z_index": 0, "style_id": "default", "cues": [{
                     "id": f"cue-{index:06d}", "start": float(item["start"]),
                     "end": float(item["end"]), "text": str(item["text"]),
                     "speaker": str(item.get("speaker", "")), "words": []}
                     for index, item in enumerate(segments, 1)]}
        payload["tracks"] = [track, *[item for item in payload.get("tracks", [])
                                             if item.get("id") != "track-source"]]
        payload["active_step"] = "transcript"
        validated = _validated_project_payload(payload)
        saved = app_projects.save(db, project_id=project_id, user_id=current.id,
                                  app_slug=MANIFEST.slug, revision=revision,
                                  name=row.name, schema_version=1, payload=validated)
    except app_projects.ProjectConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None
    except (ValueError, app_projects.ProjectError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _project_response(saved)


_TRANSCRIBE_DAILY_LIMIT, _DIARIZE_DAILY_LIMIT, _TRANSLATE_DAILY_LIMIT = 12, 6, 20

@router.post("/api/projects/{project_id}/source")
async def project_attach_source(
        request: Request, project_id: str, revision: int = Form(...),
        csrf_token: str = Form(""), upload_id: str = Form(""),
        filename: str = Form(""), duration_s: float = Form(0),
        width: int = Form(0), height: int = Form(0),
        video: UploadFile = File(default=None),
        _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    from pydantic import ValidationError
    from apps.autosubvideo.services import source_drafts
    from platform_core import app_projects, upload_sessions
    from platform_core.storage import CLOUDFLARE_BODY_LIMIT, get_storage
    if not verify_csrf_token(request, request.headers.get("X-CSRF-Token", "") or csrf_token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))
    current = _api_user(request); storage = get_storage()
    try:
        raw = await video.read() if video is not None else None
        if raw is not None and len(raw) > min(_LOCAL_VIDEO_MAX, CLOUDFLARE_BODY_LIMIT):
            raise upload_sessions.UploadSessionError(
                _t('Video local rỗng hoặc quá 90MB.'))
        saved = source_drafts.attach(
            db, storage, project_id=project_id, user_id=current.id,
            app_slug=MANIFEST.slug, revision=revision, upload_id=upload_id,
            video_name=getattr(video, "filename", "") or "",
            video_content_type=getattr(video, "content_type", "") or "",
            video_data=raw, filename=filename, duration_s=duration_s,
            width=width, height=height, local_max=_LOCAL_VIDEO_MAX,
            allowed_types=_VIDEO_TYPES)
    except app_projects.ProjectConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None
    except (upload_sessions.UploadSessionError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _project_response(saved)


@router.post("/api/projects/{project_id}/transcribe")
async def project_transcribe(request: Request, project_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    from sqlalchemy import func, select
    from platform_core import app_projects
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.models import Job, User
    from platform_core.storage import get_storage

    body = await request.json(); _verify_json_csrf(request, body)
    current = _api_user(request)
    try:
        revision = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
        row = app_projects.get_owned(db, project_id, current.id, MANIFEST.slug)
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail=_t('Thiếu revision hợp lệ.')) from None
    if row.revision != revision:
        raise HTTPException(status_code=409, detail=_t('Project đã được sửa ở phiên khác.'))
    source = (row.payload or {}).get("source") or {}
    key = str(source.get("key", ""))
    if not key.startswith(f"autosubvideo/{current.id}/") or not get_storage().exists(key):
        raise HTTPException(status_code=422, detail=_t('Source video chưa upload hoặc không thuộc user.'))
    duration = float(source.get("duration_s", 0) or 0)
    if duration > 7200:
        raise HTTPException(status_code=422, detail=_t('Mỗi lượt chép lời tối đa 120 phút.'))

    # Lock user while checking quota and creating the job; concurrent submits
    # cannot all observe the same pre-limit count on PostgreSQL.
    db.execute(select(User).where(User.id == current.id).with_for_update()).scalar_one()
    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    used = db.execute(select(func.count(Job.id)).where(
        Job.user_id == current.id, Job.job_type == "autosubvideo.transcribe",
        Job.created_at >= day_start)).scalar_one()
    if int(used or 0) >= _TRANSCRIBE_DAILY_LIMIT:
        raise HTTPException(status_code=429, detail=_t('Đã dùng hết 12 lượt chép lời miễn phí hôm nay.'))

    params = {"operation": "transcribe", "owner_id": current.id,
              "project_id": row.id, "project_revision": row.revision,
              "video_key": key, "duration_s": duration,
              "language": str(body.get("language", ""))[:24],
              "model": str(body.get("model", "large-v3"))[:64] or "large-v3"}
    job = submit_with_credit(
        db, user_id=current.id, app_slug=MANIFEST.slug,
        job_type="autosubvideo.transcribe", params=params,
        dedupe_key=dedupe_key_for("autosubvideo.transcribe", params), max_attempts=2)
    current_used = db.execute(select(func.count(Job.id)).where(
        Job.user_id == current.id, Job.job_type == "autosubvideo.transcribe",
        Job.created_at >= day_start)).scalar_one()
    return JSONResponse({"ok": True, "job_id": job.id, "status": job.status,
                         "credit": 0, "quota_remaining": max(
                             0, _TRANSCRIBE_DAILY_LIMIT - int(current_used or 0))},
                        status_code=202)


@router.get("/api/capabilities")
def studio_capabilities(_identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    from apps.autosubvideo.ai_workflows import diarization_available, gemini_available
    return {"whisperx": bool(os.environ.get("LTT_WHISPERX_PYTHON", "").strip()),
            "diarization": diarization_available(), "translation": gemini_available(db),
            "credit": {"transcribe": 0, "diarize": 0, "translate": 0}}


def _submit_auxiliary(db: Session, *, current, row, operation: str,
                      params: dict, daily_limit: int):
    from sqlalchemy import func, select
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.models import Job, User
    job_type = f"autosubvideo.{operation}"
    db.execute(select(User).where(User.id == current.id).with_for_update()).scalar_one()
    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    used = int(db.execute(select(func.count(Job.id)).where(
        Job.user_id == current.id, Job.job_type == job_type,
        Job.created_at >= day_start)).scalar_one() or 0)
    if used >= daily_limit:
        raise HTTPException(status_code=429,
                            detail=f"Đã dùng hết {daily_limit} lượt {operation} miễn phí hôm nay.")
    payload = {"operation": operation, "owner_id": current.id,
               "project_id": row.id, "project_revision": row.revision, **params}
    job = submit_with_credit(db, user_id=current.id, app_slug=MANIFEST.slug,
        job_type=job_type, params=payload, dedupe_key=dedupe_key_for(job_type, payload),
        max_attempts=2)
    return JSONResponse({"ok": True, "job_id": job.id, "status": job.status,
        "credit": 0, "quota_remaining": max(0, daily_limit - used - 1)}, status_code=202)


def _render_snapshot(row, current, body: dict, request: Request) -> tuple[dict, dict]:
    """Validate revision/output and return an immutable render snapshot + quote."""
    from apps.autosubvideo.schemas import StudioProjectV1, StudioOutput
    from platform_core.storage import get_storage
    try:
        revision = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail=_t('Thiếu revision hợp lệ.')) from None
    if row.revision != revision:
        raise HTTPException(status_code=409, detail=_t('Project đã được sửa ở phiên khác.'))
    payload = copy.deepcopy(row.payload or {})
    try:
        current_output = dict(payload.get("output") or {})
        current_output.update(body.get("output") or {})
        payload["output"] = StudioOutput.model_validate(current_output).model_dump(mode="json")
        project = StudioProjectV1.model_validate(payload)
    except Exception as exc:  # Pydantic reports exact validation at the API edge.
        raise HTTPException(status_code=422, detail=f"Tùy chọn render không hợp lệ: {exc}") from None
    key = project.source.key
    if not key.startswith(f"autosubvideo/{current.id}/") or not get_storage().exists(key):
        raise HTTPException(status_code=422, detail=_t('Source video chưa sẵn sàng hoặc không thuộc user.'))
    selected = set(project.output.track_ids)
    available = [track for track in project.tracks
                 if track.visible and (not selected or track.id in selected) and track.cues]
    if not available:
        raise HTTPException(status_code=422, detail=_t('Chọn ít nhất một track đang hiện và có cue.'))
    unknown = selected.difference(track.id for track in project.tracks)
    if unknown:
        raise HTTPException(status_code=422, detail=_t('Track render không tồn tại.'))
    preflight = render_preflight(project, available)
    if preflight["error_count"]:
        raise HTTPException(status_code=422, detail=_t(
            'Transcript còn lỗi nội dung/timing phải sửa trước khi xuất video.'))
    quote = cost.uoc_luong(project.source.duration_s, project.output.quality)
    quote.update({"resolution": project.output.resolution, "format": project.output.format,
                  "track_ids": [track.id for track in available],
                  "project_revision": row.revision, "preflight": preflight})
    return project.model_dump(mode="json"), quote


@router.post("/api/projects/{project_id}/quote")
async def project_render_quote(request: Request, project_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    from platform_core import app_projects
    body = await request.json(); _verify_json_csrf(request, body); current = _api_user(request)
    try: row = app_projects.get_owned(db, project_id, current.id, MANIFEST.slug)
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None
    _snapshot, quote = _render_snapshot(row, current, body, request)
    return {"ok": True, "quote": quote}


@router.post("/api/projects/{project_id}/render")
async def project_render_submit(request: Request, project_id: str,
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    from platform_core import app_projects, credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    body = await request.json(); _verify_json_csrf(request, body); current = _api_user(request)
    try: row = app_projects.get_owned(db, project_id, current.id, MANIFEST.slug)
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None
    snapshot, quote = _render_snapshot(row, current, body, request)
    canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    params = {"operation": "render_project", "owner_id": current.id,
              "project_id": row.id, "project_revision": row.revision,
              "project_snapshot": snapshot,
              "snapshot_sha256": hashlib.sha256(canonical).hexdigest(),
              "video_key": snapshot["source"]["key"],
              "duration_s": snapshot["source"]["duration_s"],
              "quality": snapshot["output"]["quality"]}
    try:
        job = submit_with_credit(db, user_id=current.id, app_slug=MANIFEST.slug,
            job_type="autosubvideo.render", params=params,
            dedupe_key=dedupe_key_for("autosubvideo.render", params), max_attempts=2)
    except (credit.ThieuCreditError, RegistryError) as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from None
    return JSONResponse({"ok": True, "job_id": job.id, "status": job.status,
        "quote": quote, "snapshot_sha256": params["snapshot_sha256"]}, status_code=202)


@router.post("/api/projects/{project_id}/diarize")
async def project_diarize(request: Request, project_id: str,
                          _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    from platform_core import app_projects
    from platform_core.storage import get_storage
    from apps.autosubvideo.ai_workflows import diarization_available
    body = await request.json(); _verify_json_csrf(request, body); current = _api_user(request)
    try:
        revision = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
        row = app_projects.get_owned(db, project_id, current.id, MANIFEST.slug)
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail=_t('Thiếu revision hợp lệ.')) from None
    if row.revision != revision:
        raise HTTPException(status_code=409, detail=_t('Project đã được sửa ở phiên khác.'))
    if not diarization_available():
        raise HTTPException(status_code=503, detail=_t('Pyannote chưa cấu hình token/model.'))
    source = (row.payload or {}).get("source") or {}; key = str(source.get("key", ""))
    tracks = (row.payload or {}).get("tracks") or []
    if not key.startswith(f"autosubvideo/{current.id}/") or not get_storage().exists(key):
        raise HTTPException(status_code=422, detail=_t('Source video chưa sẵn sàng.'))
    if not any(t.get("kind") == "source" and t.get("cues") for t in tracks):
        raise HTTPException(status_code=422, detail=_t('Cần transcript nguồn trước khi phân vai.'))
    minimum = max(0, min(int(body.get("min_speakers", 0) or 0), 20))
    maximum = max(0, min(int(body.get("max_speakers", 0) or 0), 20))
    if minimum and maximum and minimum > maximum:
        raise HTTPException(status_code=422, detail=_t('Khoảng số speaker không hợp lệ.'))
    return _submit_auxiliary(db, current=current, row=row, operation="diarize",
        params={"video_key": key, "duration_s": float(source.get("duration_s", 0) or 0),
                "min_speakers": minimum, "max_speakers": maximum},
        daily_limit=_DIARIZE_DAILY_LIMIT)


@router.post("/api/projects/{project_id}/translate")
async def project_translate(request: Request, project_id: str,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    import re
    from platform_core import app_projects
    from apps.autosubvideo.ai_workflows import gemini_available
    body = await request.json(); _verify_json_csrf(request, body); current = _api_user(request)
    try:
        revision = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
        row = app_projects.get_owned(db, project_id, current.id, MANIFEST.slug)
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail=_t('Thiếu revision hợp lệ.')) from None
    if row.revision != revision:
        raise HTTPException(status_code=409, detail=_t('Project đã được sửa ở phiên khác.'))
    if not gemini_available(db):
        raise HTTPException(status_code=503, detail=_t('Gemini translation chưa cấu hình API key.'))
    track_id = str(body.get("track_id", "")); language = str(body.get("target_language", "")).lower()
    if not re.fullmatch(r"[a-z]{2,3}(?:-[a-z]{2,4})?", language):
        raise HTTPException(status_code=422, detail=_t('Mã ngôn ngữ đích không hợp lệ.'))
    track = next((t for t in (row.payload or {}).get("tracks", [])
                  if t.get("id") == track_id), None)
    if not track or not track.get("cues"):
        raise HTTPException(status_code=422, detail=_t('Track nguồn không có cue.'))
    return _submit_auxiliary(db, current=current, row=row, operation="translate",
        params={"track_id": track_id, "target_language": language,
                "cue_count": len(track["cues"])}, daily_limit=_TRANSLATE_DAILY_LIMIT)


def _studio_job_payload(job) -> dict:
    now = datetime.now(timezone.utc)
    started = job.started_at
    if started is not None and started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = max(0.0, (now - started).total_seconds()) if started else 0.0
    eta = round(elapsed * (100 - job.progress) / job.progress, 1) if (
        job.status == "running" and job.progress >= 3 and elapsed > 0) else None
    return {"id": job.id, "type": job.job_type, "status": job.status,
            "progress": job.progress, "message": job.progress_msg,
            "elapsed_s": round(elapsed, 1), "eta_s": eta,
            "error": job.error if job.status == "error" else "",
            "result": job.result if job.status == "done" else {},
            "project_id": str((job.params or {}).get("project_id", "")),
            "created_at": job.created_at.isoformat() if job.created_at else ""}


@router.get("/api/jobs")
def studio_jobs(request: Request, project_id: str = "", limit: int = 20,
                _identity: str = Depends(require_login),
                db: Session = Depends(get_db)):
    """Lich su job trong tool, owner-scoped va co the loc theo project."""
    from sqlalchemy import select
    from platform_core.models import Job
    current = _api_user(request)
    rows = db.execute(select(Job).where(
        Job.user_id == current.id, Job.app_slug == MANIFEST.slug,
    ).order_by(Job.created_at.desc()).limit(100)).scalars().all()
    if project_id:
        rows = [row for row in rows
                if str((row.params or {}).get("project_id", "")) == project_id]
    safe_limit = max(1, min(int(limit or 20), 50))
    return {"items": [_studio_job_payload(row) for row in rows[:safe_limit]]}


@router.get("/api/jobs/{job_id}")
def studio_job_status(request: Request, job_id: str,
                      _identity: str = Depends(require_login),
                      db: Session = Depends(get_db)):
    from platform_core.models import Job
    current = _api_user(request); job = db.get(Job, job_id)
    if job is None or job.user_id != current.id or job.app_slug != MANIFEST.slug:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
    return _studio_job_payload(job)


@router.post("/api/jobs/{job_id}/cancel")
async def studio_job_cancel(request: Request, job_id: str,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    from platform_core import jobs, credit
    from platform_core.models import Job
    body = await request.json(); _verify_json_csrf(request, body); current = _api_user(request)
    job = db.get(Job, job_id)
    if job is None or job.user_id != current.id or job.app_slug != MANIFEST.slug:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
    cancelled = jobs.cancel(db, job)
    if cancelled:
        credit.hoan(db, job.user_id, job.id)
    return {"ok": cancelled, "status": job.status}


@router.post("/api/jobs/{job_id}/retry")
async def studio_job_retry(request: Request, job_id: str,
                           _identity: str = Depends(require_login),
                           db: Session = Depends(get_db)):
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.models import Job
    body = await request.json(); _verify_json_csrf(request, body); current = _api_user(request)
    old = db.get(Job, job_id)
    if old is None or old.user_id != current.id or old.app_slug != MANIFEST.slug:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
    if old.status not in {"error", "cancelled"} or old.params.get("operation") != "render_project":
        raise HTTPException(status_code=409, detail=_t('Chỉ retry render đã lỗi hoặc đã hủy.'))
    params = copy.deepcopy(old.params)
    canonical = json.dumps(params.get("project_snapshot") or {}, sort_keys=True,
                           ensure_ascii=False, separators=(",", ":"),
                           allow_nan=False).encode("utf-8")
    key = str(params.get("video_key", ""))
    from platform_core.storage import get_storage
    if (hashlib.sha256(canonical).hexdigest() != params.get("snapshot_sha256") or
            not key.startswith(f"autosubvideo/{current.id}/") or
            not get_storage().exists(key)):
        raise HTTPException(status_code=409, detail=_t('Snapshot/source của job cũ không còn hợp lệ.'))
    try:
        job = submit_with_credit(db, user_id=current.id, app_slug=MANIFEST.slug,
            job_type=old.job_type, params=params,
            dedupe_key=dedupe_key_for(old.job_type, params), max_attempts=2)
    except credit.ThieuCreditError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from None
    return JSONResponse({"ok": True, "job_id": job.id, "status": job.status}, status_code=202)


@router.post("/estimate", response_class=HTMLResponse)
def estimate(request: Request, duration_s: str = Form("0"), quality: str = Form("standard"),
             user: str = Depends(require_login)):
    try:
        dur = float(duration_s or 0)
    except (TypeError, ValueError):
        dur = 0.0
    e = cost.uoc_luong(dur, quality if quality in ("draft", "standard", "high") else "standard")
    if dur <= 0:
        return HTMLResponse('<span class="dim">Chọn video để tính chi phí.</span>')
    return HTMLResponse(
        f'<strong>{e["credit"]} credit</strong> '
        f'<span class="dim">(~{e["vnd"]:,}đ · {e["minutes"]} phút · {e["quality"]})</span>')


@router.post("/upload-url")
def upload_url(request: Request, filename: str = Form(""), content_type: str = Form(""),
               user: str = Depends(require_login)):
    """Cấp vé upload video. R2 → presigned PUT (browser tải thẳng, né 100MB).
    Local → báo client gửi multipart qua /queue (chỉ hợp file nhỏ)."""
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(status_code=400, detail=_t('Cần tài khoản người dùng.'))
    from platform_core.storage import get_storage
    ext = ""
    if "." in (filename or ""):
        ext = "." + filename.rsplit(".", 1)[1].lower()[:5]
    key = f"autosubvideo/{u.id}/uploads/{uuid.uuid4().hex}{ext}"
    ct = (content_type or "video/mp4").split(";")[0].strip() or "video/mp4"
    storage = get_storage()
    if not _browser_direct_upload_enabled():
        return JSONResponse({"mode": "local", "key": key})
    target = storage.try_put_url(key, ttl_s=3600, content_type=ct)
    if target is None:
        return JSONResponse({"mode": "local", "key": key})
    return JSONResponse({"mode": "direct", "key": target.key, "url": target.url,
                         "method": target.method, "headers": target.headers or {}})


@router.post("/queue")
async def queue(request: Request, csrf_token: str = Form(...),
                video_key: str = Form(""), duration_s: str = Form("0"),
                style_id: str = Form("default"), segment_mode: str = Form("sentence"),
                quality: str = Form("standard"), output_format: str = Form("mp4"),
                export_srt: str = Form(""), ajax: str = Form(""),
                video: UploadFile = File(default=None),
                transcript: UploadFile = File(default=None),
                user: str = Depends(require_login)):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    from platform_core.storage import CLOUDFLARE_BODY_LIMIT, get_storage
    from apps.autosubvideo.parsers import parse_transcript

    def _fail(msg, code=400):
        if ajax:
            return JSONResponse({"ok": False, "error": msg}, status_code=code)
        return _render(request, user, error=msg, status_code=code)

    if not verify_csrf_token(request, csrf_token):
        return _fail("Phiên đã hết hạn — tải lại trang.")
    u = user_hien_tai(request)
    if u is None:
        return _fail("Cần đăng nhập bằng tài khoản người dùng.")

    # Transcript bắt buộc.
    if transcript is None or not getattr(transcript, "filename", ""):
        return _fail("Chưa nạp transcript (.srt/.json/.vtt/.ass).")
    traw = await transcript.read()
    if not traw or len(traw) > _TRANSCRIPT_MAX:
        return _fail("Transcript rỗng hoặc quá lớn (>8MB).")
    try:
        segs = parse_transcript(transcript.filename, traw)
    except Exception as e:  # noqa: BLE001
        return _fail(f"Không đọc được transcript: {e}")
    if not segs:
        return _fail("Transcript không có dòng phụ đề nào.")

    storage = get_storage()
    # Video: đã upload thẳng R2 (video_key) HOẶC gửi multipart (Local fallback).
    vkey = (video_key or "").strip()
    if vkey:
        if not vkey.startswith(f"autosubvideo/{u.id}/") or not storage.exists(vkey):
            return _fail("Video chưa upload xong hoặc không hợp lệ.")
    else:
        if video is None or not getattr(video, "filename", ""):
            return _fail("Chưa chọn video.")
        vdata = await video.read()
        if not vdata:
            return _fail("File video rỗng.")
        if len(vdata) > min(_LOCAL_VIDEO_MAX, CLOUDFLARE_BODY_LIMIT):
            return _fail("Video >90MB phải dùng upload thẳng (R2). Bật R2 hoặc chọn file nhỏ hơn.")
        ext = ""
        if "." in video.filename:
            ext = "." + video.filename.rsplit(".", 1)[1].lower()[:5]
        vkey = f"autosubvideo/{u.id}/uploads/{uuid.uuid4().hex}{ext}"
        import io as _io
        storage.put(vkey, _io.BytesIO(vdata),
                    content_type=(video.content_type or "video/mp4"))

    if style_id not in dict(_PRESETS):
        style_id = "default"
    if segment_mode not in dict(_SEGMENTS):
        segment_mode = "sentence"
    if quality not in ("draft", "standard", "high"):
        quality = "standard"
    if output_format not in _FORMATS:
        output_format = "mp4"
    try:
        dur = float(duration_s or 0)
    except (TypeError, ValueError):
        dur = 0.0

    params = {"video_key": vkey, "transcript": segs, "style_id": style_id,
              "segment_mode": segment_mode, "quality": quality,
              "output_format": output_format, "export_srt": bool(export_srt),
              "duration_s": dur, "owner_id": u.id}
    gen = get_session(); db = next(gen)
    last_id = None
    try:
        try:
            job = submit_with_credit(
                db, user_id=u.id, app_slug=MANIFEST.slug,
                job_type="autosubvideo.render", params=params,
                dedupe_key=dedupe_key_for("autosubvideo.render", params))
            last_id = job.id
            db.commit()
        except (credit.ThieuCreditError, RegistryError) as exc:
            db.rollback()
            return _fail(str(exc))
    finally:
        try: next(gen)
        except StopIteration: pass

    if ajax:
        return JSONResponse({"ok": True, "redirect": f"/jobs/{last_id}"})
    return RedirectResponse(f"/jobs/{last_id}", status_code=303)


def _guard_key(request: Request, key: str) -> None:
    u = user_hien_tai(request)
    segs = key.split("/")
    if len(segs) < 2 or segs[0] != "autosubvideo" or u is None or segs[1] != u.id:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy.'))


def _iter_storage_range(stream, start: int, length: int):
    """Yield a byte range from local files or non-seekable R2 StreamingBody."""
    try:
        try:
            stream.seek(start)
        except (AttributeError, OSError):
            skipped = 0
            while skipped < start:
                chunk = stream.read(min(1024 * 1024, start - skipped))
                if not chunk:
                    return
                skipped += len(chunk)
        remaining = length
        while remaining > 0:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                return
            remaining -= len(chunk)
            yield chunk
    finally:
        stream.close()


@router.get("/v/{key:path}")
def video_out(request: Request, key: str, user: str = Depends(require_login)):
    """Serve video output theo HTTP Range; R2 → redirect presigned (né 100MB)."""
    from platform_core.storage import StorageError, get_storage
    _guard_key(request, key)
    storage = get_storage()
    direct = storage.try_url_for(key)
    if direct and _browser_direct_upload_enabled():
        return RedirectResponse(direct, status_code=302)
    try:
        total = storage.size(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy video.'))
    rng = request.headers.get("range")
    if rng and rng.startswith("bytes="):
        try:
            s, _, e = rng[len("bytes="):].partition("-")
            start = int(s) if s else 0
            end = int(e) if e else total - 1
        except ValueError:
            start, end = 0, total - 1
        start = max(0, start); end = min(end, total - 1)
        if start > end:
            start = 0
        length = end - start + 1
        return StreamingResponse(_iter_storage_range(storage.open(key), start, length),
                        status_code=206, media_type="video/mp4",
                        headers={"Content-Range": f"bytes {start}-{end}/{total}",
                                 "Accept-Ranges": "bytes",
                                 "Content-Length": str(length)})
    return StreamingResponse(storage.open(key), media_type="video/mp4",
                             headers={"Accept-Ranges": "bytes",
                                      "Content-Length": str(total)})


@router.get("/f/{key:path}")
def file_out(request: Request, key: str, user: str = Depends(require_login)):
    """Tải file phụ đề (.srt/.ass). R2 → redirect presigned."""
    from platform_core.storage import StorageError, get_storage
    _guard_key(request, key)
    storage = get_storage()
    direct = storage.try_url_for(key)
    if direct:
        return RedirectResponse(direct, status_code=302)
    try:
        storage.size(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy file.'))
    name = key.rsplit("/", 1)[-1]
    if name.endswith(".srt"): ct = "application/x-subrip"
    elif name.endswith(".zip"): ct = "application/zip"
    elif name.endswith(".json"): ct = "application/json"
    else: ct = "text/plain; charset=utf-8"
    return StreamingResponse(storage.open(key), media_type=ct,
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})
