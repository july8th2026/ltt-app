"""Resumable DAG scheduler for approved AgentRun plans."""
from __future__ import annotations

import copy
import re

from sqlalchemy.orm import Session as DbSession

from platform_core import registry
from platform_core.agent import budget, runs
from platform_core.agent.tools import discover_tools
from platform_core.agent import verifier
from platform_core.models import (
    AGENT_CANCELLED, AGENT_DONE, AGENT_ERROR, AGENT_RUNNING,
    JOB_DONE, JOB_ERROR, AgentRun, Job,
)

_REFERENCE = re.compile(r"^\$(input|[a-z][a-z0-9_-]{0,31})\.([a-z][a-z0-9_]*)$")


class ExecutorError(ValueError):
    pass


def _steps(run: AgentRun) -> list[dict]:
    return list((run.plan or {}).get("steps") or [])


def _resolve_value(value, run: AgentRun):
    if isinstance(value, dict):
        return {key: _resolve_value(item, run) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item, run) for item in value]
    if not isinstance(value, str):
        return value
    match = _REFERENCE.fullmatch(value)
    if not match:
        return value
    source, port = match.groups()
    if source == "input":
        inputs = (run.plan or {}).get("inputs") or {}
        if port not in inputs:
            raise ExecutorError(f"Thiếu input {port}.")
        return copy.deepcopy(inputs[port])
    state = (run.checkpoint or {}).get(source) or {}
    if state.get("status") != "done":
        raise ExecutorError(f"Step {source} chưa hoàn tất.")
    outputs = state.get("outputs") or {}
    if port not in outputs:
        raise ExecutorError(f"Step {source} không có output {port}.")
    return copy.deepcopy(outputs[port])


def resolve_params(run: AgentRun, step: dict) -> dict:
    return _resolve_value(step.get("params") or {}, run)


def _aggregate(rows: list[Job]) -> dict:
    keys = set().union(*(set((row.result or {}).keys()) for row in rows))
    if len(rows) == 1:
        return {key: copy.deepcopy((rows[0].result or {}).get(key)) for key in keys}
    return {
        key: [copy.deepcopy((row.result or {}).get(key)) for row in rows]
        for key in keys
    }


def _sync_children(db: DbSession, run: AgentRun, *, verify_kwargs: dict) -> None:
    checkpoint = dict(run.checkpoint or {})
    for step in _steps(run):
        sid = step["id"]
        all_rows = runs.children(db, run, step_id=sid)
        state = checkpoint.get(sid) or {}
        selected = set(state.get("job_ids") or [])
        rows = [row for row in all_rows if row.id in selected] if selected else all_rows
        if not rows:
            continue
        if any(row.status == JOB_ERROR for row in rows):
            checkpoint[sid] = {
                "status": "error",
                "job_ids": [row.id for row in rows],
                "error": next(row.error for row in rows if row.status == JOB_ERROR),
                "attempt": int(state.get("attempt", 0)),
            }
        elif len(rows) == int(step.get("fanout", 1)) and all(
                row.status == JOB_DONE for row in rows):
            outputs = _aggregate(rows)
            verify_config = step.get("verify")
            if not verify_config:
                checkpoint[sid] = {
                    "status": "done", "job_ids": [row.id for row in rows],
                    "outputs": outputs, "attempt": int(state.get("attempt", 0)),
                }
                continue
            results = verifier.verify(outputs, verify_config, **verify_kwargs)
            last = results[-1]
            verify_credit = sum(result.credit for result in results)
            event = {
                "event": "verify", "step_id": sid,
                "attempt": int(state.get("attempt", 0)),
                "checks": [result.public_dict() for result in results],
                "credit": verify_credit,
            }
            runs.append_decision(db, run, event)
            if last.passed:
                checkpoint[sid] = {
                    "status": "done", "job_ids": [row.id for row in rows],
                    "outputs": outputs, "attempt": int(state.get("attempt", 0)),
                    "verification": event,
                }
            else:
                attempt = int(state.get("attempt", 0))
                can_retry = last.fault != "policy" and attempt < int(step.get("max_retry", 0))
                checkpoint[sid] = {
                    "status": "retry_needed" if can_retry else "error",
                    "job_ids": [row.id for row in rows], "outputs": outputs,
                    "attempt": attempt, "fault": last.fault,
                    "reason": last.reason, "action": step.get("on_fail", "retry_same"),
                }
        else:
            checkpoint[sid] = {
                "status": "submitted", "job_ids": [row.id for row in rows],
                "attempt": int(state.get("attempt", 0)),
            }
    run.checkpoint = checkpoint
    db.flush()


def actual_cost(run: AgentRun, rows: list[Job]) -> int:
    """Planning plus actual terminal child attempts, never the quoted maximum."""
    planning = next((int(event.get("planning_cost", 0))
                     for event in reversed(run.decision_log or [])
                     if event.get("event") == "quote"), 0)
    total = planning
    for row in rows:
        if row.status not in (JOB_DONE, JOB_ERROR):
            continue
        unit = registry.credit_for(row.job_type, row.params)
        attempts = row.attempts + (1 if row.status == JOB_DONE else 0)
        total += unit * attempts
    total += sum(int(event.get("credit", 0)) for event in (run.decision_log or [])
                 if event.get("event") == "verify")
    return total


