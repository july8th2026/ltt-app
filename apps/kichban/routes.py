"""
UI app `script` (di trú A1). Đầu ra VĂN BẢN → luồng: form → /r/{job_id} (HTMX
poll trạng thái, render kịch bản khi xong). Router KHÔNG tự viết prefix.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from apps.kichban.jobs import _PROMPTS_DIR
from apps.kichban.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["script"])

_GROUPS = ("do_dai_video", "giong_van", "doi_tuong", "ngon_ngu")


def _catalog() -> dict:
    from platform_core import prompt_fragments as pf
    return {g: pf.options(_PROMPTS_DIR, g) for g in _GROUPS}


def _defaults() -> dict:
    from platform_core import prompt_fragments as pf
    return {g: pf.default_option(_PROMPTS_DIR, g) for g in _GROUPS}


def _clean(group: str, value: str) -> str:
    from platform_core import prompt_fragments as pf
    labels = pf.load_labels(_PROMPTS_DIR, group)
    return value if value in labels else pf.default_option(_PROMPTS_DIR, group)


def _render(request: Request, user: str, *, error: str = "", status_code: int = 200):
    return templates.TemplateResponse(request, "script.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "catalog": _catalog(), "defaults": _defaults(), "error": error,
        "jobs": _jobs_cua_toi(request),
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
        rows = db.execute(select(Job).where(
            Job.user_id == u.id, Job.app_slug == MANIFEST.slug
        ).order_by(Job.created_at.desc()).limit(12)).scalars().all()
        return [{"id": j.id, "status": j.status, "progress": j.progress,
                 "topic": str((j.params or {}).get("topic") or "")[:120],
                 "created_at": j.created_at,
                 "title": str(((j.result or {}).get("script") or {}).get("title") or "")[:160]}
                for j in rows]
    finally:
        try: next(gen)
        except StopIteration: pass


def _lay_job(request: Request, job_id: str):
    u = user_hien_tai(request)
    if u is None:
        return None
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); db = next(gen)
    try:
        j = db.get(Job, job_id)
        if j is None or j.user_id != u.id or j.app_slug != MANIFEST.slug:
            return None
        return {"id": j.id, "status": j.status, "progress": j.progress,
                "error": j.error,
                "script": (j.result or {}).get("script") if j.result else None}
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("", response_class=HTMLResponse)
def page(request: Request, user: str = Depends(require_login)):
    return _render(request, user)


@router.post("/queue", response_class=HTMLResponse)
def queue(
    request: Request,
    csrf_token: str = Form(...),
    topic: str = Form(""),
    duration: str = Form(""),
    tone: str = Form(""),
    audience: str = Form(""),
    language: str = Form(""),
    user: str = Depends(require_login),
):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError

    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, error="Phiên đã hết hạn — tải lại trang.", status_code=400)
    if len(topic.strip()) < 3:
        return _render(request, user, error="Chủ đề tối thiểu 3 ký tự.", status_code=400)

    u = user_hien_tai(request)
    if u is None:
        return _render(request, user, error="Cần đăng nhập bằng tài khoản người dùng.", status_code=400)

    params = {"topic": topic.strip()[:500],
              "duration": _clean("do_dai_video", duration),
              "tone": _clean("giong_van", tone),
              "audience": _clean("doi_tuong", audience),
              "language": _clean("ngon_ngu", language), "owner_id": u.id}
    gen = get_session(); db = next(gen)
    try:
        try:
            job = submit_with_credit(
                db, user_id=u.id, app_slug=MANIFEST.slug,
                job_type="kichban.generate", params=params,
                dedupe_key=dedupe_key_for("kichban.generate", params))
            db.commit(); job_id = job.id
        except (credit.ThieuCreditError, RegistryError) as exc:
            db.rollback()
            return _render(request, user, error=str(exc), status_code=400)
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse(f"{MANIFEST.route_prefix}/r/{job_id}", status_code=303)


@router.get("/r/{job_id}", response_class=HTMLResponse)
def result(request: Request, job_id: str, user: str = Depends(require_login)):
    job = _lay_job(request, job_id)
    if job is None:
        return HTMLResponse("Không thấy kịch bản.", status_code=404)
    return templates.TemplateResponse(request, "script_result.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST, "job": job,
    })


@router.get("/r/{job_id}/status", response_class=HTMLResponse)
def result_status(request: Request, job_id: str, user: str = Depends(require_login)):
    job = _lay_job(request, job_id)
    if job is None:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse(request, "_script_view.html", {
        "app": MANIFEST, "job": job,
    })
