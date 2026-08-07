"""
UI app `seedance` (A2, Pha 1: text→video). Router KHÔNG tự viết prefix.

Video output serve theo HTTP RANGE (`/v/{key}`) — player tải từng đoạn nhỏ nên
KHÔNG dính trần 100MB của Cloudflare (không cần R2 cho clip ngắn).
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import uuid
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse

from apps.taovideo import cost, models
from apps.taovideo.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["seedance"])


def _render(request: Request, user: str, *, error: str = "", jobs=None, status_code: int = 200, **extra):
    reg_ui = {k: {"resolutions": v["resolutions"], "durations": v["durations"],
                  "aspects": v["aspects"],
                  "supports_seed": bool(v.get("supports_seed")),
                  "prompt_controls": v.get("prompt_controls", [])}
              for k, v in models.MODELS.items() if v.get("active")}
    if isinstance(jobs, dict):
        # Các nhánh validation/credit dùng cùng payload workspace với GET. Trước
        # đây truyền nguyên dict vào template khiến grid lặp qua key thay vì job.
        extra.setdefault("job_counts", jobs.get("counts", {}))
        extra.setdefault("prompt_history", jobs.get("history", []))
        extra.setdefault("saved_assets", jobs.get("assets", []))
        jobs = jobs.get("items", [])
    context = {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "models": models.options(), "reg_ui": reg_ui,
        "default_model": models.DEFAULT_MODEL, "error": error, "jobs": jobs or [],
    }
    context.update(extra)
    return templates.TemplateResponse(request, "taovideo.html", context, status_code=status_code)


def _jobs_cua_toi(request: Request, status: str = "all", sort: str = "newest"):
    u = user_hien_tai(request)
    if u is None:
        return []
    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, JOB_ERROR, JOB_QUEUED, JOB_RUNNING, Job
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        rows = db.execute(
            select(Job).where(Job.user_id == u.id, Job.app_slug == MANIFEST.slug)
            .order_by(Job.created_at.asc() if sort == "oldest" else Job.created_at.desc()).limit(60)
        ).scalars().all()
        counts = {"all": len(rows), "running": 0, "done": 0, "error": 0}
        for j in rows:
            if j.status in (JOB_QUEUED, JOB_RUNNING): counts["running"] += 1
            elif j.status == JOB_DONE: counts["done"] += 1
            elif j.status == JOB_ERROR: counts["error"] += 1
        filtered = rows if status == "all" else [j for j in rows if (
            j.status in (JOB_QUEUED, JOB_RUNNING) if status == "running" else j.status == status)]
        history=[]; seen=set(); assets=[]; seen_keys=set()
        for j in rows:
            prompt=str((j.params or {}).get("prompt", "")).strip()
            if prompt and prompt not in seen: history.append(prompt); seen.add(prompt)
            for ref in ((j.params or {}).get("refs") or []):
                key = str(ref.get("storage_key") or "")
                if (not key.startswith(f"taovideo/{u.id}/refs/") or
                        key in seen_keys or len(assets) >= 40):
                    continue
                seen_keys.add(key)
                assets.append({
                    "storage_key": key, "kind": ref.get("kind", "image"),
                    "role": ref.get("role", "reference_image"),
                    "handle": ref.get("handle", ""),
                    "name": ref.get("name") or f"Tài sản {len(assets) + 1}",
                    "size": int(ref.get("size") or 0),
                })
        return {"items": [{"id": j.id, "status": j.status, "progress": j.progress,
                 "progress_msg": j.progress_msg, "error": j.error,
                 "video_key": (j.result or {}).get("video_key") if j.result else None,
                 "model": (j.result or {}).get("model") or (j.params or {}).get("model"),
                 "prompt": str((j.params or {}).get("prompt", ""))[:180],
                 "raw_prompt": str((j.params or {}).get("raw_prompt") or
                                   (j.params or {}).get("prompt", ""))[:10000],
                 "resolution": (j.params or {}).get("resolution", ""),
                 "duration": (j.params or {}).get("duration", ""),
                 "aspect_ratio": (j.params or {}).get("aspect_ratio", "")}
                for j in filtered], "counts": counts, "history": history[:10],
                "assets": assets}
    finally:
        try: next(gen)
        except StopIteration: pass


def _clean(model, resolution, duration, aspect):
    m = models.get(model) or models.get(models.DEFAULT_MODEL)
    mid = model if models.get(model) else models.DEFAULT_MODEL
    if resolution not in m["resolutions"]:
        resolution = m["resolutions"][0]
    if aspect not in m["aspects"]:
        aspect = m["aspects"][0]
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = 5
    if duration not in m["durations"]:
        duration = 5 if 5 in m["durations"] else m["durations"][0]
    return mid, resolution, duration, aspect


_CAMERA = {
    "static": "locked-off static camera",
    "dolly_in": "slow cinematic dolly-in",
    "tracking": "smooth subject tracking shot",
    "orbit": "controlled orbit shot around the subject",
    "aerial": "wide aerial establishing shot",
    "handheld": "subtle handheld documentary movement",
}
_MOTION = {
    "subtle": "subtle natural motion",
    "dynamic": "dynamic energetic motion",
    "cinematic": "cinematic paced motion with smooth acceleration",
}
_VISUAL_STYLE = {
    "realistic": "photorealistic, natural detail",
    "cinematic": "cinematic lighting and filmic color grading",
    "anime": "polished anime visual style",
    "product": "premium commercial product photography",
}


def _compose_prompt(prompt: str, camera: str = "", motion: str = "",
                    visual_style: str = "") -> str:
    """Prompt guidance tất định; không giả đây là tham số camera native."""
    base = str(prompt or "").strip()
    guidance = [mapping[value] for mapping, value in (
        (_CAMERA, camera), (_MOTION, motion), (_VISUAL_STYLE, visual_style)
    ) if value in mapping]
    return (base + ("\n\nDirection: " + "; ".join(guidance) + "." if guidance else ""))[:10000]


def _clean_seed(value: str) -> int | None:
    if str(value or "").strip() == "":
        return None
    try:
        seed = int(value)
    except (TypeError, ValueError):
        raise ValueError(_t('Seed phải là số nguyên từ 0 đến 2147483647.'))
    if not 0 <= seed <= 2_147_483_647:
        raise ValueError(_t('Seed phải là số nguyên từ 0 đến 2147483647.'))
    return seed


@router.get("", response_class=HTMLResponse)
def page(request: Request, status: str = "all", sort: str = "newest", user: str = Depends(require_login)):
    status = status if status in {"all", "running", "done", "error"} else "all"
    sort = sort if sort in {"newest", "oldest"} else "newest"
    data = _jobs_cua_toi(request, status, sort)
    return _render(request, user, jobs=data["items"], job_counts=data["counts"],
                   prompt_history=data["history"], saved_assets=data["assets"],
                   active_status=status, active_sort=sort)


@router.post("/estimate", response_class=HTMLResponse)
def estimate(request: Request, model: str = Form(""), resolution: str = Form("480p"),
             duration: str = Form("5"), aspect_ratio: str = Form("16:9"),
             user: str = Depends(require_login)):
    mid, res, dur, _asp = _clean(model, resolution, duration, aspect_ratio)
    e = cost.uoc_luong(mid, res, dur, False)
    return HTMLResponse(
        f'<strong>{e["credit"]} credit</strong> '
        f'<span class="dim">(~{e["vnd"]:,}đ · {e["tokens"]:,} token ước tính)</span>')


@router.post("/translate", response_class=HTMLResponse)
async def translate(request: Request, prompt: str = Form(""), target: str = Form("en"),
                    csrf_token: str = Form(""), user: str = Depends(require_login)):
    """Dịch prompt qua Gemini chat (HTMX trả <textarea> mới). Không tốn credit."""
    from markupsafe import escape
    from starlette.concurrency import run_in_threadpool
    from apps.taovideo import translate as tr
    if not verify_csrf_token(request, csrf_token):   # chống lạm dụng quota dịch cross-site
        return HTMLResponse('<span class="dim">Phiên hết hạn — tải lại trang.</span>')
    p = prompt.strip()[:10000]
    if not p:
        return HTMLResponse('<span class="dim">Nhập mô tả rồi bấm dịch.</span>')
    try:
        # dich() gọi httpx đồng bộ + DB → đẩy khỏi event loop để không chặn web.
        out = await run_in_threadpool(tr.dich, p, target if target in ("en", "zh", "vi") else "en")
    except Exception:  # noqa: BLE001
        return HTMLResponse('<span class="dim">Dịch lỗi — thử lại sau.</span>')
    return HTMLResponse(
        f'<textarea id="tv-prompt" name="prompt" rows="4" form="sdform" '
        f'aria-describedby="tv-prompt-hint" maxlength="10000" required '
        f'style="width:100%">{escape(out)}</textarea>'
        f'<div class="dim" style="font-size:12px;margin-top:4px">Đã dịch → {escape(target)}. '
        f'Sửa nếu cần rồi bấm Tạo video.</div>')


@router.post("/prompt-assist", response_class=HTMLResponse)
def prompt_assist(request: Request, prompt: str = Form(""), camera: str = Form(""),
                  motion: str = Form(""), visual_style: str = Form(""),
                  csrf_token: str = Form(""), user: str = Depends(require_login)):
    """Preview prompt final bằng cùng helper mà queue dùng; không gọi provider."""
    from markupsafe import escape
    if not verify_csrf_token(request, csrf_token):
        return HTMLResponse('<span class="tv-assist-error">Phiên hết hạn — tải lại trang.</span>', 400)
    final = _compose_prompt(prompt, camera, motion, visual_style)
    if not final:
        return HTMLResponse('<span class="tv-assist-error">Nhập prompt để xem gợi ý.</span>', 400)
    return HTMLResponse(f'<pre class="tv-assist-preview">{escape(final)}</pre>')


_CAP = {"image": 20 * 1024 * 1024, "video": 60 * 1024 * 1024, "audio": 20 * 1024 * 1024}


async def _luu_refs(u_id: str, files, roles, handles=None) -> list:
    """Lưu ref (ảnh/video/audio) → spec {kind,storage_key,role}. ≤4 tệp. Ảnh ≤8MB đi
    inline; ảnh lớn/video/audio đi asset:// (worker lo). Cap: ảnh 20MB, video 60MB, audio 20MB."""
    from platform_core.storage import get_storage
    import io as _io
    storage = get_storage()
    specs = []; prepared = []
    actual = [f for f in (files or []) if f and getattr(f, "filename", "")]
    if len(actual) > 4:
        raise ValueError(_t('Tối đa 4 file tham chiếu.'))
    for i, f in enumerate(actual):
        if not f or not getattr(f, "filename", ""):
            continue
        ct = (f.content_type or "").lower()
        if ct.startswith("image/"):
            kind = "image"
        elif ct in {"video/mp4", "video/quicktime", "video/webm"}:
            kind = "video"
        elif ct.startswith("audio/"):
            kind = "audio"
        else:
            raise ValueError(f"Định dạng tham chiếu không hỗ trợ: {f.filename}")
        data = await f.read()
        if not data:
            raise ValueError(f"File tham chiếu rỗng: {f.filename}")
        if len(data) > _CAP[kind]:
            raise ValueError(f"File tham chiếu vượt giới hạn: {f.filename}")
        role = roles[i] if roles and i < len(roles) else "reference_image"
        role = (role if kind == "image" and role in
                {"reference_image", "first_frame", "last_frame", "mask"}
                else f"reference_{kind}")
        name = PurePath(str(f.filename).replace("\\", "/")).name[:120]
        prepared.append((kind, ct, data, role, name,
                         (handles[i] if handles and i < len(handles) else "")[:32]))
    # Chỉ ghi sau khi TOÀN BỘ batch đã qua MIME/size/empty validation.
    for kind, ct, data, role, name, handle in prepared:
        skey = f"taovideo/{u_id}/refs/{uuid.uuid4().hex}"
        storage.put(skey, _io.BytesIO(data), content_type=ct or "image/png")
        specs.append({"kind": kind, "storage_key": skey,
                      "role": role, "handle": handle,
                      "name": name, "content_type": ct, "size": len(data)})
    return specs


