"""HTTP của App `audio_pause` — CHỈ HTTP. Nghiệp vụ ở `services/chen_lang.py`.

Router **không** tự viết prefix: nền tảng gắn từ `MANIFEST.route_prefix`.
"""
from __future__ import annotations

import io
import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from platform_core.i18n import _ as _t
from platform_core.storage import get_storage
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.templating import templates

from .manifest import MANIFEST
from .services import chen_lang

log = logging.getLogger("apps.audio_pause.routes")

router = APIRouter(tags=["audio_pause"])

#: 95 MB, không phải 100: Cloudflare chặn ở 100 MB cho **cả request**, và một
#: multipart còn mang biên + các trường khác. Đặt đúng 100 là để người dùng gặp
#: HTTP 413 của Cloudflare — một lỗi xảy ra **trước khi** tới máy chủ, nên ta
#: không nói được câu gì tử tế về nó.
TRAN_BYTE = 95 * 1024 * 1024

DUOI_NHAN = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".webm")


def _jobs_cua_toi(user: str) -> list:
    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select

    gen = get_session()
    db = next(gen)
    try:
        return list(db.execute(
            select(Job).where(Job.user_id == user,
                              Job.job_type == "audio_pause.run")
            .order_by(Job.created_at.desc()).limit(20)).scalars())
    finally:
        db.close()


def _trang(request: Request, user: str, *, loi: str = "",
           status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, "audio_pause.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "loi": loi, "jobs": _jobs_cua_toi(user),
    }, status_code=status_code)


@router.get("/", response_class=HTMLResponse)
def page(request: Request, user: str = Depends(require_login)):
    return _trang(request, user)


@router.post("/tao")
async def queue(
    request: Request,
    csrf_token: str = Form(...),
    audio: UploadFile = File(...),
    pause_plan: str = Form(...),
    language: str = Form("vi"),
    min_pause_ms: int = Form(50),
    max_pause_ms: int = Form(15000),
    min_gap_s: float = Form(0.8),
    nguong_khop: float = Form(0.65),
    user: str = Depends(require_login),
):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit

    if not verify_csrf_token(request, csrf_token):
        return _trang(request, user, loi=_t("Phiên đã hết hạn — tải lại trang."),
                      status_code=400)

    ten = (audio.filename or "").lower()
    if not ten.endswith(DUOI_NHAN):
        return _trang(request, user, status_code=400,
                      loi=_t("Chỉ nhận tệp âm thanh: %(d)s.") % {"d": ", ".join(DUOI_NHAN)})
    du_lieu = await audio.read()
    if not du_lieu:
        return _trang(request, user, loi=_t("Tệp âm thanh rỗng."), status_code=400)
    if len(du_lieu) > TRAN_BYTE:
        return _trang(request, user, status_code=400,
                      loi=_t("Tệp vượt 95 MB — hãy cắt ngắn hoặc nén lại."))

    try:
        ke_hoach = json.loads(pause_plan)
    except ValueError as e:
        return _trang(request, user, status_code=400,
                      loi=_t("`pause_plan` không phải JSON hợp lệ: %(e)s") % {"e": e})

    # 🔴 Lay duoi tu DANH SACH CHO PHEP, khong tu chuoi tho cua khach.
    #    `ten.rsplit(".", 1)[-1]` tren `a.mp3/../../x` tra ve `mp3/../../x` —
    #    tuc mot duong vuot thu muc di THANG vao khoa luu tru. `_safe_key` cua
    #    `storage` co chan, nhung no chan bang cach NEM: mot loi 500 thay vi mot
    #    cau tra loi tu te, va mot lop phong thu o xa ma App khong duoc dua vao.
    duoi = next(d for d in DUOI_NHAN if ten.endswith(d))
    khoa = f"audio_pause/{user}/{uuid.uuid4().hex}{duoi}"
    tham_so = {"audio": khoa, "pause_plan": ke_hoach, "language": language,
               "min_pause_ms": min_pause_ms, "max_pause_ms": max_pause_ms,
               "min_gap_s": min_gap_s, "nguong_khop": nguong_khop,
               "owner_id": user}
    # Chuẩn hoá bằng CHÍNH hàm mà worker dùng — một chỗ kiểm, một câu trả lời.
    try:
        chen_lang.chuan_hoa(tham_so)
    except chen_lang.LoiChenLang as e:
        return _trang(request, user, loi=str(e), status_code=400)

    get_storage().put(khoa, io.BytesIO(du_lieu))

    gen = get_session()
    db = next(gen)
    try:
        job = submit_with_credit(
            db, user_id=user, app_slug="audio_pause",
            job_type="audio_pause.run", params=tham_so,
            dedupe_key=dedupe_key_for("audio_pause.run", tham_so),
            admission_resource="gpu_stt", admission_slots=1)
        db.commit()
    except credit.ThieuCreditError as e:
        db.rollback()
        return _trang(request, user, loi=str(e), status_code=402)
    finally:
        db.close()

    return JSONResponse({"job_id": job.id}, status_code=202)


@router.get("/ket-qua/{job_id}")
def ket_qua(job_id: str, user: str = Depends(require_login)):
    """Job của người khác trả **404**, không phải 403: một mã 403 xác nhận rằng
    job ấy tồn tại, và đó là một rò rỉ nhỏ nhưng có thật."""
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
