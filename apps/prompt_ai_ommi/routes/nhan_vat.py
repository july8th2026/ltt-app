"""routes/nhan_vat.py — endpoint nhan vat / trang phuc / dang / boi canh
(spec Sec 6.5).

CRUD di theo dung khuon cua `routes/bindings.py` va `routes/projects.py`: moi
route ghi co `_csrf`; route tao job co `_require_run_enabled`; doc chu so huu
qua `KeyError -> 404`.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    MANIFEST, _csrf, _require_run_enabled, _user, router, require_login, get_db)
from apps.prompt_ai_ommi.services import nhan_vat as nv


def _row_character(row) -> dict:
    return {"id": row.id, "name": row.name, "gender": row.gender,
           "age_range": row.age_range, "face_description": row.face_description,
           "body_description": row.body_description,
           "hair_description": row.hair_description,
           "outfit_description": row.outfit_description,
           "personality": row.personality,
           "expression_style": row.expression_style,
           "movement_style": row.movement_style,
           "fixed_prompt_block": row.fixed_prompt_block,
           "negative_notes": row.negative_notes,
           "reference_variant_ids": list(row.reference_variant_ids or []),
           "share_level": row.share_level,
           "created_at": row.created_at.isoformat(),
           "updated_at": row.updated_at.isoformat()}


def _row_background(row) -> dict:
    return {"id": row.id, "name": row.name, "location_type": row.location_type,
           "environment_description": row.environment_description,
           "lighting_description": row.lighting_description,
           "color_palette": row.color_palette, "camera_feel": row.camera_feel,
           "important_objects": row.important_objects,
           "fixed_prompt_block": row.fixed_prompt_block,
           "negative_notes": row.negative_notes,
           "reference_variant_ids": list(row.reference_variant_ids or []),
           "share_level": row.share_level,
           "created_at": row.created_at.isoformat(),
           "updated_at": row.updated_at.isoformat()}


def _row_outfit(row) -> dict:
    return {"id": row.id, "character_id": row.character_id, "name": row.name,
           "description": row.description,
           "reference_variant_ids": list(row.reference_variant_ids or []),
           "created_at": row.created_at.isoformat()}


def _row_pose(row) -> dict:
    return {"id": row.id, "name": row.name, "description": row.description,
           "pose_block": row.pose_block, "tags": list(row.tags or []),
           "reference_variant_ids": list(row.reference_variant_ids or []),
           "share_level": row.share_level,
           "created_at": row.created_at.isoformat()}


def _submit_khoa(request: Request, db: Session, *, operation: str,
                 params: dict) -> dict:
    """Nộp job `prompt_ai_ommi.generate` với `operation` chỉ định.

    ⚠️ `operation="character_lock"` — enum của `manifest.py` (làn M) hiện CHƯA
       khai giá trị này (chỉ có `"director"`); dispatch trong `jobs.py::handle`
       cũng chưa gọi `nhan_vat.chay_khoa_nhan_vat`. Cả hai là việc của M3
       ("M3 gọi" — plan Task E2). Route này nộp job đúng hình dạng cho khi
       M3 nối xong; ⛔ không tự sửa `manifest.py`/`jobs.py` (ngoài phạm vi làn E).
    """
    user = _user(request)
    _require_run_enabled(user)
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    params = dict(params); params["operation"] = operation
    params["owner_id"] = user.id
    try:
        job = submit_with_credit(
            db, user_id=user.id, app_slug=MANIFEST.slug,
            job_type="prompt_ai_ommi.generate", params=params,
            dedupe_key=dedupe_key_for("prompt_ai_ommi.generate", params))
    except (credit.ThieuCreditError, RegistryError) as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"id": job.id, "status": job.status, "job_url": f"/jobs/{job.id}"}


# ── Nhân vật ─────────────────────────────────────────────────────────────

@router.get("/api/characters")
async def list_characters(request: Request, _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    user = _user(request)
    return {"characters": [_row_character(row) for row in nv.liet_ke(db, user.id)]}


@router.post("/api/characters", status_code=201)
async def create_character(request: Request, _identity: str = Depends(require_login),
                           db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    row = nv.tao(db, user.id, body)
    db.commit()
    return _row_character(row)


@router.get("/api/characters/{cid}")
async def get_character(request: Request, cid: str,
                        _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    user = _user(request)
    try:
        row = nv.doc(db, cid, user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy nhân vật.')) from None
    return _row_character(row)


@router.put("/api/characters/{cid}")
async def update_character(request: Request, cid: str,
                           _identity: str = Depends(require_login),
                           db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = nv.doc(db, cid, user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy nhân vật.')) from None
    nv.sua(db, row, body)
    db.commit()
    return _row_character(row)


@router.delete("/api/characters/{cid}")
async def delete_character(request: Request, cid: str,
                           _identity: str = Depends(require_login),
                           db: Session = Depends(get_db)):
    body = await body_khong_bat_buoc(request)
    _csrf(request, body); user = _user(request)
    try:
        row = nv.doc(db, cid, user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy nhân vật.')) from None
    from datetime import datetime, timezone
    row.archived_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/api/characters/{cid}/lock")
async def lock_character(request: Request, cid: str,
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = nv.doc(db, cid, user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy nhân vật.')) from None
    params = {"character_id": row.id, "name": row.name, "gender": row.gender,
             "age_range": row.age_range, "face_description": row.face_description,
             "body_description": row.body_description,
             "hair_description": row.hair_description,
             "outfit_description": row.outfit_description,
             "personality": row.personality,
             "expression_style": row.expression_style,
             "movement_style": row.movement_style,
             "negative_notes": row.negative_notes,
             "model": str(body.get("model") or "")}
    return _submit_khoa(request, db, operation="character_lock", params=params)


# ── Trang phục ───────────────────────────────────────────────────────────

@router.get("/api/characters/{cid}/outfits")
async def list_outfits(request: Request, cid: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    user = _user(request)
    try:
        nv.doc(db, cid, user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy nhân vật.')) from None
    return {"outfits": [_row_outfit(row) for row in nv.liet_ke_trang_phuc(db, cid)]}


@router.post("/api/characters/{cid}/outfits", status_code=201)
async def create_outfit(request: Request, cid: str,
                        _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        nv.doc(db, cid, user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy nhân vật.')) from None
    row = nv.tao_trang_phuc(db, cid, body)
    db.commit()
    return _row_outfit(row)


# ── Dáng ─────────────────────────────────────────────────────────────────

@router.get("/api/poses")
async def list_poses(request: Request, _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    user = _user(request)
    return {"poses": [_row_pose(row) for row in nv.liet_ke_dang(db, user.id)]}


@router.post("/api/poses", status_code=201)
async def create_pose(request: Request, _identity: str = Depends(require_login),
                      db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    row = nv.tao_dang(db, user.id, body)
    db.commit()
    return _row_pose(row)


# ── Bối cảnh ─────────────────────────────────────────────────────────────

@router.get("/api/backgrounds")
async def list_backgrounds(request: Request, _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    user = _user(request)
    return {"backgrounds": [_row_background(row)
                            for row in nv.liet_ke_boi_canh(db, user.id)]}


@router.post("/api/backgrounds", status_code=201)
async def create_background(request: Request, _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    row = nv.tao_boi_canh(db, user.id, body)
    db.commit()
    return _row_background(row)


@router.post("/api/backgrounds/{bid}/lock")
async def lock_background(request: Request, bid: str,
                          _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    """⚠️ NỢ CÓ TÊN: plan không khai một hàm-thân-job riêng cho bối cảnh (chỉ
    `chay_khoa_nhan_vat` cho nhân vật), và làn E không được tạo thêm tệp mẫu
    lời nhắc mới ngoài `khoa_nhan_vat.txt`. Tạm ghép các trường mô tả có sẵn
    thành `fixed_prompt_block` KHÔNG gọi LLM, thay vì bịa một mẫu lời nhắc mới
    ngoài phạm vi được giao. Cần một `prompts/khoa_boi_canh.txt` + thân job
    riêng ở lượt sau để bối cảnh cũng được LLM khoá như nhân vật.
    """
    user = _user(request)
    try:
        row = nv.doc_boi_canh(db, bid, user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy bối cảnh.')) from None
    phan = [row.environment_description, row.lighting_description,
           row.color_palette, row.camera_feel, row.important_objects]
    row.fixed_prompt_block = ", ".join(p.strip() for p in phan if p and p.strip())
    db.commit()
    return _row_background(row)
