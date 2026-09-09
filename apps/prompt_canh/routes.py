"""HTTP của App `prompt_canh` — CHỈ HTTP. Nghiệp vụ ở `services/kich_ban.py`.

## ⚠️ Cửa số dư ở đây là một ĐIỀU KIỆN, không phải một GIÁ

`credit_cost` của App này là **0**, vì `runtime_noi_bo` đã thu theo từng lượt
model (xem `manifest.py`). Nhưng 0 nghĩa là job vào hàng đợi mà **không giữ
chỗ**: một tài khoản 0 credit vẫn nộp được, worker vẫn chạy, rồi lượt model đầu
tiên trả `ThieuCredit` — khách chờ vô ích và máy chủ làm không công.

⇒ Chặn ở **trước khi nộp**, bằng một phép so số dư. Nó không ghi bút toán nào,
  nên nó không tính hai lần thứ gì.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.templating import templates

from .manifest import MANIFEST
from .services import kich_ban

log = logging.getLogger("apps.prompt_canh.routes")

router = APIRouter(tags=["prompt_canh"])

#: Số dư tối thiểu để được nộp. Một ước trần THÔ, cố ý thô: nó chỉ chặn trường
#: hợp "gần như không có credit", không thay cho kế toán thật ở tầng dưới.
SO_DU_TOI_THIEU = 10


def _jobs_cua_toi(user: str) -> list:
    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select

    gen = get_session()
    db = next(gen)
    try:
        return list(db.execute(
            select(Job).where(Job.user_id == user, Job.job_type == "prompt_canh.run")
            .order_by(Job.created_at.desc()).limit(20)).scalars())
    finally:
        db.close()


def _trang(request: Request, user: str, *, loi: str = "",
           status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, "prompt_canh.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "loi": loi, "jobs": _jobs_cua_toi(user),
    }, status_code=status_code)


@router.get("/", response_class=HTMLResponse)
def page(request: Request, user: str = Depends(require_login)):
    return _trang(request, user)


@router.post("/tao")
def queue(
    request: Request,
    csrf_token: str = Form(...),
    kich_ban_van: str = Form(..., alias="kich_ban"),
    so_canh: int = Form(20),
    batch_step2: int = Form(10),
    batch_step3: int = Form(5),
    visual_style: str = Form(""),
    duration: str = Form(""),
    user: str = Depends(require_login),
):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit

    if not verify_csrf_token(request, csrf_token):
        return _trang(request, user, loi="Phiên đã hết hạn — tải lại trang.",
                      status_code=400)

    tham_so = {"kich_ban": kich_ban_van, "so_canh": so_canh,
               "batch_step2": batch_step2, "batch_step3": batch_step3,
               "visual_style": visual_style, "duration": duration,
               "owner_id": user}
    try:
        kich_ban.chuan_hoa(tham_so)
    except kich_ban.LoiKichBan as e:
        return _trang(request, user, loi=str(e), status_code=400)

    gen = get_session()
    db = next(gen)
    try:
        if credit.so_du(db, user) < SO_DU_TOI_THIEU:
            return _trang(request, user, status_code=402,
                          loi=("Số dư quá thấp để bắt đầu. Mỗi lượt model được "
                               "tính riêng khi chạy."))
        job = submit_with_credit(
            db, user_id=user, app_slug="prompt_canh", job_type="prompt_canh.run",
            params=tham_so, dedupe_key=dedupe_key_for("prompt_canh.run", tham_so))
        db.commit()
    except credit.ThieuCreditError as e:
        db.rollback()
        return _trang(request, user, loi=str(e), status_code=402)
    finally:
        db.close()

    return JSONResponse({"job_id": job.id}, status_code=202)


@router.get("/ket-qua/{job_id}")
def ket_qua(job_id: str, user: str = Depends(require_login)):
    """Job của người khác trả **404**, không phải 403 — 403 xác nhận rằng job ấy
    tồn tại, và đó là một rò rỉ nhỏ nhưng có thật."""
    from platform_core.db import get_session
    from platform_core.models import Job

    gen = get_session()
    db = next(gen)
    try:
        job = db.get(Job, job_id)
        if job is None or job.user_id != user:
            return JSONResponse({"error": "khong tim thay"}, status_code=404)
        return JSONResponse({
            "job_id": job.id, "status": job.status,
            "progress": getattr(job, "progress", 0),
            "result": job.result or {}, "error": job.error or "",
        })
    finally:
        db.close()
