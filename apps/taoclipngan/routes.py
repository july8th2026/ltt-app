"""
UI app `taoclipngan` (Đợt C, GPU). Upload video lớn thẳng browser→R2 (presigned PUT),
lùi multipart nếu chưa CORS. Job GPU dài → hàng đợi worker. Router KHÔNG tự viết prefix.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse,
                               Response, StreamingResponse)

from apps.taoclipngan import cost
from apps.taoclipngan.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["taoclipngan"])

_TIERS = [("high_quality", "Cao (large-v3 + tách nhạc)"), ("balanced", "Cân bằng"),
          ("fast", "Nhanh")]
_ASPECTS = [("9:16", "Dọc 9:16"), ("1:1", "Vuông 1:1"), ("16:9", "Ngang 16:9"),
            ("4:5", "4:5")]
_GENRES = [("talking_head", "Nói chuyện/vlog"), ("podcast", "Podcast"),
           ("interview", "Phỏng vấn"), ("storytelling", "Kể chuyện"),
           ("comedy", "Hài"), ("education", "Giáo dục"),
           ("news_commentary", "Bình luận/tin"), ("review", "Review"),
           ("history", "Lịch sử"), ("kids_music", "Nhạc thiếu nhi")]
_LANGS = [("", "Tự nhận"), ("vi", "Tiếng Việt"), ("en", "English")]
_LOCAL_VIDEO_MAX = 90 * 1024 * 1024


def _render(request: Request, user: str, *, error: str = "", status_code: int = 200):
    return templates.TemplateResponse(request, "taoclipngan.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "tiers": _TIERS, "aspects": _ASPECTS, "genres": _GENRES, "langs": _LANGS,
        "jobs": _jobs_cua_toi(request), "error": error,
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
            .order_by(Job.created_at.desc()).limit(8)
        ).scalars().all()
        out = []
        for j in rows:
            r = j.result or {}
            out.append({"id": j.id, "status": j.status, "progress": j.progress,
                        "progress_msg": j.progress_msg, "error": j.error,
                        "clips": r.get("clips") or []})
        return out
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("", response_class=HTMLResponse)
def page(request: Request, user: str = Depends(require_login)):
    return _render(request, user)


@router.post("/estimate", response_class=HTMLResponse)
def estimate(request: Request, duration_s: str = Form("0"), tier: str = Form("high_quality"),
             target_clip_count: str = Form("3"), user: str = Depends(require_login)):
    try:
        dur = float(duration_s or 0)
    except (TypeError, ValueError):
        dur = 0.0
    try:
        n = int(target_clip_count or 3)
    except (TypeError, ValueError):
        n = 3
    e = cost.uoc_luong(dur, tier if tier in ("fast", "balanced", "high_quality") else "high_quality", n)
    if dur <= 0:
        return HTMLResponse('<span class="dim">Chọn video để tính chi phí.</span>')
    return HTMLResponse(
        f'<strong>{e["credit"]} credit</strong> '
        f'<span class="dim">(~{e["vnd"]:,}đ · {e["minutes"]} phút nguồn · {e["tier"]} · {n} clip)</span>')


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
    key = f"taoclipngan/{u.id}/uploads/{uuid.uuid4().hex}{ext}"
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
                tier: str = Form("high_quality"), genre: str = Form("talking_head"),
                aspect_ratio: str = Form("9:16"), language: str = Form(""),
                target_clip_count: str = Form("3"),
                min_clip_duration_sec: str = Form("15"),
                max_clip_duration_sec: str = Form("60"), ajax: str = Form(""),
                video: UploadFile = File(default=None),
                user: str = Depends(require_login)):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    from platform_core.storage import CLOUDFLARE_BODY_LIMIT, get_storage

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
        if not vkey.startswith(f"taoclipngan/{u.id}/") or not storage.exists(vkey):
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
        vkey = f"taoclipngan/{u.id}/uploads/{uuid.uuid4().hex}{ext}"
        import io as _io
        storage.put(vkey, _io.BytesIO(vdata), content_type=(video.content_type or "video/mp4"))

    if tier not in ("fast", "balanced", "high_quality"):
        tier = "high_quality"
    if aspect_ratio not in dict(_ASPECTS):
        aspect_ratio = "9:16"
    if genre not in dict(_GENRES):
        genre = "talking_head"
    try:
        dur = float(duration_s or 0)
        n = max(1, min(int(target_clip_count or 3), 10))
        mn = float(min_clip_duration_sec or 15)
        mx = float(max_clip_duration_sec or 60)
    except (TypeError, ValueError):
        dur, n, mn, mx = 0.0, 3, 15.0, 60.0

    params = {"video_key": vkey, "duration_s": dur, "tier": tier, "genre": genre,
              "aspect_ratio": aspect_ratio, "language": language,
              "target_clip_count": n, "min_clip_duration_sec": mn,
              "max_clip_duration_sec": mx, "owner_id": u.id}
    gen = get_session(); db = next(gen)
    last_id = None
    try:
        try:
            job = submit_with_credit(db, user_id=u.id, app_slug=MANIFEST.slug,
                                     job_type="taoclipngan.render", params=params,
                                     dedupe_key=dedupe_key_for("taoclipngan.render", params))
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


@router.get("/v/{key:path}")
def clip_out(request: Request, key: str, user: str = Depends(require_login)):
    from platform_core.storage import StorageError, get_storage
    u = user_hien_tai(request)
    segs = key.split("/")
    if len(segs) < 2 or segs[0] != "taoclipngan" or u is None or segs[1] != u.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy.")
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
        raise HTTPException(status_code=404, detail="Không tìm thấy clip.")
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
