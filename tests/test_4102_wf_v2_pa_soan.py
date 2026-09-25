"""P-A task A3 — Agent Designer `/soan` ĐÃ với tới được từ giao diện (25/09/2026).

Cùng bối cảnh với `tests/test_4100` (đọc chú thích ở đó): route
`POST /api/v3/workflows/{workflow_id}/soan` (`agent_v3.py:37`) có sẵn từ P9b
nhưng frontend chưa từng gọi — không nút "Soạn bằng AI" nào trên Canvas. Task
A3 nối dây qua `workflowApi.soanWorkflowV3()`, gọi từ `CanvasShell`.

⛔ Cửa `/soan` KHÔNG publish — nó chỉ ghi `workflow_draft` + trả báo giá
(xem chú thích ở `agent_v3.py`). `CanvasShell` chỉ được NẠP document trả về
vào trình soạn, ⛔ không được tự gọi publish/tạo run theo sau — publish vẫn
phải là một hành động RIÊNG của người dùng (nút "Chạy").
"""
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.
from __future__ import annotations

import pathlib

from tests.test_1728_canvas_khong_goi_duong_chet import (  # noqa: F401
    bang_dinh_tuyen, duong_voi_toi_duoc)

DUONG = "/agent/api/v3/workflows/{}/soan"
SRC = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "agent-canvas" / "src"


def test_duong_soan_co_trong_bang_dinh_tuyen_that(bang_dinh_tuyen):
    assert DUONG in bang_dinh_tuyen


def test_frontend_DA_voi_toi_duoc_duong_soan(duong_voi_toi_duoc):
    assert DUONG in duong_voi_toi_duoc, (
        f"{DUONG} chua duoc goi tu frontend — CanvasShell phai goi "
        "workflowApi.soanWorkflowV3()")
    noi = duong_voi_toi_duoc[DUONG]
    assert any("workflowApi.ts::soanWorkflowV3" == n for n in noi), noi


def test_canvasShell_KHONG_tu_publish_sau_khi_soan():
    """⛔ Vế phòng thủ: `soan*`/`chayWorkflow` (dây `saveWorkflowV3 ->
    publishWorkflowV3 -> createRunV3`) phải là HAI đường riêng. Nếu một bản
    sửa sau này nối `soanBangAI` thẳng vào `publishWorkflowV3`/`createRunV3`,
    bài này bắt được — đọc thân hàm `soanBangAI`, không đọc cả tệp (tệp có
    `publishWorkflowV3` ở chỗ khác, của `chayWorkflow`)."""
    nguon = (SRC / "CanvasShell.tsx").read_text(encoding="utf-8")
    i = nguon.index("soanBangAI=useCallback(")
    than = nguon[i:nguon.index("},[workflow,readOnly,dangSoan", i)]
    assert "soanWorkflowV3(" in than
    assert "publishWorkflowV3(" not in than
    assert "createRunV3(" not in than
