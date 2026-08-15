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
#: How often a kill switch actually refused something. A switch nobody can see
#: working is a switch nobody trusts is working (EXT-14).
KILL_SWITCH_REFUSED = "kill_switch_refused"
#: How often a job was refused because the machinery behind it was missing,
#: rather than because the caller had had enough. Different cause, different
#: fix, so a different counter.
CAPACITY_REFUSED = "capacity_refused"
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


# ── Đường ra khỏi tiến trình ─────────────────────────────────────────────────
#
# Mọi thứ trên đây sống trong một tiến trình. Điều đó đúng cho đường nóng và sai
# cho người vận hành: số mất khi khởi động lại, không đọc được từ ngoài, và nền
# tảng chạy nhiều tiến trình worker nên mỗi tiến trình giữ một bản riêng mà
# không ai cộng lại. Phần dưới là cách chúng rời khỏi tiến trình — định kỳ,
# theo lô, và **không** trên đường phục vụ request.

#: Ô thời gian gom số. Đủ thô để một lượt ghi mỗi tiến trình mỗi phút là đủ,
#: đủ mịn để một cơn tăng đột biến còn nhìn thấy được trong biểu đồ.
WINDOW_S = 60

#: Giữ bao lâu. Bảng ghi theo phút thì phải có người dọn — đó là bài học EXT-19,
#: và store tương ứng được khai trong `governance.py`.
RETENTION_DAYS = 14


def _o_thoi_gian(now=None):
    from datetime import datetime, timezone

    current = now or datetime.now(timezone.utc)
    giay = int(current.timestamp()) // WINDOW_S * WINDOW_S
    return datetime.fromtimestamp(giay, tz=timezone.utc)


def _process_id() -> str:
    from platform_core import leases

    return leases.holder_id()


def drain() -> dict:
    """Lấy phần tăng thêm rồi reset bộ đếm cục bộ. Nguyên tử với người ghi.

    Lấy-rồi-xoá chứ không phải đọc-rồi-xoá: nếu một request tăng bộ đếm giữa hai
    thao tác đó, số đếm ấy sẽ mất. Ở đây cả hai nằm trong cùng một lần giữ khoá.
    """
    with _lock:
        counters = dict(_counters)
        latencies = {name: dict(bucket) for name, bucket in _latencies.items()}
        _counters.clear()
        _latencies.clear()
    return {"counters": counters, "latency": latencies}


def flush(db, *, now=None, process: str = "") -> int:
    """Ghi phần tăng thêm của tiến trình này xuống CSDL. Trả số dòng đã ghi.

    Gọi từ **mọi** tiến trình, không nấp sau lease bảo trì: mỗi tiến trình có bộ
    đếm riêng, nên để một tiến trình xả hộ nghĩa là mất số của tất cả những
    tiến trình còn lại.
    """
    import uuid as _uuid

    from platform_core.public_api.tables import ApiMetricSample

    delta = drain()
    if not delta["counters"] and not delta["latency"]:
        return 0

    who = process or _process_id()
    o = _o_thoi_gian(now)
    n = 0
    for name, value in delta["counters"].items():
        db.add(ApiMetricSample(id=str(_uuid.uuid4()), process=who, name=name,
                               kind="counter", value=int(value),
                               window_start=o))
        n += 1
    for name, bucket in delta["latency"].items():
        db.add(ApiMetricSample(
            id=str(_uuid.uuid4()), process=who, name=name, kind="latency",
            value=int(bucket["count"]),
            total_ms=int(bucket["total_ms"]),
            max_ms=int(bucket["max_ms"]), window_start=o))
        n += 1
    db.flush()
    return n


def aggregate(db, *, hours: int = 24, now=None) -> dict:
    """Cộng mọi tiến trình lại trong cửa sổ thời gian. Hình dạng như `snapshot()`.

    Cùng hình dạng là cố ý: trang quản trị và test đọc được cả hai mà không cần
    biết số đến từ một tiến trình hay từ tám.
    """
    from datetime import datetime, timedelta, timezone

    import sqlalchemy as sa

    from platform_core.public_api.tables import ApiMetricSample

    current = now or datetime.now(timezone.utc)
    since = current - timedelta(hours=max(1, int(hours)))
    rows = db.execute(sa.select(ApiMetricSample).where(
        ApiMetricSample.window_start >= since)).scalars().all()

    counters: dict = {}
    latency: dict = {}
    for row in rows:
        if row.kind == "counter":
            counters[row.name] = counters.get(row.name, 0) + int(row.value)
        else:
            bucket = latency.setdefault(row.name, {"count": 0, "total_ms": 0,
                                                   "max_ms": 0})
            bucket["count"] += int(row.value)
            bucket["total_ms"] += int(row.total_ms)
            bucket["max_ms"] = max(bucket["max_ms"], int(row.max_ms))

    return {
        "counters": dict(sorted(counters.items())),
        "latency": {name: {"count": b["count"],
                           "avg_ms": round(b["total_ms"] / b["count"], 2)
                           if b["count"] else 0.0,
                           "max_ms": round(b["max_ms"], 2)}
                    for name, b in sorted(latency.items())},
        "since": since.isoformat(),
        "processes": len({row.process for row in rows}),
    }


def purge_expired(db, *, days: int = RETENTION_DAYS, now=None) -> int:
    """Dọn mẫu cũ. Bảng ghi mỗi phút mỗi tiến trình thì không dọn là phình mãi."""
    from datetime import datetime, timedelta, timezone

    import sqlalchemy as sa

    from platform_core.public_api.tables import ApiMetricSample

    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=max(1, int(days)))
    rows = db.execute(sa.select(ApiMetricSample).where(
        ApiMetricSample.window_start < cutoff)).scalars().all()
    for row in rows:
        db.delete(row)
    db.flush()
    return len(rows)
