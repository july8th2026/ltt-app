"""Storyboard, canh va phien ban theo tung canh."""
from __future__ import annotations

from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    MANIFEST, _IMAGE_JOB_TYPE, _csrf, _owned_production,
    _require_run_enabled, _user, get_db, require_login, router)


# ── Storyboard (R3) ────────────────────────────────────────────────────────
#
# Chỗ hai lớp trước gặp nhau: mỗi cảnh lấy tài nguyên để giữ nhất quán nhân vật
# và lấy phong cách từ thư viện để giữ giọng chung. Sinh ảnh vẫn đi qua
# `taoanh.generate` theo phương án đã chốt — OMMI sở hữu điều phối, không sở
# hữu engine.

def _storyboard_error(exc: Exception) -> HTTPException:
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    if isinstance(exc, ssvc.StoryboardNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ssvc.StoryboardError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


def _board_json(row) -> dict:
    return {"id": row.id, "project_id": row.project_id, "name": row.name,
            "meta_prompt_id": row.meta_prompt_id or "",
            "style_id": row.style_id or "", "aspect_ratio": row.aspect_ratio,
            "archived": row.archived_at is not None,
            "updated_at": row.updated_at.isoformat()}


def _scene_json(row) -> dict:
    return {"id": row.id, "storyboard_id": row.storyboard_id,
            "position": row.position, "title": row.title, "prompt": row.prompt,
            "camera": row.camera, "continuity": row.continuity,
            "resource_ids": list(row.resource_ids or []),
            "image_key": row.image_key, "version": row.version}


@router.get("/api/storyboards")
def list_storyboards(request: Request, project_id: str = "",
                     archived: bool = False,
                     _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    user = _user(request)
    rows = ssvc.list_boards(db, user.id, project_id=project_id,
                            include_archived=bool(archived))
    return {"items": [_board_json(row) for row in rows], "total": len(rows)}


@router.post("/api/storyboards", status_code=201)
async def create_storyboard(request: Request,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    project_id = str(body.get("project_id") or "")
    # Chỉ cho gắn vào project CỦA CHÍNH mình — nếu không, biết ID là gắn
    # storyboard vào project người khác.
    _owned_production(db, project_id, user.id)
    try:
        row = ssvc.create_board(db, owner_id=user.id, project_id=project_id,
                                name=body.get("name", "Storyboard mới"),
                                aspect_ratio=str(body.get("aspect_ratio") or "16:9"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _board_json(row)


@router.get("/api/storyboards/{board_id}")
def get_storyboard(request: Request, board_id: str,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    user = _user(request)
    try:
        board = ssvc.get_owned_board(db, board_id, user.id)
        rows = ssvc.scenes(db, board_id, user.id)
    except Exception as exc:
        raise _storyboard_error(exc) from exc
    return {**_board_json(board), "scenes": [_scene_json(row) for row in rows]}


@router.put("/api/storyboards/{board_id}")
async def update_storyboard(request: Request, board_id: str,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    fields = {key: body[key] for key in
              ("name", "aspect_ratio", "meta_prompt_id", "style_id") if key in body}
    try:
        row = ssvc.update_board(db, board_id=board_id, owner_id=user.id, **fields)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _board_json(row)


@router.post("/api/storyboards/{board_id}/scenes", status_code=201)
async def add_storyboard_scene(request: Request, board_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = ssvc.add_scene(db, board_id=board_id, owner_id=user.id,
                             title=body.get("title", ""),
                             prompt=body.get("prompt", ""),
                             camera=body.get("camera", ""),
                             resource_ids=body.get("resource_ids"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _scene_json(row)


@router.put("/api/scenes/{scene_id}")
async def update_scene_route(request: Request, scene_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    fields = {key: body[key] for key in
              ("title", "prompt", "camera", "continuity", "resource_ids")
              if key in body}
    try:
        row = ssvc.update_scene(db, scene_id=scene_id, owner_id=user.id, **fields)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _scene_json(row)


@router.delete("/api/scenes/{scene_id}")
async def delete_scene_route(request: Request, scene_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    _csrf(request); user = _user(request)
    try:
        ssvc.delete_scene(db, scene_id=scene_id, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return {"ok": True}


@router.post("/api/storyboards/{board_id}/reorder")
async def reorder_scenes(request: Request, board_id: str,
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        rows = ssvc.reorder(db, board_id=board_id, owner_id=user.id,
                            scene_ids=body.get("scene_ids") or [])
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return {"scenes": [_scene_json(row) for row in rows]}


@router.get("/api/scenes/{scene_id}/versions")
def scene_versions(request: Request, scene_id: str,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    user = _user(request)
    try:
        rows = ssvc.versions(db, scene_id, user.id)
    except Exception as exc:
        raise _storyboard_error(exc) from exc
    return {"items": [{"version": row.version, "image_key": row.image_key,
                       "job_id": row.job_id,
                       "created_at": row.created_at.isoformat()} for row in rows]}


@router.post("/api/scenes/{scene_id}/restore/{version}")
async def restore_scene_version(request: Request, scene_id: str, version: int,
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = ssvc.restore_version(db, scene_id=scene_id, owner_id=user.id,
                                   version=int(version))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _scene_json(row)


@router.post("/api/scenes/{scene_id}/render")
async def render_scene(request: Request, scene_id: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    """Báo giá rồi chạy MỘT cảnh. Cảnh khác không bị đụng và không bị tính tiền."""
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    from platform_core.registry import credit_for
    body = await request.json(); _csrf(request, body); user = _user(request)
    # Góp ý khi bấm "Chạy lại": người dùng nói cái gì cần đổi so với bản trước,
    # thay vì phải sửa tay cả đoạn prompt rồi quên mình đã sửa gì (H19.5).
    feedback = str(body.get("feedback") or "").strip()
    try:
        scene = ssvc.get_owned_scene(db, scene_id, user.id)
        board = ssvc.get_owned_board(db, scene.storyboard_id, user.id)
        prompt = ssvc.compose_prompt(db, scene_id=scene_id, owner_id=user.id,
                                     feedback=feedback)
        refs = ssvc.reference_keys(db, scene_id=scene_id, owner_id=user.id)
    except Exception as exc:
        raise _storyboard_error(exc) from exc
    if len(prompt.strip()) < 8:
        raise HTTPException(status_code=422,
                            detail=_t('Cảnh chưa đủ mô tả để sinh ảnh.'))

    params = {"prompt": prompt[:4000], "aspect_ratio": board.aspect_ratio,
              "count": 1, "owner_id": user.id}
    if refs:
        params["image_keys"] = refs
    model = str(body.get("model") or "").strip()
    if model:
        params["model"] = model

    estimate = int(credit_for(_IMAGE_JOB_TYPE, params))
    if not body.get("confirmed"):
        return {"credit": estimate, "scene_id": scene_id,
                "reference_count": len(refs), "prompt_preview": prompt[:400],
                "confirmed": False}

    _require_run_enabled(user)
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    try:
        job = submit_with_credit(
            db, user_id=user.id, app_slug=MANIFEST.slug,
            job_type=_IMAGE_JOB_TYPE, params=params,
            dedupe_key=dedupe_key_for(_IMAGE_JOB_TYPE, params))
        db.commit()
    except (credit.ThieuCreditError, RegistryError) as exc:
        db.rollback()
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"id": job.id, "status": job.status, "credit": estimate,
            "scene_id": scene_id}


@router.post("/api/scenes/{scene_id}/attach/{job_id}", status_code=201)
async def attach_scene_render(request: Request, scene_id: str, job_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    """Gắn ảnh job đã sinh vào cảnh và ghi một phiên bản mới."""
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    from platform_core.models import JOB_DONE, Job
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        ssvc.get_owned_scene(db, scene_id, user.id)
    except Exception as exc:
        raise _storyboard_error(exc) from exc

    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy job.'))
    if job.status != JOB_DONE:
        raise HTTPException(status_code=409, detail=_t('Job chưa chạy xong.'))
    keys = [k for k in ((job.result or {}).get("image_keys") or []) if k]
    if not keys:
        raise HTTPException(status_code=400, detail=_t('Job không trả về ảnh nào.'))
    try:
        ssvc.record_version(db, scene_id=scene_id, owner_id=user.id,
                            image_key=keys[0], job_id=job_id,
                            feedback=str(body.get("feedback") or ""))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _storyboard_error(exc) from exc
    return _scene_json(ssvc.get_owned_scene(db, scene_id, user.id))


@router.get("/api/scenes/{scene_id}/compare")
def compare_scene_versions(request: Request, scene_id: str, left: int, right: int,
                           _identity: str = Depends(require_login),
                           db: Session = Depends(get_db)):
    """Hai bản đặt cạnh nhau, kèm phần prompt đã đổi (H19.5).

    Nhìn từng bản một rồi bấm khôi phục là đoán; đặt cạnh nhau kèm prompt và
    góp ý mới là so.
    """
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    user = _user(request)
    try:
        return ssvc.compare_versions(db, scene_id=scene_id, owner_id=user.id,
                                     left=int(left), right=int(right))
    except Exception as exc:
        raise _storyboard_error(exc) from exc


@router.post("/api/storyboards/{storyboard_id}/breakdown")
async def breakdown_storyboard(request: Request, storyboard_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    """Chia một câu chuyện tự do thành N cảnh theo khung storyboard (Task 10).

    ⚠️ `storyboard_id` CHỈ dùng để xác nhận quyền sở hữu — `OmmiStoryboard`
    (bảng "khung hình", spec Sec 4.3) KHÔNG có cột lưu "câu chuyện"; plan gốc
    giả định `storyboard.story` nhưng cột đó không tồn tại (đã báo cáo lại,
    xem báo cáo làm I). `story_vi` vì vậy phải do khách gõ trực tiếp trong
    body của request này.
    """
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    from apps.prompt_ai_ommi.tables import OmmiStoryboardFramework
    body = await request.json(); _csrf(request, body); user = _user(request)

    try:
        ssvc.get_owned_board(db, storyboard_id, user.id)
    except Exception as exc:
        raise _storyboard_error(exc) from exc

    framework = db.get(OmmiStoryboardFramework,
                       str(body.get("framework_id") or ""))
    if framework is None:
        # Ban co dau that: "Không tìm thấy khung." (xem bao cao lam I).
        raise HTTPException(status_code=404,
                            detail=_t('Không tìm thấy khung.'))

    story_vi = str(body.get("story_vi") or "").strip()
    if not story_vi:
        # Ban co dau that: "Thiếu nội dung câu chuyện." (xem bao cao lam I).
        raise HTTPException(status_code=422,
                            detail=_t('Thiếu nội dung câu chuyện.'))

    n_scenes = body.get("n_scenes")
    try:
        scenes = bsvc.breakdown(db, framework=framework, story_vi=story_vi,
                               n_scenes=int(n_scenes) if n_scenes else None)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"scenes": scenes}
