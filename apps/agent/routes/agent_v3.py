"""Agent Designer v3 (spec §12.2) — cửa soạn draft bằng AI.

⛔ **Cửa này KHÔNG publish.** Spec §12.2: *"Agent không publish: nó ghi draft,
   người dùng xem báo giá rồi bấm publish."* Nên nó ghi `workflow_draft` qua
   `dinh_nghia.luu_draft` và trả **báo giá** — nút publish vẫn là
   `POST /api/v3/workflows/{id}/publish`, một hành động của NGƯỜI.

   Bánh cóc cơ học `test_2923` ghim mệnh đề ấy bằng đồ thị gọi, không bằng lời
   hứa trong tệp này.

⚠️ Thay cho `POST /api/workflows/plan` (Trợ lý AI v2) — cửa cũ sinh **Plan v1**
   trên không gian id `agent_workflows`, thứ giao diện v3 không bao giờ chạm
   tới được (nợ §5 của plan MASTER). Xem `task-5-report.md`.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _user, _verify_json_csrf, router
from apps.agent.routes.drafts_v3 import _cua_toi
from platform_core.agent import ke_hoach_v3
from platform_core.agent.planner import PlannerError
from platform_core.i18n import _ as _t
from platform_core.models import WorkflowDraft
from platform_core.workflow import bao_gia, dinh_nghia
from server.auth.session import require_login
from server.deps import get_db

#: Trần ngân sách một lượt soạn được nêu trong prompt. Đây là **con số kể cho
#: model**, không phải một khoản giữ chỗ: không credit nào bị giữ ở cửa này vì
#: không run nào được mở. Tiền chỉ xuất hiện khi người dùng bấm publish rồi chạy.
NGAN_SACH_MAC_DINH = 100


@router.post("/api/v3/workflows/{workflow_id}/soan")
async def v3_soan(request: Request, workflow_id: str,
                  _identity: str = Depends(require_login),
                  db: Session = Depends(get_db)):
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)

    goal = str(body.get("goal") or "").strip()
    if not goal:
        raise HTTPException(status_code=422, detail=_t('Thiếu mục tiêu.'))
    try:
        ngan_sach = int(body.get("ngan_sach_credit") or NGAN_SACH_MAC_DINH)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422,
                            detail=_t('Ngân sách không hợp lệ.')) from None

    try:
        kq = ke_hoach_v3.soan_draft(db, goal=goal, ngan_sach_credit=ngan_sach)
    except PlannerError as exc:
        # 503 chứ không 500: model nhà bận là một tình huống **có tên**, và
        # người dùng bấm lại sau là cách xử lý đúng.
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except ke_hoach_v3.LoiSoan as exc:
        raise HTTPException(status_code=422, detail={
            "ma": exc.ma, "node_id": exc.node_id,
            "thong_diep": str(exc)}) from None

    # GHI draft — ⛔ không publish. `revision` lấy từ bản hiện có: lượt soạn là
    # một lần ghi như mọi lần ghi khác, nên nó cũng đi qua khoá lạc quan.
    hien = db.get(WorkflowDraft, wf.id)
    try:
        draft = dinh_nghia.luu_draft(db, wf.id, document=kq["document"],
                                     revision=int(hien.revision if hien else 0))
    except dinh_nghia.XungDotRevision as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from None

    gia = None
    if kq["graph"] is not None:
        try:
            bg = bao_gia.bao_gia_do_thi(kq["graph"])
            gia = {"credit_max": bg.toi_da, "credit_estimate": bg.uoc_tinh}
        except bao_gia.KhongBaoGiaDuoc as exc:
            # ⚠️ Báo giá hỏng KHÔNG làm mất bản nháp vừa soạn: người dùng vẫn
            #    sửa được nó trên Canvas. Nó chỉ làm mất con số, và chỗ mất
            #    phải đọc được — `hop_le` xuống `False` kèm mã.
            kq = {**kq, "hop_le": False,
                  "loi": kq["loi"] + ({"ma": "khong_bao_gia_duoc",
                                       "thong_diep": str(exc),
                                       "node_id": ""},)}
    db.commit()
    return JSONResponse({"workflow_id": wf.id, "revision": int(draft.revision),
                         "document": kq["document"], "hop_le": kq["hop_le"],
                         "loi": list(kq["loi"]), "bao_gia": gia})
