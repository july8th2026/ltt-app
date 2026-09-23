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
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from platform_core.i18n import _ as _t
from platform_core.storage import get_storage
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

from .manifest import MANIFEST
from .services import he as he_phien_am
from .services import phien_am
from platform_core.jobs import loi_cho_khach

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


def _do_thoi_luong(du_lieu: bytes, duoi: str) -> float:
    """Thời lượng THẬT của tệp vừa nhận (ffprobe) — giá tính theo con số này."""
    from platform_core import media

    with tempfile.TemporaryDirectory(prefix="transcript_gia_") as tam:
        duong = Path(tam) / f"vao{duoi}"
        duong.write_bytes(du_lieu)
        return float(media.duration_seconds(str(duong)) or 0.0)


def _ma_user(request: Request) -> str:
    """`User.id` của phiên — khoá của sổ credit, của job và của kho lưu trữ.

    🔴 22/09/2026: bản đầu dùng thẳng chuỗi `require_login()` trả về (EMAIL) làm
       `user_id` cho `submit_with_credit`. Sổ credit ghi theo `User.id` ⇒ mọi khách
       nhận 402 "con 0" dù có tiền; lịch sử và `/ket-qua` cũng lọc sai khoá. Đo được
       ở E2E thật trên production. Cùng khuôn `apps/autosubvideo` (`user_hien_tai`).
    Rỗng khi phiên không có User CSDL (tài khoản quản trị từ env).
    """
    u = user_hien_tai(request)
    return str(getattr(u, "id", "") or "") if u is not None else ""


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
        "loi": loi, "jobs": _jobs_cua_toi(request, _ma_user(request)),
        "cac_he": list(he_phien_am.HE.values()), "he_mac_dinh": he_phien_am.MAC_DINH,
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
    min_s: float = Form(phien_am.MIN_S_MAC_DINH),
    max_s: float = Form(6.0),
    include_silence: str = Form(""),
    he: str = Form(he_phien_am.MAC_DINH),
    user: str = Depends(require_login),
):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit

    if not verify_csrf_token(request, csrf_token):
        return _trang(request, user, loi=_t("Phiên đã hết hạn — tải lại trang."),
                      status_code=400)
    uid = _ma_user(request)
    if not uid:
        return _trang(request, user, status_code=403,
                      loi=_t("Cần tài khoản người dùng để dùng credit."))

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

    # Chuẩn hoá tham số bằng CHÍNH hàm mà worker dùng: một chỗ kiểm, một câu
    # trả lời. Nếu route tự kiểm thì hai bộ luật sẽ lệch nhau, và bên lệch sẽ
    # là bên ít được chạy hơn.
    # 🔴 Lay duoi tu DANH SACH CHO PHEP, khong tu chuoi tho cua khach.
    #    `ten.rsplit(".", 1)[-1]` tren `a.mp3/../../x` tra ve `mp3/../../x` —
    #    tuc mot duong vuot thu muc di THANG vao khoa luu tru. `_safe_key` cua
    #    `storage` co chan, nhung no chan bang cach NEM: mot loi 500 thay vi mot
    #    cau tra loi tu te, va mot lop phong thu o xa ma App khong duoc dua vao.
    duoi = next(d for d in DUOI_NHAN if ten.endswith(d))
    khoa = f"transcript/{uid}/{uuid.uuid4().hex}{duoi}"
    # Giá theo phút audio đo từ CHÍNH tệp (gia.py). Không đo được = không phải
    # audio dùng được — từ chối trước khi giữ tiền, thay vì giữ 1 credit sai.
    thoi_luong = _do_thoi_luong(du_lieu, duoi)
    if thoi_luong <= 0:
        return _trang(request, user, status_code=400,
                      loi=_t("Không đọc được thời lượng tệp âm thanh — tệp hỏng hoặc sai định dạng."))
    try:
        tham_so = {"audio": khoa, "language": language.strip(),
                   "min_s": min_s, "max_s": max_s,
                   "include_silence": bool(include_silence),
                   "he": he.strip() or he_phien_am.MAC_DINH,
                   "duration_s": round(thoi_luong, 3)}
        phien_am.chuan_hoa(tham_so)
    except phien_am.LoiPhienAm as e:
        return _trang(request, user, loi=str(e), status_code=400)

    get_storage().put(khoa, io.BytesIO(du_lieu))

    gen = get_session()
    db = next(gen)
    try:
        job = submit_with_credit(
            db, user_id=uid, app_slug="transcript",
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
        if job is None or not _ma_user(request) or job.user_id != _ma_user(request):
            return JSONResponse({"error": "khong tim thay"}, status_code=404)
        return JSONResponse({
            "job_id": job.id,
            "status": job.status,
            "progress": getattr(job, "progress", 0),
            "result": job.result or {},
            "error": loi_cho_khach(job),
        })
    finally:
        db.close()
