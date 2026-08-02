"""
UI app `autosubvideo` (Đợt B). Upload video LỚN đi thẳng browser→R2 (presigned
PUT, P1) để né trần 100MB Cloudflare; transcript nhỏ nạp kèm khi submit. Router
KHÔNG tự viết prefix (nền tảng gắn theo manifest).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse,
                               Response, StreamingResponse)
from sqlalchemy.orm import Session

from apps.autosubvideo import cost
from apps.autosubvideo.manifest import MANIFEST
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


def _render(request: Request, user: str, *, error: str = "", status_code: int = 200):
    return templates.TemplateResponse(request, "autosubvideo.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "presets": _PRESETS, "segments": _SEGMENTS, "qualities": _QUALITY,
        "formats": _FORMATS, "jobs": _jobs_cua_toi(request), "error": error,
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


def _api_user(request: Request):
    current = user_hien_tai(request)
    if current is None:
        raise HTTPException(status_code=403, detail="Cần tài khoản người dùng.")
    return current


def _verify_json_csrf(request: Request, body: dict) -> None:
    token = request.headers.get("X-CSRF-Token", "") or str(body.get("csrf_token", ""))
    if not verify_csrf_token(request, token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn.")


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
        out["payload"] = row.payload
    return out


def _project_response(row, *, status_code: int = 200):
    return JSONResponse(_project_json(row), status_code=status_code,
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
    from platform_core import app_projects
    current = _api_user(request)
    try:
        return _project_response(app_projects.get_owned(
            db, project_id, current.id, MANIFEST.slug))
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy project.") from None


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
        raise HTTPException(status_code=404, detail="Không tìm thấy project.") from None
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
        raise HTTPException(status_code=404, detail="Không tìm thấy project.") from None
    return _project_response(app_projects.archive(db, row))


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
        raise HTTPException(status_code=400, detail="Cần tài khoản người dùng.")
    from platform_core.storage import get_storage
    ext = ""
    if "." in (filename or ""):
        ext = "." + filename.rsplit(".", 1)[1].lower()[:5]
    key = f"autosubvideo/{u.id}/uploads/{uuid.uuid4().hex}{ext}"
    ct = (content_type or "video/mp4").split(";")[0].strip() or "video/mp4"
    storage = get_storage()
    try:
        target = storage.put_url(key, ttl_s=3600, content_type=ct)
    except Exception:  # noqa: BLE001
        target = None
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
        raise HTTPException(status_code=404, detail="Không tìm thấy.")


@router.get("/v/{key:path}")
def video_out(request: Request, key: str, user: str = Depends(require_login)):
    """Serve video output theo HTTP Range; R2 → redirect presigned (né 100MB)."""
    from platform_core.storage import StorageError, get_storage
    _guard_key(request, key)
    storage = get_storage()
    try:
        direct = storage.url_for(key)
    except Exception:  # noqa: BLE001
        direct = None
    if direct:
        return RedirectResponse(direct, status_code=302)
    try:
        total = storage.size(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Không tìm thấy video.")
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
        f = storage.open(key)
        try:
            f.seek(start); chunk = f.read(length)
        finally:
            f.close()
        return Response(content=chunk, status_code=206, media_type="video/mp4",
                        headers={"Content-Range": f"bytes {start}-{end}/{total}",
                                 "Accept-Ranges": "bytes",
                                 "Content-Length": str(len(chunk))})
    return StreamingResponse(storage.open(key), media_type="video/mp4",
                             headers={"Accept-Ranges": "bytes",
                                      "Content-Length": str(total)})


@router.get("/f/{key:path}")
def file_out(request: Request, key: str, user: str = Depends(require_login)):
    """Tải file phụ đề (.srt/.ass). R2 → redirect presigned."""
    from platform_core.storage import StorageError, get_storage
    _guard_key(request, key)
    storage = get_storage()
    try:
        direct = storage.url_for(key)
    except Exception:  # noqa: BLE001
        direct = None
    if direct:
        return RedirectResponse(direct, status_code=302)
    try:
        storage.size(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Không tìm thấy file.")
    name = key.rsplit("/", 1)[-1]
    ct = "application/x-subrip" if name.endswith(".srt") else "text/plain; charset=utf-8"
    return StreamingResponse(storage.open(key), media_type=ct,
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})