def _saved_refs_for_user(user_id: str, keys: list[str]) -> list[dict]:
    """Resolve key từ lịch sử job owner; browser không được tự khai storage key."""
    requested = list(dict.fromkeys(str(k) for k in (keys or [])))
    if not requested:
        return []
    if len(requested) > 4:
        raise ValueError(_t('Tối đa 4 tài sản đã lưu.'))
    data = _jobs_cua_toi_for_user(user_id)
    allowed = {a["storage_key"]: a for a in data}
    from platform_core.storage import get_storage
    storage = get_storage(); out = []
    for key in requested:
        asset = allowed.get(key)
        if asset is None or not storage.exists(key):
            raise ValueError(_t('Tài sản đã lưu không hợp lệ hoặc không còn tồn tại.'))
        clean = dict(asset)
        kind = str(clean.get("kind") or "image")
        if kind not in {"image", "video", "audio"}:
            raise ValueError(_t('Loại tài sản đã lưu không hợp lệ.'))
        role = str(clean.get("role") or "")
        clean["role"] = (role if kind == "image" and role in
                         {"reference_image", "first_frame", "last_frame", "mask"}
                         else f"reference_{kind}")
        clean["handle"] = str(clean.get("handle") or "")[:32]
        out.append(clean)
    return out


def _jobs_cua_toi_for_user(user_id: str) -> list[dict]:
    """Danh sách asset lịch sử tối thiểu cho submit; owner-scoped tại DB."""
    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        rows = db.execute(select(Job).where(
            Job.user_id == user_id, Job.app_slug == MANIFEST.slug
        ).order_by(Job.created_at.desc()).limit(60)).scalars().all()
        out=[]; seen=set()
        for job in rows:
            for ref in ((job.params or {}).get("refs") or []):
                key=str(ref.get("storage_key") or "")
                if key.startswith(f"taovideo/{user_id}/refs/") and key not in seen:
                    seen.add(key); out.append(dict(ref))
        return out
    finally:
        try: next(gen)
        except StopIteration: pass


