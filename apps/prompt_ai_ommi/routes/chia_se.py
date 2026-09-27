"""
chia_se.py - be mat HTTP cho chia se bang ma (spec S6.6).

Muc dinh gia tri admin luon doc tu CSDL qua is_operator(request), khong bao
gio tin bat cu truong nao trong body - giong het luat da ap dung cho
publish/deprecate cua library.py (routes/library.py).

⚠️ Endpoint `POST /api/library/{kind}/{item_id}/share-level` KHONG nam trong
danh sach S6.6 cua spec theo ten, nhung S4.2 yeu cau "share_level='catalog'
CHI admin dat duoc" ma khong khai duong HTTP nao lam viec do - thieu no thi
cot `share_level` la cot CHET (ghi duoc ma khong ai goi). Day la quyet dinh bo
khuyet da duoc dieu phoi CHOT (PHAN QUYET #4, plan pha 4), khong phai tu y.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _user, get_db, is_operator, require_login, router)


def _share_error(exc: Exception) -> HTTPException:
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    if isinstance(exc, ssvc.ShareNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ssvc.ShareError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.post("/api/share", status_code=201)
async def create_share(request: Request,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = ssvc.sinh_ma(
            db, owner_id=user.id,
            target_kind=str(body.get("target_kind") or ""),
            target_id=str(body.get("target_id") or ""),
            max_uses=body.get("max_uses"),
            expires_in_days=body.get("expires_in_days"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _share_error(exc) from exc
    return {"code": row.code, "expires_at": row.expires_at.isoformat()
           if row.expires_at else None}


@router.delete("/api/share/{code}")
async def revoke_share(request: Request, code: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    _csrf(request); user = _user(request)
    try:
        ssvc.thu_hoi(db, code=code, owner_id=user.id,
                    is_admin=is_operator(request))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _share_error(exc) from exc
    return {"revoked": True}


@router.get("/api/share/{code}")
def preview_share(code: str, db: Session = Depends(get_db),
                  _identity: str = Depends(require_login)):
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    try:
        return ssvc.xem_truoc(db, code=code)
    except Exception as exc:
        raise _share_error(exc) from exc


@router.post("/api/share/{code}/nhan", status_code=201)
async def receive_share(request: Request, code: str,
                        _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = ssvc.nhan(db, code=code, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _share_error(exc) from exc
    return {"id": row.id, "name": getattr(row, "name", getattr(row, "title", ""))}


@router.post("/api/library/{kind}/{item_id}/share-level")
async def set_share_level(request: Request, kind: str, item_id: str,
                          _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    """Dat muc chia se cho MOT muc thu vien. Dung kind cua library.py (meta/
    snippet/style) - anh xa sang target_kind day du cua chia_se.py."""
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    target_kind = {"meta": "meta_prompt", "snippet": "snippet",
                  "style": "style"}.get(kind, kind)
    level = str(body.get("level") or "")
    is_admin = is_operator(request)
    if level == "catalog" and not is_admin:
        # Tai dung nguyen van msgid da dich cua assets_catalog.py:143 - tranh
        # them msgid MOI (banh coc `ban-dich-thieu` chi cho GIAM, xem
        # tools/check_dich_thieu.py; dieu phoi so huu locale/, Lan F khong
        # tu sua). Bao dieu phoi neu can mot msgid rieng, chinh xac hon.
        raise HTTPException(status_code=403,
                            detail=_t('Chỉ admin được publish catalog.'))
    try:
        row = ssvc.dat_muc_chia_se(db, target_kind=target_kind, item_id=item_id,
                                   owner_id=user.id, is_admin=is_admin,
                                   level=level)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _share_error(exc) from exc
    return {"id": row.id, "share_level": row.share_level}
