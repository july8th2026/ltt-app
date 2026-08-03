"""
UI app `script` (di trú A1). Đầu ra VĂN BẢN → luồng: form → /r/{job_id} (HTMX
poll trạng thái, render kịch bản khi xong). Router KHÔNG tự viết prefix.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select

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
        project = None
        from platform_core.models import APP_PROJECT_ACTIVE, AppProject
        projects = db.execute(select(AppProject).where(
            AppProject.user_id == u.id, AppProject.app_slug == MANIFEST.slug,
            AppProject.status == APP_PROJECT_ACTIVE
        ).order_by(AppProject.updated_at.desc()).limit(60)).scalars().all()
        row = next((x for x in projects
                    if (x.payload or {}).get("source_job_id") == j.id), None)
        if row:
            project = {"id": row.id, "revision": row.revision,
                       "payload": row.payload or {}}
        return {"id": j.id, "status": j.status, "progress": j.progress,
                "error": j.error,
                "script": ((project or {}).get("payload") or {}).get("script") or
                          ((j.result or {}).get("script") if j.result else None),
                "shot_list": ((project or {}).get("payload") or {}).get("shot_list") or
                             ((j.result or {}).get("shot_list") if j.result else []),
                "sources": ((project or {}).get("payload") or {}).get("sources") or
                           str((j.params or {}).get("sources") or ""),
                "research": ((project or {}).get("payload") or {}).get("research") or
                            str((j.params or {}).get("research") or ""),
                "project": project}
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
    sources: str = Form(""),
    research: str = Form(""),
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
              "language": _clean("ngon_ngu", language), "owner_id": u.id,
              "sources": sources.strip()[:8000], "research": research.strip()[:8000]}
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
        "csrf_token": issue_csrf_token(request),
    })


@router.get("/r/{job_id}/status", response_class=HTMLResponse)
def result_status(request: Request, job_id: str, user: str = Depends(require_login)):
    job = _lay_job(request, job_id)
    if job is None:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse(request, "_script_view.html", {
        "app": MANIFEST, "job": job, "csrf_token": issue_csrf_token(request),
    })


@router.post("/r/{job_id}/save")
def save_version(request: Request, job_id: str, csrf_token: str = Form(...),
                 script_json: str = Form("{}"), project_id: str = Form(""),
                 revision: int = Form(0), sources: str = Form(""),
                 research: str = Form(""), user: str = Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return JSONResponse({"ok": False, "error": "Phiên hết hạn."}, status_code=400)
    job = _lay_job(request, job_id)
    if job is None or job["status"] != "done":
        return JSONResponse({"ok": False, "error": "Không tìm thấy kịch bản."}, status_code=404)
    import json
    try:
        script = json.loads(script_json)
        if not isinstance(script, dict):
            raise ValueError
    except (ValueError, TypeError):
        return JSONResponse({"ok": False, "error": "Dữ liệu editor không hợp lệ."},
                            status_code=400)
    from apps.kichban.features import project_payload
    from platform_core import app_projects
    from platform_core.db import get_session
    u = user_hien_tai(request); gen = get_session(); db = next(gen)
    try:
        payload = project_payload(job_id=job_id, script=script,
                                  sources=sources, research=research)
        if project_id:
            current = app_projects.get_owned(db, project_id, u.id, MANIFEST.slug)
            if (current.payload or {}).get("source_job_id") != job_id:
                raise app_projects.ProjectNotFound("Không tìm thấy project.")
            row = app_projects.save(db, project_id=project_id, user_id=u.id,
                                    app_slug=MANIFEST.slug, revision=revision,
                                    name=str(script.get("title") or "Kịch bản"),
                                    schema_version=1, payload=payload)
        else:
            row = app_projects.create(db, user_id=u.id, app_slug=MANIFEST.slug,
                                      name=str(script.get("title") or "Kịch bản"),
                                      schema_version=1, payload=payload)
        db.commit(); result = {"ok": True, "project_id": row.id,
                               "revision": row.revision,
                               "shot_list": (row.payload or {}).get("shot_list", [])}
    except app_projects.ProjectError as exc:
        db.rollback(); return JSONResponse({"ok": False, "error": str(exc)}, status_code=409)
    finally:
        try: next(gen)
        except StopIteration: pass
    return JSONResponse(result)
