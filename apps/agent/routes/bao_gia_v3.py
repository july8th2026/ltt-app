"""`/agent/api/v3/workflows/{id}/bao-gia` — MOT cua bao gia cho CA do thi.

Cua mong dung khuon `bieu_thuc_v3.py`: xac thuc, kiem chu so huu, roi giao cho
`platform_core.workflow.bao_gia`. ⛔ Khong mot phep nhan gia nao o day.

## ⭐ VI SAO MOT CUA CHU KHONG PHAI MOT CUA MOI NODE

`CanvasShell` truoc 24/09 goi `/agent/api/tools/{ten}/quote` **mot lan moi
node**, trong mot effect chay lai moi lan `page.nodes` doi — tuc moi lan nguoi
ta go mot ky tu. Do thi 12 node = **12 request** moi lan bung
(`frontend/agent-canvas/tests/BaoGiaMotCua.test.tsx` do duoc dung con so ay).

⛔ **Debounce khong chua benh nay.** `setTimeout(...,450)` da co san tu truoc;
   no giam TAN SUAT bung, khong giam **do lon** cua mot lan bung.

## 🔴 MOT NGUON GIA

Cua cu tra `credit_for(...) * fanout * (1 + max_retry)`. Hai thua so ay khong
ton tai o bat ky cho nao trong runtime v2 — con so nen tang GIU tien theo la
`bao_gia._gia_node` (`bao_gia_do_thi` ghi no vao `node["gia_tran"]`, va
`cau_noi.nop_job` tu choi job khi `gia_that > gia_tran`). Cua nay goi thang
ham ay. `tests/test_3520::test_gia_KHOP_bao_gia_do_thi` chot rang hai ben
khong the lech nhau.

## ⭐ VI SAO NHAN `document` TRONG THAN YEU CAU

Y het `bieu_thuc_v3.py`: autosave cham 800 ms, nen doc ban da luu nghia la bao
gia tre hon o tham so nguoi dung vua go. Tai lieu gui kem **khong noi quyen** —
`_cua_toi()` van chay truoc.
"""
from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _user, _verify_json_csrf, router
from apps.agent.routes.drafts_v3 import _cua_toi, _tai_lieu_rong
from platform_core.models import WorkflowDraft
from platform_core.workflow import bao_gia as _bao_gia
from server.auth.session import require_login
from server.deps import get_db


@router.post("/api/v3/workflows/{workflow_id}/bao-gia")
async def v3_bao_gia_do_thi(request: Request, workflow_id: str,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)      # 404 neu khong phai cua minh
    tai_lieu = body.get("document")
    if not isinstance(tai_lieu, dict):
        draft = db.get(WorkflowDraft, wf.id)
        tai_lieu = draft.document if draft else _tai_lieu_rong()
    bang = _bao_gia.bang_gia_song(tai_lieu)
    # ⛔ 200 ngay ca khi do thi chua dung cau truc: nguoi dung dang o GIUA mot
    #    thao tac (vua nhan mot node, chua noi canh). Mot 422 o day chi lam
    #    trinh soan hien loi mang cho mot trang thai binh thuong.
    return JSONResponse({"gia": bang.gia, "loi": bang.loi,
                         "loi_do_thi": bang.loi_do_thi})
