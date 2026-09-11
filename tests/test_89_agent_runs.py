"""P3: AgentRun state/checkpoint and child job fan-out."""
from __future__ import annotations

from datetime import timedelta

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'agent-runs.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


def _running(db, user_id="u1"):
    from platform_core.agent import runs
    from platform_core.models import AGENT_AWAITING_APPROVAL, AGENT_RUNNING
    run = runs.create_run(db, user_id=user_id, goal="Tạo video", plan={"version": 1})
    runs.transition(db, run, AGENT_AWAITING_APPROVAL)
    # Structural P3 fixture; P5 production path crosses this boundary via approve.
    run.status = AGENT_RUNNING
    db.commit()
    return run


def test_job_cu_giu_default_safe(db):
    from platform_core import jobs
    job = jobs.submit(db, user_id="u", app_slug="appthu", job_type="appthu.dao_nguoc",
                      params={"text": "abc"})
    db.commit()
    assert (job.parent_id, job.plan_id, job.step_id) == ("", "", "")


def test_agent_run_co_lap_theo_user(db):
    from platform_core.agent import runs
    run = runs.create_run(db, user_id="u1", goal="x")
    db.commit()
    assert runs.get_owned(db, run.id, "u1").id == run.id
    with pytest.raises(runs.AgentRunError):
        runs.get_owned(db, run.id, "u2")


def test_state_machine_hop_le_va_tu_choi_lui(db):
    from platform_core.agent import runs
    from platform_core.models import AGENT_AWAITING_APPROVAL, AGENT_DONE, AGENT_RUNNING
    run = runs.create_run(db, user_id="u1", goal="x")
    runs.transition(db, run, AGENT_AWAITING_APPROVAL)
    with pytest.raises(runs.AgentRunError):
        runs.transition(db, run, AGENT_RUNNING)
    run.approved_at = runs.datetime.now(runs.timezone.utc)
    runs._mark_approved_running(db, run)
    runs.transition(db, run, AGENT_DONE)
    assert run.finished_at is not None
    with pytest.raises(runs.AgentRunError):
        runs.transition(db, run, AGENT_RUNNING)


def test_checkpoint_va_decision_log_khong_mat_du_lieu_cu(db):
    from platform_core.agent import runs
    run = runs.create_run(db, user_id="u1", goal="x")
    runs.checkpoint_step(db, run, "s1", {"status": "done", "result": {"text": "a"}})
    runs.checkpoint_step(db, run, "s2", {"status": "running"})
    runs.append_decision(db, run, {"step": "s1", "reason": "ok"})
    db.commit()
    db.refresh(run)
    assert set(run.checkpoint) == {"s1", "s2"}
    assert run.decision_log == [{"step": "s1", "reason": "ok"}]


def test_chi_running_moi_tao_child(db):
    from platform_core.agent import runs
    run = runs.create_run(db, user_id="u1", goal="x")
    with pytest.raises(runs.AgentRunError):
        runs.submit_child(db, run, step_id="s1", app_slug="appthu",
                          job_type="appthu.dao_nguoc", params={"text": "a"})


def test_child_job_nhan_owner_tu_run_va_khong_tin_client(db):
    from platform_core.agent import runs
    run = _running(db, user_id="owner-a")
    child = runs.submit_child(
        db, run, step_id="s1", app_slug="appthu", job_type="appthu.dao_nguoc",
        params={"text": "a", "owner_id": "attacker"})
    assert child.params["owner_id"] == "owner-a"
    assert (child.origin, child.priority_class) == ("agent", "internal")


def test_bon_child_cung_parent_va_mot_loi_duoc_dem_dung(db):
    from platform_core import jobs
    from platform_core.agent import runs
    run = _running(db)
    parent = runs.submit_child(db, run, step_id="s1", app_slug="appthu",
                               job_type="appthu.dao_nguoc", params={"text": "parent"})
    children = [
        runs.submit_child(db, run, step_id="s2", app_slug="appthu",
                          job_type="appthu.dao_nguoc", params={"text": str(i)},
                          parent_id=parent.id, dedupe_key=f"{run.id}:s2:{i}",
                          max_attempts=1)
        for i in range(4)
    ]
    for child in children[:3]:
        jobs.complete(db, child, {"output": "ok"})
    jobs.fail(db, children[3], "provider error")
    db.commit()
    summary = runs.child_summary(db, run, step_id="s2")
    assert summary == {"total": 4, "done": 3, "error": 1, "pending": 0}
    assert all(child.parent_id == parent.id and child.plan_id == run.id
               for child in children)


def test_orphan_child_duoc_reclaim(db):
    from platform_core import jobs
    from platform_core.agent import runs
    from platform_core.models import JOB_QUEUED
    run = _running(db)
    child = runs.submit_child(db, run, step_id="s1", app_slug="appthu",
                              job_type="appthu.dao_nguoc", params={"text": "x"})
    db.commit()
    claimed = jobs.claim(db, worker_id="dead-worker")
    assert claimed.id == child.id
    claimed.heartbeat_at = jobs._bay_gio() - timedelta(minutes=10)
    db.commit()
    assert jobs.reclaim_orphans(db) == 1
    db.commit()
    assert child.status == JOB_QUEUED and child.attempts == 1
