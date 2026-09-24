"""Workflow V2 — bảng chuyển trạng thái theo spec §5.2–5.3 (22/09)."""
from __future__ import annotations

import pytest

from platform_core.workflow import may_trang_thai as mtt


def test_run_khong_con_VALIDATING_va_queued_thuong():
    assert "VALIDATING" not in mtt.RUN_CHUYEN
    assert "queued" not in mtt.RUN_CHUYEN
    assert mtt.RUN_CHUYEN["CREATED"] == frozenset({"QUEUED", "FAILED", "CANCELLED"})


def test_node_co_WAITING_va_RETRY_SCHEDULED_khong_co_RESUMING():
    assert "RUNNING_WITH_WAITPOINTS" not in mtt.NODE_CHUYEN
    assert "RESUMING" not in mtt.NODE_CHUYEN
    assert mtt.NODE_CHUYEN["RUNNING"] >= {"WAITING", "RETRY_SCHEDULED", "ABANDONED"}
    assert mtt.NODE_CHUYEN["RETRY_SCHEDULED"] == frozenset({"READY", "CANCELLED"})
    assert mtt.NODE_CHUYEN["WAITING"] == frozenset(
        {"RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"})


@pytest.mark.parametrize("tu,sang", [
    ("QUEUED", "SUCCEEDED"), ("QUEUED", "FAILED"), ("QUEUED", "ABANDONED"),
    ("QUEUED", "RETRY_SCHEDULED"), ("READY", "RUNNING"), ("READY", "WAITING"),
])
def test_chuyen_moi_hop_le(tu, sang):
    # Job có thể kết thúc trước khi động cơ kịp thấy nó chạy (spec §5.8).
    assert sang in mtt.NODE_CHUYEN[tu]


#: Trạng thái KẾT THÚC được phép có lối ra, và lối ra của nó là gì.
#:
#: 🔴 SIẾT 24/09/2026 (plan wf-v2 P8 Task 3). Trước đó bài này nói *"KHÔNG
#:    trạng thái kết thúc nào có lối ra"* — một mệnh đề mạnh và đúng cho tới
#:    khi spec §12.4 đòi Supervisor *"thử lại node (trong `retry.max` còn
#:    lại)"* và *"bỏ qua nhánh node có `settings.khong_quan_trong = true"*.
#:    Cả hai chỉ có nghĩa khi node đã `FAILED`.
#:
#: ⛔ Nên bài không bị NỚI thành "kết thúc có thể có lối ra"; nó đổi thành một
#:    **bản khai chính xác**: đúng một trạng thái, đúng hai lối. `ABANDONED`
#:    (provider CÓ THỂ đã nhận), `CANCELLED`, `SUCCEEDED`, `SKIPPED` vẫn là ngõ
#:    cụt tuyệt đối — và `FAILED` **không** có lối `READY` (quay thẳng về READY
#:    là bỏ qua `retry.max`, backoff và `_khoa_idem` theo lượt).
NGOAI_LE_KET_THUC = {"FAILED": frozenset({"RETRY_SCHEDULED", "SKIPPED"})}


def test_trang_thai_ket_thuc_khong_co_loi_ra():
    for kt in mtt.NODE_KET_THUC:
        if kt in NGOAI_LE_KET_THUC:
            assert mtt.NODE_CHUYEN[kt] == NGOAI_LE_KET_THUC[kt], kt
            continue
        assert kt not in mtt.NODE_CHUYEN, kt
    # 🔑 Đối chứng: danh sách ngoại lệ không được phình ra bằng cách liệt kê
    #    một trạng thái vốn KHÔNG phải trạng thái kết thúc.
    assert set(NGOAI_LE_KET_THUC) <= mtt.NODE_KET_THUC
    assert mtt.NODE_DANG_CHAY == frozenset({"QUEUED", "RUNNING", "WAITING"})
