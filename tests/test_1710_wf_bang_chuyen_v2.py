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


def test_trang_thai_ket_thuc_khong_co_loi_ra():
    for kt in mtt.NODE_KET_THUC:
        assert kt not in mtt.NODE_CHUYEN
    assert mtt.NODE_DANG_CHAY == frozenset({"QUEUED", "RUNNING", "WAITING"})