@router.post("/queue", response_class=HTMLResponse)
async def queue(request: Request, csrf_token: str = Form(...), prompt: str = Form(""),
                model: str = Form(""), resolution: str = Form("480p"),
                duration: str = Form("5"), aspect_ratio: str = Form("16:9"),
                generate_audio: str = Form(""), count: str = Form("1"),
                camera: str = Form(""), motion: str = Form(""),
                visual_style: str = Form(""), seed: str = Form(""),
                ref_images: list[UploadFile] = File(default=[]),
                ref_roles: list[str] = Form(default=[]), ref_handles: list[str] = Form(default=[]),
                saved_ref_keys: list[str] = Form(default=[]),
                user: str = Depends(require_login)):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError

    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, error="Phiên đã hết hạn — tải lại trang.",
                       jobs=_jobs_cua_toi(request), status_code=400)
    if not prompt.strip():
        return _render(request, user, error="Chưa nhập mô tả video.",
                       jobs=_jobs_cua_toi(request), status_code=400)
    mid, res, dur, asp = _clean(model, resolution, duration, aspect_ratio)
    try:
        fixed_seed = _clean_seed(seed)
    except ValueError as exc:
        return _render(request, user, error=str(exc), jobs=_jobs_cua_toi(request), status_code=400)
    try:
        n = max(1, min(int(count or 1), 2))
    except (TypeError, ValueError):
        n = 1
    u = user_hien_tai(request)
    if u is None:
        return _render(request, user, error="Cần đăng nhập bằng tài khoản người dùng.",
                       jobs=_jobs_cua_toi(request), status_code=400)

    try:
        saved_refs = _saved_refs_for_user(u.id, saved_ref_keys)
        new_count = sum(1 for f in (ref_images or [])
                        if f and getattr(f, "filename", ""))
        if len(saved_refs) + new_count > 4:
            raise ValueError(_t('Tổng tài sản đã lưu và file mới không được vượt quá 4.'))
        ref_specs = saved_refs + await _luu_refs(u.id, ref_images, ref_roles, ref_handles)
    except ValueError as exc:
        return _render(request, user, error=str(exc), jobs=_jobs_cua_toi(request), status_code=400)
    final_prompt = _compose_prompt(prompt, camera, motion, visual_style)
    base_params = {"prompt": final_prompt, "raw_prompt": prompt.strip()[:10000],
                   "camera": camera if camera in _CAMERA else "",
                   "motion": motion if motion in _MOTION else "",
                   "visual_style": visual_style if visual_style in _VISUAL_STYLE else "",
                   "model": mid, "resolution": res,
                   "duration": dur, "aspect_ratio": asp,
                   "generate_audio": bool(generate_audio), "owner_id": u.id,
                   "refs": ref_specs}
    gen = get_session(); db = next(gen)
    last_id = None
    try:
        try:
            for k in range(n):                      # ×N video (dedupe khác nhau theo idx)
                p = dict(base_params, _n=k)
                if fixed_seed is not None:
                    p["seed"] = (fixed_seed + k) % 2_147_483_648
                job = submit_with_credit(
                    db, user_id=u.id, app_slug=MANIFEST.slug,
                    job_type="taovideo.generate", params=p,
                    dedupe_key=dedupe_key_for("taovideo.generate", p))
                last_id = job.id
            db.commit()
        except (credit.ThieuCreditError, RegistryError) as exc:
            db.rollback()
            return _render(request, user, error=str(exc),
                           jobs=_jobs_cua_toi(request), status_code=400)
    finally:
        try: next(gen)
        except StopIteration: pass
    # Luôn về /taovideo (có player "Video của tôi") thay vì /jobs/{id} (chỉ JSON thô).
    return RedirectResponse("/taovideo", status_code=303)


