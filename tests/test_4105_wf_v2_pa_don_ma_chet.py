"""P-A task A6 — bánh cóc TẬP HỢP cho `workflowApi.ts` (25/09/2026).

⭐ Chốt theo TẬP HỢP tên xuất khẩu còn sống, ⛔ không theo SỐ LƯỢNG — một bài
   chỉ đếm `len(...)` sẽ XANH cả khi ai đó xoá nhầm một hàm v3 đang được dùng
   VÀ thêm lại một hàm v2 chết trong cùng một lần sửa (hai việc bù số lượng
   cho nhau). Bài này so hai *tập hợp* riêng:

   1. `DA_XOA` — cụm v2 (`agent_workflows`/`agent_runs`) bị xoá khỏi
      `workflowApi.ts` ở lần này (`createRun`/`approveRun`/`tickRun`/
      `cancelRun`/`runAgain`/`restoreRunAsWorkflow`/`loadRunHistory`/
      `loadRun`/`loadOrCreateWorkflow`/`saveWorkflow`/`validateWorkflow`/
      `RunScope`/`AgentRun`/`AgentRunSummary`) — PHẢI rời khỏi tập xuất khẩu,
      mãi mãi (⛔ ai thêm lại một trong các tên này là mở lại cụm đã đóng —
      `tests/test_2934`/`tests/test_3521` đóng phía máy chủ/đường gọi; bài
      này đóng phía TÊN HÀM).
   2. `PHAI_CON` — tập v3 phải còn sống nguyên vẹn, gồm cả ba hàm mới của
      P-A (`chayLaiTuNodeV3`/`soSanhRunV3`/`soanWorkflowV3`, task A1/A2/A3).

   Nguồn duy nhất: chính `workflowApi.ts` — không chép danh sách tay từ nơi
   khác, chỉ khai HAI tập đối chứng ở trên.
"""
from __future__ import annotations

import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "agent-canvas" / "src"
API_TS = SRC / "workflowApi.ts"

#: `export function|const|class|type NAME` ở CỘT 0 (khai báo thật, không phải
#: một chuỗi nhắc tên trong chú thích).
_EXPORT = re.compile(
    r"^export\s+(?:async\s+)?(?:function|const|class|type)\s+(\w+)", re.M)


def ten_xuat_khau() -> set[str]:
    return set(_EXPORT.findall(API_TS.read_text(encoding="utf-8")))


#: Cụm v2 bị xoá ở task A6 (lằn `wfa`, 25/09/2026) — xem docstring.
DA_XOA = frozenset({
    "createRun", "approveRun", "tickRun", "cancelRun", "runAgain",
    "restoreRunAsWorkflow", "loadRunHistory", "loadRun",
    "loadOrCreateWorkflow", "saveWorkflow", "validateWorkflow", "RunScope",
    "AgentRun", "AgentRunSummary",
})

#: Tập v3 phải còn sống — kể cả ba hàm P-A vừa thêm (A1/A2/A3).
PHAI_CON = frozenset({
    "loadOrCreateWorkflowV3", "loadWorkflowV3", "createWorkflowV3",
    "listWorkflowsV3", "saveWorkflowV3", "publishWorkflowV3",
    "createRunV3", "loadRunV3", "theoDoiRunV3", "cancelRunV3",
    "chayLaiTuNodeV3", "soSanhRunV3", "soanWorkflowV3",
    "baoGiaDoThi", "goiYBieuThuc", "loadPalette",
    "loadPreferences", "savePreferences", "uploadAsset",
    "createAutosave", "normalizeCanvas", "toV3", "fromV3",
    "WorkflowConflictError", "WorkflowCompileError", "RUN_V3_KET_THUC",
})


def test_cum_v2_KHONG_con_trong_tap_xuat_khau():
    con = ten_xuat_khau() & DA_XOA
    assert not con, (
        f"Cum v2 da xoa nhung con xuat khau lai: {sorted(con)} — "
        "xem tests/test_2934 (may chu) / tests/test_3521 (duong goi).")


def test_tap_v3_con_nguyen_ven_ke_ca_ba_ham_PA_moi():
    thieu = PHAI_CON - ten_xuat_khau()
    assert not thieu, f"Mat ham v3 dang song: {sorted(thieu)}"


def test_hai_tap_doi_chung_KHONG_giao_nhau():
    """🔑 Đối chứng: hai tập trên phải rời nhau — nếu không, một tên vừa
    "phải xoá" vừa "phải còn" thì cả hai bài trên là vô nghĩa."""
    assert not (DA_XOA & PHAI_CON)


def test_bo_do_DOC_DUOC_tu_workflowApi(tmp_path):
    """🔑 Đối chứng bộ đo: một `_EXPORT` hỏng (regex sai) đọc ra tập RỖNG và
    hai bài trên xanh vô căn cứ."""
    mau = tmp_path / "mau.ts"
    mau.write_text(
        "export function a(){}\nexport const b = 1\n"
        "export type C = {}\nexport class D {}\n"
        "// export function khong_tinh(){}\n",
        encoding="utf-8")
    ten = set(_EXPORT.findall(mau.read_text(encoding="utf-8")))
    assert ten == {"a", "b", "C", "D"}
    assert len(ten_xuat_khau()) >= len(PHAI_CON)