def _advance_branch_states(db: DbSession, run: AgentRun) -> None:
    """Mark branches that can no longer match without executing or spending."""
    checkpoint = dict(run.checkpoint or {})
    changed = True
    while changed:
        changed = False
        for step in _steps(run):
            sid = step["id"]
            if checkpoint.get(sid):
                continue
            success_states = [str((checkpoint.get(dep) or {}).get("status", ""))
                              for dep in step.get("after", []) or []]
            error_states = [str((checkpoint.get(dep) or {}).get("status", ""))
                            for dep in step.get("after_error", []) or []]
            reason = ""
            if any(status in {"error", "skipped"} for status in success_states):
                reason = "success dependency không hoàn tất"
            elif any(status in {"done", "skipped"} for status in error_states):
                reason = "error dependency không phát sinh lỗi"
            if reason:
                checkpoint[sid] = {"status": "skipped", "reason": reason}
                runs.append_decision(db, run, {
                    "event": "branch_skipped", "step_id": sid, "reason": reason,
                })
                changed = True
    run.checkpoint = checkpoint


def _terminal_status(run: AgentRun) -> str | None:
    steps = _steps(run); checkpoint = run.checkpoint or {}
    terminal = {"done", "error", "skipped"}
    if not steps or any(str((checkpoint.get(step["id"]) or {}).get("status", ""))
                        not in terminal for step in steps):
        return None
    errored = {sid for sid,state in checkpoint.items() if state.get("status") == "error"}
    unhandled = []
    for sid in errored:
        handlers = [step["id"] for step in steps if sid in (step.get("after_error") or [])]
        if not any((checkpoint.get(target) or {}).get("status") == "done" for target in handlers):
            unhandled.append(sid)
    return AGENT_ERROR if unhandled else AGENT_DONE


def tick(db: DbSession, *, run_id: str, user_id: str,
         max_parallel: int = 4, probe=None, judge=None, face_compare=None,
         retry_adapter=None) -> AgentRun:
    """Advance one run transactionally; safe to call repeatedly after restart."""
    run = runs.get_owned(db, run_id, user_id, lock=True)
    if run.status in (AGENT_DONE, AGENT_ERROR, AGENT_CANCELLED):
        return run
    if run.status != AGENT_RUNNING:
        raise ExecutorError("AgentRun chưa được phê duyệt.")
    _sync_children(db, run, verify_kwargs={
        "probe": probe, "judge": judge, "face_compare": face_compare,
    })
    _advance_branch_states(db, run)
    all_children = runs.children(db, run)
    steps = _steps(run)
    done = {sid for sid, state in (run.checkpoint or {}).items()
            if state.get("status") == "done"}
    errored = {sid for sid, state in (run.checkpoint or {}).items()
               if state.get("status") == "error"}
    terminal_status = _terminal_status(run)
    if terminal_status:
        if terminal_status == AGENT_ERROR:
            runs.append_decision(db, run, {"event": "child_error",
                                           "steps": sorted(errored)})
        elif errored:
            runs.append_decision(db, run, {"event": "error_handled",
                                           "steps": sorted(errored)})
        return budget.settle(
            db, run_id=run.id, user_id=run.user_id,
            actual=actual_cost(run, all_children), final_status=terminal_status)

    active = sum(state.get("status") == "submitted"
                 for state in (run.checkpoint or {}).values())
    tools = discover_tools()
    owners = registry.discover()
    owner_by_tool = {
        tool.name: app.slug for app in owners for tool in app.manifest.tools
    }
    checkpoint = dict(run.checkpoint or {})
    for step in steps:
        sid = step["id"]
        if active >= max(1, int(max_parallel)):
            break
        state = checkpoint.get(sid) or {}
        if state and state.get("status") != "retry_needed":
            continue
        if not set(step.get("after") or []).issubset(done):
            continue
        if not set(step.get("after_error") or []).issubset(errored):
            continue
        spec = tools.get(step.get("tool"))
        if spec is None:
            raise ExecutorError(f"Tool không còn khả dụng: {step.get('tool')}.")
        params = resolve_params(run, step)
        attempt = int(state.get("attempt", -1)) + 1
        if state.get("status") == "retry_needed":
            action = state.get("action", "retry_same")
            if action in ("refine", "switch_model"):
                if retry_adapter is None:
                    state["status"] = "error"
                    state["reason"] = f"Không có adapter cho {action}."
                    checkpoint[sid] = state
                    runs.append_decision(db, run, {
                        "event": "retry_unavailable", "step_id": sid,
                        "attempt": attempt, "action": action,
                    })
                    continue
                params = retry_adapter(action, params, state.get("outputs") or {}, step)
            runs.append_decision(db, run, {
                "event": "retry", "step_id": sid, "attempt": attempt,
                "action": action, "fault": state.get("fault", ""),
            })
        fanout = int(step.get("fanout", 1))
        current_cost = actual_cost(run, runs.children(db, run))
        next_cost = (registry.credit_for(spec.job_type, params) +
                     verifier.verifier_cost(step.get("verify"))) * fanout
        try:
            budget.ensure_can_spend(run, current_cost + next_cost)
        except budget.BudgetError:
            checkpoint[sid] = {
                "status": "error", "attempt": attempt, "fault": "policy",
                "reason": "Không đủ phần ngân sách đã duyệt cho attempt kế tiếp.",
            }
            runs.append_decision(db, run, {
                "event": "budget_stop", "step_id": sid, "attempt": attempt,
                "actual": current_cost, "next_cost": next_cost,
            })
            continue
        child_ids = []
        for index in range(fanout):
            child = runs.submit_child(
                db, run, step_id=sid, app_slug=owner_by_tool[spec.name],
                job_type=spec.job_type, params=params,
                dedupe_key=f"agent:{run.id}:v{run.version}:{sid}:a{attempt}:{index}",
                # Provider/runtime retry is separate from verifier regeneration.
                max_attempts=1,
            )
            child_ids.append(child.id)
        checkpoint[sid] = {"status": "submitted", "job_ids": child_ids,
                           "attempt": attempt}
        active += 1
    run.checkpoint = checkpoint
    db.flush()
    return run
