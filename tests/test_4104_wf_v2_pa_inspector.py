"""P-A task A5 — inspector input/output/log qua `@uiw/react-json-view`
(25/09/2026).

Bối cảnh: `RunV3.su_kien[].du_lieu` (payload thô của MỖI sự kiện) và phần lớn
trường của `RunV3Node` (`job_id`, `attempt`, `waiting_kind`, `het_han`…) đã có
trong dữ liệu `RunV3Panel` nhận mỗi nhịp SSE, nhưng panel đó chỉ vẽ một dòng
văn bản `loai · node_id` cho mỗi sự kiện — bỏ hẳn `du_lieu`. Task A5 mở một
panel THÔ (`RunInspector.tsx`) cho đúng phần bị bỏ đó, không gọi thêm cửa máy
chủ nào (khác A1–A3, vốn mở CỬA MỚI).
"""
from __future__ import annotations

import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "agent-canvas" / "src"


def test_RunInspector_ton_tai_va_dung_react_json_view():
    tep = SRC / "RunInspector.tsx"
    assert tep.exists(), "task A5 phải có frontend/agent-canvas/src/RunInspector.tsx"
    nguon = tep.read_text(encoding="utf-8")
    assert "from '@uiw/react-json-view'" in nguon
    # Không gọi thêm fetch/cửa máy chủ nào — dữ liệu lấy thẳng từ `RunV3` đã có.
    assert "fetch(" not in nguon
    assert "request(" not in nguon


def test_RunInspector_doc_ca_node_lan_su_kien():
    nguon = (SRC / "RunInspector.tsx").read_text(encoding="utf-8")
    assert "run.nodes" in nguon
    assert "run.su_kien" in nguon


def test_CanvasShell_da_noi_RunInspector():
    nguon = (SRC / "CanvasShell.tsx").read_text(encoding="utf-8")
    assert "RunInspector" in nguon
    assert "from './RunInspector'" in nguon


def test_react_json_view_khai_trong_package_json_MIT():
    pkg = SRC.parent / "package.json"
    nguon = pkg.read_text(encoding="utf-8")
    assert '"@uiw/react-json-view"' in nguon
