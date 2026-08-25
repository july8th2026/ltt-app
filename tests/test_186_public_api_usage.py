"""Q92 / Prompt 10 — balance, usage, reconciliation.

Usage is derived from the credit ledger, so these tests are really asking one
question in several ways: does what a customer is shown always equal what the
ledger says happened?
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from platform_core.models import Job
from platform_core.public_api import keys as devkeys, usage
from platform_core.public_api.scopes import (SCOPE_CREDITS_READ,
                                             SCOPE_JOBS_CANCEL, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ,
                                             SCOPE_USAGE_READ)
from platform_core.registry import AppManifest, LoadedApp, ToolSpec
from server.api.inventory import API_V1_PREFIX

PEPPER = "usage-test-pepper-" + "s" * 40
TOOL = "text.metered"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_JOBS_CANCEL, SCOPE_CREDITS_READ, SCOPE_USAGE_READ)


def _fixture_apps():
    tool = ToolSpec(
        name=TOOL, job_type="samplemeter.generate", description="Fixture tool.",
        params_schema={"prompt": {"type": "string", "required": True,
                                  "max_length": 100}},
        returns={"text": "text"}, api_exposed=True,
        api_contract={"scopes": (SCOPE_JOBS_CREATE,)})
    manifest = AppManifest(
        slug="samplemeter", display_name="Sample", route_prefix="/samplemeter",
        job_types=("samplemeter.generate",), credit_cost=lambda params: 10,
        lifecycle="released", surface="customer", tools=(tool,))
    return [LoadedApp(manifest=manifest, router=None, error="")]


@pytest.fixture()
def api(tmp_path, monkeypatch):
    import platform_core.registry as registry_mod
    monkeypatch.setattr(registry_mod, "discover", _fixture_apps)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'usage.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "usage-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": TOOL, "LTT_PUBLIC_API_MAX_ACTIVE_JOBS": "0",
    })
    try:
        with TestClient(app) as client:
            yield client
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
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
        user = tao_nguoi_dung(db, email=f"u-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, credits, by="test")
        key, token = devkeys.issue(db, user_id=user.id, scopes=ALL_SCOPES,
                                   env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        return user.id, token, key.key_id
    finally:
        _close(gen)


def _auth(token, idem=""):
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _job(api, token, idem):
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": {"prompt": "x"}},
                     headers=_auth(token))
    return api.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "quote": quote.json()["quote"],
                          "input": {"prompt": "x"}},
                    headers=_auth(token, idem))


def _settle(job_id, user_id, provider_cost=10):
    from platform_core import credit, jobs as jobq

    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        jobq.complete(db, job, {"text": "ok"})
        credit.quyet_toan(db, user_id, job_id, provider_cost)
        db.commit()
    finally:
        _close(gen)


def _fail(job_id, user_id):
    from platform_core import credit, jobs as jobq

    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        job.attempts = job.max_attempts - 1
        jobq.fail(db, job, "provider said no")
        credit.hoan(db, user_id, job_id)
        db.commit()
    finally:
        _close(gen)


# ── Balance ───────────────────────────────────────────────────────────────────

def test_balance_matches_the_ledger(api):
    user_id, token, _key_id = _account(credits=250)
    response = api.get(f"{API_V1_PREFIX}/credits/balance", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == 250 and body["unit"] == "credit"

    _job(api, token, "balance-moves-key01")
    after = api.get(f"{API_V1_PREFIX}/credits/balance",
                    headers=_auth(token)).json()["balance"]
    assert after == 240

    gen, db = _session()
    try:
        from platform_core import credit

        assert credit.so_du(db, user_id) == after
    finally:
        _close(gen)


def test_balance_needs_its_own_scope(api):
    _user_id, token, _key_id = _account()
    gen, db = _session()
    try:
        user_id = _user_id
        _key, limited = devkeys.issue(db, user_id=user_id,
                                      scopes=(SCOPE_JOBS_READ,),
                                      env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
    finally:
        _close(gen)
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(limited)).status_code == 403


# ── Usage ─────────────────────────────────────────────────────────────────────

def test_usage_nets_out_a_refunded_job(api):
    user_id, token, key_id = _account()
    done = _job(api, token, "usage-settled-job01").json()["id"]
    failed = _job(api, token, "usage-refunded-job1").json()["id"]
    _settle(done, user_id)
    _fail(failed, user_id)

    report = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(token)).json()
    by_job = {line["job_id"]: line for line in report["items"]}
    assert by_job[done]["credit"]["net_charged"] == 10
    assert by_job[failed]["credit"]["net_charged"] == 0
    assert by_job[failed]["credit"]["refunded"] == 10
    assert report["totals"]["net_charged_credit"] == 10
    # And it agrees with the balance: started 500, kept 10.
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 490


def test_usage_reports_a_partial_settlement(api):
    """Provider came in cheaper than the quote: the customer keeps the rest."""
    user_id, token, _key_id = _account()
    job_id = _job(api, token, "usage-partial-job01").json()["id"]
    _settle(job_id, user_id, provider_cost=4)

    report = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(token)).json()
    line = report["items"][0]
    assert line["credit"] == {"held": 10, "refunded": 0, "net_charged": 4}
    assert report["totals"]["net_charged_credit"] == 4
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 496


def test_a_capped_settlement_never_reports_more_than_the_hold(api):
    """Q84: provider overshoot is the platform's variance, not the invoice."""
    user_id, token, _key_id = _account()
    job_id = _job(api, token, "usage-capped-job-01").json()["id"]
    _settle(job_id, user_id, provider_cost=99)

    report = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(token)).json()
    assert report["items"][0]["credit"]["net_charged"] == 10
    assert report["totals"]["net_charged_credit"] == 10


