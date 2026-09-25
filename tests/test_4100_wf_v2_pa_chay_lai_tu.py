"""P-A task A1 — `chay-lai-tu` ĐÃ với tới được từ giao diện (25/09/2026).

Bối cảnh (`docs/superpowers/plans/2026-09-25-wf-v2-VAN-HANH.md` §5): route
`POST /api/v3/runs/{run_id}/chay-lai-tu/{node_id}` (`runs_v3.py:864`) đã tồn
tại từ P9b, có test phía máy chủ, nhưng `grep` trong `frontend/agent-canvas/
src/` ra RỖNG — frontend chưa từng gọi. Việc của task A1 là NỐI DÂY: gọi nó từ
`RunV3Panel` (nút "Chạy lại từ đây") qua `workflowApi.chayLaiTuNodeV3`.

⭐ Đây là VẾ NGƯỢC của `tests/test_1728` cho đúng MỘT đường: trước bản sửa
   này, đường `chay-lai-tu` nằm trong `KHONG_TOI_DUOC` (đúng nghĩa, vì không
   ai import `chayLaiTuNodeV3`); giờ nó phải chuyển sang `duong_voi_toi_duoc`
   — dùng LẠI đúng bộ đo của `test_1728`, không viết một bộ đo mới.
"""
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.
from __future__ import annotations

# ⭐ Dùng LẠI đúng hai fixture của `test_1728` (import thẳng hàm, không chép
#   lại logic) — pytest chấp nhận fixture "mượn" thế này: tên có trong
#   namespace module nào thì tệp test ở module đó dùng được.
from tests.test_1728_canvas_khong_goi_duong_chet import (  # noqa: F401
    bang_dinh_tuyen, chuan_hoa, duong_voi_toi_duoc)

#: Hình dạng chuẩn hoá của route máy chủ (`runs_v3.py:864`), khớp cách
#: `chuan_hoa()` thu gọn `${runId}`/`${nodeId}` (TS) và `{run_id}`/`{node_id}`
#: (FastAPI) về cùng `{}`.
DUONG = "/agent/api/v3/runs/{}/chay-lai-tu/{}"


def test_duong_chay_lai_tu_co_trong_bang_dinh_tuyen_that(bang_dinh_tuyen):
    """🔑 Đối chứng: route máy chủ vẫn còn — nếu mất, bài dưới xanh sai lý do."""
    assert DUONG in bang_dinh_tuyen


def test_frontend_DA_voi_toi_duoc_duong_chay_lai_tu(duong_voi_toi_duoc):
    """⭐ Vế đo chính của A1: giao diện giờ VỚI TỚI ĐƯỢC route này.

    Trước bản sửa: `DUONG not in duong_voi_toi_duoc` (route tồn tại ở máy
    chủ, ⛔ nhưng không ai gọi trong `src/**`).
    """
    assert DUONG in duong_voi_toi_duoc, (
        f"{DUONG} chua duoc goi tu frontend — CanvasShell/RunV3Panel phai "
        "goi workflowApi.chayLaiTuNodeV3()")
    noi = duong_voi_toi_duoc[DUONG]
    assert any("workflowApi.ts::chayLaiTuNodeV3" == n for n in noi), noi


def test_ham_chayLaiTuNodeV3_ton_tai_va_dung_duong():
    """Kiểm TĨNH trực tiếp trên `workflowApi.ts`: hàm tồn tại, POST, có
    `Idempotency-Key` — cửa này TIÊU TIỀN (một khoản giữ mới), cùng luật với
    `createRunV3` (xem chú thích ở route)."""
    import pathlib
    src = pathlib.Path(__file__).resolve().parent.parent / "frontend" \
        / "agent-canvas" / "src" / "workflowApi.ts"
    nguon = src.read_text(encoding="utf-8")
    assert "export async function chayLaiTuNodeV3(" in nguon
    than = nguon[nguon.index("export async function chayLaiTuNodeV3("):]
    than = than[:than.index("\n}\n") + 3]
    assert "chay-lai-tu" in than
    assert "Idempotency-Key" in than
    assert "'POST'" in than or '"POST"' in than


def test_khong_theo_so_chuan_hoa_sai(bang_dinh_tuyen):
    """🔑 Đối chứng bộ đo: `chuan_hoa` phải thật sự thu gọn tham số nội suy
    (TS `${...}` / FastAPI `{...}`), không phải một chuỗi trùng hợp — nếu
    không hàm này tự trùng bài trên trong im lặng."""
    assert chuan_hoa(
        "/agent/api/v3/runs/${runId}/chay-lai-tu/${encodeURIComponent(nodeId)}"
    ) == DUONG
    assert chuan_hoa("/agent/api/v3/runs/{run_id}/chay-lai-tu/{node_id}") == DUONG
    assert DUONG in bang_dinh_tuyen
