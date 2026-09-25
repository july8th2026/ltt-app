"""Làn `wfk` — Lỗi 1 (`docs/superpowers/plans/2026-09-25-wf-v2-VAN-HANH.md`,
brief làn wfk): `/soan` (Agent Designer, `apps/agent/routes/agent_v3.py
::v3_soan`) ghi và trả thẳng `document` từ `ke_hoach_v3.chuan_hoa()` —
CanvasShell nạp `document` đó **KHÔNG qua bất kỳ phép chuyển đổi nào**
(`fromV3`/`toV3` trong `frontend/agent-canvas/src/workflowApi.ts` chỉ đổi
`edges`, `nodes` đi xuyên nguyên vẹn — xem docstring `fromV3`).

## Hình dạng ĐÚNG canvas cần — lấy từ mã sống, không suy đoán

`frontend/agent-canvas/src/editorState.ts::nextNode()` (nơi CHÍNH canvas
dựng một node mới từ palette) dựng:

    { id, type: 'tool', position, data: { tool: slugCongCu(nd), params, ... } }

và `CanvasShell.tsx::displayNodes` đọc `node.data.tool` (qua `dinhNghiaCua()`)
**không có optional-chaining trên `node.data`** — `node.data` là `undefined`
(node `chuan_hoa()` sinh ra không có khoá `data`) ném ngay
`TypeError: Cannot read properties of undefined (reading 'tool')` giữa
`useMemo` render → canvas trắng/sập đúng lúc người dùng bấm "Soạn bằng AI".

`nodeDefinition.ts::slugCongCu`: bỏ tiền tố `app.` cho node app/tool, GIỮ
NGUYÊN chuỗi cho node lõi (`core.*`/`trigger.*`/`ai.*`/`connector.*` không có
tiền tố đó) — `data.tool` của `core.if` phải là `"core.if"`, không phải
`"if"`.

## Vì sao không đổi khoá `type`/`params` top-level

`bien_dich._node()` (`platform_core/workflow/bien_dich.py`) đọc node lõi
qua `_node_loi()` — TOÀN BỘ từ khoá top-level (`n["type"]`, `n["params"]`,
`n["credential_ref"]`, `n["settings"]`), **không đụng `data`** — và đọc node
app dạng phẳng (`type` bắt đầu `"app."`) cũng vậy
(`tests/test_1783_wf_nut_dieu_huong.py::_core`/`_app` ghim cả hai hình dạng
sống trên cổng biên dịch thật). Đổi `type` sang `'tool'` cho node lõi sẽ làm
`_node()` lạc sang nhánh `elif loai.startswith("app.")`/`if loai == "tool"`
và tra `cong_cu.tat_ca()` (chỉ có app tool, không có `core.if`) → sinh lỗi
`node_khong_ton_tai` MỚI không có trước bản vá. ⇒ `data` là một khoá THÊM,
không phải một khoá THAY.
"""
from __future__ import annotations

from platform_core.agent import ke_hoach_v3
from platform_core.workflow import bien_dich


def _raw(node_type: str, node_id: str = "n1", **params) -> dict:
    return {"nodes": [{"id": node_id, "type": node_type, "params": params}],
            "edges": []}


def test_node_loi_co_data_tool_giu_nguyen_type():
    """`core.if` — `data.tool` PHẢI bằng đúng `type` (không bỏ tiền tố gì,
    vì `slugCongCu` chỉ bỏ tiền tố `app.`)."""
    doc = ke_hoach_v3.chuan_hoa(_raw("core.if", dieu_kien="1 == 1"))
    node = doc["pages"][0]["nodes"][0]
    assert "data" in node and isinstance(node["data"], dict), (
        "node.data phai la mot object -- thieu no lam `node.data.tool` "
        "nem TypeError luc canvas render (xem docstring module)")
    assert node["data"]["tool"] == "core.if"
    assert node["data"]["params"] == {"dieu_kien": "1 == 1"}
    # Hình dạng CŨ (cổng biên dịch dùng) phải còn nguyên -- không phá `_node_loi`.
    assert node["type"] == "core.if"
    assert node["params"] == {"dieu_kien": "1 == 1"}


def test_node_app_co_data_tool_la_slug_bo_tien_to_app():
    """`app.video.generate` — `data.tool` bỏ tiền tố `app.` (khớp
    `slugCongCu`), y hệt cách `nextNode()` đặt tên cho node app/tool."""
    doc = ke_hoach_v3.chuan_hoa(_raw("app.video.generate", prompt="x"))
    node = doc["pages"][0]["nodes"][0]
    assert node["data"]["tool"] == "video.generate"
    assert node["data"]["params"] == {"prompt": "x"}
    # Hình dạng CŨ (cổng biên dịch dùng) phải còn nguyên.
    assert node["type"] == "app.video.generate"
    assert node["params"] == {"prompt": "x"}


def test_them_khoa_data_khong_pha_cong_bien_dich_node_loi():
    """Bằng chứng CHẠY THẬT qua `bien_dich.bien_dich()`, không suy diễn:
    một khoá `data` thêm vào không làm `core.if` bị từ chối."""
    doc = ke_hoach_v3.chuan_hoa(_raw("core.if", dieu_kien="1 == 1"))
    graph = bien_dich.bien_dich(doc, cong_cu={})
    assert graph["nodes"][0]["type"] == "core.if"
