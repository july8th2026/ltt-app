"""routes/briefs.py -- brief va canh kich ban, be mat web (spec Sec 6.4).

`preflight` va `bundle` la buoc MIEN PHI (Q-6) => KHONG goi
`_require_run_enabled`. Goi no nghia la khach gap 503 ngay o buoc khong ton
tien, va se ket luan app hong.

`quote` DUNG LAI `services/iterate.py::bao_gia` -- KHONG tu tinh lai
"2 - free_iterations_used". Hai cho khai cung mot dieu (`LUOT_MIEN_PHI`) la
dung con bo dieu phoi da bat o brief pha 3.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from platform_core.i18n import _ as _t
from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _require_run_enabled, _user, body_khong_bat_buoc, get_db,
    require_login, router)
from apps.prompt_ai_ommi.services import briefs as bf
from apps.prompt_ai_ommi.services import iterate as it
from apps.prompt_ai_ommi.services.bundle import dung_bundle
from apps.prompt_ai_ommi.tables import OmmiMetaPrompt, OmmiStyle


def _ra(b) -> dict:
    return {"id": b.id, "title": b.title, "story_vi": b.story_vi,
           "goal": b.goal, "audience": b.audience,
           "target_duration_sec": b.target_duration_sec,
           "target_scenes": b.target_scenes, "aspect_ratio": b.aspect_ratio,
           "language": b.language, "style_id": b.style_id,
           "meta_prompt_id": b.meta_prompt_id,
           "character_id": b.character_id, "background_id": b.background_id,
           "status": b.status,
           "free_iterations_used": b.free_iterations_used,
           "project_id": b.project_id,
           "updated_at": b.updated_at.isoformat() if b.updated_at else None}


def _lay(db, bid: str, user):
    try:
        return bf.doc_brief(db, bid, user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy brief.')) from None


@router.get("/api/briefs")
def liet_ke(request: Request, archived: bool = False, q: str = "",
           _identity: str = Depends(require_login),
           db: Session = Depends(get_db)):
    user = _user(request)
    rows = bf.liet_ke(db, user.id, archived=archived, q=q)
    return {"briefs": [_ra(b) for b in rows], "total": len(rows)}


@router.post("/api/briefs", status_code=201)
async def tao(request: Request, _identity: str = Depends(require_login),
             db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    b = bf.tao_brief(db, user.id, body); db.commit()
    return {"brief": _ra(b)}


@router.get("/api/briefs/{bid}")
def doc(request: Request, bid: str, _identity: str = Depends(require_login),
       db: Session = Depends(get_db)):
    b = _lay(db, bid, _user(request))
    return {"brief": _ra(b),
           "canh": [{"id": c.id, "position": c.position, "title": c.title,
                    "prompt": c.prompt, "camera": c.camera,
                    "lighting": c.lighting, "mood": c.mood,
                    "duration_seconds": c.duration_seconds}
                   for c in bf.doc_canh(db, b)]}


@router.put("/api/briefs/{bid}")
async def sua(request: Request, bid: str,
             _identity: str = Depends(require_login),
             db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body)
    b = _lay(db, bid, _user(request))
    bf.sua_brief(db, b, body)
    if isinstance(body.get("canh"), list):
        bf.dat_canh(db, b, body["canh"])
    db.commit()
    return {"brief": _ra(b)}


@router.delete("/api/briefs/{bid}")
async def xoa(request: Request, bid: str,
             _identity: str = Depends(require_login),
             db: Session = Depends(get_db)):
    body = await body_khong_bat_buoc(request)
    _csrf(request, body)
    b = _lay(db, bid, _user(request))
    b.archived_at = datetime.now(timezone.utc); db.commit()
    return {"brief": _ra(b)}


@router.post("/api/briefs/{bid}/clone", status_code=201)
async def nhan_ban(request: Request, bid: str,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body)
    b = _lay(db, bid, _user(request))
    ban_sao = bf.nhan_ban(db, b); db.commit()
    return {"brief": _ra(ban_sao)}


@router.post("/api/briefs/{bid}/preflight")
async def preflight(request: Request, bid: str,
                    _identity: str = Depends(require_login),
                    db: Session = Depends(get_db)):
    """MIEN PHI => khong bi khoa boi rollout, khong ghi CSDL."""
    body = await request.json(); _csrf(request, body)
    return bf.preflight(_lay(db, bid, _user(request)))


@router.post("/api/briefs/{bid}/bundle")
async def bundle(request: Request, bid: str,
                 _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    """MIEN PHI (Q-6) => khong bi khoa boi rollout."""
    body = await request.json(); _csrf(request, body)
    b = _lay(db, bid, _user(request))
    meta_id = str(body.get("meta_prompt_id") or b.meta_prompt_id or "")
    meta = db.get(OmmiMetaPrompt, meta_id) if meta_id else None
    if meta is None:
        raise HTTPException(status_code=422,
                            detail=_t('Chưa chọn prompt meta.'))
    style = db.get(OmmiStyle, b.style_id) if b.style_id else None
    return dung_bundle(db, b, meta, style)


@router.post("/api/briefs/{bid}/quote")
async def quote(request: Request, bid: str,
               _identity: str = Depends(require_login),
               db: Session = Depends(get_db)):
    """Gia cho luot TIEP THEO. DUNG LAI `iterate.bao_gia` -- KHONG go tay lai
    "LUOT_MIEN_PHI - free_iterations_used"; hang so do la cua services/iterate.py,
    khai lai o day la hai noi cung khai mot dieu (dung bay dieu phoi da bat).
    """
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    b = _lay(db, bid, user)
    return it.bao_gia(db, b)
