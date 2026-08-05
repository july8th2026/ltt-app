"""
UI app `upscalevideo` (Đợt C). Upload video LỚN đi thẳng browser→R2 (presigned PUT,
P1), lùi về multipart nếu R2 chưa mở CORS. Router KHÔNG tự viết prefix.
"""
from __future__ import annotations

import uuid
import json
import os
from datetime import datetime, timezone
from pathlib import PurePosixPath
from statistics import median

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


def _browser_direct_upload_enabled() -> bool:
    """R2 presigned PUT only works after the bucket CORS rule is verified.

    Default-off avoids a guaranteed browser CORS error followed by multipart
    fallback. Watch Agent is not a browser and keeps using direct R2 uploads.
    """
    return os.environ.get("LTT_R2_BROWSER_UPLOAD_ENABLED", "").strip() == "1"


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
            .order_by(Job.created_at.desc()).limit(50)
        ).scalars().all()
        queued_ids = [value for (value,) in db.execute(select(Job.id).where(
            Job.app_slug == MANIFEST.slug, Job.status == "queued")
            .order_by(Job.created_at)).all()]
        queue_positions = {value: index + 1 for index, value in enumerate(queued_ids)}
        samples = []
        for sample in rows:
            result = sample.result or {}; params = sample.params or {}
            seconds = float(result.get("processing_seconds") or 0)
            duration = float(result.get("duration_s") or params.get("duration_s") or 0)
            if sample.status == "done" and seconds > 0 and duration > 0:
                samples.append((params.get("preset", "fast"),
                                int(params.get("target_height", 1080)),
                                bool(params.get("stabilize")),
                                bool(params.get("smooth_motion")),
                                seconds / duration))
        out = []
        now = datetime.now(timezone.utc)
        for j in rows[:12]:
            r = j.result or {}
            p = j.params or {}
            source_key = str(p.get("video_key") or "")
            eta_text = ""
            if j.status == "queued":
                eta_text = f"Vị trí {queue_positions.get(j.id, '?')} trong hàng đợi"
            elif j.status == "running":
                rates = [value for preset, height, stabilize, smooth_motion, value in samples
                         if preset == p.get("preset", "fast") and
                         height == int(p.get("target_height", 1080)) and
                         stabilize == bool(p.get("stabilize")) and
                         smooth_motion == bool(p.get("smooth_motion"))]
                duration = float(p.get("duration_s") or 0)
                if len(rates) >= 3 and duration > 0 and j.started_at:
                    started = j.started_at if j.started_at.tzinfo else j.started_at.replace(tzinfo=timezone.utc)
                    remaining = max(0, median(rates) * duration - (now - started).total_seconds())
                    eta_text = f"Còn khoảng {max(1, round(remaining / 60))} phút"
                else:
                    eta_text = "Đang ước tính ETA"
            out.append({"id": j.id, "status": j.status, "progress": j.progress,
                        "progress_msg": j.progress_msg, "error": j.error,
                        "video_key": r.get("video_key"), "duration_s": r.get("duration_s"),
                        "target_height": r.get("target_height") or p.get("target_height"),
                        "source_key": source_key,
                        "source_name": p.get("source_name") or PurePosixPath(source_key).name or "video.mp4",
                        "preset": p.get("preset", "fast"), "codec": p.get("codec", "h264"),
                        "preserve_fps": p.get("preserve_fps", True),
                        "preserve_audio": p.get("preserve_audio", True),
                        "stabilize": p.get("stabilize", False),
                        "smooth_motion": p.get("smooth_motion", False),
                        "warning": r.get("warning"), "eta_text": eta_text})
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
             stabilize: str = Form(""), smooth_motion: str = Form(""),
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
                       bool(preview), stabilize == "1", smooth_motion == "1")
    if dur <= 0:
        return HTMLResponse('<span class="dim">Chọn video để tính chi phí.</span>')
    return HTMLResponse(
        f'<strong>{e["credit"]} credit</strong> '
        f'<span class="dim">(~{e["vnd"]:,}đ · {e["minutes"]} phút · {th}p · {e["preset"]}'
        f'{" · xem thử" if e["preview"] else ""})</span>')


