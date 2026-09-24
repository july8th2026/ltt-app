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


def test_seq_cuoi_khong_co_su_kien_tra_0(db):
    from platform_core.workflow import su_kien
    assert su_kien.seq_cuoi(db, "r-trong") == 0


def test_seq_cuoi_la_MOT_truy_van_tong_hop_khong_doc_toan_bo_lich_su(db):
    """`runs_v3._run_json_v3` gọi `seq_cuoi` mỗi nhịp poll (task-2-review.md,
    Important #1). Cách cũ — `doc(sau=0)` rồi lấy `[-1].seq` — kéo TOÀN BỘ
    hàng (kể cả cột `du_lieu` JSON) về Python chỉ để đọc một số nguyên, chi
    phí tăng theo TUỔI của run.

    Đếm câu SQL thật qua `before_cursor_execute` (khuôn `test_953`): nếu
    `seq_cuoi` thoái hoá về gọi `doc()` rồi lấy phần tử cuối, câu SQL bắt
    được sẽ là `SELECT workflow_event.*` (nhiều cột) thay vì một hàm tổng hợp
    — bắt được cả khi số câu SQL vẫn là 1.
    """
    from sqlalchemy import event

    from platform_core.workflow import su_kien

    for _ in range(300):
        su_kien.ghi(db, "r-nhieu", "NodeResumed")
    db.commit()

    dem: list[str] = []
    bind = db.get_bind()

    def _ghi(conn, cursor, statement, parameters, context, executemany):
        dem.append(statement)

    event.listen(bind, "before_cursor_execute", _ghi)
    try:
        ra = su_kien.seq_cuoi(db, "r-nhieu")
    finally:
        event.remove(bind, "before_cursor_execute", _ghi)

    assert ra == 300
    assert len(dem) == 1, (
        f"seq_cuoi chay {len(dem)} cau SQL - phai la 1")
    assert "max(" in dem[0].lower(), (
        f"seq_cuoi khong con la truy van tong hop: {dem[0]!r}")
