"""
_shared.py - router va helper dung chung cho moi module route cua app agent.

Truoc 2026-08-06 ca 48 handler nam trong MOT file 1.308 dong. Tach theo mien
(AGENTS.md muc 8) de debug theo hang muc: loi chia se link thi mo `sharing.py`,
khong phai cuon qua tro ly AI va man hinh quan tri.

Logic nghiep vu cua app nay nam o `platform_core/agent/` (planner, validator,
verifier, tools, workflows) chu khong o `services/` trong app: agent
la mot phan cua nen tang, khong phai app khach.

🗑️ `budget.py` va `runs.py` da bi go ngay 23/09/2026 cung model `AgentRun`
   (plan 01b Task 9, spec §17.3+§17.5). Ranh gioi tien va trang thai cua mot
   luot chay nay o `platform_core/workflow/` (v3).

Router khai o day chu khong o `__init__` de moi module import duoc no ma khong
tao vong import.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.agent.manifest import MANIFEST
from platform_core.agent import workflows
from platform_core.agent.tools import resolve_params_schema
from platform_core.models import (APP_PROJECT_ACTIVE, AgentWorkflow,
                                  AppProject)
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.deps import user_hien_tai

router = APIRouter(tags=["agent"])
_ASSET_LIMIT = 90 * 1024 * 1024
_ASSET_MIME_PREFIXES = ("image/", "video/", "audio/")
_PREFERENCES_SLUG = "agent.preferences"
_DEFAULT_PREFERENCES = {"theme": "dark", "catalog_mode": "simple",
                        "presentation_version": "creative-v1"}


def _canvas_presentation_mode() -> str:
    """Creative is the default; legacy keeps the H20 renderer as rollback."""
    configured = os.environ.get("LTT_AGENT_CANVAS_PRESENTATION", "creative")
    return "legacy" if configured.strip().lower() == "legacy" else "creative"

def _user(request: Request):
    user = user_hien_tai(request)
    if user is None:
        raise HTTPException(status_code=403, detail=_t('Cần tài khoản người dùng.'))
    return user


def _page_context(request: Request, *, error: str = "") -> dict:
    return {"nav": MANIFEST.slug, "app": MANIFEST,
            "csrf_token": issue_csrf_token(request), "error": error}


def _verify_json_csrf(request: Request, body: dict) -> None:
    token = request.headers.get("X-CSRF-Token", "") or str(body.get("csrf_token", ""))
    if not verify_csrf_token(request, token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))


def _workflow_json(row: AgentWorkflow, *, include_canvas: bool = True) -> dict:
    payload = {"id": row.id, "name": row.name, "status": row.status,
               "revision": row.revision, "plan_version": row.plan_version,
               "budget_max": row.budget_max, "estimated": row.estimated,
               "source_workflow_id": row.source_workflow_id,
               "created_at": row.created_at.isoformat(),
               "updated_at": row.updated_at.isoformat()}
    if include_canvas:
        payload["canvas"] = workflows.as_canvas(row)
    return payload


def _workflow_response(row: AgentWorkflow, *, status_code: int = 200):
    return JSONResponse(_workflow_json(row), status_code=status_code,
                        headers={"ETag": f'"{row.revision}"'})


def _palette_tool(name, spec, owner, loaded) -> dict:
    schema = resolve_params_schema(name, apps=loaded)
    variants = {}
    for field, rule in schema.items():
        if rule.get("type") == "model_ref":
            variants[field] = {str(value): resolve_params_schema(
                name, {field: value}, apps=loaded) for value in rule.get("values", [])}
    # Nhãn hiển thị cho palette. Đây là bảng TRA CỨU CÓ MẶC ĐỊNH — tool không có
    # trong đây vẫn hiện, chỉ là lấy nhãn suy ra từ chính tên nó (xem
    # `presentation.get(...)` ngay dưới). Thiếu một dòng ở đây không bao giờ làm
    # mất một node; nó chỉ làm node đó trông kém trau chuốt.
    #
    # 🗑️ Gỡ 11 dòng ngày 2026-08-25 cùng ba app `kichban`, `mediatools`, `demo`:
    #    `text.generate` · `text.script` · `audio.generate` · `asset.image` ·
    #    `asset.images` · `asset.video` · `asset.audio` · `video.extract_frames`
    #    · `media.merge_image` · `media.merge_video` · `video.social_import`.
    #
    # ⚠️ Bốn tool `asset.*` là các node **ĐẦU VÀO** của workflow — đường đưa tệp
    #    của khách vào một chuỗi Agent. Gỡ chúng là gỡ luôn đường đó, và **7
    #    trong 10 workflow đang lưu** có node thuộc nhóm 11 tool trên. Chủ sản
    #    phẩm đã biết con số đó và vẫn quyết gỡ (xem NHAT_KY 2026-08-25).
    presentation = {
        "image.generate": ("Tạo hình ảnh", "content", True),
        "video.generate": ("Tạo video", "content", True),
        "image.thumbnail": ("Tạo thumbnail", "specialized", False),
        "image.batch_generate": ("Tạo nhiều ảnh", "specialized", False),
        "image.upscale": ("Nâng cấp ảnh", "transform", False),
        "video.upscale": ("Nâng cấp video", "transform", False),
    }
    label, category, primary = presentation.get(
        spec.name, (spec.name.replace(".", " ").title(), "advanced", False))
    return {"name": spec.name, "label": label, "category": category,
            "primary": primary, "description": spec.description,
            "customer_visible": spec.customer_visible,
            "app_slug": owner.slug, "app_name": owner.manifest.display_name,
            "requires": list(owner.manifest.requires), "params_schema": schema,
            "schema_variants": variants, "returns": spec.returns,
            "verifiable": list(spec.verifiable)}


def _preferences_row(db: Session, user_id: str) -> AppProject | None:
    return db.query(AppProject).filter_by(
        user_id=user_id, app_slug=_PREFERENCES_SLUG,
        status=APP_PROJECT_ACTIVE).order_by(AppProject.updated_at.desc()).first()


def _preferences_json(row: AppProject | None) -> dict:
    payload = dict(_DEFAULT_PREFERENCES)
    if row:
        saved = row.payload or {}
        if saved.get("theme") in {"light", "dark"}:
            payload["theme"] = saved["theme"]
        # H20 stored "advanced" as its default. An unversioned row is not an
        # explicit customer opt-in, so H21 migrates its presentation to simple
        # without changing the workflow document or ToolSpec runtime.
        if (saved.get("presentation_version") == "creative-v1" and
                saved.get("catalog_mode") in {"simple", "advanced"}):
            payload["catalog_mode"] = saved["catalog_mode"]
    return {**payload, "revision": row.revision if row else 0}

def _require_admin_user(request: Request):
    user = _user(request)
    if getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy.'))
    return user
