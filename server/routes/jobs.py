"""
jobs.py — trang job của người dùng: danh sách, chi tiết, tiến độ (H2.3).

Tiến độ đẩy về trình duyệt bằng HTMX (Q18): trang chi tiết poll
`/jobs/{id}/progress` mỗi 2 giây, server trả về một mẩu HTML, trang tự thay chỗ.
Không JavaScript tự viết, mọi logic ở máy chủ.

Cách ly người dùng: mọi truy vấn job **lọc theo user_id của người đang đăng
nhập**. Xem job của người khác → 404 (không xác nhận job tồn tại). Đây là bất
biến "A không đọc được job của B", có test.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import copy
import mimetypes
import os
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import require_operator, user_hien_tai
from server.templating import templates

router = APIRouter(tags=["jobs"])

_STATUSES = {"queued", "running", "done", "error", "cancelled"}


def _artifacts(result: dict | None) -> list[dict]:
    """Turn owned result keys into opaque, indexed downloads; never expose params."""
    found: list[dict] = []

    def visit(value, label="result"):
        if len(found) >= 20:
            return
        if isinstance(value, dict):
            for name, child in value.items():
                if isinstance(child, str) and name.endswith("_key") and child:
                    found.append({"label": name.removesuffix("_key").replace("_", " "), "key": child})
                elif name.endswith("_keys") and isinstance(child, list):
                    for index, key in enumerate(child):
                        if isinstance(key, str) and key and len(found) < 20:
                            found.append({"label": f"{name.removesuffix('_keys').replace('_', ' ')} {index + 1}", "key": key})
                elif isinstance(child, (dict, list)):
                    visit(child, name)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, (dict, list)):
                    visit(child, label)

    visit(result or {})
    return found


def _job_cua_user(request: Request, job_id: str):
    """Lấy job nếu thuộc về người đang đăng nhập, ngược lại None."""
    u = user_hien_tai(request)
    if u is None:
        return None, None
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); db = next(gen)
    try:
        job = db.get(Job, job_id)
        if job is None or job.user_id != u.id:
            return u, None
        # Tách khỏi session để dùng sau khi đóng (đọc thuần).
        db.expunge(job)
        return u, job
    finally:
        try: next(gen)
        except StopIteration: pass


def _events_cua_job(job_id: str, *, include_internal: bool = False):
    from platform_core import job_events
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        rows = job_events.timeline(db, job_id, include_internal=include_internal)
        for row in rows:
            db.expunge(row)
        return rows
    finally:
        try: next(gen)
        except StopIteration: pass


def _lineage_cua_user(user_id: str, job):
    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        ids = [job.retry_of_id] if job.retry_of_id else []
        children = db.execute(select(Job).where(
            Job.user_id == user_id, Job.retry_of_id == job.id,
        ).order_by(Job.created_at)).scalars().all()
        if ids:
            parent = db.get(Job, ids[0])
            parent = parent if parent is not None and parent.user_id == user_id else None
        else:
            parent = None
        rows = ([parent] if parent else []) + list(children)
        for row in rows:
            db.expunge(row)
        return parent, list(children)
    finally:
        try: next(gen)
        except StopIteration: pass


def _parse_date(value: str, *, end: bool = False):
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return datetime.combine(parsed, time.max if end else time.min, tzinfo=timezone.utc)


@router.get("/jobs", response_class=HTMLResponse)
def danh_sach(request: Request, status: str = Query(""), app: str = Query(""),
               date_from: str = Query(""), date_to: str = Query(""),
               cursor: str = Query(""), user: str = Depends(require_login)):
    u = user_hien_tai(request)
    jobs_list = []
    so_du = 0
    if u is not None:
        from platform_core import credit
        from platform_core.db import get_session
        from platform_core.models import Job
        from sqlalchemy import distinct, select
        gen = get_session(); db = next(gen)
        try:
            stmt = select(Job).where(Job.user_id == u.id)
            if status in _STATUSES:
                stmt = stmt.where(Job.status == status)
            if app:
                stmt = stmt.where(Job.app_slug == app[:64])
            start = _parse_date(date_from)
            end = _parse_date(date_to, end=True)
            if start:
                stmt = stmt.where(Job.created_at >= start)
            if end:
                stmt = stmt.where(Job.created_at <= end)
            if cursor:
                anchor = db.get(Job, cursor[:36])
                if anchor is not None and anchor.user_id == u.id:
                    stmt = stmt.where(Job.created_at < anchor.created_at)
            rows = db.execute(stmt.order_by(Job.created_at.desc()).limit(51)).scalars().all()
            jobs_list = rows[:50]
            next_cursor = jobs_list[-1].id if len(rows) > 50 and jobs_list else ""
            app_options = list(db.execute(
                select(distinct(Job.app_slug)).where(Job.user_id == u.id)
                .order_by(Job.app_slug)
            ).scalars().all())
            so_du = credit.so_du(db, u.id)
            for j in jobs_list:
                db.expunge(j)
        finally:
            try: next(gen)
            except StopIteration: pass

    return templates.TemplateResponse(request, "jobs.html", {
        "user": user, "nav": "jobs", "jobs": jobs_list,
        "so_du": so_du, "co_user_csdl": u is not None,
        "status_filter": status if status in _STATUSES else "", "app_filter": app[:64],
        "date_from": date_from if _parse_date(date_from) else "",
        "date_to": date_to if _parse_date(date_to, end=True) else "",
        "app_options": locals().get("app_options", []),
        "next_cursor": locals().get("next_cursor", ""),
    })


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def chi_tiet(request: Request, job_id: str, user: str = Depends(require_login)):
    current, job = _job_cua_user(request, job_id)
    if job is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
    retry_parent, retry_children = _lineage_cua_user(current.id, job)
    return templates.TemplateResponse(request, "job_detail.html", {
        "user": user, "nav": "jobs", "job": job, "artifacts": _artifacts(job.result),
        "events": _events_cua_job(job.id),
        "retry_parent": retry_parent, "retry_children": retry_children,
        "csrf_token": issue_csrf_token(request),
    })


@router.get("/jobs/{job_id}/progress", response_class=HTMLResponse)
def tien_do(request: Request, job_id: str, user: str = Depends(require_login)):
    """Mẩu HTML cho HTMX poll. Trả trạng thái + tiến độ hiện tại của job."""
    _u, job = _job_cua_user(request, job_id)
    if job is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
    return templates.TemplateResponse(request, "_job_progress.html", {
        "job": job, "events": _events_cua_job(job.id),
    })


@router.get("/api/jobs")
def jobs_api(request: Request, status: str = Query(""), app: str = Query(""),
             date_from: str = Query(""), date_to: str = Query(""),
             cursor: str = Query(""), limit: int = Query(30, ge=1, le=100),
             _user: str = Depends(require_login)):
    """Contract History dùng chung cho các tool; không trả params/result/error."""
    current = user_hien_tai(request)
    if current is None:
        return {"items": [], "next_cursor": ""}
    from platform_core import job_history
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        rows, next_cursor = job_history.list_owned(
            db, current.id, app_slug=app, status=status,
            start=_parse_date(date_from), end=_parse_date(date_to, end=True),
            cursor=cursor, limit=limit,
        )
        return {"items": [job_history.customer_payload(db, row) for row in rows],
                "next_cursor": next_cursor}
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("/api/jobs/{job_id}")
def job_api(request: Request, job_id: str, _user: str = Depends(require_login)):
    current = user_hien_tai(request)
    if current is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
    from platform_core import job_history
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        job = job_history.get_owned(db, current.id, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
        return job_history.customer_payload(db, job, with_events=True)
    finally:
        try: next(gen)
        except StopIteration: pass


@router.post("/jobs/{job_id}/cancel")
def huy_job(request: Request, job_id: str, csrf_token: str = Form(""),
            user: str = Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))
    u = user_hien_tai(request)
    from platform_core import credit, jobs
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); db = next(gen)
    try:
        job = db.get(Job, job_id)
        if job is None or u is None or job.user_id != u.id:
            raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
        if jobs.cancel(db, job):
            credit.hoan(db, u.id, job.id)
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@router.post("/jobs/{job_id}/retry")
def thu_lai_job(request: Request, job_id: str, csrf_token: str = Form(""),
                user: str = Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))
    u = user_hien_tai(request)
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.models import Job
    from platform_core.registry import RegistryError
    gen = get_session(); db = next(gen)
    try:
        old = db.get(Job, job_id)
        if old is None or u is None or old.user_id != u.id:
            raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
        if old.status not in {"error", "cancelled"}:
            raise HTTPException(status_code=409, detail=_t('Chỉ thử lại job đã lỗi hoặc đã hủy.'))
        params = copy.deepcopy(old.params or {})
        try:
            new_job = submit_with_credit(
                db, user_id=u.id, app_slug=old.app_slug, job_type=old.job_type,
                params=params, dedupe_key=dedupe_key_for(old.job_type, params),
                max_attempts=old.max_attempts,
                correlation_id=getattr(request.state, "correlation_id", ""),
                retry_of_id=old.id)
            db.commit()
        except (credit.ThieuCreditError, RegistryError, ValueError) as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        new_id = new_job.id
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse(f"/jobs/{new_id}", status_code=303)


@router.get("/ops/jobs/{job_id}/events")
def debug_events(request: Request, job_id: str,
                 _operator: str = Depends(require_operator)):
    """Log kỹ thuật đã lọc bí mật; chỉ operator/support được đọc."""
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); db = next(gen)
    try:
        job = db.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
        rows = _events_cua_job(job.id, include_internal=True)
        return {
            "job_id": job.id,
            "correlation_id": job.correlation_id,
            "events": [{
                "sequence": row.sequence, "code": row.event_code,
                "level": row.level, "visibility": row.visibility,
                "message": row.public_message, "details": row.details,
                "created_at": row.created_at,
            } for row in rows],
        }
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("/ops/jobs/{job_id}/support-export")
def support_export(request: Request, job_id: str,
                   _operator: str = Depends(require_operator)):
    """Tải gói debug đã lọc; không xuất payload, lỗi thô, PII hay ledger note."""
    from platform_core import job_history
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); db = next(gen)
    try:
        job = db.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
        payload = job_history.support_payload(db, job)
        return JSONResponse(
            content=jsonable_encoder(payload),
            headers={"Content-Disposition":
                     f'attachment; filename="ltt-support-{job.id[:8]}.json"'},
        )
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("/ops/jobs-retention")
def jobs_retention(_request: Request,
                   _operator: str = Depends(require_operator)):
    """Dry-run retention cho operator; endpoint này tuyệt đối không xóa dữ liệu."""
    from platform_core import job_events
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        return job_events.retention_report(db)
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("/ops/jobs-metrics")
def jobs_metrics(_request: Request, _operator: str = Depends(require_operator)):
    from platform_core import job_metrics
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        metrics = job_metrics.snapshot(db)
        return {"metrics": metrics, "alerts": job_metrics.alerts(metrics)}
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("/jobs/{job_id}/artifacts/{index}")
def tai_artifact(request: Request, job_id: str, index: int,
                 user: str = Depends(require_login)):
    _u, job = _job_cua_user(request, job_id)
    artifacts = _artifacts(job.result if job else None)
    if job is None or index < 0 or index >= len(artifacts):
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy tệp kết quả.'))
    key = artifacts[index]["key"]
    from platform_core.storage import StorageError, get_storage
    storage = get_storage()
    direct = storage.try_url_for(key)
    if direct:
        return RedirectResponse(direct, status_code=302)
    try:
        stream = storage.open(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail=_t('Tệp kết quả không còn tồn tại.'))

    def chunks():
        try:
            while data := stream.read(1024 * 1024):
                yield data
        finally:
            stream.close()

    raw_name = os.path.basename(key)
    filename = "".join(ch for ch in raw_name if ch.isalnum() or ch in "._-")[:180]
    filename = filename or f"artifact-{index + 1}"
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return StreamingResponse(chunks(), media_type=media_type,
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
