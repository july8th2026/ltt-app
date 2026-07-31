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

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["jobs"])


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


@router.get("/jobs", response_class=HTMLResponse)
def danh_sach(request: Request, user: str = Depends(require_login)):
    u = user_hien_tai(request)
    jobs_list = []
    so_du = 0
    if u is not None:
        from platform_core import credit
        from platform_core.db import get_session
        from platform_core.models import Job
        from sqlalchemy import select
        gen = get_session(); db = next(gen)
        try:
            jobs_list = db.execute(
                select(Job).where(Job.user_id == u.id)
                .order_by(Job.created_at.desc()).limit(50)
            ).scalars().all()
            so_du = credit.so_du(db, u.id)
            for j in jobs_list:
                db.expunge(j)
        finally:
            try: next(gen)
            except StopIteration: pass

    return templates.TemplateResponse(request, "jobs.html", {
        "user": user, "nav": "jobs", "jobs": jobs_list,
        "so_du": so_du, "co_user_csdl": u is not None,
    })


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def chi_tiet(request: Request, job_id: str, user: str = Depends(require_login)):
    _u, job = _job_cua_user(request, job_id)
    if job is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    return templates.TemplateResponse(request, "job_detail.html", {
        "user": user, "nav": "jobs", "job": job,
    })


@router.get("/jobs/{job_id}/progress", response_class=HTMLResponse)
def tien_do(request: Request, job_id: str, user: str = Depends(require_login)):
    """Mẩu HTML cho HTMX poll. Trả trạng thái + tiến độ hiện tại của job."""
    _u, job = _job_cua_user(request, job_id)
    if job is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    return templates.TemplateResponse(request, "_job_progress.html", {"job": job})