@router.post("/batch-quote")
async def batch_quote(request: Request, user: str = Depends(require_login)):
    """Quote server-side cho 1–3 video; đây chưa phải thao tác giữ credit."""
    try:
        body = await request.json()
        durations = body.get("durations") if isinstance(body, dict) else None
        if not isinstance(durations, list) or not 1 <= len(durations) <= 3:
            raise ValueError
        target = int(body.get("target_height", 1080))
        target = target if target in (1080, 1440, 2160) else 1080
        preset = body.get("preset") if body.get("preset") in ("fast", "quality") else "fast"
        preview = bool(body.get("preview"))
        stabilize = body.get("stabilize") is True
        smooth_motion = body.get("smooth_motion") is True
        entries = [cost.uoc_luong(float(value or 0), target, preset, preview,
                                  stabilize, smooth_motion)
                   for value in durations]
    except (TypeError, ValueError, json.JSONDecodeError):
        return JSONResponse({"ok": False, "error": "Danh sách video không hợp lệ."},
                            status_code=400)
    return JSONResponse({"ok": True, "items": entries,
                         "total_credit": sum(x["credit"] for x in entries)})


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
    target = None
    if _browser_direct_upload_enabled():
        try:
            target = get_storage().put_url(key, ttl_s=3600, content_type=ct)
        except Exception:  # noqa: BLE001
            target = None
    if target is None:
        return JSONResponse({"mode": "local", "key": key})
    return JSONResponse({"mode": "direct", "key": target.key, "url": target.url,
                         "method": target.method, "headers": target.headers or {}})


def _watch_user_id(request: Request) -> str:
    from apps.upscalevideo.watch_auth import authenticate
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        user = authenticate(db, request.headers.get("authorization", ""))
        if user is None:
            raise HTTPException(status_code=401, detail="Watch Agent token không hợp lệ.")
        return user.id
    finally:
        try: next(gen)
        except StopIteration: pass


@router.post("/watch/token")
def watch_token(request: Request, csrf_token: str = Form(...),
                user: str = Depends(require_login)):
    """Rotate token; raw value is returned exactly once and never logged."""
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn.")
    u = user_hien_tai(request)
    from apps.upscalevideo.watch_auth import issue
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        raw = issue(db, u.id); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    return JSONResponse({"ok": True, "token": raw,
                         "note": "Token chỉ hiển thị một lần."})


