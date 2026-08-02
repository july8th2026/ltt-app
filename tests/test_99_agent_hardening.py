"""P13 isolated load/rollback drills; no production service or provider calls."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace


def test_ten_runs_progress_concurrently_without_duplicate_submission(tmp_path, monkeypatch):
    db_file = tmp_path / "agent-load.db"
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core import credit
    from platform_core.agent import budget, executor, runs
    from platform_core.agent.validator import ValidationResult
    from platform_core.registry import ToolSpec
    from platform_core.users import tao_nguoi_dung

    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    spec = ToolSpec(name="fake.load", job_type="fake.load", description="load",
                    params_schema={}, returns={"output": "text"})
    app = SimpleNamespace(slug="load", error="",
                          manifest=SimpleNamespace(tools=(spec,), requires=("api",)))
    monkeypatch.setattr(executor, "discover_tools", lambda: {spec.name: spec})
    monkeypatch.setattr(executor.registry, "discover", lambda: [app])
    monkeypatch.setattr(executor.registry, "credit_for", lambda *_a, **_k: 1)
    setup = next(dbmod.get_session()); run_ids = []
    plan = {"version": 1, "goal": "load", "budget_max_credit": 20,
            "steps": [{"id": "s1", "tool": spec.name, "after": [], "params": {},
                       "fanout": 1, "max_retry": 0, "on_fail": "retry_same", "verify": None}]}
    for index in range(10):
        user = tao_nguoi_dung(setup, email=f"load-{index}@example.com",
                              password="Strong-pass-123", is_verified=True)
        credit.cap_tay(setup, user.id, 20, by="load-test")
        run = runs.create_run_capped(setup, user_id=user.id, goal="load",
                                     plan=plan, budget_max=20)
        budget.set_quote(setup, run, plan=plan, validation=ValidationResult(True, (), 1, ()))
        budget.approve(setup, run_id=run.id, user_id=user.id, approved_by=user.id,
                       expected_version=run.version)
        run_ids.append((run.id, user.id))
    setup.commit(); setup.close()

    def tick(item):
        session = next(dbmod.get_session())
        try:
            executor.tick(session, run_id=item[0], user_id=item[1]); session.commit()
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(tick, run_ids))
    verify = next(dbmod.get_session())
    try:
        rows = verify.query(platform_core.models.Job).all()
        assert len(rows) == 10
        assert len({row.dedupe_key for row in rows}) == 10
    finally:
        verify.close(); dbmod.reset_engine()
