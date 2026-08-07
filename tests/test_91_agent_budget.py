"""P5: maximum quote, atomic approval and idempotent settlement."""
from __future__ import annotations

from tests.conftest import bao_dam_user
import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'agent-budget.db').as_posix()}"
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


def _validation(cost=10):
    from platform_core.agent.validator import ValidationResult
    return ValidationResult(True, (), cost, ({"step_id": "s1", "maximum": cost},))


def _quoted(db, *, user_id="u1", budget_max=20, cost=10):
    from platform_core.agent import budget, runs
    plan = {"version": 1, "budget_max_credit": budget_max, "steps": [{"id": "s1"}]}
    run = runs.create_run(db, user_id=user_id, goal="Tạo video")
    budget.set_quote(db, run, plan=plan, validation=_validation(cost))
    db.commit()
    return run


def test_quote_tach_planning_va_chua_giu_credit(db):
    from platform_core import credit
    run = _quoted(db)
    assert run.estimated == 14
    assert run.decision_log[-1]["planning_cost"] == 4
    assert run.decision_log[-1]["execution_max"] == 10
    assert credit.so_da_giu(db, run.id) == 0


def test_quote_tu_choi_tong_chi_phi_vuot_budget(db):
    from platform_core.agent import budget, runs
    run = runs.create_run(db, user_id="u", goal="x")
    with pytest.raises(budget.BudgetError, match="vượt ngân sách"):
        budget.set_quote(
            db, run,
            plan={"version": 1, "budget_max_credit": 13, "steps": []},
            validation=_validation(10),
        )


def test_approve_lap_lai_chi_mot_hold(db):
    from platform_core import credit
    from platform_core.agent import budget
    bao_dam_user(db, "u1"); credit.cap_tay(db, "u1", 30, by="test")
    run = _quoted(db)
    budget.approve(db, run_id=run.id, user_id="u1", approved_by="u1",
                   expected_version=run.version)
    db.commit()
    budget.approve(db, run_id=run.id, user_id="u1", approved_by="u1",
                   expected_version=run.version)
    db.commit()
    assert credit.so_da_giu(db, run.id) == 14
    assert credit.so_du(db, "u1") == 16


def test_thieu_credit_van_awaiting_va_khong_hold(db):
    from platform_core import credit
    from platform_core.agent import budget
    from platform_core.models import AGENT_AWAITING_APPROVAL
    run = _quoted(db)
    with pytest.raises(credit.ThieuCreditError):
        budget.approve(db, run_id=run.id, user_id="u1", approved_by="u1",
                       expected_version=run.version)
    db.rollback()
    db.refresh(run)
    assert run.status == AGENT_AWAITING_APPROVAL
    assert credit.so_da_giu(db, run.id) == 0


def test_sua_plan_tang_version_va_vo_hieu_approval_cu(db):
    from platform_core.agent import budget
    run = _quoted(db)
    old_version = run.version
    plan = {"version": 1, "budget_max_credit": 30, "steps": [{"id": "s2"}]}
    budget.set_quote(db, run, plan=plan, validation=_validation(12))
    assert run.version == old_version + 1
    assert run.approved_at is None
    with pytest.raises(budget.BudgetError, match="phiên bản mới"):
        budget.approve(db, run_id=run.id, user_id="u1", approved_by="u1",
                       expected_version=old_version)


def test_user_khac_khong_approve_hoac_cancel_duoc(db):
    from platform_core.agent import budget, runs
    run = _quoted(db)
    with pytest.raises(runs.AgentRunError):
        budget.approve(db, run_id=run.id, user_id="u2", approved_by="u2",
                       expected_version=run.version)
    with pytest.raises(runs.AgentRunError):
        budget.cancel(db, run_id=run.id, user_id="u2")


def test_cancel_truoc_approval_khong_ghi_credit(db):
    from platform_core import credit
    from platform_core.agent import budget
    from platform_core.models import AGENT_CANCELLED
    run = _quoted(db)
    budget.cancel(db, run_id=run.id, user_id="u1")
    db.commit()
    assert run.status == AGENT_CANCELLED
    assert credit.so_da_giu(db, run.id) == 0


def test_chan_truoc_provider_va_quyet_toan_idempotent(db):
    from platform_core import credit
    from platform_core.agent import budget
    from platform_core.models import AGENT_CANCELLED
    bao_dam_user(db, "u1"); credit.cap_tay(db, "u1", 30, by="test")
    run = _quoted(db)
    budget.approve(db, run_id=run.id, user_id="u1", approved_by="u1",
                   expected_version=run.version)
    with pytest.raises(budget.BudgetError, match="vượt mức"):
        budget.ensure_can_spend(run, 15)
    budget.settle(db, run_id=run.id, user_id="u1", actual=7,
                  final_status=AGENT_CANCELLED)
    db.commit()
    budget.settle(db, run_id=run.id, user_id="u1", actual=7,
                  final_status=AGENT_CANCELLED)
    db.commit()
    assert run.actual == 7
    assert credit.so_du(db, "u1") == 23
