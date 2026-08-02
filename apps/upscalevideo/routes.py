"""
UI app `upscalevideo` (Đợt C). Upload video LỚN đi thẳng browser→R2 (presigned PUT,
P1), lùi về multipart nếu R2 chưa mở CORS. Router KHÔNG tự viết prefix.
"""
from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse,
                               Response, StreamingResponse)

from apps.upscalevideo import cost
from apps.upscalevideo.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["upscalevideo"])

_PRESETS = [("fast", "⚡ Fast (khuyến nghị)"), ("quality", "💎 Quality (nét hơn, chậm)")]
_HEIGHTS = [(1080, "1080p"), (1440, "1440p (2K)"), (2160, "2160p (4K)")]
_CODECS = [("h264", "H.264"), ("hevc", "H.265 (nhỏ hơn)")]
_LOCAL_VIDEO_MAX = 90 * 1024 * 1024


def _render(request: Request, user: str, *, error: str = "", status_code: int = 200):
    own_jobs = _jobs_cua_toi(request)
    return templates.TemplateResponse(request, "upscalevideo.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "presets": _PRESETS, "heights": _HEIGHTS, "codecs": _CODECS,
        "jobs": own_jobs, "latest_done": next((j for j in own_jobs if j["status"] == "done"), None),
        "error": error,
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
            p = j.params or {}
            source_key = str(p.get("video_key") or "")
            out.append({"id": j.id, "status": j.status, "progress": j.progress,
                        "progress_msg": j.progress_msg, "error": j.error,
                        "video_key": r.get("video_key"), "duration_s": r.get("duration_s"),
                        "target_height": r.get("target_height") or p.get("target_height"),
                        "source_key": source_key,
                        "source_name": PurePosixPath(source_key).name or "video.mp4",
                        "preset": p.get("preset", "fast"), "codec": p.get("codec", "h264"),
                        "preserve_fps": p.get("preserve_fps", True),
                        "preserve_audio": p.get("preserve_audio", True),
                        "warning": r.get("warning")})
        return out
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("", response_class=HTMLResponse)
def page(request: Request, user: str = Depends(require_login)):
    return _render(request, user)


@router.post("/estimate", response_class=HTMLResponse)
def estimate(request: Request, duration_s: str = Form("0"), target_height: str = Form("1080"),
             preset: str = Form("fast"), preview: str = Form(""),
             user: str = Depends(require_login)):
    try:
        dur = float(duration_s or 0)
    except (TypeError, ValueError):
        dur = 0.0
    try:
        th = int(target_height)
    except (TypeError, ValueError):
        th = 1080
    e = cost.uoc_luong(dur, th, preset if preset in ("fast", "quality") else "fast",
                       bool(preview))
    if dur <= 0:
        return HTMLResponse('<span class="dim">Chọn video để tính chi phí.</span>')
    return HTMLResponse(
        f'<strong>{e["credit"]} credit</strong> '
        f'<span class="dim">(~{e["vnd"]:,}đ · {e["minutes"]} phút · {th}p · {e["preset"]}'
        f'{" · xem thử" if e["preview"] else ""})</span>')


@router.post("/upload-url")
def upload_url(request: Request, filename: str = Form(""), content_type: str = Form(""),
               user: str = Depends(require_login)):
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(status_code=400, detail="Cần tài khoản người dùng.")
    from platform_core.storage import get_storage
    ext = ""
    if "." in (filename or ""):
        ext = "." + filename.rsplit(".", 1)[1].lower()[:5]
    key = f"upscalevideo/{u.id}/uploads/{uuid.uuid4().hex}{ext}"
    ct = (content_type or "video/mp4").split(";")[0].strip() or "video/mp4"
    try:
        target = get_storage().put_url(key, ttl_s=3600, content_type=ct)
    except Exception:  # noqa: BLE001
        target = None
    if target is None:
        return JSONResponse({"mode": "local", "key": key})
    return JSONResponse({"mode": "direct", "key": target.key, "url": target.url,
                         "method": target.method, "headers": target.headers or {}})


@router.post("/queue")
async def queue(request: Request, csrf_token: str = Form(...),
                video_key: str = Form(""), duration_s: str = Form("0"),
                preset: str = Form("fast"), target_height: str = Form("1080"),
                codec: str = Form("h264"), preview: str = Form(""), ajax: str = Form(""),
                preserve_fps: str = Form("1"), preserve_audio: str = Form("1"),
                video: UploadFile = File(default=None),
                user: str = Depends(require_login)):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.registry import RegistryError
    from platform_core.storage import CLOUDFLARE_BODY_LIMIT, get_storage
    from apps.upscalevideo.service import submit_upscale_job

    def _fail(msg, code=400):
        if ajax:
            return JSONResponse({"ok": False, "error": msg}, status_code=code)
        return _render(request, user, error=msg, status_code=code)

    if not verify_csrf_token(request, csrf_token):
        return _fail("Phiên đã hết hạn — tải lại trang.")
    u = user_hien_tai(request)
    if u is None:
        return _fail("Cần đăng nhập bằng tài khoản người dùng.")

    storage = get_storage()
    vkey = (video_key or "").strip()
    if vkey:
        if not vkey.startswith(f"upscalevideo/{u.id}/") or not storage.exists(vkey):
            return _fail("Video chưa upload xong hoặc không hợp lệ.")
    else:
        if video is None or not getattr(video, "filename", ""):
            return _fail("Chưa chọn video.")
        vdata = await video.read()
        if not vdata:
            return _fail("File video rỗng.")
        if len(vdata) > min(_LOCAL_VIDEO_MAX, CLOUDFLARE_BODY_LIMIT):
            return _fail("Video >90MB phải dùng upload thẳng (R2). Bật CORS bucket R2.")
        ext = ""
        if "." in video.filename:
            ext = "." + video.filename.rsplit(".", 1)[1].lower()[:5]
        vkey = f"upscalevideo/{u.id}/uploads/{uuid.uuid4().hex}{ext}"
        import io as _io
        storage.put(vkey, _io.BytesIO(vdata), content_type=(video.content_type or "video/mp4"))

    if preset not in ("fast", "quality"):
        preset = "fast"
    try:
        th = int(target_height)
    except (TypeError, ValueError):
        th = 1080
    if th not in (1080, 1440, 2160):
        th = 1080
    if codec not in ("h264", "hevc"):
        codec = "h264"
    try:
        dur = float(duration_s or 0)
    except (TypeError, ValueError):
        dur = 0.0

    gen = get_session(); db = next(gen)
    last_id = None
    try:
        try:
            job = submit_upscale_job(db, user_id=u.id, video_key=vkey, preset=preset,
                                     target_height=th, codec=codec,
                                     preview=bool(preview), duration_s=dur,
                                     preserve_fps=preserve_fps != "0",
                                     preserve_audio=preserve_audio != "0")
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


@router.post("/jobs/{job_id}/cancel")
def cancel_job(request: Request, job_id: str, csrf_token: str = Form(...),
               user: str = Depends(require_login)):
    """Owner-only cooperative cancel; refund is atomic and idempotent."""
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn.")
    u = user_hien_tai(request)
    from platform_core import credit, jobs
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); db = next(gen)
    try:
        job = db.get(Job, job_id)
        if job is None or u is None or job.user_id != u.id or job.app_slug != MANIFEST.slug:
            raise HTTPException(status_code=404, detail="Không tìm thấy job.")
        if jobs.cancel(db, job):
            credit.hoan(db, u.id, job.id)
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse("/upscalevideo", status_code=303)


