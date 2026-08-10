"""UI/API operator-only của Quality Lab foundation."""
from __future__ import annotations

import io
import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select

from apps.qualitylab.manifest import MANIFEST
from apps.qualitylab.registry import PACKS, public_registry
from platform_core.i18n import _ as _t
from platform_core.job_submit import dedupe_key_for, submit_with_credit
from platform_core.models import Job
from platform_core.storage import CLOUDFLARE_BODY_LIMIT, get_storage
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.deps import get_db, require_operator, user_hien_tai
from server.templating import templates

router = APIRouter(tags=["qualitylab"])
MAX_LOCAL_UPLOAD = min(90 * 1024 * 1024, CLOUDFLARE_BODY_LIMIT)
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp",
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v",
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".srt",
}


def _recent(db, limit: int = 30) -> list[Job]:
    return list(db.execute(select(Job).where(
        Job.app_slug == MANIFEST.slug).order_by(Job.created_at.desc()).limit(limit)
    ).scalars().all())


def _context(request: Request, db, *, error: str = "") -> dict:
    return {
        "request": request, "app": MANIFEST, "nav": MANIFEST.slug,
        "csrf_token": issue_csrf_token(request), "packs": PACKS,
        "registry": public_registry(), "recent_jobs": _recent(db), "error": error,
    }


@router.get("", response_class=HTMLResponse)
def page(request: Request, _operator: str = Depends(require_operator),
         db=Depends(get_db)):
    return templates.TemplateResponse(request, "qualitylab.html", _context(request, db))


async def _store_upload(upload: UploadFile, owner_id: str) -> tuple[str, str]:
    name = PurePosixPath(upload.filename or "").name
    ext = PurePosixPath(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=_t("Định dạng input chưa được hỗ trợ."))
    data = await upload.read(MAX_LOCAL_UPLOAD + 1)
    if not data or len(data) > MAX_LOCAL_UPLOAD:
        raise HTTPException(status_code=400, detail=_t("Input rỗng hoặc vượt 90 MB."))
    key = f"qualitylab/{owner_id}/ephemeral/{uuid.uuid4().hex}{ext}"
    get_storage().put(key, io.BytesIO(data),
                      content_type=(upload.content_type or "application/octet-stream"))
    return key, f"input{ext}"


def _store_truth(text: str, owner_id: str) -> str:
    payload = text.encode("utf-8")
    if len(payload) > 100_000:
        raise HTTPException(status_code=400, detail=_t("Transcript chuẩn vượt 100 KB."))
    key = f"qualitylab/{owner_id}/ephemeral/{uuid.uuid4().hex}.truth.txt"
    get_storage().put(key, io.BytesIO(payload), content_type="text/plain; charset=utf-8")
    return key


@router.post("/evaluate")
async def evaluate(
    request: Request,
    csrf_token: str = Form(...),
    pack: str = Form(...),
    source_key: str = Form(""),
    source_name: str = Form(""),
    expected_text: str = Form(""),
    expected_width: int = Form(0),
    expected_height: int = Form(0),
    expected_duration: float = Form(0),
    expected_fps: float = Form(0),
    expected_audio: str = Form(""),
    source_file: UploadFile | None = File(default=None),
    reference_key: str = Form(""),
    low_input_key: str = Form(""),
    reference_file: UploadFile | None = File(default=None),
    low_input_file: UploadFile | None = File(default=None),
    _operator: str = Depends(require_operator),
    db=Depends(get_db),
):
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "qualitylab.html", _context(
                request, db, error=_t("Phiên đã hết hạn — tải lại trang rồi thử lại.")),
            status_code=400)
    if pack not in PACKS:
        raise HTTPException(status_code=400, detail=_t("Pack đánh giá không hợp lệ."))
    current = user_hien_tai(request)
    if current is None:
        return templates.TemplateResponse(
            request, "qualitylab.html", _context(
                request, db, error=_t("Cần tài khoản quản trị CSDL để tạo evaluation job.")),
            status_code=400)

    ephemeral: list[str] = []
    key = source_key.strip()
    name = PurePosixPath(source_name or key).name
    ref_key = reference_key.strip()
    low_key = low_input_key.strip()
    try:
        if source_file is not None and source_file.filename:
            key, name = await _store_upload(source_file, current.id)
            ephemeral.append(key)
        if not key or not get_storage().exists(key):
            raise HTTPException(status_code=400, detail=_t("Source artifact không tồn tại."))
        if reference_file is not None and reference_file.filename:
            ref_key, _ = await _store_upload(reference_file, current.id)
            ephemeral.append(ref_key)
        if low_input_file is not None and low_input_file.filename:
            low_key, _ = await _store_upload(low_input_file, current.id)
            ephemeral.append(low_key)
        if ref_key and not get_storage().exists(ref_key):
            raise HTTPException(status_code=400, detail=_t("Ảnh HR reference không tồn tại."))
        if low_key and not get_storage().exists(low_key):
            raise HTTPException(status_code=400, detail=_t("Ảnh LR đầu vào không tồn tại."))
        if pack == "upscale_paired_diagnostic" and not ref_key:
            raise HTTPException(status_code=400, detail=_t("Pack paired cần ảnh HR reference."))
        audio_expectation = None
        if expected_audio in {"yes", "no"}:
            audio_expectation = expected_audio == "yes"
        truth_key = ""
        if expected_text:
            truth_key = _store_truth(expected_text, current.id)
            ephemeral.append(truth_key)
        params = {
            "pack": pack, "source_key": key, "source_name": name,
            "reference_key": ref_key, "low_input_key": low_key,
            "expected_text_key": truth_key,
            "expectations": {
                "expected_width": max(0, expected_width),
                "expected_height": max(0, expected_height),
                "expected_duration": max(0.0, expected_duration),
                "expected_fps": max(0.0, expected_fps),
                "expected_audio": audio_expectation,
            },
            "ephemeral_keys": ephemeral,
        }
        job = submit_with_credit(
            db, user_id=current.id, app_slug=MANIFEST.slug,
            job_type="qualitylab.evaluate", params=params,
            dedupe_key=dedupe_key_for("qualitylab.evaluate", params), max_attempts=2,
        )
        db.flush()
        return RedirectResponse(f"/jobs/{job.id}", status_code=303)
    except Exception:
        for item in ephemeral:
            get_storage().delete(item)
        raise


def _quality_job(db, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.app_slug != MANIFEST.slug:
        raise HTTPException(status_code=404, detail=_t("Không tìm thấy evaluation."))
    return job


@router.get("/reports/{job_id}", response_class=HTMLResponse)
def report_page(request: Request, job_id: str,
                _operator: str = Depends(require_operator), db=Depends(get_db)):
    job = _quality_job(db, job_id)
    report = (job.result or {}).get("report") if isinstance(job.result, dict) else None
    return templates.TemplateResponse(request, "qualitylab_report.html", {
        "request": request, "app": MANIFEST, "nav": MANIFEST.slug,
        "job": job, "report": report,
    })


@router.get("/api/reports/{job_id}")
def report_api(job_id: str, _operator: str = Depends(require_operator),
               db=Depends(get_db)):
    job = _quality_job(db, job_id)
    report = (job.result or {}).get("report") if isinstance(job.result, dict) else None
    if report is None:
        return JSONResponse({"ok": False, "status": job.status}, status_code=409)
    return JSONResponse({"ok": True, "report": report})
