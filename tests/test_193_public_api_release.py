"""Q92 / Prompt 17 — the release gate: canary, load, failure recovery.

No new behaviour is added here. This file answers the question a release
decision actually turns on: *when things go wrong — a crash between the hold and
the queue, a provider timeout, a worker restart, a duplicate retry under
concurrency — does the platform still owe exactly what it charged?*
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from platform_core.models import (CREDIT_HOLD, CREDIT_REFUND, CREDIT_SETTLE,
                                  CreditEntry, Job)
from platform_core.public_api import keys as devkeys, limits, metrics, usage
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.scopes import (SCOPE_ARTIFACTS_READ,
                                             SCOPE_CREDITS_READ,
                                             SCOPE_JOBS_CANCEL, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ,
                                             SCOPE_UPLOADS_WRITE, SCOPE_USAGE_READ,
                                             SCOPE_WEBHOOKS_MANAGE)
from platform_core.registry import discover
from server.api.inventory import API_V1_PREFIX

PEPPER = "release-test-pepper-" + "k" * 40
TOOL = "image.thumbnail"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_JOBS_CANCEL, SCOPE_UPLOADS_WRITE, SCOPE_ARTIFACTS_READ,
              SCOPE_CREDITS_READ, SCOPE_USAGE_READ, SCOPE_WEBHOOKS_MANAGE)
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 200
GOLDEN = Path(__file__).parent / "golden" / "public_api_catalog_v1.json"


# ── A. Inventory freeze ──────────────────────────────────────────────────────

def test_the_release_inventory_is_frozen_and_self_consistent():
    """Endpoints, tools, migrations and flags all agree with each other."""
    from server.api.inventory import API_V1_ROUTES, declared_paths

    # Endpoints: the declared set is what the sub-app serves (checked in
    # test_192); here we freeze the *count* so an accidental addition shows up
    # in a diff rather than in production.
    assert len(declared_paths()) == 24        # +2: /models, /models/{name}
    assert all(route.path.startswith(API_V1_PREFIX) for route in API_V1_ROUTES)

    # Tools: the published catalog equals the golden contract.
    published = sorted(entry["name"] for entry in
                       json.loads(GOLDEN.read_text(encoding="utf-8"))["tools"])
    exposed = sorted(tool.name for item in discover() if not item.error
                     for tool in item.manifest.tools if tool.api_exposed)
    assert published == exposed == ["image.generate", "image.thumbnail",
                                    "image.upscale", "story.storyboard",
                                    "text.prompt_package"]

    # Migrations: three, and the head is the last of them.
    versions = sorted(path.name for path in
                      Path("alembic/versions").glob("2026081*_public_api*.py"))
    assert len(versions) == 3   # idempotency + webhooks + request log
    assert Path("alembic/versions/20260813_1000_developer_api_keys.py").exists()

    # Flags: every switch the runbook mentions exists with a safe default.
    config = load_public_api_config({})
    for field in ("enabled", "read_only", "exposed_tools", "cors_origins",
                  "max_body_bytes", "request_rpm", "create_rpm",
                  "max_active_jobs", "class_concurrency", "daily_credit_limit",
                  "auth_failure_limit", "trusted_proxies"):
        assert hasattr(config, field), field


def test_the_two_credential_domains_are_still_separate():
    """The single most dangerous thing to merge, checked one last time."""
    from platform_core.models import ApiKey
    from platform_core.public_api.tables import DeveloperApiKey

    assert ApiKey.__tablename__ == "api_keys"
    assert DeveloperApiKey.__tablename__ == "developer_api_keys"
    # The provider key is recoverable (the worker must call with it); the
    # customer key is not (nothing may ever present it again).
    assert hasattr(ApiKey, "credential_enc")
    assert not hasattr(DeveloperApiKey, "credential_enc")
    assert hasattr(DeveloperApiKey, "verifier_digest")

    source = Path("platform_core/public_api/keys.py").read_text(encoding="utf-8")
    assert "lay_credential" not in source and "secretbox" not in source


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'release.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    monkeypatch.setenv("GEMINI_API_KEY", "stub-key-not-used")

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    limits.reset()
    metrics.reset()

    import apps.thumbnail.jobs as thumbnail_jobs
    monkeypatch.setattr(thumbnail_jobs, "_goi_gemini",
                        lambda *args, **kwargs: PNG)

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "release-secret",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": TOOL,
    })
    try:
        with TestClient(app) as client:
            yield client
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        storage_mod.set_storage(None)
        limits.reset()
        metrics.reset()
        dbmod.reset_engine()


def _session():
    from platform_core.db import get_session

    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _account(credits: int = 500):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"r-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, credits, by="test")
        _key, token = devkeys.issue(db, user_id=user.id, scopes=ALL_SCOPES,
                                    env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        return user.id, token
    finally:
        _close(gen)


def _auth(token, idem=""):
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _run(api, token, idem, count=1):
    payload = {"topic": "release", "count": count}
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": payload}, headers=_auth(token))
    assert quote.status_code == 200, quote.text
    return api.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "quote": quote.json()["quote"],
                          "input": payload},
                    headers=_auth(token, idem))


def _ledger(user_id: str) -> dict:
    gen, db = _session()
    try:
        rows = db.execute(
            sa.select(CreditEntry.kind, sa.func.count(CreditEntry.id),
                      sa.func.coalesce(sa.func.sum(CreditEntry.delta), 0))
            .where(CreditEntry.user_id == user_id)
            .group_by(CreditEntry.kind)).all()
        return {kind: {"rows": int(count), "delta": int(total)}
                for kind, count, total in rows}
    finally:
        _close(gen)


# ── C. Canary: the whole chain, once, for a real tool ────────────────────────

def test_the_full_chain_runs_and_settles_exactly_once(api):
    """auth → scope → quote → idempotency → hold → queue → worker → artifact →
    settle → usage → webhook, with only the provider stubbed."""
    from platform_core import secretbox
    from platform_core.job_runner import _chay_mot_job
    from platform_core.public_api.tables import WebhookSubscription

    user_id, token = _account()
    import os
    os.environ["LTT_TOKEN_ENCRYPTION_KEY"] = "release-encryption-key-0123456789"
    gen, db = _session()
    try:
        db.add(WebhookSubscription(
            id=str(uuid.uuid4()), user_id=user_id, key_id="",
            url="https://receiver.example.com/hook",
            secret_enc=secretbox.ma_hoa("release-webhook-secret"),
            events=[], enabled=True, created_at=datetime.now(timezone.utc)))
        db.commit()
    finally:
        _close(gen)

    created = _run(api, token, "release-canary-00001", count=2)
    assert created.status_code == 201
    job_id = created.json()["id"]
    assert created.json()["credit"]["held"] == 10

    assert _chay_mot_job("release-canary-worker") is True

    detail = api.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=_auth(token)).json()
    assert detail["status"] == "succeeded"
    assert detail["credit"] == {"held": 10, "charged": 10}
    assert len(detail["outputs"]) == 2

    artifact = api.get(f"{API_V1_PREFIX}/artifacts/{detail['outputs'][0]['id']}",
                       headers=_auth(token))
    assert artifact.status_code == 200

    report = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(token)).json()
    assert report["totals"]["net_charged_credit"] == 10
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 490

    deliveries = api.get(f"{API_V1_PREFIX}/webhooks/deliveries",
                         headers=_auth(token)).json()["items"]
    assert [item["event_type"] for item in deliveries] == ["job.succeeded"]

    # Exactly one of each money row, and they sum to what the customer paid.
    ledger = _ledger(user_id)
    assert ledger[CREDIT_HOLD]["rows"] == 1 and ledger[CREDIT_HOLD]["delta"] == -10
    assert ledger[CREDIT_SETTLE]["rows"] == 1 and ledger[CREDIT_SETTLE]["delta"] == 0
    assert CREDIT_REFUND not in ledger


# ── E. Failure recovery ──────────────────────────────────────────────────────

def test_a_crash_between_hold_and_queue_leaves_the_ledger_clean(api, monkeypatch):
    user_id, token = _account()
    from platform_core.public_api import idempotency as idem_mod

    monkeypatch.setattr(idem_mod, "complete", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("crash between hold and queue")))
    with pytest.raises(RuntimeError):
        _run(api, token, "release-crash-000001")

    assert _ledger(user_id).get(CREDIT_HOLD) is None
    gen, db = _session()
    try:
        assert db.execute(sa.select(sa.func.count(Job.id))).scalar_one() == 0
        assert usage.reconcile(db, user_id=user_id)["ok"] is True
    finally:
        _close(gen)


def test_a_worker_crash_mid_job_is_reclaimed_and_never_double_settles(api):
    """The orphan path: worker dies holding a job, another picks it up."""
    from platform_core import jobs as jobq
    from platform_core.job_runner import _chay_mot_job

    user_id, token = _account()
    job_id = _run(api, token, "release-orphan-00001").json()["id"]

    # Simulate a worker that claimed the job and then died.
    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        jobq.claim(db, worker_id="worker-that-dies")
        job.heartbeat_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        db.commit()
    finally:
        _close(gen)

    gen, db = _session()
    try:
        assert jobq.reclaim_orphans(db) >= 1
        db.commit()
    finally:
        _close(gen)

    # A fresh worker finishes it, and the money moves exactly once.
    for _ in range(4):
        gen, db = _session()
        try:
            job = db.get(Job, job_id)
            if job.status in ("done", "error", "cancelled"):
                break
            job.next_run_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            _close(gen)
        _chay_mot_job("release-second-worker")

    ledger = _ledger(user_id)
    assert ledger[CREDIT_HOLD]["rows"] == 1
    finalised = (ledger.get(CREDIT_SETTLE, {"rows": 0})["rows"] +
                 ledger.get(CREDIT_REFUND, {"rows": 0})["rows"])
    assert finalised == 1, "a job may be settled or refunded once, never twice"

    gen, db = _session()
    try:
        assert usage.reconcile(db, user_id=user_id)["ok"] is True
    finally:
        _close(gen)


def test_a_provider_timeout_refunds_and_reconciles(api, monkeypatch):
    import apps.thumbnail.jobs as thumbnail_jobs
    from platform_core.job_runner import _chay_mot_job

    user_id, token = _account()
    job_id = _run(api, token, "release-timeout-0001").json()["id"]

    def _timeout(*args, **kwargs):
        raise TimeoutError("provider did not answer")

    monkeypatch.setattr(thumbnail_jobs, "_goi_gemini", _timeout)
    for _ in range(5):
        _chay_mot_job("release-timeout-worker")
        gen, db = _session()
        try:
            job = db.get(Job, job_id)
            if job.status in ("error", "cancelled"):
                break
            job.next_run_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            _close(gen)

    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 500
    ledger = _ledger(user_id)
    assert ledger[CREDIT_REFUND]["rows"] == 1
    gen, db = _session()
    try:
        assert usage.reconcile(db, user_id=user_id)["ok"] is True
    finally:
        _close(gen)


def test_a_storage_failure_does_not_charge_the_customer(api, monkeypatch):
    from platform_core.job_runner import _chay_mot_job
    from platform_core.storage import get_storage

    user_id, token = _account()
    job_id = _run(api, token, "release-storage-0001").json()["id"]

    storage = get_storage()
    monkeypatch.setattr(storage, "put", lambda *a, **k: (_ for _ in ()).throw(
        OSError("disk full")))
    for _ in range(5):
        _chay_mot_job("release-storage-worker")
        gen, db = _session()
        try:
            job = db.get(Job, job_id)
            if job.status in ("error", "cancelled"):
                break
            job.next_run_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            _close(gen)

    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 500
    assert _ledger(user_id)[CREDIT_REFUND]["rows"] == 1


def test_a_webhook_receiver_being_down_changes_no_money(api):
    from platform_core import secretbox
    from platform_core.job_runner import _chay_mot_job
    from platform_core.public_api import outbox
    from platform_core.public_api.tables import WebhookSubscription

    user_id, token = _account()
    import os
    os.environ["LTT_TOKEN_ENCRYPTION_KEY"] = "release-encryption-key-0123456789"
    gen, db = _session()
    try:
        db.add(WebhookSubscription(
            id=str(uuid.uuid4()), user_id=user_id, key_id="",
            url="https://down.example.com/hook",
            secret_enc=secretbox.ma_hoa("release-secret"), events=[],
            enabled=True, created_at=datetime.now(timezone.utc)))
        db.commit()
    finally:
        _close(gen)

    job_id = _run(api, token, "release-hookdown-001").json()["id"]
    assert _chay_mot_job("release-hook-worker") is True

    def _down(subscription, delivery):
        raise ConnectionError("receiver down")

    gen, db = _session()
    try:
        outbox.deliver_due(db, sender=_down)
        db.commit()
    finally:
        _close(gen)

    detail = api.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=_auth(token)).json()
    assert detail["status"] == "succeeded"
    assert detail["credit"]["charged"] == 5
    assert _ledger(user_id)[CREDIT_SETTLE]["rows"] == 1


# ── D. Load / soak (short, in process) ───────────────────────────────────────
# Not marked `slow`: the repo has no pytest config registering such a marker and
# nothing filters on one, so it would only promise a selectivity that does not
# exist (and warn on every run). These three take a few seconds each.

def test_concurrent_duplicate_retries_create_one_job_and_one_hold():
    """The load harness, run briefly, proving the money invariant under load."""
    from tools.public_api_load_test import run

    report = run("duplicates", seconds=3.0, workers=6)
    assert report["requests"] > 20, report
    assert report["jobs"] == 1 and report["holds"] == 1
    assert set(report["statuses"]) <= {200, 201, 409}
    assert report["statuses"].get(201, 0) == 1


def test_the_load_harness_leaves_the_process_as_it_found_it():
    """A test that changes the environment for every test after it is a bug.

    This one is not hypothetical: the harness pointed LTT_DATA_DIR at a temp
    folder and never put it back, so a much later test built the app, failed to
    load config, and its maintenance daemon silently never started.
    """
    from tools.public_api_load_test import run

    before = {name: os.environ.get(name)
              for name in ("LTT_DATABASE_URL", "LTT_DATA_DIR",
                           "LTT_API_KEY_PEPPER")}
    run("reads", seconds=1.0, workers=2)
    after = {name: os.environ.get(name) for name in before}
    assert after == before


def test_one_abusive_key_does_not_degrade_a_well_behaved_one():
    from tools.public_api_load_test import run

    report = run("abusive", seconds=3.0, workers=4)
    by_client = report["statuses_by_client"]
    assert by_client["abusive"].get(429, 0) > 0, "the limiter must fire"
    assert by_client["normal"].get(429, 0) == 0, "well-behaved keys stay served"
    assert by_client["normal"].get(200, 0) > 0