def _owned_video_job(db, user_id: str, job_id: str):
    from platform_core.models import JOB_DONE, Job
    job = db.get(Job, job_id)
    if job is None or job.user_id != user_id or job.app_slug != MANIFEST.slug or job.status != JOB_DONE:
        return None
    if not (job.result or {}).get("video_key"):
        return None
    return job


@router.post("/upscale-quote")
def upscale_quote(request: Request, job_id: str = Form(""), target_height: str = Form("1080"),
                  preset: str = Form("fast"), user: str = Depends(require_login)):
    """Server-side quote for a completed, owned Seedance video; never trust browser price."""
    u = user_hien_tai(request)
    from platform_core.db import get_session
    from apps.upscalevideo import cost as upscale_cost
    gen = get_session(); db = next(gen)
    try:
        job = _owned_video_job(db, u.id if u else "", job_id)
        if job is None:
            return JSONResponse({"ok": False, "error": "Video không hợp lệ."}, status_code=404)
        try: height = int(target_height)
        except ValueError: height = 1080
        height = height if height in (1080, 1440, 2160) else 1080
        preset = preset if preset in ("fast", "quality") else "fast"
        duration = float((job.result or {}).get("duration") or (job.params or {}).get("duration") or 0)
        return {"ok": True, "job_id": job.id, "credit": upscale_cost.uoc_luong_credit(duration, height, preset),
                "duration_s": duration, "target_height": height, "preset": preset}
    finally:
        try: next(gen)
        except StopIteration: pass


