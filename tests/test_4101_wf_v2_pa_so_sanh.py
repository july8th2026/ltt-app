"""P-A task A2 — `so-sanh` ĐÃ với tới được từ giao diện (25/09/2026).

Cùng bối cảnh với `tests/test_4100` (đọc chú thích ở đó): route
`GET /api/v3/runs/{run_id}/so-sanh?voi=` (`runs_v3.py:658`) có sẵn từ P9b
nhưng frontend chưa từng gọi. Task A2 nối dây qua
`workflowApi.soSanhRunV3()` + component `RunDiff.tsx` (diff bằng
`jsondiffpatch`, xem `docs/superpowers/plans/2026-09-25-wf-v2-VAN-HANH.md`
§2 — thư viện MIT lấy qua npm, không tự viết).
"""
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.
from __future__ import annotations

import pathlib

from tests.test_1728_canvas_khong_goi_duong_chet import (  # noqa: F401
    bang_dinh_tuyen, duong_voi_toi_duoc)

DUONG = "/agent/api/v3/runs/{}/so-sanh"
SRC = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "agent-canvas" / "src"


def test_duong_so_sanh_co_trong_bang_dinh_tuyen_that(bang_dinh_tuyen):
    assert DUONG in bang_dinh_tuyen


def test_frontend_DA_voi_toi_duoc_duong_so_sanh(duong_voi_toi_duoc):
    assert DUONG in duong_voi_toi_duoc, (
        f"{DUONG} chua duoc goi tu frontend — CanvasShell phai goi "
        "workflowApi.soSanhRunV3()")
    noi = duong_voi_toi_duoc[DUONG]
    assert any("workflowApi.ts::soSanhRunV3" == n for n in noi), noi


def test_ham_soSanhRunV3_la_GET_thuan_khong_CSRF():
    """`v3_so_sanh_run` là `@router.get` — GET thuần không cần `X-CSRF-Token`,
    giống `loadRunV3`. Một bản vá lỡ thêm CSRF vào đây không sai chức năng
    (máy chủ bỏ qua header thừa) nhưng lộ ra một hiểu nhầm về GET/POST."""
    nguon = (SRC / "workflowApi.ts").read_text(encoding="utf-8")
    than = nguon[nguon.index("export async function soSanhRunV3("):]
    than = than[:than.index("\n}\n") + 3]
    assert "so-sanh" in than
    assert "voi=" in than
    assert "X-CSRF-Token" not in than


def test_RunDiff_dung_jsondiffpatch_khong_tu_viet_bo_dinh_dang():
    """Task A2 đòi rõ `jsondiffpatch` (spec §2 của plan) — kiểm tĩnh rằng
    component mới THẬT SỰ import thư viện đó, ⛔ không tự viết một bộ so
    JSON tay (đúng luật D4 của plan: không nguồn ⇒ loại khỏi plan)."""
    tep = SRC / "RunDiff.tsx"
    assert tep.exists(), "task A2 phải có frontend/agent-canvas/src/RunDiff.tsx"
    nguon = tep.read_text(encoding="utf-8")
    assert "from 'jsondiffpatch'" in nguon
    assert "jsondiffpatch/formatters/jsonpatch" in nguon


def test_jsondiffpatch_khai_trong_package_json_MIT():
    pkg = SRC.parent / "package.json"
    assert '"jsondiffpatch"' in pkg.read_text(encoding="utf-8")
