"""Workflow V2 — workflow_event chỉ-thêm, seq tăng, dữ liệu đã che (spec §5.11)."""
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.
from __future__ import annotations

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401  (fixture)


def test_seq_tang_theo_run(db):
    from platform_core.workflow import su_kien
    a = su_kien.ghi(db, "r1", "WorkflowStarted")
    b = su_kien.ghi(db, "r1", "WorkflowCompleted", du_lieu={"status": "SUCCEEDED"})
    c = su_kien.ghi(db, "r2", "WorkflowStarted")
    assert (a.seq, b.seq, c.seq) == (1, 2, 1)
    assert [e.loai for e in su_kien.doc(db, "r1", sau=1)] == ["WorkflowCompleted"]


def test_loai_la_bi_tu_choi(db):
    from platform_core.workflow import su_kien
    with pytest.raises(ValueError):
        su_kien.ghi(db, "r1", "KhongCo")


def test_du_lieu_bi_che(db):
    from platform_core.workflow import su_kien
    e = su_kien.ghi(db, "r1", "WorkflowFailed",
                    du_lieu={"authorization": "Bearer abc", "ly_do": "x"})
    assert "abc" not in str(e.du_lieu)