@router.post("/upscale-confirm")
def upscale_confirm(request: Request, csrf_token: str = Form(...), job_id: str = Form(""),
                    target_height: str = Form("1080"), preset: str = Form("fast"),
                    codec: str = Form("h264"), user: str = Depends(require_login)):
    """Confirm the quoted action: submit exactly one shared Upscale job + credit hold."""
    if not verify_csrf_token(request, csrf_token):
        return JSONResponse({"ok": False, "error": "Phiên đã hết hạn."}, status_code=400)
    u = user_hien_tai(request)
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.registry import RegistryError
    from apps.upscalevideo.service import submit_upscale_job
    gen = get_session(); db = next(gen)
    try:
        source = _owned_video_job(db, u.id if u else "", job_id)
        if source is None:
            return JSONResponse({"ok": False, "error": "Video không hợp lệ."}, status_code=404)
        try: height = int(target_height)
        except ValueError: height = 1080
        duration = float((source.result or {}).get("duration") or
                         (source.params or {}).get("duration") or 0)
        output = submit_upscale_job(db, user_id=u.id,
                                    video_key=(source.result or {})["video_key"],
                                    preset=preset, target_height=height, codec=codec,
                                    duration_s=duration)
        db.commit()
        return {"ok": True, "upscale_job_id": output.id, "redirect": f"/jobs/{output.id}"}
    except (credit.ThieuCreditError, RegistryError) as exc:
        db.rollback()
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("/v/{key:path}")
def video(request: Request, key: str, user: str = Depends(require_login)):
    """Serve video theo HTTP Range (né trần 100MB CF). Chỉ chủ sở hữu."""
    from fastapi import HTTPException
    from platform_core.storage import StorageError, get_storage

    u = user_hien_tai(request)
    segs = key.split("/")
    if len(segs) < 2 or segs[0] != "taovideo" or u is None or segs[1] != u.id:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy video.'))
    storage = get_storage()
    # R2 (H10): trả presigned URL → trình duyệt tải THẲNG từ R2, né trần 100MB.
    direct = storage.try_url_for(key)
    if direct:
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
        f = storage.open(key)
        try:
            f.seek(start)
            chunk = f.read(length)
        finally:
            f.close()
        return Response(content=chunk, status_code=206, media_type="video/mp4",
                        headers={"Content-Range": f"bytes {start}-{end}/{total}",
                                 "Accept-Ranges": "bytes",
                                 "Content-Length": str(len(chunk))})
    return StreamingResponse(storage.open(key), media_type="video/mp4",
                             headers={"Accept-Ranges": "bytes",
                                      "Content-Length": str(total)})