@router.post("/watch/revoke")
def watch_revoke(request: Request, csrf_token: str = Form(...),
                 user: str = Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn.")
    u = user_hien_tai(request)
    from apps.upscalevideo.watch_auth import revoke
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        count = revoke(db, u.id); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    return JSONResponse({"ok": True, "revoked": count})


@router.get("/watch/status")
def watch_status(request: Request):
    user_id = _watch_user_id(request)
    from platform_core import credit
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        balance = credit.so_du(db, user_id)
    finally:
        try: next(gen)
        except StopIteration: pass
    return JSONResponse({"ok": True, "credit": balance, "max_batch": 3,
                         "accepting": balance > 0})


@router.get("/admin-telemetry")
def admin_telemetry(request: Request, user: str = Depends(require_login)):
    from apps.upscalevideo.telemetry import gpu_snapshot, queue_snapshot, storage_snapshot
    from platform_core.db import get_session
    from platform_core.storage import get_storage
    from server.deps import is_operator
    if not is_operator(request):
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên được xem telemetry.")
    gen = get_session(); db = next(gen)
    try:
        queue_data = queue_snapshot(db)
    finally:
        try: next(gen)
        except StopIteration: pass
    return JSONResponse({"ok": True, "gpu": gpu_snapshot(),
                         "queue": queue_data, "storage": storage_snapshot(get_storage())})


@router.post("/watch/upload-url")
def watch_upload_url(request: Request, filename: str = Form(""),
                     content_type: str = Form("")):
    user_id = _watch_user_id(request)
    from platform_core.storage import get_storage
    ext = PurePosixPath(filename).suffix.lower()[:6]
    key = f"upscalevideo/{user_id}/watch/{uuid.uuid4().hex}{ext}"
    ct = (content_type or "video/mp4").split(";")[0].strip()
    try:
        target = get_storage().put_url(key, ttl_s=3600, content_type=ct)
    except Exception:  # noqa: BLE001
        target = None
    if target is None:
        return JSONResponse({"mode": "local", "key": key})
    return JSONResponse({"mode": "direct", "key": target.key, "url": target.url,
                         "method": target.method, "headers": target.headers or {}})


@router.post("/watch/batch")
async def watch_batch(request: Request, manifest: str = Form("[]"),
                      videos: list[UploadFile] = File(default=[])):
    """Bearer-scoped submit for Watch Agent; no browser cookie is accepted."""
    user_id = _watch_user_id(request)
    from apps.upscalevideo.service import submit_upscale_batch
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.registry import RegistryError
    from platform_core.storage import CLOUDFLARE_BODY_LIMIT, get_storage
    try:
        items = json.loads(manifest)
    except (TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Batch manifest không hợp lệ.")
    if not isinstance(items, list) or not 1 <= len(items) <= 3:
        raise HTTPException(status_code=400, detail="Watch batch chỉ nhận 1–3 video.")
    request_ids = [str(item.get("request_id") or "") for item in items
                   if isinstance(item, dict)]
    if len(request_ids) != len(items) or any(not value or len(value) > 96
                                             for value in request_ids):
        raise HTTPException(status_code=400, detail="Watch batch thiếu request id.")
    # Retry sau khi client mất response phải trả đúng job cũ trước khi ghi lại
    # artifact local. Atomic batch nghĩa là chỉ có trạng thái all/none; subset là
    # xung đột idempotency và phải dừng để operator kiểm tra.
    from platform_core.db import get_session
    from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job
    from sqlalchemy import select
    pre_gen = get_session(); pre_db = next(pre_gen)
    try:
        active = pre_db.execute(select(Job).where(
            Job.user_id == user_id, Job.app_slug == MANIFEST.slug,
            Job.status.in_((JOB_QUEUED, JOB_RUNNING)))).scalars().all()
        by_request = {(row.params or {}).get("request_id"): row for row in active}
        existing = [by_request[value] for value in request_ids if value in by_request]
    finally:
        try: next(pre_gen)
        except StopIteration: pass
    if len(existing) == len(items):
        return JSONResponse({"ok": True, "deduplicated": True, "jobs": [
            {"job_id": by_request[value].id, "status": by_request[value].status}
            for value in request_ids]})
    if existing:
        raise HTTPException(status_code=409, detail="Batch retry chỉ khớp một phần.")
    local_count = sum(1 for item in items if not str(item.get("video_key") or ""))
    if local_count != len(videos):
        raise HTTPException(status_code=400, detail="Số file không khớp manifest.")
    storage = get_storage(); cursor = 0; total = 0; prepared = []
    for index, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail=f"Video {index + 1} không hợp lệ.")
        item = dict(raw); key = str(item.get("video_key") or "").strip()
        if key:
            if not key.startswith(f"upscalevideo/{user_id}/watch/") or not storage.exists(key):
                raise HTTPException(status_code=400, detail=f"Video {index + 1} chưa upload xong.")
        else:
            upload = videos[cursor]; cursor += 1
            ext = PurePosixPath(upload.filename or "").suffix.lower()
            if ext not in {".mp4", ".mov", ".mkv", ".avi", ".webm"}:
                raise HTTPException(status_code=400, detail=f"Video {index + 1} sai định dạng.")
            data = await upload.read(); total += len(data)
            if not data or total > min(_LOCAL_VIDEO_MAX, CLOUDFLARE_BODY_LIMIT):
                raise HTTPException(status_code=400, detail="File local rỗng hoặc tổng >90MB.")
            key = f"upscalevideo/{user_id}/watch/{uuid.uuid4().hex}{ext}"
            item["_data"] = data
        request_id = str(item.get("request_id") or "")
        if not request_id or len(request_id) > 96:
            raise HTTPException(status_code=400, detail=f"Video {index + 1} thiếu request id.")
        item["video_key"] = key; prepared.append(item)
    import io as _io
    for item in prepared:
        if "_data" in item:
            storage.put(item["video_key"], _io.BytesIO(item.pop("_data")),
                        content_type="video/mp4")
    gen = get_session(); db = next(gen)
    try:
        try:
            rows = submit_upscale_batch(db, user_id=user_id, items=prepared)
            db.commit()
        except credit.ThieuCreditError as exc:
            db.rollback()
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=402)
        except (RegistryError, ValueError) as exc:
            db.rollback()
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    finally:
        try: next(gen)
        except StopIteration: pass
    return JSONResponse({"ok": True, "jobs": [{"job_id": row.id,
                                                  "status": row.status}
                                                 for row in rows]})


@router.post("/queue")
async def queue(request: Request, csrf_token: str = Form(...),
                video_key: str = Form(""), duration_s: str = Form("0"),
                preset: str = Form("fast"), target_height: str = Form("1080"),
                codec: str = Form("h264"), preview: str = Form(""), ajax: str = Form(""),
                preserve_fps: str = Form("1"), preserve_audio: str = Form("1"),
                stabilize: str = Form(""), smooth_motion: str = Form(""),
                video: UploadFile = File(default=None),
                user: str = Depends(require_login)):
    from platform_core import credit
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
                                     preserve_audio=preserve_audio != "0",
                                     stabilize=stabilize == "1",
                                     smooth_motion=smooth_motion == "1",
                                     source_name=(getattr(video, "filename", "") or ""))
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


