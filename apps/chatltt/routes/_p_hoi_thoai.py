"""_p_hoi_thoai.py — CRUD hội thoại. Mọi thứ đi qua `services/hoi_thoai` với `user_id`."""
from __future__ import annotations

from fastapi import Depends, Request

from apps.chatltt.routes._chung import doc_json, json_ok, kiem_csrf, loi, router, uid
from apps.chatltt.services import hoi_thoai as H
from server.auth.session import require_login
from server.deps import get_db


def _tom_tat(h) -> dict:
    return {"id": h.id, "title": h.title, "model_alias": h.model_alias,
            "current_leaf_id": h.current_leaf_id, "archived": h.archived_at is not None,
            "updated_at": h.updated_at.isoformat(), "created_at": h.created_at.isoformat()}


@router.get("/api/hoi-thoai")
def liet_ke(request: Request, tim: str = "", luu_tru: int = 0,
            _=Depends(require_login), db=Depends(get_db)):
    ds = H.liet_ke(db, user_id=uid(request), tim=tim, gom_luu_tru=bool(luu_tru))
    return json_ok({"hoi_thoai": [_tom_tat(h) for h in ds]})


@router.post("/api/hoi-thoai")
async def tao(request: Request, _=Depends(require_login), db=Depends(get_db)):
    than = await doc_json(request)
    if not kiem_csrf(request, than):
        return loi(403, "csrf")
    h = H.tao_hoi_thoai(db, user_id=uid(request), model_alias=str(than.get("model_alias") or ""),
                        title=str(than.get("title") or ""))
    db.commit()
    return json_ok(_tom_tat(h), 201)


@router.get("/api/hoi-thoai/{conv_id}")
def su_that(request: Request, conv_id: str, _=Depends(require_login), db=Depends(get_db)):
    try:
        return json_ok(H.su_that(db, user_id=uid(request), conv_id=conv_id))
    except H.KhongTimThay:
        return loi(404, "khong_tim_thay")


@router.post("/api/hoi-thoai/{conv_id}/doi-ten")
async def doi_ten(request: Request, conv_id: str, _=Depends(require_login), db=Depends(get_db)):
    than = await doc_json(request)
    if not kiem_csrf(request, than):
        return loi(403, "csrf")
    try:
        h = H.doi_ten(db, user_id=uid(request), conv_id=conv_id, title=str(than.get("title") or ""))
    except H.KhongTimThay:
        return loi(404, "khong_tim_thay")
    db.commit()
    return json_ok(_tom_tat(h))


@router.post("/api/hoi-thoai/{conv_id}/luu-tru")
async def luu_tru(request: Request, conv_id: str, _=Depends(require_login), db=Depends(get_db)):
    than = await doc_json(request)
    if not kiem_csrf(request, than):
        return loi(403, "csrf")
    try:
        h = H.luu_tru(db, user_id=uid(request), conv_id=conv_id, luu=bool(than.get("luu", True)))
    except H.KhongTimThay:
        return loi(404, "khong_tim_thay")
    db.commit()
    return json_ok(_tom_tat(h))


@router.post("/api/hoi-thoai/{conv_id}/xoa")
async def xoa(request: Request, conv_id: str, _=Depends(require_login), db=Depends(get_db)):
    than = await doc_json(request)
    if not kiem_csrf(request, than):
        return loi(403, "csrf")
    try:
        H.xoa(db, user_id=uid(request), conv_id=conv_id)
    except H.KhongTimThay:
        return loi(404, "khong_tim_thay")
    db.commit()
    return json_ok({"id": conv_id, "deleted": True})


@router.post("/api/hoi-thoai/{conv_id}/chon-la")
async def chon_la(request: Request, conv_id: str, _=Depends(require_login), db=Depends(get_db)):
    than = await doc_json(request)
    if not kiem_csrf(request, than):
        return loi(403, "csrf")
    try:
        h = H.chon_la(db, user_id=uid(request), conv_id=conv_id,
                      msg_id=str(than.get("message_id") or ""))
    except H.KhongTimThay:
        return loi(404, "khong_tim_thay")
    db.commit()
    return json_ok(_tom_tat(h))
