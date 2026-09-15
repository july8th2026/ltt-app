"""Rate, quota, concurrency and capacity limits for the Public API.

Five independent layers, because one number cannot protect five different
resources:

1. **auth-failure throttle** — protects the credential space. Without it, a
   caller can grind through key ids at request speed;
2. **request RPM per key** — protects this process and the database from a
   client in a loop;
3. **chargeable-create RPM per key** — protects the ledger and the provider
   quota, which are much more expensive than a read;
4. **concurrent active jobs per account** — protects the worker, the GPU and
   the queue. This is the one that keeps one customer from filling the queue
   with work everybody else then waits behind;
5. **daily credit ceiling per account** — a blast radius limit for a leaked key
   or a runaway script; off by default because it is a product decision, not a
   safety default.

**Where the numbers come from.** Until EXT-14 every limit came straight from the
deployment's environment, which meant one number for every customer. They now
come from ``policy.resolve()``, which walks global → tier → user → project →
credential → tool and hands back a ``Limits``. This module still owns *how* a
limit is enforced; it no longer owns *what the number is*.

**Per key and per account.** Layers 2 and 3 used to be bucketed on ``key_id``
alone, so an account that wanted five times the rate created five keys — no
exploit needed, just the credential page. Each rate is now charged to the key
*and* to the account: the key bucket stops one broken client, and the account
bucket is the one that means anything commercially. Layers 4 and 5 were already
per account.

**Where the counters live.** The platform runs a single web process (ADR-005,
one NSSM service), so an in-process window is authoritative for the RPM layers
and costs nothing. The layers that must stay correct regardless of how many
processes exist — concurrency and the credit ceiling — are computed from the
database, which is the same source the worker and the ledger already use. That
is why no Redis appears here: adding a service to hold counters that PostgreSQL
already holds correctly would be a new thing to install, monitor, back up and
lose at 2am, for no property we lack (COMMON_RULES §6).

If the web tier is ever run multi-instance, layers 1-3 become per-instance
(effective limit = configured × instances). Layers 4-5 stay exact. That is the
failure mode to weigh in the ADR before scaling out, and the reason it is
written down here rather than discovered later.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from platform_core.public_api.errors import (ApiError, CODE_CONCURRENCY_LIMITED,
                                             CODE_QUOTA_EXCEEDED,
                                             CODE_RATE_LIMITED)

# Kept as local aliases so the call sites below read the same as before; the
# codes themselves now live with every other code, because a code defined next
# to the one module that raises it is a code the error registry cannot see.
CODE_CONCURRENCY = CODE_CONCURRENCY_LIMITED
CODE_QUOTA = CODE_QUOTA_EXCEEDED

_lock = threading.Lock()
_windows: dict = defaultdict(deque)
_counters: dict = defaultdict(int)


def _now() -> float:
    return time.monotonic()


def reset() -> None:
    """Drop every in-memory window. For tests and for a clean process start."""
    with _lock:
        _windows.clear()
        _counters.clear()


def metrics() -> dict:
    """Counters an operator can graph: what tripped, and how often."""
    with _lock:
        return dict(_counters)


def _bump(name: str) -> None:
    _counters[name] += 1


def _record_admission_rejected(reason: str) -> None:
    """Đếm cả tổng và lý do trong bộ metrics được xả bền xuống CSDL."""
    from platform_core.public_api import metrics as durable_metrics

    durable_metrics.increment(durable_metrics.ADMISSION_REJECTED)
    durable_metrics.increment(f"admission_rejected:{str(reason)[:40]}")


def _hit(bucket: str, limit: int, window_s: float) -> tuple[bool, int]:
    """Sliding window. Returns ``(allowed, retry_after_seconds)``.

    A sliding window rather than a fixed one: a fixed window lets a caller send
    two full allowances back to back across the boundary, which is exactly the
    burst the limit is meant to prevent.
    """
    if limit <= 0:
        return True, 0
    now = _now()
    with _lock:
        events = _windows[bucket]
        cutoff = now - window_s
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            retry = max(1, int(round(events[0] + window_s - now)))
            return False, retry
        events.append(now)
        return True, 0


def allow(bucket: str, limit: int, *, window_s: float = 60.0) -> tuple[bool, int]:
    """Cửa công khai của cửa sổ trượt. Trả `(được_phép, giây_thử_lại)`.

    Có mặt vì `_hit` là nội bộ, và Nexus (Q93) cần **cùng một** bộ đếm chứ không
    phải bộ đếm thứ hai — một hệ có hai bộ đếm nhịp thì không ai trả lời được
    "khách này đang bị chặn bởi cái nào".

    Đổi lại: người gọi tự chọn tên `bucket`, nên hai chỗ vô tình dùng chung một
    tên sẽ chia nhau hạn mức. Quy ước: `<mien>:<khoa>`, ví dụ `<mien>:<ip>`.
    """
    return _hit(str(bucket), int(limit), float(window_s))


def _too_many(detail: str, retry_after: int, code: str = CODE_RATE_LIMITED,
              **extra) -> ApiError:
    return ApiError(429, code, detail, extra={"retry_after": int(retry_after),
                                              **extra})


def execution_busy(resource: str, *, retry_after: int = 15,
                   reason: str = "") -> ApiError:
    """429 chung khi sync/stream không giành được slot thực thi.

    ⛔ `retry_after` KHÔNG được để mặc định khi bên ném đã biết số. `luong.DangBan`
       mang sẵn `thu_lai_sau_s`, và trước 14/09/2026 cửa stream vứt nó rồi luôn
       nói `15`. Một `Retry-After` bịa ra tệ hơn không có: client lịch sự sẽ
       **tin** nó, nên số sai đẩy cả đàn client quay lại sai nhịp.

    ⭐ `reason` mang `DangBan.nguon` ra ngoài: `suat` (hàng của TA đầy) khác hẳn
       `thuong_nguon` (máy B trả 429) và `het_cho` (phòng chờ chạm trần). Cùng
       một mã HTTP, ba nguyên nhân — và client điều phối tải cần phân biệt.
    """
    _bump("concurrency_limited")
    return _too_many(
        "The requested execution resource is busy. Retry later or submit an "
        "asynchronous job.", retry_after, code=CODE_CONCURRENCY,
        scope="execution", resource=str(resource),
        **({"reason": reason} if reason else {}))


# ── Layer 1: authentication failures ──────────────────────────────────────────

def note_auth_failure(*, client_ip: str, key_id: str, config) -> None:
    """Count a rejected credential; raise 429 once a source is clearly probing.

    Keyed by IP **and** by key id: the first catches a scanner walking the key
    space, the second catches a broken client hammering with one dead key from
    many addresses.
    """
    limit = config.auth_failure_limit
    window = config.auth_failure_window_s
    for bucket in (f"authfail:ip:{client_ip}", f"authfail:key:{key_id or '-'}"):
        allowed, retry = _hit(bucket, limit, window)
        if not allowed:
            _bump("auth_failure_throttled")
            raise _too_many(
                "Too many failed authentication attempts. Try again later.",
                retry)


# ── Layers 2 and 3: request rate ──────────────────────────────────────────────

def enforce_request_rate(*, key_id: str, config, limits=None,
                         user_id: str = "", is_write: bool = False) -> None:
    """Ration ordinary calls, per key and per account.

    Reads and writes get separate allowances once a policy says so. A read costs
    a query; a write costs a row, a lock and often a hold, so a burst of cheap
    reads must not be able to consume the allowance that protects them — nor the
    reverse. Without a policy both come from the same configured number, which
    is exactly the behaviour deployments already had.
    """
    ceiling = config.request_rpm if limits is None else (
        limits.rpm_write if is_write else limits.rpm_read)
    allowed, retry = _hit(f"rpm:{key_id}", ceiling, 60.0)
    if not allowed:
        _bump("request_rate_limited")
        raise _too_many("Too many requests for this API key.", retry,
                        scope="key", reason="request_rate")

    if user_id:
        # The anti-bypass bucket. Same ceiling, wider subject: more keys buy
        # more parallelism against the platform, never more rate.
        allowed, retry = _hit(f"rpm:acct:{user_id}", ceiling, 60.0)
        if not allowed:
            _bump("request_rate_limited_account")
            raise _too_many("Too many requests for this account.", retry,
                            scope="account", reason="request_rate")


def enforce_create_rate(*, key_id: str, config, limits=None,
                        user_id: str = "") -> None:
    """Chargeable creates are rationed separately and much more tightly.

    A read costs a query; a create costs credit, a worker slot and provider
    quota. Sharing one budget between them would let a burst of cheap calls
    exhaust the allowance that protects the expensive ones — or the reverse.
    """
    ceiling = config.create_rpm if limits is None else limits.rpm_create
    allowed, retry = _hit(f"create:{key_id}", ceiling, 60.0)
    if not allowed:
        _bump("create_rate_limited")
        raise _too_many("Too many job creations for this API key.", retry,
                        scope="key", reason="create_rate")

    if user_id:
        allowed, retry = _hit(f"create:acct:{user_id}", ceiling, 60.0)
        if not allowed:
            _bump("create_rate_limited_account")
            raise _too_many("Too many job creations for this account.", retry,
                            scope="account", reason="create_rate")


# ── Layer 4: concurrency and capacity (database-backed) ───────────────────────

def active_job_count(db, user_id: str, *, app_slugs=None,
                     resource: str = "") -> int:
    from sqlalchemy import func, select
    from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job

    statement = select(func.count(Job.id)).where(
        Job.user_id == str(user_id),
        Job.status.in_((JOB_QUEUED, JOB_RUNNING)))
    if app_slugs:
        statement = statement.where(Job.app_slug.in_(list(app_slugs)))
    if resource:
        statement = statement.where(Job.admission_resource == str(resource))
    return int(db.execute(statement).scalar_one())


def queued_job_count(db, *, resource: str = "") -> int:
    """Queued work admitted through the Public API, globally or by resource."""
    from sqlalchemy import func, select
    from platform_core.models import JOB_QUEUED, Job

    statement = select(func.count(Job.id)).where(
        Job.status == JOB_QUEUED,
        # Empty is a legacy/UI job. Public API submission always snapshots a
        # resource, so the global Public API cap cannot throttle unrelated UI.
        Job.admission_resource != "",
    )
    if resource:
        statement = statement.where(Job.admission_resource == str(resource))
    return int(db.execute(statement).scalar_one())


def _lock_job_admission(db, *, user_id: str, resource: str,
                        global_limit: int, resource_limit: int,
                        account_limit: int, account_resource_limit: int) -> None:
    """Serialise quota check + caller's later insert in the same transaction.

    Every caller takes locks in one fixed order. They are transaction locks, so
    the route's final commit/rollback releases them together with job+credit.
    SQLite skips this; the PostgreSQL concurrency suite proves the race path.
    """
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    from sqlalchemy import text

    keys: list[str] = []
    if global_limit > 0:
        keys.append("public-api-admission:0:global")
    if resource and (resource_limit > 0 or account_resource_limit > 0):
        keys.append(f"public-api-admission:1:resource:{resource}")
    if account_limit > 0 or account_resource_limit > 0:
        keys.append(f"public-api-admission:2:account:{user_id}")
    for key in keys:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": key})


def resource_class(manifest) -> str:
    """Which scarce resource a job of this app competes for.

    Read from ``manifest.requires`` — the platform must not know app names
    (``AGENTS.md`` 8.4), and the app already declares what it needs.
    """
    requires = set(getattr(manifest, "requires", ()) or ())
    if "gpu" in requires:
        return "gpu"
    if "ffmpeg" in requires:
        return "ffmpeg"
    if "browser" in requires:
        return "browser"
    return "api"


def enforce_active_jobs(db, *, principal, config, app_slug: str,
                        class_slugs=None, resource: str = "api",
                        limits=None) -> None:
    """Refuse to open a new job when this account already has enough running.

    Backpressure at admission, not in the queue: an unbounded queue turns a
    burst into an hours-long backlog that every other customer waits behind,
    and the credit for it is already held.
    """
    enforce_job_admission(
        db, principal=principal, config=config, app_slug=app_slug,
        class_slugs=class_slugs, resource=resource, limits=limits)


def enforce_job_admission(db, *, principal, config, app_slug: str = "",
                          class_slugs=None, resource: str = "api",
                          limits=None) -> None:
    """Atomically enforce durable queue/account caps before job+credit insert.

    Caller must insert and commit on this same session. Calling this function
    and then committing before the insert re-opens the exact race it closes.
    """
    limit = (config.max_active_jobs if limits is None else limits.max_active_jobs)
    classes = (config.class_concurrency if limits is None
               else limits.class_concurrency)
    class_limit = classes.get(resource, 0)
    global_limit = int(getattr(config, "global_queue_limit", 0) or 0)
    resource_limits = dict(getattr(config, "resource_queue_limits", {}) or {})
    resource_limit = int(resource_limits.get(resource, 0) or 0)

    _lock_job_admission(
        db, user_id=principal.user_id, resource=resource,
        global_limit=global_limit, resource_limit=resource_limit,
        account_limit=limit, account_resource_limit=class_limit)

    if global_limit > 0:
        queued = queued_job_count(db)
        if queued >= global_limit:
            _bump("queue_limited:global")
            _record_admission_rejected("global_queue")
            raise _too_many(
                "The job queue is full right now.", 30,
                code=CODE_CONCURRENCY, scope="global_queue",
                queued_jobs=queued, limit=global_limit)

    if resource_limit > 0:
        queued = queued_job_count(db, resource=resource)
        if queued >= resource_limit:
            _bump(f"queue_limited:{resource}")
            _record_admission_rejected("resource_queue")
            raise _too_many(
                f"The {resource} queue is full right now.", 30,
                code=CODE_CONCURRENCY, scope="resource_queue",
                resource=resource, queued_jobs=queued, limit=resource_limit)

    if limit > 0:
        active = active_job_count(db, principal.user_id)
        if active >= limit:
            _bump("concurrency_limited")
            _record_admission_rejected("account")
            raise _too_many(
                "This account already has the maximum number of active jobs.",
                30, code=CODE_CONCURRENCY, active_jobs=active, limit=limit)

    if class_limit > 0:
        active = active_job_count(
            db, principal.user_id,
            resource=resource,
            # Old rows created before admission metadata still count by app
            # class during a rolling deploy.
            app_slugs=class_slugs if not resource else None)
        if active >= class_limit:
            _bump(f"capacity_limited:{resource}")
            _record_admission_rejected("account_resource")
            raise _too_many(
                f"This account already has the maximum number of active "
                f"{resource} jobs.", 30, code=CODE_CONCURRENCY,
                active_jobs=active, limit=class_limit, resource=resource)


# ── Layer 5: daily credit ceiling ─────────────────────────────────────────────

def credit_spent_since(db, user_id: str, since: datetime) -> int:
    """Credit committed **through the API** in a window.

    Holds minus what came back, counting only jobs the API created. Counting
    every credit entry — which is what this did until EXT-11 — meant a customer
    using the web app could exhaust their own integration's daily allowance. The
    ceiling exists to bound the blast radius of a leaked *API key*, so it counts
    what an API key can spend (decision D3).

    Counting holds rather than settlements is deliberate: the ceiling has to
    stop spending *before* the work runs, and a hold is the moment the account
    commits to the cost.
    """
    from platform_core.public_api.budgets import api_spend_since

    return api_spend_since(db, user_id=str(user_id), since=since)


def enforce_budget(db, *, principal, cost: int) -> None:
    """Refuse when a hard-capped budget of the customer's own is exhausted.

    Separate from the operator's ceiling and checked alongside it: whichever
    allows less wins, and the refusal says which, because "quota_exceeded" with
    no attribution turns every support conversation into an investigation.
    """
    from platform_core.public_api import budgets

    for budget in budgets.list_for(db, user_id=principal.user_id):
        if not budget.hard_cap:
            continue
        if budget.scope == budgets.SCOPE_PROJECT and \
                str(budget.project_id or "") != str(
                    getattr(principal, "project_id", "") or ""):
            continue
        state = budgets.status(db, budget)
        if state["spent"] + int(cost) > state["amount"]:
            raise _too_many(
                f"This call would exceed the {budget.period} budget you set "
                f"for this account.", 60, code=CODE_QUOTA,
                limit=state["amount"], spent=state["spent"],
                scope=budget.scope, period=budget.period, source="budget")


def enforce_daily_credit(db, *, principal, config, cost: int,
                         limits=None) -> None:
    ceiling = (config.daily_credit_limit if limits is None
               else limits.daily_credit)
    if ceiling <= 0:
        return
    since = datetime.now(timezone.utc) - timedelta(days=1)
    spent = credit_spent_since(db, principal.user_id, since)
    if spent + max(0, int(cost)) > ceiling:
        _bump("daily_credit_limited")
        raise _too_many(
            "This account has reached its daily credit ceiling for the API.",
            3600, code=CODE_QUOTA, spent_credit=spent, limit=ceiling)
