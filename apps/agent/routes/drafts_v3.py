"""Cua NOI BO cho ban nhap Canvas **v3** (`WorkflowDraft`) — Dot 5.2 phan C.

## Vi sao phai co mot cua rieng thay vi mo rong cua cu

Hom nay `/agent/api/workflows` phuc vu `AgentWorkflow.document` — Canvas **v2**.
Ban nhap v3 nam o mot BANG KHAC (`workflow_draft`), voi mot canh mang KIEU va
CONG. Hai bang, hai luoc do, hai vong doi:

    AgentWorkflow.document   v2   Plan v1 doc no, `canvas_to_plan()` VUT cong
    WorkflowDraft.document   v3   `dinh_nghia.xuat_ban()` doc no, GIU cong

⇒ Nhet v3 vao cua v2 se buoc mot trong hai ben phai chuyen doi ngam o giua, va
  cho chuyen doi ngam ay chinh la cho cong bi danh roi lan truoc.

## ⭐ `revision` la khoa LAC QUAN, khong phai mot bo dem

Hai tab cung mo thi tab den sau nhan `409` thay vi ghi de am tham phan nguoi kia
vua go. Do la ly do `PUT` doi `If-Match`, y het cua v2 — mot nguoi dang dung ca
hai cua khong phai hoc hai luat.

## ⛔ KHONG co cua `POST /runs` o day

Chay mot workflow di qua `/api/v1/workflows/{id}/runs` (`WF-802`), noi co bao
gia da ky, `Idempotency-Key` va mot khoan giu cho. Mo mot duong chay thu hai o
tang noi bo se la mot cua tieu tien **khong di qua** bat ky thu nao trong ba thu
do — va no se trong y het mot tien nghi cho nguoi dung giao dien.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _user, _verify_json_csrf, router
from platform_core.i18n import _ as _t
from platform_core.models import Workflow, WorkflowDraft
from platform_core.workflow import bao_gia, bien_dich, dinh_nghia
from server.auth.session import require_login
from server.deps import get_db

#: Tai lieu v3 rong ma mot workflow moi bat dau. Giu **cung hinh dang** voi thu
#: `di_tru_m1` sinh ra, de mot ban di tru va mot ban tao moi khong khac nhau o
#: cho nguoi doc phai nho.
def _tai_lieu_rong() -> dict:
    return {"version": 3, "goal": "", "budget_max_credit": 0,
            "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "", "nodes": [], "edges": []}]}


def _cua_toi(db: Session, workflow_id: str, user_id: str) -> Workflow:
    """Workflow da loc theo chu so huu, hoac 404.

    Loc ngay trong truy van: *"khong co"* va *"cua nguoi khac"* phai tra ve cung
    mot 404, neu khong mot nguoi la do duoc id nao co that.
    """
    wf = db.execute(
        select(Workflow).where(Workflow.id == str(workflow_id or ""),
                               Workflow.owner_id == user_id)).scalars().first()
    if wf is None:
        raise HTTPException(status_code=404,
                            detail=_t('Không tìm thấy workflow.'))
    return wf


def _json(wf: Workflow, draft: WorkflowDraft | None) -> dict:
    return {
        "id": wf.id,
        "name": wf.name,
        "published_version_id": wf.published_version_id,
        "revision": int(draft.revision if draft else 0),
        "document": (draft.document if draft else _tai_lieu_rong()),
    }


@router.get("/api/v3/workflows")
def v3_danh_sach(request: Request, luu_tru: int = 0,
                 _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    """Workflow cua nguoi dang dang nhap.

    ⭐ `?luu_tru=1` doi sang **kho luu tru** — hai tap RIENG BIET, khong phai
       mot tap rong hon. Khong co cua nay thi `/mo-lai` ton tai nhung
       KHONG VOI TOI DUOC: mot workflow da luu tru bien mat khoi moi danh sach,
       nen giao dien khong con cho nao de bam mo lai no.
    """
    user = _user(request)
    dieu_kien = (Workflow.archived_at.is_not(None) if luu_tru
                 else Workflow.archived_at.is_(None))
    rows = db.execute(
        select(Workflow).where(Workflow.owner_id == user.id, dieu_kien)
        .order_by(Workflow.updated_at.desc())).scalars().all()
    return JSONResponse({"items": [
        {"id": w.id, "name": w.name,
         "published": bool(w.published_version_id),
         "da_luu_tru": w.archived_at is not None} for w in rows]})


@router.post("/api/v3/workflows")
async def v3_tao(request: Request, _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = dinh_nghia.tao_workflow(db, owner_id=user.id,
                                 name=str(body.get("name") or ""))
    draft = dinh_nghia.luu_draft(db, wf.id,
                                 document=body.get("document") or _tai_lieu_rong(),
                                 revision=0)
    db.commit()
    return JSONResponse(_json(wf, draft), status_code=201)


@router.get("/api/v3/workflows/{workflow_id}")
def v3_doc(request: Request, workflow_id: str,
           _identity: str = Depends(require_login),
           db: Session = Depends(get_db)):
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)
    return JSONResponse(_json(wf, db.get(WorkflowDraft, wf.id)))


@router.put("/api/v3/workflows/{workflow_id}")
async def v3_luu(request: Request, workflow_id: str,
                 _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)
    try:
        rev = int(request.headers.get("If-Match", "").strip('"')
                  or body["revision"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=422,
                            detail=_t('Thiếu số hiệu bản sửa.')) from None
    try:
        draft = dinh_nghia.luu_draft(db, wf.id, document=body.get("document"),
                                     revision=rev)
    except dinh_nghia.XungDotRevision as exc:
        # 409 chu khong 422: khach khong gui sai gi ca — ho gui dung, chi la
        # nguoi khac (hoac chinh ho o tab khac) da ghi truoc.
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from None
    db.commit()
    return JSONResponse(_json(wf, draft))


@router.post("/api/v3/workflows/{workflow_id}/luu-tru")
async def v3_luu_tru(request: Request, workflow_id: str,
                     _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    """Dat `Workflow.archived_at` — chu du an duyet mo be mat nay 28/09/2026.

    ## Vi sao cua nay khong ton tai tu truoc

    `archived_at` co trong luoc do tu dau va **ba** noi da DOC no:
    `v3_danh_sach` (loc khoi danh sach), `tao_run.tao_run` (tu choi run moi) va
    `nut.type_version_thieu` (bo qua khi do drift). Toan bo NGHIA da song;
    thieu dung mot cua DAT no. Lan UI-1 gap cho nay va **dung lai hoi** thay vi
    tu mo mot cua POST — dung luat.

    ## ⛔ Day KHONG phai xoa, va no KHONG dung luot dang chay

    Ban ghi, ban nhap va moi `workflow_version` o lai nguyen ven; `/mo-lai` dua
    tat ca tro lai. Va no chi chan **tao run MOI** — mot luot dang chay chay
    not. Huy mot luot la mot hanh dong khac, co cua rieng; gop hai viec vao mot
    nut la lam khach huy mat mot luot da tieu tien ma khong dinh.

    ## ⭐ Luy dang, va day khong phai chi tien nghi

    Bam lan hai **khong lam moc troi**. Bat ky danh sach nao sap theo
    `archived_at` se doi thu tu moi lan ai do bam lai, va do la mot thay doi
    khong ai yeu cau.
    """
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)
    if wf.archived_at is None:
        wf.archived_at = datetime.now(timezone.utc)
        db.commit()
    return JSONResponse({"id": wf.id, "da_luu_tru": True,
                         "luu_tru_luc": wf.archived_at.isoformat()})


@router.post("/api/v3/workflows/{workflow_id}/mo-lai")
async def v3_mo_lai(request: Request, workflow_id: str,
                    _identity: str = Depends(require_login),
                    db: Session = Depends(get_db)):
    """Xoa `archived_at` — duong ve tu `?luu_tru=1`.

    ⭐ Luy dang y nhu `/luu-tru`: giao dien co the goi tu mot danh sach da cu
       (hai tab, hoac mot tab mo tu truoc khi ai do mo lai o tab khac), va mot
       `409` o day chi bat khach lam lai dung viec ho vua lam.
    """
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)
    if wf.archived_at is not None:
        wf.archived_at = None
        db.commit()
    return JSONResponse({"id": wf.id, "da_luu_tru": False})


@router.post("/api/v3/workflows/{workflow_id}/publish")
async def v3_xuat_ban(request: Request, workflow_id: str,
                      _identity: str = Depends(require_login),
                      db: Session = Depends(get_db)):
    """Dong bang ban nhap thanh mot version BAT BIEN.

    ⭐ Xuat ban lai **cung noi dung** tra ve dung version cu — hanh vi cua
       `UNIQUE (workflow_id, graph_hash)`. Nen bam nut hai lan khong de lai hai
       ban, va do la rang buoc CSDL chu khong phai ma can than.
    """
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)

    # Bien dich + bao gia truoc khi dong bang: `estimated_max` phai bi DONG
    # BANG CUNG graph DA BIEN DICH (`23_24`), vi tinh lai luc chay nghia la
    # mot luot co the vuot mot tran ma nguoi duyet chua tung thay.
    try:
        version = dinh_nghia.xuat_ban_draft(db, wf.id, created_by=user.id)
    except bien_dich.LoiBienDich as exc:
        raise HTTPException(status_code=422, detail={
            "ma": exc.ma, "node_id": exc.node_id, "thong_diep": str(exc)}) from None
    except bao_gia.KhongBaoGiaDuoc as exc:
        raise HTTPException(status_code=422, detail={
            "ma": "khong_bao_gia_duoc", "thong_diep": str(exc)}) from None

    toi_da = int(version.estimated_max or 0)
    uoc = int(math.ceil(toi_da * bao_gia._TY_LE_UOC_TINH))
    wf.published_version_id = version.id
    db.commit()
    return JSONResponse({"workflow_id": wf.id, "version_id": version.id,
                         "credit_max": toi_da,
                         "credit_estimate": uoc})
