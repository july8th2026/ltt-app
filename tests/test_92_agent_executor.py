"""P6: resumable DAG scheduling, fan-out/join and capability routing."""
from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'agent-executor.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


@pytest.fixture()
def fake_tools(monkeypatch):
    from platform_core.agent import executor
    from platform_core.registry import ToolSpec
    specs = {
        name: ToolSpec(name=name, job_type=f"fake.{name}", description=name,
                       params_schema={}, returns={"output": "text"})
        for name in ("text", "image", "video", "join")
    }
    app = SimpleNamespace(
        slug="fake", error="",
        manifest=SimpleNamespace(tools=tuple(specs.values()), requires=("api",)),
    )
    monkeypatch.setattr(executor, "discover_tools", lambda: specs)
    monkeypatch.setattr(executor.registry, "discover", lambda: [app])
    monkeypatch.setattr(executor.registry, "credit_for", lambda *_args, **_kw: 2)
    return specs


def _approved(db, plan):
    from platform_core import credit
    from platform_core.agent import budget, runs
    from platform_core.agent.validator import ValidationResult
    credit.cap_tay(db, "u1", 200, by="test")
    run = runs.create_run(db, user_id="u1", goal="workflow")
    validation = ValidationResult(True, (), 50, ())
    budget.set_quote(db, run, plan=plan, validation=validation)
    budget.approve(db, run_id=run.id, user_id="u1", approved_by="u1",
                   expected_version=run.version)
    db.commit()
    return run


def _plan(steps):
    return {"version": 1, "budget_max_credit": 100,
            "inputs": {"prompt": "hello"}, "steps": steps}


def test_text_image_video_dung_thu_tu_va_resolve_server_side(db, fake_tools):
    from platform_core import jobs
    from platform_core.agent import executor, runs
    run = _approved(db, _plan([
        {"id": "s1", "tool": "text", "after": [],
         "params": {"value": "$input.prompt"}},
        {"id": "s2", "tool": "image", "after": ["s1"],
         "params": {"value": "$s1.output"}},
        {"id": "s3", "tool": "video", "after": ["s2"],
         "params": {"value": "$s2.output"}},
    ]))
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    assert [row.step_id for row in runs.children(db, run)] == ["s1"]
    first = runs.children(db, run)[0]
    assert first.params["value"] == "hello"
    jobs.complete(db, first, {"output": "script"}); db.commit()
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    second = runs.children(db, run, step_id="s2")[0]
    assert second.params["value"] == "script"
    jobs.complete(db, second, {"output": "image-ref"}); db.commit()
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    assert runs.children(db, run, step_id="s3")[0].params["value"] == "image-ref"


def test_hai_nhanh_song_song_join_cho_du_va_fanout(db, fake_tools):
    from platform_core import jobs
    from platform_core.agent import executor, runs
    run = _approved(db, _plan([
        {"id": "a", "tool": "image", "after": [], "params": {}, "fanout": 2},
        {"id": "b", "tool": "text", "after": [], "params": {}},
        {"id": "j", "tool": "join", "after": ["a", "b"], "params": {}},
    ]))
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    assert len(runs.children(db, run, step_id="a")) == 2
    assert len(runs.children(db, run, step_id="b")) == 1
    jobs.complete(db, runs.children(db, run, step_id="a")[0], {"output": "a1"})
    jobs.complete(db, runs.children(db, run, step_id="a")[1], {"output": "a2"})
    db.commit(); executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    assert not runs.children(db, run, step_id="j")
    jobs.complete(db, runs.children(db, run, step_id="b")[0], {"output": "b"})
    db.commit(); executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    assert len(runs.children(db, run, step_id="j")) == 1


def test_restart_va_tick_lap_khong_submit_lai_step(db, fake_tools):
    from platform_core import jobs
    from platform_core.agent import executor, runs
    run = _approved(db, _plan([
        {"id": "s1", "tool": "text", "after": [], "params": {}},
    ]))
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    assert len(runs.children(db, run)) == 1
    jobs.complete(db, runs.children(db, run)[0], {"output": "done"}); db.commit()
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    assert len(runs.children(db, run)) == 1
    assert run.status == "done"


def test_actual_theo_attempt_va_child_error_co_decision_log(db, fake_tools):
    from platform_core import credit, jobs
    from platform_core.agent import executor, runs
    run = _approved(db, _plan([
        {"id": "s1", "tool": "text", "after": [], "params": {}, "max_retry": 1},
    ]))
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    child = runs.children(db, run)[0]
    jobs.fail(db, child, "provider error"); db.commit()
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    assert run.status == "error" and run.actual == 6  # planning 4 + 1 attempt * 2
    assert {e["event"] for e in run.decision_log[-2:]} == {"child_error", "settle"}
    assert credit.so_du(db, "u1") == 194


def test_cancel_ngan_submit_moi(db, fake_tools):
    from platform_core.agent import budget, executor, runs
    run = _approved(db, _plan([
        {"id": "s1", "tool": "text", "after": [], "params": {}},
    ]))
    budget.cancel(db, run_id=run.id, user_id="u1", actual=4); db.commit()
    executor.tick(db, run_id=run.id, user_id="u1"); db.commit()
    assert not runs.children(db, run)


def test_claim_loc_dung_capability(db, monkeypatch):
    from platform_core import jobs
    api = SimpleNamespace(slug="api-app", error="",
                          manifest=SimpleNamespace(requires=("api",)))
    gpu = SimpleNamespace(slug="gpu-app", error="",
                          manifest=SimpleNamespace(requires=("gpu",)))
    import platform_core.registry as registry
    monkeypatch.setattr(registry, "discover", lambda: [api, gpu])
    jobs.submit(db, user_id="u", app_slug="gpu-app", job_type="x.gpu", params={})
    api_job = jobs.submit(db, user_id="u", app_slug="api-app", job_type="x.api", params={})
    db.commit()
    assert jobs.claim(db, worker_id="api-worker", capabilities={"api"}).id == api_job.id
