"""
_shared.py - router va cac helper dung chung cho moi module route cua app.

Truoc 2026-08-06 toan bo 64 handler nam trong MOT file 1.799 dong, lon nhat
repo. Tach theo mien de debug theo hang muc: loi o Kho tai nguyen thi mo
`resources.py`, khong phai cuon qua storyboard va bao gia.

Router khai o day chu khong o `__init__` de moi module import duoc no ma khong
tao vong import.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import copy
import io
import json
import os
import uuid
import zipfile
from pathlib import Path, PurePath

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Request,
                     UploadFile)
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.manifest import MANIFEST
from apps.prompt_ai_ommi.project_schema import (MAX_SCENES, SCHEMA_VERSION,
                                                clean_project, empty_project,
                                                prompt_job_params)
from apps.prompt_ai_ommi.services.composer import load_catalog
from platform_core.frontend_bundle import bundle_assets
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, is_operator, user_hien_tai
from server.templating import templates
from platform_core.jobs import loi_cho_khach

router = APIRouter(tags=["prompt-ai-ommi"])
_ASSET_CAP = {"image": 20 * 1024 * 1024, "video": 60 * 1024 * 1024,
              "audio": 20 * 1024 * 1024}
_PREFERENCES_KIND = "preferences"
# Dat o _shared vi ba mien deu dung: resources, library, storyboard.
_IMAGE_JOB_TYPE = "taoanh.generate"


def _run_mode() -> str:
    configured = os.environ.get("LTT_PROMPT_AI_OMMI_ROLLOUT")
    if configured is not None:
        mode = configured.strip().lower()
        return mode if mode in {"off", "admin", "allowlist", "public"} else "off"
    return "off" if os.environ.get("LTT_ENV", "").strip().lower() in {
        "production", "prod"} else "public"


def _require_run_enabled(user) -> None:
    mode = _run_mode()
    allowed = {value.strip() for value in os.environ.get(
        "LTT_PROMPT_AI_OMMI_USER_IDS", "").split(",") if value.strip()}
    enabled = (mode == "public" or
               mode == "admin" and getattr(user, "role", "") == "admin" or
               mode == "allowlist" and (getattr(user, "role", "") == "admin" or
                                         str(getattr(user, "id", "")) in allowed))
    if not enabled:
        raise HTTPException(status_code=503, detail=_t('Tạo job PROMPT AI OMMI đang tạm khóa.'))


def _user(request: Request):
    user = user_hien_tai(request)
    if user is None:
        raise HTTPException(status_code=403,
                            detail=_t('Cần tài khoản người dùng trong CSDL để sử dụng app.'))
    return user


def _csrf(request: Request, body: dict | None = None) -> None:
    token = request.headers.get("X-CSRF-Token", "") or str((body or {}).get("csrf_token") or "")
    if not verify_csrf_token(request, token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn — tải lại trang.'))


def _as_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


def _row(row) -> dict:
    return {"id": row.id, "name": row.name, "revision": row.revision,
            "schema_version": row.schema_version, "status": row.status,
            "payload": row.payload or {}, "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat()}


def _production_rows(db: Session, user_id: str, *, include_archived: bool = False):
    from platform_core.models import APP_PROJECT_ACTIVE, AppProject
    stmt = select(AppProject).where(AppProject.user_id == user_id,
                                    AppProject.app_slug == MANIFEST.slug)
    if not include_archived:
        stmt = stmt.where(AppProject.status == APP_PROJECT_ACTIVE)
    rows = db.execute(stmt.order_by(AppProject.updated_at.desc()).limit(120)).scalars().all()
    return [row for row in rows if (row.payload or {}).get("kind") == "production"]


def _owned_production(db: Session, project_id: str, user_id: str):
    from platform_core import app_projects
    try:
        row = app_projects.get_owned(db, project_id, user_id, MANIFEST.slug)
    except app_projects.ProjectNotFound:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.')) from None
    if (row.payload or {}).get("kind") != "production":
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy project.'))
    return row


def _models(category: str) -> list[dict]:
    """Model cho bộ chọn trên giao diện.

    🔴 SỬA 08/09/2026 — AI CLEAN REBUILD V2 pha 05.5. Bản cũ ghi cứng
       `("gemini",)` cho `chat`/`image`. Khi pha 04 retire Gemini, bộ lọc ấy làm
       danh sách thành **RỖNG** — và một enum rỗng từng làm `validate_tool_params`
       **tự tắt** (lỗ fail-open đã vá ở `platform_core/agent/tools.py`).

    ⛔ Không ghi cứng tên provider ở tầng app nữa. `model_options` đã lọc theo
       `is_active` ở **cả hai** mức (provider và model), nên bỏ bộ lọc là đủ:
       app hỏi *"model nào phục vụ được category này"* và nền tảng trả lời.
       Ngày nền tảng đổi động cơ, chỗ này **không phải sửa một dòng nào**.
    """
    from platform_core import providers
    return providers.model_options(category)


def _preference_row(db: Session, user_id: str):
    from platform_core.models import AppProject
    rows = db.execute(select(AppProject).where(
        AppProject.user_id == user_id, AppProject.app_slug == MANIFEST.slug
    ).order_by(AppProject.updated_at.desc()).limit(160)).scalars().all()
    return next((row for row in rows if (row.payload or {}).get("kind") == _PREFERENCES_KIND), None)


def _preference_payload(row) -> dict:
    raw = (row.payload or {}) if row is not None else {}
    return {"theme": raw.get("theme") if raw.get("theme") in {"light", "dark"} else "light"}


def _jobs(db: Session, user_id: str) -> list[dict]:
    from platform_core.models import Job
    rows = db.execute(select(Job).where(
        Job.user_id == user_id, Job.app_slug == MANIFEST.slug
    ).order_by(Job.created_at.desc()).limit(30)).scalars().all()
    return [{"id": row.id, "status": row.status, "progress": row.progress,
             "progress_msg": row.progress_msg, "error": loi_cho_khach(row),
             "operation": str((row.params or {}).get("operation") or "director"),
             "project_id": str((row.params or {}).get("project_id") or ""),
             "created_at": row.created_at.isoformat()} for row in rows]


def _render_workspace(request: Request):
    scripts, styles = bundle_assets("prompt-ai-ommi")
    return templates.TemplateResponse(request, "prompt_ai_ommi_workspace.html", {
        "user": _user(request).email, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "workspace_js": scripts, "workspace_css": styles,
        # Tran so canh di RA frontend thay vi frontend tu go lai. Hai cho khai
        # cung mot dai luong thi som muon lech, va cho lech o day nam ngay
        # trong `max` cua input KHACH DANG GO.
        "max_scenes": MAX_SCENES,
    })

def _resource_error(exc: Exception) -> HTTPException:
    """Chỉ dịch lỗi CỦA NGƯỜI DÙNG. Mọi thứ khác để nguyên cho 500.

    Bản đầu bắt `Exception` rồi trả 400 cho tất cả. Hậu quả thấy ngay trên
    browser: bảng CSDL chưa tồn tại — lỗi máy chủ — lại báo "yêu cầu không hợp
    lệ", nên người dùng đi sửa thứ họ gõ trong khi hỏng nằm ở máy chủ, và log
    không ghi gì vì 400 được coi là bình thường.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    if isinstance(exc, rsvc.ResourceNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, rsvc.ResourceError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc
