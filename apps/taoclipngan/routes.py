"""
UI app `taoclipngan` (Đợt C, GPU). Upload video lớn thẳng browser→R2 (presigned PUT),
lùi multipart nếu chưa CORS. Job GPU dài → hàng đợi worker. Router KHÔNG tự viết prefix.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse,
                               Response, StreamingResponse)
from starlette.background import BackgroundTask

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
    from apps.taoclipngan.features import BRAND_PRESETS, PLATFORMS
    return templates.TemplateResponse(request, "taoclipngan.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "tiers": _TIERS, "aspects": _ASPECTS, "genres": _GENRES, "langs": _LANGS,
        "jobs": _jobs_cua_toi(request), "library": _source_library(request),
        "brand_presets": [(key, value["label"]) for key, value in BRAND_PRESETS.items()],
        "platforms": PLATFORMS,
        "error": error,
    }, status_code=status_code)


def _jobs_cua_toi(request: Request):
    u = user_hien_tai(request)
    if u is None:
        return []
    from platform_core.db import get_session
    from platform_core.models import APP_PROJECT_ACTIVE, AppProject, Job
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        rows = db.execute(
            select(Job).where(Job.user_id == u.id, Job.app_slug == MANIFEST.slug)
            .order_by(Job.created_at.desc()).limit(8)
        ).scalars().all()
        projects = db.execute(select(AppProject).where(
            AppProject.user_id == u.id, AppProject.app_slug == MANIFEST.slug,
            AppProject.status == APP_PROJECT_ACTIVE
        ).order_by(AppProject.updated_at.desc()).limit(100)).scalars().all()
        project_by_job = {}
        for project in projects:
            source_job_id = str((project.payload or {}).get("source_job_id") or "")
            if source_job_id and source_job_id not in project_by_job:
                project_by_job[source_job_id] = project
        out = []
        for j in rows:
            r = j.result or {}
            project = project_by_job.get(j.id)
            payload = (project.payload or {}) if project else {}
            out.append({"id": j.id, "status": j.status, "progress": j.progress,
                        "progress_msg": j.progress_msg, "error": j.error,
                        "clips": payload.get("clips") or r.get("clips") or [],
                        "source_name": str((j.params or {}).get("source_filename") or
                                           (j.params or {}).get("video_key") or "Video")[:160],
                        "tier": str((j.params or {}).get("tier") or ""),
                        "aspect_ratio": str((j.params or {}).get("aspect_ratio") or ""),
                        "brand_preset": str((j.params or {}).get("brand_preset") or "auto"),
                        "platforms": payload.get("platforms") or r.get("platforms") or [],
                        "project": ({"id": project.id, "revision": project.revision}
                                    if project else None)})
        return out
    finally:
        try: next(gen)
        except StopIteration: pass


def _source_library(request: Request):
    """Recent owner source assets backed by Storage, never cross-user."""
    u = user_hien_tai(request)
    if u is None:
        return []
    from platform_core.db import get_session
    from platform_core.models import Job
    from platform_core.storage import get_storage
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        rows = db.execute(select(Job).where(
            Job.user_id == u.id, Job.app_slug == MANIFEST.slug
        ).order_by(Job.created_at.desc()).limit(60)).scalars().all()
        storage = get_storage(); seen = set(); out = []
        for row in rows:
            params = row.params or {}; key = str(params.get("video_key") or "")
            if not key.startswith(f"taoclipngan/{u.id}/") or key in seen:
                continue
            try:
                exists = storage.exists(key)
            except Exception:  # noqa: BLE001
                exists = False
            if not exists:
                continue
            seen.add(key)
            out.append({"key": key,
                        "name": str(params.get("source_filename") or key.rsplit("/", 1)[-1])[:160],
                        "duration_s": float(params.get("duration_s") or 0),
                        "created_at": row.created_at})
            if len(out) >= 8:
                break
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
                source_filename: str = Form(""),
                tier: str = Form("high_quality"), genre: str = Form("talking_head"),
                aspect_ratio: str = Form("9:16"), language: str = Form(""),
                target_clip_count: str = Form("3"),
                min_clip_duration_sec: str = Form("15"),
                max_clip_duration_sec: str = Form("60"), ajax: str = Form(""),
                brand_preset: str = Form("auto"), platforms: list[str] = Form([]),
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

    from apps.taoclipngan.features import clean_brand, clean_platforms
    params = {"video_key": vkey, "duration_s": dur, "tier": tier, "genre": genre,
              "aspect_ratio": aspect_ratio, "language": language,
              "target_clip_count": n, "min_clip_duration_sec": mn,
              "max_clip_duration_sec": mx, "owner_id": u.id,
              "source_filename": (source_filename or
                                  getattr(video, "filename", "") or
                                  vkey.rsplit("/", 1)[-1])[:160],
              "brand_preset": clean_brand(brand_preset),
              "platforms": clean_platforms(platforms)}
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


def _owned_done_job(db, user_id: str, job_id: str):
    from platform_core.models import Job
    row = db.get(Job, job_id)
    if (row is None or row.user_id != user_id or row.app_slug != MANIFEST.slug or
            row.status != "done"):
        return None
    return row


@router.post("/package/{job_id}/save")
def save_package(request: Request, job_id: str, csrf_token: str = Form(...),
                 package_json: str = Form("{}"), project_id: str = Form(""),
                 revision: int = Form(0), user: str = Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return JSONResponse({"ok": False, "error": "Phiên hết hạn."}, status_code=400)
    import json
    try:
        draft = json.loads(package_json)
        if not isinstance(draft, dict):
            raise ValueError
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "Package không hợp lệ."}, status_code=400)
    from apps.taoclipngan.features import package_payload
    from platform_core import app_projects
    from platform_core.db import get_session
    u = user_hien_tai(request); gen = get_session(); db = next(gen)
    try:
        job = _owned_done_job(db, u.id, job_id) if u else None
        if job is None:
            return JSONResponse({"ok": False, "error": "Không tìm thấy job."}, status_code=404)
        payload = package_payload(job_id=job_id,
            original_clips=list((job.result or {}).get("clips") or []),
            drafts=list(draft.get("clips") or []), platforms=draft.get("platforms") or [],
            brand_preset=str((job.params or {}).get("brand_preset") or "auto"))
        try:
            if project_id:
                current = app_projects.get_owned(db, project_id, u.id, MANIFEST.slug)
                if (current.payload or {}).get("source_job_id") != job_id:
                    raise app_projects.ProjectNotFound("Không tìm thấy package.")
                row = app_projects.save(db, project_id=project_id, user_id=u.id,
                    app_slug=MANIFEST.slug, revision=revision,
                    name=f"Package {str((job.params or {}).get('source_filename') or job.id)[:120]}",
                    schema_version=1, payload=payload)
            else:
                row = app_projects.create(db, user_id=u.id, app_slug=MANIFEST.slug,
                    name=f"Package {str((job.params or {}).get('source_filename') or job.id)[:120]}",
                    schema_version=1, payload=payload)
            db.commit()
        except app_projects.ProjectError as exc:
            db.rollback()
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=409)
        return JSONResponse({"ok": True, "project_id": row.id,
                             "revision": row.revision})
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("/package/{job_id}.zip")
def download_package(request: Request, job_id: str, user: str = Depends(require_login)):
    import json
    import shutil
    import tempfile
    import zipfile
    from apps.taoclipngan.features import package_payload, srt_text
    from platform_core.db import get_session
    from platform_core.models import APP_PROJECT_ACTIVE, AppProject
    from platform_core.storage import get_storage
    from sqlalchemy import select
    u = user_hien_tai(request); gen = get_session(); db = next(gen)
    try:
        job = _owned_done_job(db, u.id, job_id) if u else None
        if job is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy package.")
        project = db.execute(select(AppProject).where(
            AppProject.user_id == u.id, AppProject.app_slug == MANIFEST.slug,
            AppProject.status == APP_PROJECT_ACTIVE
        ).order_by(AppProject.updated_at.desc()).limit(100)).scalars().all()
        saved = next((row for row in project
                      if (row.payload or {}).get("source_job_id") == job_id), None)
        payload = (saved.payload or {}) if saved else package_payload(
            job_id=job_id, original_clips=list((job.result or {}).get("clips") or []),
            drafts=[], platforms=(job.result or {}).get("platforms") or [],
            brand_preset=str((job.params or {}).get("brand_preset") or "auto"))
    finally:
        try: next(gen)
        except StopIteration: pass
    spool = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)
    storage = get_storage()
    with zipfile.ZipFile(spool, "w") as archive:
        for index, clip in enumerate(payload.get("clips") or [], 1):
            key = str(clip.get("video_key") or "")
            if not key.startswith(f"taoclipngan/{u.id}/"):
                continue
            info = zipfile.ZipInfo(f"clips/clip_{index:02d}.mp4")
            info.compress_type = zipfile.ZIP_STORED
            with storage.open(key) as source, archive.open(info, "w", force_zip64=True) as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
            archive.writestr(f"captions/clip_{index:02d}.srt",
                             srt_text(list(clip.get("transcript") or [])))
        archive.writestr("package.json", json.dumps(payload, ensure_ascii=False, indent=2))
        archive.writestr("README.txt", "LTT Clip social package\nVideo dùng chung cho TikTok, YouTube Shorts và Instagram Reels; metadata theo package.json.\n")
    spool.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="ltt-clips-{job_id[:8]}.zip"',
               "X-Content-Type-Options": "nosniff"}
    return StreamingResponse(spool, media_type="application/zip", headers=headers,
                             background=BackgroundTask(spool.close))


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
