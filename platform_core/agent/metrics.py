"""Small process-local counters complementing durable AgentRun/Job metrics."""
from __future__ import annotations

import threading

_lock = threading.Lock()
_values = {"planning_attempts": 0, "planning_success": 0,
           "planning_errors": 0, "planning_latency_ms_total": 0.0,
           "approval_attempts": 0, "approval_success": 0,
           "approval_errors": 0}


def record_planning(*, success: bool, latency_ms: float) -> None:
    with _lock:
        _values["planning_attempts"] += 1
        _values["planning_success" if success else "planning_errors"] += 1
        _values["planning_latency_ms_total"] += max(0.0, float(latency_ms))


def record_approval(*, success: bool) -> None:
    with _lock:
        _values["approval_attempts"] += 1
        _values["approval_success" if success else "approval_errors"] += 1


def snapshot() -> dict:
    with _lock:
        result = dict(_values)
    attempts = result["planning_attempts"]
    result["planning_latency_ms_avg"] = (
        result["planning_latency_ms_total"] / attempts if attempts else 0.0)
    approval_attempts = result["approval_attempts"]
    result["approval_rate"] = (
        result["approval_success"] / approval_attempts if approval_attempts else 0.0)
    return result


def reset_for_tests() -> None:
    with _lock:
        for key in _values:
            _values[key] = 0.0 if key.endswith("_total") else 0
