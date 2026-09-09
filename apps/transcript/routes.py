"""HTTP của App `transcript` — CHỈ HTTP.

Đọc request · kiểm quyền/CSRF · gọi service · dựng phản hồi. **Không nghiệp vụ.**
Trần cứng: 900 dòng / 30 handler (`tools/lint_app_contract.py`).

⭐ `queue()` không tự tính giá và không tự tạo hàng đợi: `submit_with_credit`
làm cả hai **trong một transaction**, nên không tồn tại trạng thái "job đã tạo
mà tiền chưa giữ" — đúng thứ đã gây lỗi tiền ở cửa job trước đây.
"""
from __future__ import annotations

import io
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from platform_core.storage import get_storage
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.templating import templates

from .manifest import MANIFEST
from .services import phien_am

log = logging.getLogger("apps.transcript.routes")

# ⛔ KHONG tu viet prefix: nen tang gan tu `MANIFEST.route_prefix`. Viet tay o
#    day la hai nguon cho mot duong dan, va chung se lech.
router = APIRouter(tags=["transcript"])

#: Trần tệp âm thanh nhận qua giao diện.
#:
#: 🔴 **95 MB, không phải 100.** Cloudflare chặn ở 100 MB cho **cả request**,
#:    và một multipart còn mang biên, tên tệp, các trường khác. Đặt đúng 100 là
#:    để người dùng gặp HTTP 413 của Cloudflare — một lỗi xảy ra **trước khi**
#:    tới máy chủ, nên ta không nói được câu gì tử tế về nó.
TRAN_BYTE = 95 * 1024 * 1024

DUOI_NHAN = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".webm")


def _jobs_cua_toi(request: Request, user: str) -> list:
    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select

    gen = get_session()
    db = next(gen)
    try:
        return list(db.execute(
            select(Job).where(Job.user_id == user,
                              Job.job_type == "transcript.run")
            .order_by(Job.created_at.desc()).limit(20)).scalars())
    finally:
        db.close()


def _trang(request: Request, user: str, *, loi: str = "",
           status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, "transcript.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "loi": loi, "jobs": _jobs_cua_toi(request, user),
    }, status_code=status_code)


@router.get("/", response_class=HTMLResponse)
def page(request: Request, user: str = Depends(require_login)):
    return _trang(request, user)


@router.post("/tao")
async def queue(
    request: Request,
    csrf_token: str = Form(...),
    audio: UploadFile = File(...),
    language: str = Form(""),
    min_s: float = Form(3.0),
    max_s: float = Form(6.0),
    include_silence: str = Form(""),
    user: str = Depends(require_login),
):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit

    if not verify_csrf_token(request, csrf_token):
        return _trang(request, user, loi="Phiên đã hết hạn — tải lại trang.",
                      status_code=400)

    ten = (audio.filename or "").lower()
    if not ten.endswith(DUOI_NHAN):
        return _trang(request, user, status_code=400,
                      loi=f"Chỉ nhận tệp âm thanh: {', '.join(DUOI_NHAN)}.")
    du_lieu = await audio.read()
    if not du_lieu:
        return _trang(request, user, loi="Tệp âm thanh rỗng.", status_code=400)
    if len(du_lieu) > TRAN_BYTE:
        return _trang(request, user, status_code=400,
                      loi="Tệp vượt 95 MB — hãy cắt ngắn hoặc nén lại.")

    # Chuẩn hoá tham số bằng CHÍNH hàm mà worker dùng: một chỗ kiểm, một câu
    # trả lời. Nếu route tự kiểm thì hai bộ luật sẽ lệch nhau, và bên lệch sẽ
    # là bên ít được chạy hơn.
    # 🔴 Lay duoi tu DANH SACH CHO PHEP, khong tu chuoi tho cua khach.
    #    `ten.rsplit(".", 1)[-1]` tren `a.mp3/../../x` tra ve `mp3/../../x` —
    #    tuc mot duong vuot thu muc di THANG vao khoa luu tru. `_safe_key` cua
    #    `storage` co chan, nhung no chan bang cach NEM: mot loi 500 thay vi mot
    #    cau tra loi tu te, va mot lop phong thu o xa ma App khong duoc dua vao.
    duoi = next(d for d in DUOI_NHAN if ten.endswith(d))
    khoa = f"transcript/{user}/{uuid.uuid4().hex}{duoi}"
    try:
        tham_so = {"audio": khoa, "language": language.strip(),
                   "min_s": min_s, "max_s": max_s,
                   "include_silence": bool(include_silence)}
        phien_am.chuan_hoa(tham_so)
    except phien_am.LoiPhienAm as e:
        return _trang(request, user, loi=str(e), status_code=400)

    get_storage().put(khoa, io.BytesIO(du_lieu))

    gen = get_session()
    db = next(gen)
    try:
        job = submit_with_credit(
            db, user_id=user, app_slug="transcript",
            job_type="transcript.run", params=tham_so,
            dedupe_key=dedupe_key_for("transcript.run", tham_so),
            admission_resource="gpu_stt", admission_slots=1)
        db.commit()
    except credit.ThieuCreditError as e:
        db.rollback()
        return _trang(request, user, loi=str(e), status_code=402)
    finally:
        db.close()

    return JSONResponse({"job_id": job.id}, status_code=202)


@router.get("/ket-qua/{job_id}")
def ket_qua(request: Request, job_id: str, user: str = Depends(require_login)):
    """Kết quả của MỘT lượt. Chỉ chủ của job đọc được.

    ⛔ Job của người khác trả **404**, không phải 403: một mã 403 xác nhận rằng
       job ấy tồn tại, và đó là một rò rỉ nhỏ nhưng có thật.
    """
    from platform_core.db import get_session
    from platform_core.models import Job

    gen = get_session()
    db = next(gen)
    try:
        job = db.get(Job, job_id)
        if job is None or job.user_id != user:
            return JSONResponse({"error": "khong tim thay"}, status_code=404)
        return JSONResponse({
            "job_id": job.id,
            "status": job.status,
            "progress": getattr(job, "progress", 0),
            "result": job.result or {},
            "error": job.error or "",
        })
    finally:
        db.close()
