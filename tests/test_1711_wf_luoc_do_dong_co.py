"""Workflow V2 — lược đồ cho động cơ (spec §5.11, §5.3, §5.7, §16)."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def test_run_moi_o_CREATED(db):
    from platform_core.models import WorkflowRun
    r = WorkflowRun(owner_id="u1", workflow_id="w1", version_id="v1")
    db.add(r)
    db.flush()
    assert r.status == "CREATED"


def test_workflow_event_seq_duy_nhat_theo_run(db):
    from sqlalchemy.exc import IntegrityError
    from platform_core.models import WorkflowEvent
    db.add(WorkflowEvent(run_id="r1", seq=1, loai="WorkflowStarted"))
    db.add(WorkflowEvent(run_id="r2", seq=1, loai="WorkflowStarted"))
    db.flush()
    db.add(WorkflowEvent(run_id="r1", seq=1, loai="WorkflowCompleted"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_waitpoint_co_so_nguon(db):
    from platform_core.models import Waitpoint
    wp = Waitpoint(run_id="r1", owner_id="u1", kind="BARRIER")
    db.add(wp)
    db.flush()
    assert wp.so_nguon == 0


def test_snapshot_khong_sua_duoc(db):
    from platform_core.models import NodeRunSnapshot, SnapshotBatBien
    s = NodeRunSnapshot(run_id="r1", node_id="n1", execution_status="READY")
    db.add(s)
    db.flush()
    s.execution_status = "SUCCEEDED"
    with pytest.raises(SnapshotBatBien):
        db.flush()
