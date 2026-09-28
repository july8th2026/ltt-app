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
    # 🔴 LAN UI-3 DOI CHO HAM NAY, va bai kiem khong di theo.
    #
    #    Truoc 28/09 dong duoi doc `src/CanvasShell.tsx` va `.index(...)` chuoi
    #    `soanBangAI=useCallback(`. UI-3 tach trinh soan ra `features/editor/`,
    #    nen `CanvasShell.tsx` nay la MOT dong re-export: tep **van ton tai** ma
    #    chuoi thi khong ⇒ `ValueError: substring not found`.
    #
    # ⚠️ Mot phep kiem "duong dan con song khong" ⛔ KHONG bat duoc ca nay — toi
    #    da viet mot bo dem nhu vay va no bao *"38/39 con song"*, tuc "khong con
    #    bai nao mu", trong khi CHINH bai nay dang do. Thu mat la **NOI DUNG**.
    #
    # ⭐ Tinh chat thi KHONG doi: `soanBangAI` phai goi `soanWorkflowV3` va ⛔
    #    KHONG duoc tu publish/tao run. Chi CHO O doi.
    nguon = (SRC / "features/editor/hooks/useWorkflowRun.ts").read_text(
        encoding="utf-8")
    NEO = "const soanBangAI = useCallback("
    assert NEO in nguon, (
        f"⛔ khong thay {NEO!r} — ham da doi cho/doi ten lan nua. Tim lai bang "
        "`grep -rn soanBangAI frontend/agent-canvas/src/` roi neo lai, ⛔ dung xoa bai.")
    i = nguon.index(NEO)
    # ⚠️ Neo DONG bang `}, [` (ket thuc `useCallback`) chu ⛔ khong bang danh sach
    #    phu thuoc cu the (`},[workflow,readOnly,dangSoan`): danh sach phu thuoc
    #    doi moi lan ai do them mot bien, va mot neo nhu vay lam bai nay do vi
    #    mot ly do ⛔ khong lien quan gi den dieu no canh.
    than = nguon[i:nguon.index("}, [", i)]
    assert "soanWorkflowV3(" in than, than
    assert "publishWorkflowV3(" not in than, than
    assert "createRunV3(" not in than, than