@router.post("/batch")
async def batch_queue(request: Request, csrf_token: str = Form(...),
                      manifest: str = Form("[]"), preset: str = Form("fast"),
                      target_height: str = Form("1080"), codec: str = Form("h264"),
                      preview: str = Form(""), preserve_fps: str = Form("1"),
                      preserve_audio: str = Form("1"),
                      stabilize: str = Form(""), smooth_motion: str = Form(""),
                      videos: list[UploadFile] = File(default=[]),
                      user: str = Depends(require_login)):
    """Nộp batch tối đa 3; job + credit là một transaction duy nhất."""
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.registry import RegistryError
    from platform_core.storage import CLOUDFLARE_BODY_LIMIT, get_storage
    from apps.upscalevideo.service import submit_upscale_batch

    def fail(message, code=400, items=None):
        return JSONResponse({"ok": False, "error": message, "items": items or []},
                            status_code=code)

    if not verify_csrf_token(request, csrf_token):
        return fail("Phiên đã hết hạn — tải lại trang.")
    u = user_hien_tai(request)
    if u is None:
        return fail("Cần đăng nhập bằng tài khoản người dùng.")
    try:
        items = json.loads(manifest)
    except (TypeError, json.JSONDecodeError):
        return fail("Batch manifest không hợp lệ.")
    if not isinstance(items, list) or not 1 <= len(items) <= 3:
        return fail("Chỉ được xử lý từ 1 đến 3 video mỗi batch.")
    if len(videos) != sum(1 for item in items if not str(item.get("video_key") or "")):
        return fail("Số file local không khớp batch manifest.")

    storage = get_storage()
    local_total = 0
    local_cursor = 0
    prepared = []
    allowed_ext = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
    for index, raw in enumerate(items):
        if not isinstance(raw, dict):
            return fail(f"Video {index + 1} không hợp lệ.")
        item = dict(raw)
        key = str(item.get("video_key") or "").strip()
        if key:
            if not key.startswith(f"upscalevideo/{u.id}/") or not storage.exists(key):
                return fail(f"Video {index + 1} chưa upload xong hoặc không thuộc tài khoản.")
        else:
            upload = videos[local_cursor]; local_cursor += 1
            filename = str(getattr(upload, "filename", "") or "")
            ext = PurePosixPath(filename).suffix.lower()
            if ext not in allowed_ext:
                return fail(f"Video {index + 1} có định dạng không hỗ trợ.")
            data = await upload.read()
            if not data:
                return fail(f"Video {index + 1} là file rỗng.")
            local_total += len(data)
            if local_total > min(_LOCAL_VIDEO_MAX, CLOUDFLARE_BODY_LIMIT):
                return fail("Tổng file local >90MB; cần upload thẳng qua R2.")
            key = f"upscalevideo/{u.id}/uploads/{uuid.uuid4().hex}{ext}"
            item["_data"] = data
            item["_content_type"] = upload.content_type or "video/mp4"
        try:
            item["duration_s"] = max(0.0, float(item.get("duration_s") or 0))
        except (TypeError, ValueError):
            return fail(f"Thời lượng video {index + 1} không hợp lệ.")
        request_id = str(item.get("request_id") or "")
        if not request_id or len(request_id) > 96:
            return fail(f"Video {index + 1} thiếu request id.")
        item["video_key"] = key
        prepared.append(item)

    # Chỉ ghi local artifact sau khi toàn bộ manifest đã qua preflight.
    import io as _io
    for item in prepared:
        if "_data" in item:
            storage.put(item["video_key"], _io.BytesIO(item.pop("_data")),
                        content_type=item.pop("_content_type"))
    try:
        th = int(target_height)
    except (TypeError, ValueError):
        th = 1080
    th = th if th in (1080, 1440, 2160) else 1080
    preset = preset if preset in ("fast", "quality") else "fast"
    codec = codec if codec in ("h264", "hevc") else "h264"

    gen = get_session(); db = next(gen)
    try:
        try:
            batch_jobs = submit_upscale_batch(
                db, user_id=u.id, items=prepared, preset=preset,
                target_height=th, codec=codec, preview=bool(preview),
                preserve_fps=preserve_fps != "0",
                preserve_audio=preserve_audio != "0",
                stabilize=stabilize == "1", smooth_motion=smooth_motion == "1")
            db.commit()
        except (credit.ThieuCreditError, RegistryError, ValueError) as exc:
            db.rollback()
            return fail(str(exc), items=[{"request_id": x["request_id"],
                                         "status": "not_submitted"} for x in prepared])
    finally:
        try: next(gen)
        except StopIteration: pass
    return JSONResponse({"ok": True, "jobs": [
        {"request_id": item["request_id"], "job_id": job.id, "status": job.status}
        for item, job in zip(prepared, batch_jobs)]})


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
