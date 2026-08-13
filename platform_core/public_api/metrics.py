"""In-process counters for the Public API.

Deliberately not a metrics *system*. The platform runs one web process and one
worker (ADR-005/Q6); adding Prometheus, a push gateway or a time-series database
to count nine things would be a new service to install, monitor and lose at 2am
— the same reasoning that kept Redis out of the rate limiter.

What this gives an operator is the set of numbers that answer "is something
wrong right now, and where": auth failures, error rates, limiter trips,
idempotency replays and conflicts, money movements, and how long the queue takes
to pick work up. They are logged periodically by the worker and readable in
process for tests.

If these ever need to leave the process, the shape here (name → integer, plus
count/total pairs for latencies) maps onto any exporter without changing call
sites.
"""
from __future__ import annotations

import threading
from collections import defaultdict

_lock = threading.Lock()
_counters: dict = defaultdict(int)
_latencies: dict = defaultdict(lambda: {"count": 0, "total_ms": 0.0, "max_ms": 0.0})

# Names are part of the operator contract: a dashboard or an alert refers to
# them, so they change like an API changes, not like a variable name.
AUTH_FAILURE = "auth_failure"
AUTH_SUCCESS = "auth_success"
REQUESTS = "requests"
RESPONSES_4XX = "responses_4xx"
RESPONSES_5XX = "responses_5xx"
RATE_LIMITED = "rate_limited"
IDEMPOTENCY_REPLAY = "idempotency_replay"
IDEMPOTENCY_CONFLICT = "idempotency_conflict"
CREDIT_HELD = "credit_held"
CREDIT_SETTLED = "credit_settled"
CREDIT_REFUNDED = "credit_refunded"
JOBS_CREATED = "jobs_created"
JOBS_CANCELLED = "jobs_cancelled"
WEBHOOK_DELIVERED = "webhook_delivered"
WEBHOOK_FAILED = "webhook_failed"

LATENCY_REQUEST = "request_ms"
LATENCY_QUEUE_PICKUP = "queue_pickup_ms"


def increment(name: str, amount: int = 1) -> None:
    with _lock:
        _counters[str(name)] += int(amount)


def observe(name: str, milliseconds: float) -> None:
    value = max(0.0, float(milliseconds))
    with _lock:
        bucket = _latencies[str(name)]
        bucket["count"] += 1
        bucket["total_ms"] += value
        bucket["max_ms"] = max(bucket["max_ms"], value)


def snapshot() -> dict:
    """Everything counted so far. Safe to call from anywhere."""
    with _lock:
        counters = dict(_counters)
        latencies = {
            name: {
                "count": bucket["count"],
                "avg_ms": round(bucket["total_ms"] / bucket["count"], 2)
                if bucket["count"] else 0.0,
                "max_ms": round(bucket["max_ms"], 2),
            }
            for name, bucket in _latencies.items()
        }
    return {"counters": counters, "latency": latencies}


def reset() -> None:
    """For tests and for a clean process start."""
    with _lock:
        _counters.clear()
        _latencies.clear()
