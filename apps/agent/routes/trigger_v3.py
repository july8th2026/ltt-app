"""Cua v3 cho trigger workflow: dat LICH (CRON) va cap URL WEBHOOK (UI-12).

Hai canh de mot workflow tu chay ma khong can khach bam nut, di qua MOT cua
tao duy nhat `platform_core.workflow.trigger.tao` — no tu choi `kind` chua
dang ky va tu goi `kiem()` cua chinh loai do NGAY LUC TAO (vi du CRON tu choi
mot bieu thuc sai, hay chu ky duoi 5 phut). Cua HTTP nay khong lam lai phep
kiem do; no chi la lop bao (CSRF, chu so huu, ma loi) quanh `trigger.tao`.

## Token webhook: sinh MOT LAN, chi luu HASH

`trigger.bam_token` bam token bang `sha256`, va hash do la thu DUY NHAT di
vao `WorkflowTrigger.config`. Token THO chi xuat hien trong THAN PHAN HOI cua
chinh luot `POST` da sinh ra no — khong co cua "xem lai token", vi sau lan do
khong con gi de doc lai (dung thiet ke: mot bi mat doc lai duoc la mot bi mat
da ro). Mat token -> tao mot trigger webhook MOI.

⛔ Token KHONG BAO GIO di vao `params` cua node Canvas — chi vao
`WorkflowTrigger.config`, mot BANG KHAC voi `workflow_version` (noi `params`
nam va bi NHAN BAN khi khach bam "Save as"). Cua nay khong dung tham so nao
tu than request lam `config` cho loai `WEBHOOK`; no luon tu sinh token va tu
dung `{"token_hash": ...}` lam `cau_hinh`, bo qua bat ky thu gi khach gui.
"""
from __future__ import annotations

import os
import secrets

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _page_context, _user, _verify_json_csrf, router
from platform_core.i18n import _ as _t
from platform_core.models import Workflow, WorkflowTrigger
from platform_core.workflow import ban_trigger, trigger
from server.auth.session import require_login
from server.deps import get_db
from server.templating import templates

#: So byte ngau nhien TRUOC khi ma hoa base64-url cho token webhook. 32 byte
#: = 256 bit, cung muc voi khoa API cua nen tang — khong phai mot con so rieng
#: bia ra cho tinh nang nay.
DO_DAI_TOKEN = 32


def _cua_toi(db: Session, workflow_id: str, user_id: str) -> Workflow:
    """Workflow da loc theo chu so huu, hoac 404.

    Cung khuon voi `drafts_v3._cua_toi`: *"khong co"* va *"cua nguoi khac"*
    phai tra cung mot 404, neu khong mot nguoi la do duoc id nao co that.
    """
    wf = db.execute(
        select(Workflow).where(Workflow.id == str(workflow_id or ""),
                               Workflow.owner_id == user_id)).scalars().first()
    if wf is None:
        raise HTTPException(status_code=404,
                            detail=_t('Không tìm thấy workflow.'))
    return wf


def _trigger_cua_toi(db: Session, wf: Workflow,
                     trigger_id: str) -> WorkflowTrigger:
    """Trigger thuoc DUNG workflow o tren, hoac 404.

    Loc theo `workflow_id` cua bien `wf` (von da loc theo chu so huu) —
    khong loc rieng theo `owner_id` mot lan nua, de tranh mot id trigger co
    that cua NGUOI KHAC tro ve 404 vi ly do khac voi id khong ton tai (cung
    mot ma loi, hai nguyen nhan, van la mot 404 duy nhat nguoi goi thay).
    """
    t = db.execute(
        select(WorkflowTrigger).where(
            WorkflowTrigger.id == str(trigger_id or ""),
            WorkflowTrigger.workflow_id == wf.id)).scalars().first()
    if t is None:
        raise HTTPException(status_code=404,
                            detail=_t('Không tìm thấy trigger.'))
    return t


def _goc_url(request: Request) -> str:
    """Goc URL cong khai de dan URL webhook chep ra la dung thang.

    Cung cong thuc voi `server/routes/developer/_chung.py::_goc_url`: viet
    cung `https://app.lttstudios.com` se sai tren moi may thu (local, staging)
    va sai mot cach im lang.
    """
    goc = os.environ.get("LTT_BASE_URL", "").strip().rstrip("/")
    if goc:
        return goc
    return str(request.base_url).rstrip("/")


async def _body_khong_bat_buoc(request: Request) -> dict:
    """Than JSON cua mot request co the KHONG CO than (`DELETE`) -> `{}`.

    ⭐ Bat `ValueError` (cha cua `json.JSONDecodeError`) chu ⛔ khong
       `Exception`: do la ca HOP LE duy nhat o day. Bat rong hon se nuot ca
       loi THAT (doc mang, encoding) va bien chung thanh mot `{}` im lang.
    """
    try:
        return await request.json()
    except ValueError:
        return {}


