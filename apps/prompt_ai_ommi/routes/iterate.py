"""Vong lap sua kich ban -- be mat web.

`verdict` KHONG hoan credit (spec Sec 6.4). Mot dong `credit.hoan(...)` o day
bien app thanh LLM mien phi vo han, va `test_5321` se do.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core.i18n import _ as _t
from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _require_run_enabled, _user, get_db, require_login, router)
from apps.prompt_ai_ommi.services import briefs as bf
from apps.prompt_ai_ommi.services import iterate as it
from apps.prompt_ai_ommi.tables import OmmiIteration

JOB_TYPE = "prompt_ai_ommi.generate"


def _lay(db, bid: str, user):
    try:
        return bf.doc_brief(db, bid, user.id)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=_t('Không tìm thấy brief.')) from None


@router.post("/api/briefs/{bid}/generate", status_code=201)
async def generate(request: Request, bid: str,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    brief = _lay(db, bid, user)
    kiem = bf.preflight(brief)
    if not kiem["passed"]:
        raise HTTPException(status_code=422, detail=_t('Brief chưa đủ điều kiện.'))
    gia = it.bao_gia(db, brief)
    if not bool(body.get("confirmed")):
        return JSONResponse({"confirmed": False, **gia}, status_code=200)

    feedback = str(body.get("feedback") or "").strip()
    params = {"operation": "iterate" if feedback else "director",
              "story": brief.story_vi, "title": brief.title,
              "goal": brief.goal, "audience": brief.audience,
              "scene_count": brief.target_scenes,
              "duration": brief.target_duration_sec,
              "aspect": brief.aspect_ratio, "language": brief.language,
              "feedback": feedback}
    luot = it.mo_luot(db, brief, feedback, "")
    if gia["was_free"]:
        # Luot mien phi: khong qua `submit_with_credit` (no se giu cho credit).
        from platform_core import jobs as job_api
        job = job_api.submit(db, user_id=user.id, app_slug="prompt_ai_ommi",
                             job_type=JOB_TYPE, params=params)
    else:
        from platform_core import credit
        from platform_core.job_submit import dedupe_key_for, submit_with_credit
        try:
            job = submit_with_credit(
                db, user_id=user.id, app_slug="prompt_ai_ommi",
                job_type=JOB_TYPE, params=params,
                dedupe_key=dedupe_key_for(JOB_TYPE, params))
        except credit.ThieuCreditError as exc:
            db.rollback()
            raise HTTPException(status_code=402, detail=str(exc)) from exc
    luot.job_id = job.id
    db.commit()
    return {"confirmed": True, "credit": luot.credit_charged,
            "was_free": luot.was_free, "iteration_id": luot.id,
            "job_id": job.id, "free_left": it.con_mien_phi(brief)}


@router.post("/api/iterations/{iid}/verdict")
async def verdict(request: Request, iid: str,
                  _identity: str = Depends(require_login),
                  db: Session = Depends(get_db)):
    """Khong tra lai credit da giu trong bat ky truong hop nao. Xem dau tep."""
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    luot = db.get(OmmiIteration, str(iid or ""))
    if luot is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy lượt.'))
    _lay(db, luot.brief_id, user)          # kiem chu so huu qua brief
    try:
        it.dat_phan_quyet(db, luot, str(body.get("verdict") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"iteration": {"id": luot.id, "verdict": luot.verdict,
                          "credit_charged": luot.credit_charged}}


@router.get("/api/briefs/{bid}/iterations")
def lich_su(request: Request, bid: str,
            _identity: str = Depends(require_login),
            db: Session = Depends(get_db)):
    brief = _lay(db, bid, _user(request))
    rows = db.execute(
        select(OmmiIteration).where(OmmiIteration.brief_id == brief.id)
        .order_by(OmmiIteration.seq)).scalars()
    return {"iterations": [
        {"id": r.id, "seq": r.seq, "feedback": r.feedback,
         "credit_charged": r.credit_charged, "was_free": r.was_free,
         "verdict": r.verdict, "job_id": r.job_id,
         "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows], "free_left": it.con_mien_phi(brief)}
