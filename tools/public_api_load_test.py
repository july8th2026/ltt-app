"""Load and soak harness for the Public API (Prompt 17 D).

Runs against the application **in process** by default: no network, no
Cloudflare, no provider spend, and therefore safe to run on a laptop or in CI.
That measures exactly what this prompt needs to know — control-plane cost, the
limiter's overhead, database contention and queue admission — and nothing about
Cloudflare, which is measured on the real deployment or not at all.

    python tools\\public_api_load_test.py --seconds 20 --workers 8
    python tools\\public_api_load_test.py --scenario abusive --seconds 20

Scenarios:
  reads       GET /tools, /jobs, /usage from several keys
  creates     POST /jobs, one unique idempotency key each (chargeable)
  duplicates  POST /jobs, the *same* idempotency key (must never double-charge)
  abusive     one key in a tight loop next to well-behaved keys (isolation)
  uploads     upload tickets until the per-account cap on open tickets engages,
              then the refusal path — read `statuses` to see the split, because
              those are two different measurements sharing one scenario
  budgeted    creates with a budget and alert thresholds configured, so the
              cost of the budget bookkeeping shows up next to plain `creates`
  worker      queue jobs, then drain them: queue admission and worker throughput
  webhooklag  time from a job finishing to its delivery being queued

It never points at production: the target is an app this process builds, with a
throwaway SQLite database. Loading a production deployment is a separate,
explicitly approved exercise.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TOOL = "image.thumbnail"
#: The upload scenario needs a tool that actually accepts a file. Pointing
#: it at a text field made every request a 400, so the numbers it reported
#: were the throughput of a validation error rather than of upload tickets.
UPLOAD_TOOL = "image.upscale"
UPLOAD_FIELD = "image_key"
PEPPER = "load-test-pepper-" + "L" * 40

# The harness points the process at a throwaway database. As a script that is
# the end of the story, but `run()` is also called from the test suite, and a
# process-wide environment change that outlives the call poisons every test that
# runs afterwards — that is exactly how this leaked once: `create_app()` in a
# much later test found LTT_DATA_DIR still aimed at a deleted temp folder, could
# not load its config, and the maintenance daemon quietly never started.
_OWNED_ENV = ("LTT_DATABASE_URL", "LTT_DATA_DIR", "LTT_API_KEY_PEPPER",
              "GEMINI_API_KEY")


def _restore_env(saved: dict) -> None:
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    import platform_core.db as dbmod

    dbmod.reset_engine()          # …and the engine built from that URL


def _build(work: Path, **env_extra):
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(work / 'load.db').as_posix()}"
    os.environ["LTT_DATA_DIR"] = str(work / "data")
    os.environ["LTT_API_KEY_PEPPER"] = PEPPER
    # The handler looks up a provider credential before it calls anything.
    # Without this the drain scenarios measure the throughput of *failing*
    # jobs, which looks like a healthy number and means nothing. The call
    # itself is stubbed, so this value never reaches a vendor.
    os.environ.setdefault("GEMINI_API_KEY", "load-test-stub-not-used")

    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())

    from fastapi.testclient import TestClient

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "load-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(work / "config.json"), "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": f"{TOOL},{UPLOAD_TOOL}",
        # Limits raised for the measurement runs; the isolation scenario sets
        # them back down so the limiter is what is being measured.
        "LTT_PUBLIC_API_RPM": "100000", "LTT_PUBLIC_API_CREATE_RPM": "100000",
        "LTT_PUBLIC_API_MAX_ACTIVE_JOBS": "0",
        **env_extra,
    })
    return TestClient(app)


def _account(credits: int = 1_000_000) -> str:
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.public_api import keys as devkeys
    from platform_core.users import tao_nguoi_dung

    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=f"load-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, credits, by="load-test")
        _key, token = devkeys.issue(db, user_id=user.id, name="load",
                                    scopes=("tools:read", "jobs:read",
                                            "jobs:create", "usage:read",
                                            "uploads:write", "credits:read",
                                            "webhooks:manage"))
        db.commit()
        return token
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _give_budget(token: str) -> None:
    """A budget with alert thresholds on the account behind this key.

    The point of the `budgeted` scenario is the comparison: the same creates,
    with the budget bookkeeping switched on. A number with no baseline says
    nothing about whether the feature is affordable.
    """
    from platform_core.db import get_session
    from platform_core.public_api import budgets, keys as devkeys

    gen = get_session()
    db = next(gen)
    try:
        key_id, _secret = devkeys.parse_token(token)
        row = db.execute(devkeys.select(devkeys.DeveloperApiKey).where(
            devkeys.DeveloperApiKey.key_id == key_id)).scalar_one()
        budgets.create(db, user_id=row.user_id, amount=10_000_000,
                       period="month", scope="account",
                       thresholds=(50, 80, 95), hard_cap=False)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _percentiles(samples: list[float]) -> dict:
    if not samples:
        return {"count": 0}
    ordered = sorted(samples)
    return {
        "count": len(ordered),
        "p50_ms": round(statistics.median(ordered) * 1000, 2),
        "p95_ms": round(ordered[int(0.95 * (len(ordered) - 1))] * 1000, 2),
        "p99_ms": round(ordered[int(0.99 * (len(ordered) - 1))] * 1000, 2),
        "max_ms": round(ordered[-1] * 1000, 2),
    }


def _quote(client, token: str) -> dict:
    response = client.post("/api/v1/quotes",
                           json={"tool": TOOL, "input": {"topic": "load", "count": 1}},
                           headers={"Authorization": f"Bearer {token}"})
    return response.json()


def run(scenario: str, seconds: float, workers: int) -> dict:
    saved = {name: os.environ.get(name) for name in _OWNED_ENV}
    try:
        return _run(scenario, seconds, workers)
    finally:
        _restore_env(saved)


def _run(scenario: str, seconds: float, workers: int) -> dict:
    work = Path(tempfile.mkdtemp(prefix="ltt-load-"))
    env_extra = {}
    if scenario == "abusive":
        # Real limits, so the thing being measured is isolation.
        env_extra = {"LTT_PUBLIC_API_RPM": "120", "LTT_PUBLIC_API_CREATE_RPM": "20"}
    client = _build(work, **env_extra)
    tokens = [_account() for _ in range(max(2, workers))]
    if scenario == "budgeted":
        for token in tokens:
            _give_budget(token)
    if scenario in ("worker", "webhooklag"):
        return _drain(client, tokens[0], scenario, seconds, workers, work)
    shared_quote = _quote(client, tokens[0]) if scenario in (
        "creates", "duplicates") else {}
    shared_key = uuid.uuid4().hex

    latencies: dict = {}
    statuses: dict = {}
    by_label: dict = {}
    lock = threading.Lock()
    deadline = time.monotonic() + float(seconds)

    def record(label: str, elapsed: float, status: int) -> None:
        with lock:
            latencies.setdefault(label, []).append(elapsed)
            statuses[status] = statuses.get(status, 0) + 1
            # Per label as well: "the limiter fired" and "the well-behaved keys
            # kept working" are two different questions, and only the second one
            # is the isolation guarantee.
            counts = by_label.setdefault(label, {})
            counts[status] = counts.get(status, 0) + 1

    def worker(index: int) -> None:
        token = tokens[0] if scenario == "abusive" and index == 0 else \
            tokens[index % len(tokens)]
        label = "abusive" if (scenario == "abusive" and index == 0) else "normal"
        headers = {"Authorization": f"Bearer {token}"}
        # A "normal" client in the isolation scenario is *well behaved*: it stays
        # inside the published limit. Without this it hammers just as hard as the
        # abusive one, gets throttled for the same good reason, and the test
        # proves nothing about isolation.
        pace = 1.0 if (scenario == "abusive" and label == "normal") else 0.0
        while time.monotonic() < deadline:
            started = time.perf_counter()
            if scenario == "reads" or (scenario == "abusive"):
                path = ("/api/v1/tools", "/api/v1/jobs", "/api/v1/usage")[
                    int(started * 1000) % 3]
                response = client.get(path, headers=headers)
            elif scenario in ("creates", "budgeted"):
                quote = _quote(client, token)
                response = client.post(
                    "/api/v1/jobs",
                    json={"tool": TOOL, "quote": quote["quote"],
                          "input": {"topic": "load", "count": 1}},
                    headers={**headers, "Idempotency-Key": uuid.uuid4().hex})
            elif scenario == "duplicates":
                response = client.post(
                    "/api/v1/jobs",
                    json={"tool": TOOL, "quote": shared_quote["quote"],
                          "input": {"topic": "load", "count": 1}},
                    headers={"Authorization": f"Bearer {tokens[0]}",
                             "Idempotency-Key": shared_key})
            else:                                   # uploads
                response = client.post(
                    "/api/v1/uploads",
                    json={"tool": UPLOAD_TOOL, "field": UPLOAD_FIELD,
                          "filename": "a.png", "content_type": "image/png",
                          "size": 1024},
                    headers=headers)
            record(label, time.perf_counter() - started, response.status_code)
            if pace:
                time.sleep(pace)

    threads = [threading.Thread(target=worker, args=(index,))
               for index in range(max(1, workers))]
    started_at = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    duration = time.monotonic() - started_at

    total = sum(len(values) for values in latencies.values())
    report = {
        "scenario": scenario, "seconds": round(duration, 2), "workers": workers,
        "requests": total, "rps": round(total / duration, 1) if duration else 0,
        "statuses": dict(sorted(statuses.items())),
        "statuses_by_client": {label: dict(sorted(counts.items()))
                               for label, counts in sorted(by_label.items())},
        "latency": {label: _percentiles(values)
                    for label, values in sorted(latencies.items())},
    }

    if scenario in ("creates", "duplicates", "budgeted"):
        from platform_core.db import get_session
        from platform_core.models import CREDIT_HOLD, CreditEntry, Job
        import sqlalchemy as sa

        gen = get_session()
        db = next(gen)
        try:
            report["jobs"] = int(db.execute(
                sa.select(sa.func.count(Job.id))).scalar_one())
            report["holds"] = int(db.execute(
                sa.select(sa.func.count(CreditEntry.id)).where(
                    CreditEntry.kind == CREDIT_HOLD)).scalar_one())
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    from platform_core.public_api import metrics

    report["metrics"] = metrics.snapshot()
    client.close()
    return report


def _drain(client, token: str, scenario: str, seconds: float, workers: int,
           work: Path) -> dict:
    """Queue jobs, then drain them, measuring the half a request cannot see.

    Everything else here measures the control plane — the part that answers in
    milliseconds. The two numbers an operator actually plans capacity with live
    on the other side of the queue: how fast a worker retires jobs, and how long
    after a job finishes its webhook is ready to send.

    The provider is stubbed. Measuring a vendor's latency would tell us about
    the vendor; what is being measured here is our own overhead around it.
    """
    import apps.thumbnail.jobs as thumbnail_jobs

    from platform_core.db import get_session
    from platform_core.job_runner import _chay_mot_job
    from platform_core.models import Job

    original = thumbnail_jobs._goi_gemini
    thumbnail_jobs._goi_gemini = lambda *a, **k: b"\x89PNG\r\n\x1a\n" + b"0" * 200

    headers = {"Authorization": f"Bearer {token}"}
    if scenario == "webhooklag":
        client.post("/api/v1/webhooks",
                    json={"url": "https://example.com/load-test-receiver",
                          "events": ["job.succeeded"]}, headers=headers)

    submitted, admission = [], []
    deadline = time.monotonic() + float(seconds)
    while time.monotonic() < deadline and len(submitted) < 400:
        quote = _quote(client, token)
        started = time.perf_counter()
        answer = client.post(
            "/api/v1/jobs",
            json={"tool": TOOL, "quote": quote["quote"],
                  "input": {"topic": "load", "count": 1}},
            headers={**headers, "Idempotency-Key": uuid.uuid4().hex})
        admission.append(time.perf_counter() - started)
        if answer.status_code == 201:
            submitted.append(answer.json()["id"])

    drained, per_job = 0, []
    drain_started = time.monotonic()
    while drained < len(submitted):
        started = time.perf_counter()
        if not _chay_mot_job("load-worker"):
            break
        per_job.append(time.perf_counter() - started)
        drained += 1
    drain_seconds = time.monotonic() - drain_started

    thumbnail_jobs._goi_gemini = original

    # Throughput of failing jobs is a meaningless number that looks fine, so
    # the count of jobs that actually produced a result is reported next to it.
    gen = get_session()
    db = next(gen)
    try:
        import sqlalchemy as sa

        succeeded = int(db.execute(
            sa.select(sa.func.count(Job.id)).where(
                Job.status == "done")).scalar_one())
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    report = {
        "scenario": scenario, "seconds": round(drain_seconds, 2),
        "workers": workers, "requests": len(submitted),
        "jobs_queued": len(submitted), "jobs_drained": drained,
        "jobs_succeeded": succeeded,
        "jobs_per_second": (round(drained / drain_seconds, 2)
                            if drain_seconds else 0),
        "latency": {"admission": _percentiles(admission),
                    "job": _percentiles(per_job)},
    }

    if scenario == "webhooklag":
        import sqlalchemy as sa

        from platform_core.public_api.tables import WebhookDelivery

        gen = get_session()
        db = next(gen)
        try:
            lags = []
            rows = db.execute(sa.select(WebhookDelivery)).scalars().all()
            for row in rows:
                job = db.get(Job, row.job_id) if row.job_id else None
                if job is not None and job.finished_at and row.created_at:
                    lags.append(max(0.0, (row.created_at - job.finished_at)
                                    .total_seconds()))
            report["deliveries_queued"] = len(rows)
            report["webhook_lag"] = _percentiles(lags)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    from platform_core.public_api import metrics

    report["metrics"] = metrics.snapshot()
    client.close()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="reads",
                        choices=("reads", "creates", "duplicates", "abusive",
                                 "uploads", "budgeted", "worker",
                                 "webhooklag"))
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    report = run(args.scenario, args.seconds, args.workers)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
