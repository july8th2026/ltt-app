"""
UI app `image` (di trú A1). Prompt tự do → ảnh. Router KHÔNG tự viết prefix.

Ảnh output phục vụ qua `/f/{key}` (kiểm sở hữu theo key `image/{owner_id}/...`).
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from apps.taoanh.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["image"])

_ASPECTS = ("16:9", "9:16", "1:1", "4:3", "3:4")


def _models() -> list:
    from platform_core import providers
    from platform_core.models import APIKEY_CAT_IMAGE
    return [(m.id, m.label())
            for m in providers.models_for("gemini", category=APIKEY_CAT_IMAGE)
            if m.is_active]


def _render(request: Request, user: str, *, error: str = "", jobs=None,
            form_values: dict | None = None, status_code: int = 200) -> HTMLResponse:
    from apps.taoanh.features import EDIT_MODES
    from apps.taoanh.manifest import MODEL_CREDIT_PER_IMAGE
    return templates.TemplateResponse(request, "image.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "aspects": _ASPECTS, "models": _models(), "error": error, "jobs": jobs or [],
        "edit_modes": EDIT_MODES, "form_values": form_values or {},
        "model_costs": MODEL_CREDIT_PER_IMAGE,
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
        def safe_count(value) -> int:
            try:
                return max(1, min(4, int(value or 1)))
            except (TypeError, ValueError):
                return 1
        rows = db.execute(
            select(Job).where(Job.user_id == u.id, Job.app_slug == MANIFEST.slug)
            .order_by(Job.created_at.desc()).limit(12)
        ).scalars().all()
        return [{"id": j.id, "status": j.status, "progress": j.progress,
                 "progress_msg": j.progress_msg, "error": j.error,
                 "created_at": j.created_at, "finished_at": j.finished_at,
                 "prompt": str((j.params or {}).get("prompt", ""))[:240],
                 "aspect_ratio": str((j.params or {}).get("aspect_ratio", "16:9")),
                 "requested_count": safe_count((j.params or {}).get("count", 1)),
                 "model": str((j.params or {}).get("model", ""))[:100],
                 "edit_mode": str((j.params or {}).get("edit_mode", "generate")),
                 "image_keys": (j.result or {}).get("image_keys", []) if j.result else []}
                for j in rows]
    finally:
        try: next(gen)
        except StopIteration: pass


def _owned_output(user_id: str, key: str) -> bool:
    if not key.startswith(f"taoanh/{user_id}/"):
        return False
    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, Job
    from platform_core.storage import get_storage
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        results = db.execute(select(Job.result).where(
            Job.user_id == user_id, Job.app_slug == MANIFEST.slug,
            Job.status == JOB_DONE
        ).order_by(Job.created_at.desc()).limit(60)).scalars().all()
        return (any(key in ((result or {}).get("image_keys") or []) for result in results)
                and get_storage().exists(key))
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("", response_class=HTMLResponse)
def page(request: Request, user: str = Depends(require_login)):
    return _render(request, user, jobs=_jobs_cua_toi(request))


@router.post("/queue", response_class=HTMLResponse)
async def queue(
    request: Request,
    csrf_token: str = Form(...),
    prompt: str = Form(""),
    model: str = Form(""),
    aspect_ratio: str = Form("16:9"),
    count: int = Form(1),
    edit_mode: str = Form("generate"),
    source_image: UploadFile | None = File(None),
    style_image: UploadFile | None = File(None),
    saved_source_key: str = Form(""),
    user: str = Depends(require_login),
):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError

    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, error="Phiên đã hết hạn — tải lại trang.",
                       jobs=_jobs_cua_toi(request), status_code=400)
    from apps.taoanh.features import clean_mode, validate_reference
    edit_mode = clean_mode(edit_mode)
    prompt = prompt.strip()[:4000]      # cap do dai (nguon gemini_image cap 4000) — chong phi credit + 400 upstream
    if not prompt:
        return _render(request, user, error="Chưa nhập mô tả ảnh.",
                       jobs=_jobs_cua_toi(request), status_code=400)
    if aspect_ratio not in _ASPECTS:
        aspect_ratio = "16:9"
    count = max(1, min(int(count or 1), 4))
    model_ids = [m[0] for m in _models()]
    if model not in model_ids:
        model = model_ids[0] if model_ids else "gemini-2.5-flash-image"

    u = user_hien_tai(request)
    if u is None:
        return _render(request, user, error="Cần đăng nhập bằng tài khoản người dùng.",
                       jobs=_jobs_cua_toi(request), status_code=400)

    references: list[dict] = []
    uploaded_keys: list[str] = []
    if saved_source_key:
        if not _owned_output(u.id, saved_source_key):
            return _render(request, user, error="Ảnh nguồn đã lưu không hợp lệ.",
                           jobs=_jobs_cua_toi(request), status_code=400)
        references.append({"key": saved_source_key, "mime": "image/png", "role": "source"})
    from platform_core.storage import get_storage
    storage = get_storage()
    for upload, role in ((source_image, "source"), (style_image, "style")):
        if upload and upload.filename:
            data = await upload.read()
            try:
                mime, _dimensions = validate_reference(data, upload.content_type or "")
            except ValueError as exc:
                for key in uploaded_keys:
                    storage.delete(key)
                return _render(request, user, error=str(exc), jobs=_jobs_cua_toi(request),
                               status_code=400)
            import io, uuid
            key = f"taoanh/{u.id}/refs/{uuid.uuid4().hex}"
            storage.put(key, io.BytesIO(data), content_type=mime)
            uploaded_keys.append(key)
            references = [r for r in references if r["role"] != role]
            references.append({"key": key, "mime": mime, "role": role})
    if edit_mode != "generate" and not any(r["role"] == "source" for r in references):
        for key in uploaded_keys:
            storage.delete(key)
        return _render(request, user, error="Chế độ chỉnh sửa cần ảnh nguồn.",
                       jobs=_jobs_cua_toi(request), status_code=400)
    if edit_mode == "style_transfer" and not any(r["role"] == "style" for r in references):
        for key in uploaded_keys:
            storage.delete(key)
        return _render(request, user, error="Chuyển phong cách cần thêm ảnh phong cách.",
                       jobs=_jobs_cua_toi(request), status_code=400)

    params = {"prompt": prompt, "model": model,
              "aspect_ratio": aspect_ratio, "count": count, "owner_id": u.id,
              "edit_mode": edit_mode, "references": references}
    gen = get_session(); db = next(gen)
    try:
        try:
            job = submit_with_credit(
                db, user_id=u.id, app_slug=MANIFEST.slug,
                job_type="taoanh.generate", params=params,
                dedupe_key=dedupe_key_for("taoanh.generate", params))
            db.commit(); job_id = job.id
        except (credit.ThieuCreditError, RegistryError) as exc:
            db.rollback()
            for key in uploaded_keys:
                storage.delete(key)
            return _render(request, user, error=str(exc),
                           jobs=_jobs_cua_toi(request), status_code=400)
    finally:
        try: next(gen)
        except StopIteration: pass
    # Ve trang app (co luoi "Anh cua toi") thay vi /jobs/{id} (chi hien JSON tho).
    return RedirectResponse(MANIFEST.route_prefix, status_code=303)


@router.get("/edit/{job_id}/{image_index}", response_class=HTMLResponse)
def edit_output(request: Request, job_id: str, image_index: int,
                user: str = Depends(require_login)):
    """Nạp output thật làm ảnh nguồn; chỉ chủ sở hữu job DONE truy cập được."""
    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, Job
    from sqlalchemy import select
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy ảnh.'))
    gen = get_session(); db = next(gen)
    try:
        job = db.execute(select(Job).where(
            Job.id == job_id, Job.user_id == u.id, Job.app_slug == MANIFEST.slug,
            Job.status == JOB_DONE)).scalar_one_or_none()
        keys = ((job.result or {}).get("image_keys") or []) if job else []
        if image_index < 0 or image_index >= len(keys) or not _owned_output(u.id, keys[image_index]):
            raise HTTPException(status_code=404, detail=_t('Không tìm thấy ảnh.'))
        values = {"prompt": str((job.params or {}).get("prompt") or ""),
                  "model": str((job.params or {}).get("model") or ""),
                  "aspect_ratio": str((job.params or {}).get("aspect_ratio") or "16:9"),
                  "edit_mode": "edit", "saved_source_key": keys[image_index]}
    finally:
        try: next(gen)
        except StopIteration: pass
    return _render(request, user, jobs=_jobs_cua_toi(request), form_values=values)


@router.get("/f/{key:path}", response_class=StreamingResponse)
def image_file(request: Request, key: str, user: str = Depends(require_login)):
    from fastapi import HTTPException
    from platform_core.storage import StorageError, get_storage
    u = user_hien_tai(request)
    segs = key.split("/")
    if len(segs) < 2 or segs[0] != "taoanh" or u is None or segs[1] != u.id:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy ảnh.'))
    storage = get_storage()
    direct = storage.try_url_for(key)            # R2 (H10) → tải thẳng CDN
    if direct:
        return RedirectResponse(direct, status_code=302)
    try:
        stream = storage.open(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy ảnh.'))
    return StreamingResponse(stream, media_type="image/png")
