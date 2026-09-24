"""`/agent/api/v3/workflows/{id}/bieu-thuc/goi-y` — gợi ý cho trình soạn §6.

Cửa mỏng đúng như `palette_v3.py`: xác thực, kiểm chủ sở hữu, rồi giao cho
`platform_core.workflow.goi_y`. ⛔ Không một bảng tên hàm / tên cổng nào ở đây —
lý do đầy đủ nằm trong docstring của `goi_y.py`.

## ⭐ VÌ SAO NHẬN `document` TRONG THÂN YÊU CẦU

Trình soạn autosave sau 800 ms (`workflowApi.createAutosave`). Đọc bản nháp
**đã lưu** nghĩa là node người dùng vừa thả xuống chưa có trong gợi ý — đúng
lúc họ cần nó nhất. Nên cửa nhận tài liệu đang gõ dở; thiếu thì lui về bản đã
lưu.

⚠️ Tài liệu gửi kèm **không nới quyền**: `_cua_toi()` vẫn chạy trước, nên một
   người lạ không đổi được id workflow để lấy cấu trúc của người khác. Gợi ý
   sinh từ tài liệu CỦA CHÍNH họ là thứ họ đã có trong trình duyệt.

## 🔴 `Accept: application/json` và cú 302

`da7fce81`: yêu cầu API không mang `Accept: application/json` từng bị coi là
điều hướng HTML và nhận `302 /login` — palette rỗng, Canvas trắng, mà phép đo
loopback vẫn xanh. Client gọi cửa này qua `workflowApi.apiFetch()`, nơi
`Accept` được gắn cho MỌI lời gọi; `tests/test_1769` đo rằng thân trả về là
JSON thật.
"""
from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _user, _verify_json_csrf, router
from apps.agent.routes.drafts_v3 import _cua_toi, _tai_lieu_rong
from platform_core.models import WorkflowDraft
from platform_core.workflow import goi_y as _goi_y
from server.auth.session import require_login
from server.deps import get_db


@router.post("/api/v3/workflows/{workflow_id}/bieu-thuc/goi-y")
async def v3_goi_y_bieu_thuc(request: Request, workflow_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    body = await request.json()
    _verify_json_csrf(request, body)
    user = _user(request)
    wf = _cua_toi(db, workflow_id, user.id)      # 404 nếu không phải của mình
    tai_lieu = body.get("document")
    if not isinstance(tai_lieu, dict):
        draft = db.get(WorkflowDraft, wf.id)
        tai_lieu = draft.document if draft else _tai_lieu_rong()
    return JSONResponse(_goi_y.goi_y(tai_lieu, str(body.get("node_id") or "")))