def _trigger_json(t: WorkflowTrigger) -> dict:
    """Dang JSON cong khai cua mot trigger.

    ⛔ `token_hash` KHONG BAO GIO ra khoi ham nay, ke ca da BAM: mot hash so
       khop duoc bang `hmac.compare_digest` van la mot bi mat dang lo mot
       phan — cua `/hooks/wf/{id}` la CONG KHAI, nen phoi no ra `GET` noi bo
       la tang dien tich tan cong cho dung mot cai gia.
    """
    cfg = dict(t.config or {})
    cfg.pop("token_hash", None)
    return {"id": t.id, "workflow_id": t.workflow_id, "kind": t.kind,
            "config": cfg, "enabled": bool(t.enabled),
            "next_fire_at": (t.next_fire_at.isoformat()
                             if t.next_fire_at else None),
            "last_fired_at": (t.last_fired_at.isoformat()
                              if t.last_fired_at else None),
            "loi_lien_tiep": int(t.loi_lien_tiep or 0),
            "created_at": t.created_at.isoformat() if t.created_at else None}


@router.get("/api/v3/workflows/{workflow_id}/triggers")
def v3_trigger_danh_sach(request: Request, workflow_id: str,
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)
    rows = db.execute(
        select(WorkflowTrigger).where(WorkflowTrigger.workflow_id == wf.id)
        .order_by(WorkflowTrigger.created_at.desc())).scalars().all()
    return JSONResponse({"items": [_trigger_json(t) for t in rows]})


@router.post("/api/v3/workflows/{workflow_id}/triggers")
async def v3_trigger_tao(request: Request, workflow_id: str,
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)

    kind = str(body.get("kind") or "").strip()
    cau_hinh = dict(body.get("cau_hinh") or {})

    if kind == "CRON":
        # `trigger.tao` -> `_TheoCron.kiem()` da tu choi bieu thuc sai / chu
        # ky duoi 5 phut, nhung KHONG kiem `bo_lo` — cot do chi duoc doc luc
        # BAN (`ban_trigger.ban_mot`), va mot gia tri la nam trong CSDL se
        # ném `ValueError` MOI VONG bo quet cho toi khi tu tat sau 5 lan lien
        # tiep (spec §11.4). Tu choi no NGAY O CUA la re hon nhieu.
        bo_lo = str(cau_hinh.get("bo_lo") or "chay_mot_lan")
        if bo_lo not in ban_trigger.BO_LO:
            raise HTTPException(status_code=422, detail=_t(
                "`bo_lo` phải là một trong {ds}, không phải {gia_tri!r}"
            ).format(ds=list(ban_trigger.BO_LO), gia_tri=bo_lo))
        cau_hinh["bo_lo"] = bo_lo

    token_tho: str | None = None
    if kind == "WEBHOOK":
        # ⛔ Bo QUA moi thu khach gui trong `cau_hinh` cho loai nay: token
        # luon do MAY sinh, khong bao gio nhan tu client — nhan mot
        # `token_hash` tu client la cho ho tu dat mat khau cho chinh minh
        # ma khong qua kenh sinh ngau nhien nao.
        token_tho = secrets.token_urlsafe(DO_DAI_TOKEN)
        cau_hinh = {"token_hash": trigger.bam_token(token_tho)}

    try:
        t = trigger.tao(db, workflow_id=wf.id, owner_id=user.id, kind=kind,
                        cau_hinh=cau_hinh, enabled=bool(body.get("enabled", True)))
    except ValueError as exc:
        db.rollback()
        # ⛔ 422 kem LY DO, khong bao gio 500: mot bieu thuc cron sai hay mot
        # `kind` chua dang ky la loi CUA NGUOI GOI, khong phai loi he thong.
        raise HTTPException(status_code=422, detail=str(exc)) from None
    db.commit()

    payload = _trigger_json(t)
    if token_tho is not None:
        # Token THO chi song trong CHINH than phan hoi nay. Khong ghi log,
        # khong tra lai o bat ky `GET` nao sau do.
        payload["token"] = token_tho
        payload["webhook_url"] = f"{_goc_url(request)}/hooks/wf/{t.id}"
    return JSONResponse(payload, status_code=201)


@router.patch("/api/v3/workflows/{workflow_id}/triggers/{trigger_id}")
async def v3_trigger_sua(request: Request, workflow_id: str, trigger_id: str,
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    """Bat/tat mot trigger. ⛔ Khong sua `kind` hay `config` o day — mot cau
    hinh CRON/WEBHOOK da tao la BAT BIEN, tao trigger moi neu can doi lich
    hay xoay token."""
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)
    t = _trigger_cua_toi(db, wf, trigger_id)
    if "enabled" in body:
        t.enabled = bool(body["enabled"])
    db.commit()
    return JSONResponse(_trigger_json(t))


@router.delete("/api/v3/workflows/{workflow_id}/triggers/{trigger_id}")
async def v3_trigger_xoa(request: Request, workflow_id: str, trigger_id: str,
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    body = await _body_khong_bat_buoc(request)
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)
    t = _trigger_cua_toi(db, wf, trigger_id)
    db.delete(t)
    db.commit()
    return JSONResponse({"ok": True})


# ── Trang HTML: hai cua cho khach (dat lich · webhook) ──────────────────────

@router.get("/workflows/{workflow_id}/triggers", response_class=HTMLResponse)
def trang_trigger(request: Request, workflow_id: str,
                  _identity: str = Depends(require_login),
                  db: Session = Depends(get_db)):
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)
    context = _page_context(request)
    context.update({"workflow_id": wf.id, "workflow_name": wf.name,
                    "bo_lo_mac_dinh": ban_trigger.BO_LO[0]})
    return templates.TemplateResponse(request, "agent_triggers.html", context)