def test_a_cancelled_job_costs_nothing(api):
    user_id, token, _key_id = _account()
    job_id = _job(api, token, "usage-cancelled-job1").json()["id"]
    api.post(f"{API_V1_PREFIX}/jobs/{job_id}/cancel", headers=_auth(token))

    report = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(token)).json()
    assert report["items"][0]["credit"]["net_charged"] == 0
    assert report["totals"]["net_charged_credit"] == 0
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 500


def test_an_idempotent_replay_is_counted_once(api):
    user_id, token, _key_id = _account()
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": {"prompt": "x"}},
                     headers=_auth(token))
    payload = {"tool": TOOL, "quote": quote.json()["quote"],
               "input": {"prompt": "x"}}
    first = api.post(f"{API_V1_PREFIX}/jobs", json=payload,
                     headers=_auth(token, "usage-replay-key-01"))
    api.post(f"{API_V1_PREFIX}/jobs", json=payload,
             headers=_auth(token, "usage-replay-key-01"))
    _settle(first.json()["id"], user_id)

    report = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(token)).json()
    assert len(report["items"]) == 1
    assert report["totals"]["net_charged_credit"] == 10


def test_usage_is_attributed_to_tool_and_key(api):
    user_id, token, key_id = _account()
    job_id = _job(api, token, "usage-attribution-1").json()["id"]
    _settle(job_id, user_id)

    line = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(token)).json()["items"][0]
    assert line["tool"] == TOOL and line["key_id"] == key_id

    filtered = api.get(f"{API_V1_PREFIX}/usage?tool={TOOL}",
                       headers=_auth(token)).json()
    assert len(filtered["items"]) == 1
    assert api.get(f"{API_V1_PREFIX}/usage?tool=other.tool",
                   headers=_auth(token)).json()["items"] == []
    assert api.get(f"{API_V1_PREFIX}/usage?key_id={key_id}",
                   headers=_auth(token)).json()["items"] == filtered["items"]


def test_totals_cover_the_window_not_the_page(api):
    """A total that only counts one page is a bug that looks like an answer."""
    user_id, token, _key_id = _account()
    for index in range(3):
        job_id = _job(api, token, f"usage-window-job-{index}0").json()["id"]
        _settle(job_id, user_id)

    page = api.get(f"{API_V1_PREFIX}/usage?limit=1", headers=_auth(token)).json()
    assert len(page["items"]) == 1 and page["page"]["has_more"] is True
    assert page["totals"]["net_charged_credit"] == 30


def test_the_window_is_validated_and_bounded(api):
    _user_id, token, _key_id = _account()
    assert api.get(f"{API_V1_PREFIX}/usage?since=not-a-date",
                   headers=_auth(token)).status_code == 400
    assert api.get(f"{API_V1_PREFIX}/usage?since=2030-01-01T00:00:00Z"
                   f"&until=2020-01-01T00:00:00Z",
                   headers=_auth(token)).status_code == 400
    assert api.get(f"{API_V1_PREFIX}/usage?since=2000-01-01T00:00:00Z",
                   headers=_auth(token)).status_code == 400

    ok = api.get(f"{API_V1_PREFIX}/usage?since=2026-08-01T00:00:00Z",
                 headers=_auth(token))
    assert ok.status_code == 200 and ok.json()["window"]["since"].startswith("2026-08-01")


def test_usage_is_owner_scoped(api):
    alice_id, alice, _alice_key = _account()
    _bob_id, bob, _bob_key = _account()
    job_id = _job(api, alice, "usage-alice-job-001").json()["id"]
    _settle(job_id, alice_id)

    assert len(api.get(f"{API_V1_PREFIX}/usage",
                       headers=_auth(alice)).json()["items"]) == 1
    bob_report = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(bob)).json()
    assert bob_report["items"] == []
    assert bob_report["totals"]["net_charged_credit"] == 0


def test_usage_never_exposes_internals(api):
    user_id, token, _key_id = _account()
    job_id = _job(api, token, "usage-no-internals1").json()["id"]
    _settle(job_id, user_id)
    body = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(token)).text
    for leak in ("samplemeter.generate", "app_slug", "worker", "prompt"):
        assert leak not in body


# ── Reconciliation ────────────────────────────────────────────────────────────

def test_reconciliation_agrees_with_the_ledger(api):
    user_id, token, _key_id = _account()
    settled = _job(api, token, "reconcile-settled-1").json()["id"]
    refunded = _job(api, token, "reconcile-refunded1").json()["id"]
    _settle(settled, user_id, provider_cost=6)
    _fail(refunded, user_id)

    gen, db = _session()
    try:
        report = usage.reconcile(db, user_id=user_id)
        assert report["ok"] is True
        assert report["jobs"] == 2 and report["mismatches"] == []
        assert report["holds_without_job"] == 0
    finally:
        _close(gen)


def test_reconciliation_notices_a_hold_with_no_job(api):
    """The failure it exists to catch: money moved with nothing to show for it."""
    user_id, token, _key_id = _account()

    gen, db = _session()
    try:
        from platform_core.models import CREDIT_HOLD, CreditEntry

        db.add(CreditEntry(user_id=user_id, delta=-5, kind=CREDIT_HOLD,
                           job_id="", note="orphan for test"))
        db.commit()
        report = usage.reconcile(db, user_id=user_id)
        assert report["holds_without_job"] == 1
        assert report["ok"] is False
    finally:
        _close(gen)


def test_the_reconcile_command_exists_and_is_read_only():
    from pathlib import Path

    source = Path("tools/reconcile_public_api_usage.py").read_text(encoding="utf-8")
    assert "usage.reconcile" in source
    for mutation in ("db.add(", "db.commit()", "DELETE", "UPDATE "):
        assert mutation not in source
