"""HTTP của App `video_assembly` — CHỈ HTTP. Nghiệp vụ ở `services/dung_video.py`.

⚠️ App này nhận **nhiều** tệp trong một request, nên trần Cloudflare (100 MB cho
   cả request) là ràng buộc thật chứ không phải lý thuyết. Trần ở đây đặt 95 MB
   cho **tổng**, và nói rõ điều đó ra giao diện.
"""
from __future__ import annotations

import io
import json
import logging
import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from platform_core.storage import get_storage
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.templating import templates

from .manifest import MANIFEST
from .services import dung_video
from .services.tuong_thich.paths import safe_name

log = logging.getLogger("apps.video_assembly.routes")

router = APIRouter(tags=["video_assembly"])

#: Trần cho TỔNG dung lượng một request. Cloudflare chặn ở 100 MB cho cả
#: request; đặt đúng 100 là để người dùng gặp HTTP 413 **trước khi** tới máy
#: chủ, nơi ta không nói được câu gì tử tế về nó.
TRAN_TONG_BYTE = 95 * 1024 * 1024

DUOI_VIDEO = (".mp4", ".mov", ".mkv", ".webm", ".avi")
DUOI_NHAC = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")


def _jobs_cua_toi(user: str) -> list:
    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select

    gen = get_session()
    db = next(gen)
    try:
        return list(db.execute(
            select(Job).where(Job.user_id == user,
                              Job.job_type == "video_assembly.run")
            .order_by(Job.created_at.desc()).limit(20)).scalars())
    finally:
        db.close()


def _trang(request: Request, user: str, *, loi: str = "",
           status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, "video_assembly.html", {
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
    clips: list[UploadFile] = File(...),
    music: UploadFile | None = File(None),
    che_do_khop: str = Form("sequential"),
    bat_demucs: str = Form("1"),
    bat_phu_de: str = Form("1"),
    bat_cham_diem: str = Form(""),
    cau_hinh: str = Form(""),
    user: str = Depends(require_login),
):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit

    if not verify_csrf_token(request, csrf_token):
        return _trang(request, user, loi="Phiên đã hết hạn — tải lại trang.",
                      status_code=400)
    if not clips:
        return _trang(request, user, loi="Chưa chọn clip nào.", status_code=400)

    tong = 0
    du_lieu: list[tuple[str, bytes]] = []
    for tep in clips:
        ten = (tep.filename or "").lower()
        if not ten.endswith(DUOI_VIDEO):
            return _trang(request, user, status_code=400,
                          loi=f"`{tep.filename}` không phải video "
                              f"({', '.join(DUOI_VIDEO)}).")
        b = await tep.read()
        tong += len(b)
        if tong > TRAN_TONG_BYTE:
            return _trang(request, user, status_code=400,
                          loi="Tổng dung lượng vượt 95 MB — tải ít clip hơn "
                              "mỗi lượt.")
        # 🔴 TEN TEP LA DAU VAO CUA KHACH, va no di THANG vao khoa luu tru.
        #    `../../x.mp4` se leo ra khoi tien to cua nguoi dung. `_safe_key`
        #    cua `storage` co chan, nhung no chan bang cach NEM — tuc mot loi
        #    500 thay vi mot cau tra loi tu te, va mot lop phong thu o xa ma
        #    App nay khong duoc phep dua vao.
        #
        # ⛔ Va ban va KHONG the la "thay bang UUID": che do `sequential` doc
        #    TIEN TO ten tep (`^\d{3,4}-scene`), nen doi ten la pha dung hanh vi
        #    production dang dung. Phai lam sach ma VAN giu ten.
        ten_sach = safe_name(PurePosixPath(
            (tep.filename or "").replace(chr(92), "/")).name)
        du_lieu.append((ten_sach or f"{uuid.uuid4().hex}.mp4", b))

    nhac_byte = b""
    ten_nhac = ""
    if music is not None and music.filename:
        if not music.filename.lower().endswith(DUOI_NHAC):
            return _trang(request, user, status_code=400,
                          loi=f"Nhạc phải là {', '.join(DUOI_NHAC)}.")
        ten_nhac = safe_name(PurePosixPath(
            music.filename.replace(chr(92), "/")).name) or "nhac"
        nhac_byte = await music.read()
        if tong + len(nhac_byte) > TRAN_TONG_BYTE:
            return _trang(request, user, status_code=400,
                          loi="Tổng dung lượng vượt 95 MB.")

    cfg = {}
    if cau_hinh.strip():
        try:
            cfg = json.loads(cau_hinh)
        except ValueError as e:
            return _trang(request, user, status_code=400,
                          loi=f"`cau_hinh` không phải JSON hợp lệ: {e}")

    lo = uuid.uuid4().hex
    khoa_clip = [f"video_assembly/{user}/{lo}/clip/{ten}" for ten, _ in du_lieu]
    # ⚠️ Đọc tên nhạc vào một biến NGAY lúc còn biết `music` khác `None`.
    #    Dùng `music.filename` ở đây là hỏi một thuộc tính trên `UploadFile |
    #    None` — mypy đúng khi kêu, và ở runtime nó chỉ an toàn nhờ một bất biến
    #    nằm cách đó 15 dòng.
    khoa_nhac = (f"video_assembly/{user}/{lo}/nhac/{ten_nhac}"
                 if nhac_byte else "")

    tham_so = {"clips": khoa_clip, "music": khoa_nhac, "cau_hinh": cfg,
               "che_do_khop": che_do_khop, "bat_demucs": bool(bat_demucs),
               "bat_phu_de": bool(bat_phu_de),
               "bat_cham_diem": bool(bat_cham_diem), "owner_id": user}
    # Chuẩn hoá bằng CHÍNH hàm mà worker dùng — một chỗ kiểm, một câu trả lời.
    try:
        dung_video.chuan_hoa({**tham_so, "clips": khoa_clip[0]})
    except dung_video.LoiDungVideo as e:
        return _trang(request, user, loi=str(e), status_code=400)

    kho = get_storage()
    for (_ten, b), khoa in zip(du_lieu, khoa_clip, strict=True):
        kho.put(khoa, io.BytesIO(b))
    if nhac_byte:
        kho.put(khoa_nhac, io.BytesIO(nhac_byte))

    gen = get_session()
    db = next(gen)
    try:
        job = submit_with_credit(
            db, user_id=user, app_slug="video_assembly",
            job_type="video_assembly.run", params=tham_so,
            dedupe_key=dedupe_key_for("video_assembly.run", tham_so),
            admission_resource="gpu_video", admission_slots=1)
        db.commit()
    except credit.ThieuCreditError as e:
        db.rollback()
        return _trang(request, user, loi=str(e), status_code=402)
    finally:
        db.close()

    return JSONResponse({"job_id": job.id}, status_code=202)


@router.get("/ket-qua/{job_id}")
def ket_qua(job_id: str, user: str = Depends(require_login)):
    """Job của người khác trả **404**, không phải 403 — 403 xác nhận job tồn tại."""
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
