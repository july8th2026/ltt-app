"""Budget, approval and settlement boundary for AgentRun."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session as DbSession

from platform_core import credit
from platform_core.agent import runs
from platform_core.agent.validator import ValidationResult
from platform_core.models import (
    AGENT_AWAITING_APPROVAL, AGENT_CANCELLED, AGENT_DONE, AGENT_ERROR,
    AGENT_RUNNING, AgentRun,
)

PLANNING_COST = 4
_TERMINAL = {AGENT_DONE, AGENT_CANCELLED, AGENT_ERROR}


class BudgetError(ValueError):
    pass


def quote(plan: dict, validation: ValidationResult,
          *, planning_cost: int = PLANNING_COST) -> dict:
    """Return the immutable maximum quote shown before approval."""
    if not validation.valid:
        raise BudgetError("Không thể báo giá cho plan chưa hợp lệ.")
    planning_cost = int(planning_cost)
    if planning_cost < 0:
        raise BudgetError("Chi phí planning không hợp lệ.")
    execution = int(validation.estimated_max_credit)
    maximum = planning_cost + execution
    try:
        limit = int(plan.get("budget_max_credit", 0))
    except (AttributeError, TypeError, ValueError) as exc:
        raise BudgetError("Ngân sách plan không hợp lệ.") from exc
    if limit < maximum:
        raise BudgetError(f"Cần tối đa {maximum}, vượt ngân sách {limit}.")
    return {
        "planning_cost": planning_cost,
        "execution_max": execution,
        "maximum": maximum,
        "steps": [dict(item) for item in validation.step_costs],
    }


def set_quote(db: DbSession, run: AgentRun, *, plan: dict,
              validation: ValidationResult,
              planning_cost: int = PLANNING_COST) -> AgentRun:
    """Attach/replace a validated quote; replacement invalidates approval."""
    if run.status not in (runs.AGENT_PLANNING, AGENT_AWAITING_APPROVAL):
        raise BudgetError("Chỉ được sửa plan trước khi chạy.")
    priced = quote(plan, validation, planning_cost=planning_cost)
    if run.status == AGENT_AWAITING_APPROVAL:
        run.version += 1
    run.plan = dict(plan)
    run.budget_max = int(plan["budget_max_credit"])
    run.estimated = priced["maximum"]
    run.approved_at = None
    run.approved_by = ""
    run.decision_log = list(run.decision_log or []) + [{
        "event": "quote", "version": run.version, **priced,
    }]
    if run.status == runs.AGENT_PLANNING:
        runs.transition(db, run, AGENT_AWAITING_APPROVAL)
    else:
        db.flush()
    return run


def approve(db: DbSession, *, run_id: str, user_id: str,
            approved_by: str, expected_version: int) -> AgentRun:
    """Atomically lock the run and make exactly one full-budget hold."""
    run = runs.get_owned(db, run_id, user_id, lock=True)
    if run.status == AGENT_RUNNING and run.approved_at is not None:
        if run.version != int(expected_version):
            raise BudgetError("Plan đã thay đổi; cần phê duyệt phiên bản mới.")
        return run
    if run.status != AGENT_AWAITING_APPROVAL:
        raise BudgetError("AgentRun không chờ phê duyệt.")
    if run.version != int(expected_version):
        raise BudgetError("Plan đã thay đổi; cần phê duyệt phiên bản mới.")
    if run.estimated < 0 or run.estimated > run.budget_max:
        raise BudgetError("Báo giá không hợp lệ hoặc vượt ngân sách.")
    credit.giu_cho(db, run.user_id, run.estimated, run.id)
    run.approved_at = datetime.now(timezone.utc)
    run.approved_by = (approved_by or user_id)[:36]
    runs._mark_approved_running(db, run)
    return run


def ensure_can_spend(run: AgentRun, prospective_actual: int) -> None:
    """Mandatory pre-provider-call guard: actual can never exceed the hold."""
    if run.status != AGENT_RUNNING:
        raise BudgetError("AgentRun chưa được phê duyệt để chi.")
    if int(prospective_actual) < 0 or int(prospective_actual) > run.estimated:
        raise BudgetError("Chi phí thực tế sẽ vượt mức tối đa đã phê duyệt.")


def settle(db: DbSession, *, run_id: str, user_id: str, actual: int,
           final_status: str = AGENT_DONE) -> AgentRun:
    """Settle once and refund the unused hold for done/cancel/error."""
    run = runs.get_owned(db, run_id, user_id, lock=True)
    actual = int(actual)
    if final_status not in _TERMINAL:
        raise BudgetError("Trạng thái quyết toán không hợp lệ.")
    if run.status in _TERMINAL:
        if run.status != final_status or run.actual != actual:
            raise BudgetError("AgentRun đã được quyết toán với kết quả khác.")
        return run
    ensure_can_spend(run, actual)
    credit.quyet_toan(db, run.user_id, run.id, actual)
    run.actual = actual
    runs.append_decision(db, run, {
        "event": "settle", "status": final_status, "actual": actual,
        "reserved": run.estimated, "refunded": max(0, run.estimated - actual),
    })
    runs.transition(db, run, final_status)
    return run


def cancel(db: DbSession, *, run_id: str, user_id: str,
           actual: int = 0) -> AgentRun:
    """Cancel an owned run; pre-approval cancellation never touches credit."""
    run = runs.get_owned(db, run_id, user_id, lock=True)
    if run.status == AGENT_AWAITING_APPROVAL:
        if int(actual) != 0:
            raise BudgetError("Run chưa duyệt không thể có chi phí thực tế.")
        return runs.transition(db, run, AGENT_CANCELLED)
    if run.status == AGENT_CANCELLED:
        if run.actual != int(actual):
            raise BudgetError("AgentRun đã hủy với chi phí khác.")
        return run
    return settle(db, run_id=run_id, user_id=user_id, actual=actual,
                  final_status=AGENT_CANCELLED)