def _serve_owned_video(request: Request, key: str):
    from platform_core.storage import StorageError, get_storage
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
                                 "Accept-Ranges": "bytes", "Content-Length": str(len(chunk))})
    return StreamingResponse(storage.open(key), media_type="video/mp4",
                             headers={"Accept-Ranges": "bytes", "Content-Length": str(total)})


@router.get("/v/{key:path}")
def video_out(request: Request, key: str, user: str = Depends(require_login)):
    u = user_hien_tai(request)
    segs = key.split("/")
    if len(segs) < 2 or segs[0] != "upscalevideo" or u is None or segs[1] != u.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy video.")
    return _serve_owned_video(request, key)


@router.get("/jobs/{job_id}/source")
def source_video(request: Request, job_id: str, user: str = Depends(require_login)):
    """Nguồn của đúng job Upscale, kể cả khi video đến từ Seedance.

    Không nhận storage key từ URL, do đó không biến endpoint này thành đường đọc
    tệp chéo người dùng.
    """
    u = user_hien_tai(request)
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); db = next(gen)
    try:
        job = db.get(Job, job_id)
        key = (job.params or {}).get("video_key") if job and u and job.user_id == u.id and job.app_slug == MANIFEST.slug else ""
    finally:
        try: next(gen)
        except StopIteration: pass
    if not key:
        raise HTTPException(status_code=404, detail="Không tìm thấy video nguồn.")
    return _serve_owned_video(request, key)
