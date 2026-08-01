"""
UI app `image` (di trú A1). Prompt tự do → ảnh. Router KHÔNG tự viết prefix.

Ảnh output phục vụ qua `/f/{key}` (kiểm sở hữu theo key `image/{owner_id}/...`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
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
            status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, "image.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "aspects": _ASPECTS, "models": _models(), "error": error, "jobs": jobs or [],
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
        return [{"id": j.id, "status": j.status, "progress": j.progress,
                 "error": j.error,
                 "image_keys": (j.result or {}).get("image_keys", []) if j.result else []}
                for j in rows]
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("", response_class=HTMLResponse)
def page(request: Request, user: str = Depends(require_login)):
    return _render(request, user, jobs=_jobs_cua_toi(request))


@router.post("/queue", response_class=HTMLResponse)
def queue(
    request: Request,
    csrf_token: str = Form(...),
    prompt: str = Form(""),
    model: str = Form(""),
    aspect_ratio: str = Form("16:9"),
    count: int = Form(1),
    user: str = Depends(require_login),
):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError

    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, error="Phiên đã hết hạn — tải lại trang.",
                       jobs=_jobs_cua_toi(request), status_code=400)
    if not prompt.strip():
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

    params = {"prompt": prompt.strip(), "model": model,
              "aspect_ratio": aspect_ratio, "count": count, "owner_id": u.id}
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
            return _render(request, user, error=str(exc),
                           jobs=_jobs_cua_toi(request), status_code=400)
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@router.get("/f/{key:path}", response_class=StreamingResponse)
def image_file(request: Request, key: str, user: str = Depends(require_login)):
    from fastapi import HTTPException
    from platform_core.storage import StorageError, get_storage
    u = user_hien_tai(request)
    segs = key.split("/")
    if len(segs) < 2 or segs[0] != "taoanh" or u is None or segs[1] != u.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    try:
        stream = get_storage().open(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    return StreamingResponse(stream, media_type="image/png")
