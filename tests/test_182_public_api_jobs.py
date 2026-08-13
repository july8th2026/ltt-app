"""Q92 / Prompt 06 — quotes, jobs, credit, idempotency, transactionality.

Every test here is about money or about a job going missing. The exposure gates
of Prompt 05 stay untouched: this file publishes a **fixture app** through the
same machinery a wave prompt will use, so the chargeable path is exercised
end-to-end without opening a real tool ahead of its wave.
"""
from __future__ import annotations

import threading
import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from platform_core.models import (CREDIT_HOLD, CREDIT_REFUND, CREDIT_SETTLE,
                                  CreditEntry, JOB_CANCELLED, JOB_DONE, Job)
from platform_core.public_api import invocation, keys as devkeys, quotes
from platform_core.public_api.scopes import (SCOPE_JOBS_CANCEL, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ)
from platform_core.registry import AppManifest, LoadedApp, ToolSpec
from server.api.inventory import API_V1_PREFIX

PEPPER = "jobs-test-pepper-" + "w" * 40
TOOL = "text.sample"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_JOBS_CANCEL)


def _cost(params: dict) -> int:
    """Priced per unit so a tampered input has a different, checkable price."""
    return 5 * max(1, int(params.get("count") or 1))


def _fixture_apps():
    tool = ToolSpec(
        name=TOOL, job_type="sampleapi.generate",
        description="Fixture tool for the chargeable path.",
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 100},
            "count": {"type": "int", "min": 1, "max": 4, "default": 1},
            "model": {"type": "model_ref", "category": "text",
                      "providers": ["gemini"]},
        },
        returns={"text": "text"},
        api_exposed=True,
        api_contract={"models": {"standard": "gemini-internal-id"},
                      "scopes": (SCOPE_JOBS_CREATE,)},
    )
    manifest = AppManifest(
        slug="sampleapi", display_name="Sample API app", route_prefix="/sampleapi",
        job_types=("sampleapi.generate",), credit_cost=_cost,
        lifecycle="released", surface="customer", tools=(tool,))
    # router=None is a legal app (jobs only, no UI) and keeps `mount_all`
    # happy when the platform boots with this fixture registry in place.
    return [LoadedApp(manifest=manifest, router=None, error="")]


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'jobs.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)

    # One patch point: the catalog, the pricing lookup and the job handler
    # resolution all read the registry, so patching `discover` keeps them
    # consistent with each other.
    import platform_core.registry as registry_mod
    monkeypatch.setattr(registry_mod, "discover", _fixture_apps)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "jobs-secret-value",
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


def _account(credits: int = 100, scopes=ALL_SCOPES) -> tuple[str, str]:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"job-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        if credits:
            credit.cap_tay(db, user.id, credits, by="test")
        _key, token = devkeys.issue(db, user_id=user.id, scopes=scopes,
                                    env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        return user.id, token
    finally:
        _close(gen)


def _auth(token: str, idem: str = "") -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _quote(api, token: str, **input_overrides) -> dict:
    payload = {"prompt": "hello", "count": 1, "model": "standard"}
    payload.update(input_overrides)
    response = api.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": payload},
                        headers=_auth(token))
    assert response.status_code == 200, response.text
    return response.json() | {"input": payload}


def _balance(user_id: str) -> int:
    from platform_core import credit

    gen, db = _session()
    try:
        return credit.so_du(db, user_id)
    finally:
        _close(gen)


def _rows(user_id: str, kind: str) -> int:
    gen, db = _session()
    try:
        return int(db.execute(sa.select(sa.func.count(CreditEntry.id)).where(
            CreditEntry.user_id == user_id, CreditEntry.kind == kind)).scalar_one())
    finally:
        _close(gen)


# ── Quotes ────────────────────────────────────────────────────────────────────

def test_a_quote_prices_the_call_without_touching_credit(api):
    user_id, token = _account()
    quote = _quote(api, token, count=2)
    assert quote["credit"] == 10 and quote["tool"] == TOOL
    assert quote["balance"] == 100
    assert _balance(user_id) == 100
    assert _rows(user_id, CREDIT_HOLD) == 0


def test_a_quote_cannot_be_moved_to_another_account(api):
    _alice_id, alice = _account()
    _bob_id, bob = _account()
    quote = _quote(api, alice)
    response = api.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": TOOL, "quote": quote["quote"],
                              "input": quote["input"]},
                        headers=_auth(bob, "bob-steals-a-quote-1"))
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_a_tampered_or_reused_quote_is_refused(api):
    _user_id, token = _account()
    quote = _quote(api, token, count=1)

    # Same token, bigger job: the fingerprint is what makes the price a promise.
    bigger = dict(quote["input"], count=4)
    swapped = api.post(f"{API_V1_PREFIX}/jobs",
                       json={"tool": TOOL, "quote": quote["quote"], "input": bigger},
                       headers=_auth(token, "swap-the-input-key-1"))
    assert swapped.status_code == 400

    forged = api.post(f"{API_V1_PREFIX}/jobs",
                      json={"tool": TOOL, "quote": quote["quote"] + "x",
                            "input": quote["input"]},
                      headers=_auth(token, "forge-the-signature-1"))
    assert forged.status_code == 400


def test_an_expired_quote_is_refused(api, monkeypatch):
    _user_id, token = _account()
    quote = _quote(api, token)
    monkeypatch.setattr(quotes, "QUOTE_TTL_S", 0)
    import time
    time.sleep(1.1)
    response = api.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": TOOL, "quote": quote["quote"],
                              "input": quote["input"]},
                        headers=_auth(token, "expired-quote-key-01"))
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


# ── Job creation ──────────────────────────────────────────────────────────────

def test_creating_a_job_holds_exactly_the_quoted_credit(api):
    user_id, token = _account()
    quote = _quote(api, token, count=2)
    response = api.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": TOOL, "quote": quote["quote"],
                              "input": quote["input"]},
                        headers=_auth(token, "first-real-job-key-1"))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "queued" and body["tool"] == TOOL
    assert body["credit"]["held"] == 10
    assert _balance(user_id) == 90
    assert _rows(user_id, CREDIT_HOLD) == 1

    # The job carries the internal model id, never the public alias.
    gen, db = _session()
    try:
        job = db.get(Job, body["id"])
        assert job.params["model"] == "gemini-internal-id"
        assert invocation.api_meta(job)["tool"] == TOOL
    finally:
        _close(gen)


def test_the_public_job_view_hides_implementation_detail(api):
    _user_id, token = _account()
    quote = _quote(api, token)
    body = api.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "quote": quote["quote"],
                          "input": quote["input"]},
                    headers=_auth(token, "hide-internals-key-01")).json()
    text = str(body)
    for leak in ("sampleapi", "sampleapi.generate", "gemini", "worker"):
        assert leak not in text


def test_unknown_fields_are_rejected_at_submit_not_ignored(api):
    _user_id, token = _account()
    quote = _quote(api, token)
    response = api.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote["quote"],
              "input": dict(quote["input"], sneaky="value")},
        headers=_auth(token, "mass-assignment-key-1"))
    assert response.status_code == 400
    assert "sneaky" in response.json()["detail"]


def test_insufficient_credit_creates_neither_hold_nor_job(api):
    user_id, token = _account(credits=3)
    quote = _quote(api, token)
    response = api.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": TOOL, "quote": quote["quote"],
                              "input": quote["input"]},
                        headers=_auth(token, "too-poor-to-run-key1"))
    assert response.status_code == 409
    body = response.json()
    assert body["required_credit"] == 5 and body["balance"] == 3
    assert _balance(user_id) == 3
    assert _rows(user_id, CREDIT_HOLD) == 0

    gen, db = _session()
    try:
        assert db.execute(sa.select(sa.func.count(Job.id)).where(
            Job.user_id == user_id)).scalar_one() == 0
    finally:
        _close(gen)


def test_missing_scope_never_reaches_the_ledger(api):
    user_id, token = _account(scopes=(SCOPE_TOOLS_READ, SCOPE_JOBS_READ))
    priced = api.post(f"{API_V1_PREFIX}/quotes",
                      json={"tool": TOOL, "input": {"prompt": "x"}},
                      headers=_auth(token))
    assert priced.status_code == 403
    assert _rows(user_id, CREDIT_HOLD) == 0


# ── Idempotency ───────────────────────────────────────────────────────────────

def test_the_same_key_and_body_replays_one_job(api):
    user_id, token = _account()
    quote = _quote(api, token)
    payload = {"tool": TOOL, "quote": quote["quote"], "input": quote["input"]}

    first = api.post(f"{API_V1_PREFIX}/jobs", json=payload,
                     headers=_auth(token, "replay-me-please-key1"))
    second = api.post(f"{API_V1_PREFIX}/jobs", json=payload,
                      headers=_auth(token, "replay-me-please-key1"))
    assert first.status_code == 201 and second.status_code == 200
    assert second.headers.get("idempotency-replayed") == "true"
    assert first.json()["id"] == second.json()["id"]
    assert _rows(user_id, CREDIT_HOLD) == 1
    assert _balance(user_id) == 95


def test_a_retry_after_the_job_finished_still_does_not_double_charge(api):
    """The exact gap `jobs.dedupe_key` leaves open."""
    user_id, token = _account()
    quote = _quote(api, token)
    payload = {"tool": TOOL, "quote": quote["quote"], "input": quote["input"]}
    first = api.post(f"{API_V1_PREFIX}/jobs", json=payload,
                     headers=_auth(token, "finish-then-retry-k1"))
    job_id = first.json()["id"]

    gen, db = _session()
    try:
        from platform_core import credit, jobs as jobq

        job = db.get(Job, job_id)
        jobq.complete(db, job, {"text": "done"})
        credit.quyet_toan(db, user_id, job_id, 5)
        db.commit()
    finally:
        _close(gen)

    retry = api.post(f"{API_V1_PREFIX}/jobs", json=payload,
                     headers=_auth(token, "finish-then-retry-k1"))
    assert retry.status_code == 200 and retry.json()["id"] == job_id
    assert _rows(user_id, CREDIT_HOLD) == 1
    assert _balance(user_id) == 95


def test_the_same_key_with_a_different_body_is_a_conflict(api):
    user_id, token = _account()
    first_quote = _quote(api, token, count=1)
    second_quote = _quote(api, token, count=2)

    api.post(f"{API_V1_PREFIX}/jobs",
             json={"tool": TOOL, "quote": first_quote["quote"],
                   "input": first_quote["input"]},
             headers=_auth(token, "one-key-two-bodies1"))
    clash = api.post(f"{API_V1_PREFIX}/jobs",
                     json={"tool": TOOL, "quote": second_quote["quote"],
                           "input": second_quote["input"]},
                     headers=_auth(token, "one-key-two-bodies1"))
    assert clash.status_code == 409 and clash.json()["code"] == "conflict"
    assert _rows(user_id, CREDIT_HOLD) == 1


def test_the_idempotency_key_is_required_and_sane(api):
    _user_id, token = _account()
    quote = _quote(api, token)
    payload = {"tool": TOOL, "quote": quote["quote"], "input": quote["input"]}
    assert api.post(f"{API_V1_PREFIX}/jobs", json=payload,
                    headers=_auth(token)).status_code == 400
    assert api.post(f"{API_V1_PREFIX}/jobs", json=payload,
                    headers=_auth(token, "short")).status_code == 400


def test_one_key_is_scoped_to_its_own_account(api):
    """Two accounts using the same idempotency string must not collide."""
    alice_id, alice = _account()
    bob_id, bob = _account()
    for token in (alice, bob):
        quote = _quote(api, token)
        response = api.post(f"{API_V1_PREFIX}/jobs",
                            json={"tool": TOOL, "quote": quote["quote"],
                                  "input": quote["input"]},
                            headers=_auth(token, "shared-key-string-01"))
        assert response.status_code == 201
    assert _rows(alice_id, CREDIT_HOLD) == 1
    assert _rows(bob_id, CREDIT_HOLD) == 1


def test_two_concurrent_requests_with_one_key_create_one_job(api):
    user_id, token = _account()
    quote = _quote(api, token)
    payload = {"tool": TOOL, "quote": quote["quote"], "input": quote["input"]}
    results = []

    def _fire():
        results.append(api.post(f"{API_V1_PREFIX}/jobs", json=payload,
                                headers=_auth(token, "race-them-together1")))

    threads = [threading.Thread(target=_fire) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    statuses = sorted(response.status_code for response in results)
    # Exactly one creates; the other either replays (200) or is told the first
    # is still in flight (409). Both are correct; two holds would not be.
    assert statuses.count(201) == 1
    assert set(statuses) <= {200, 201, 409}
    assert _rows(user_id, CREDIT_HOLD) == 1
    assert _balance(user_id) == 95


# ── Crash safety ──────────────────────────────────────────────────────────────

def test_a_crash_between_hold_and_queue_leaves_neither(api, monkeypatch):
    """Injected failure after the hold: the transaction must take it all back.

    There is no queue outside the database (Q26), so "credit held but job lost"
    can only happen if the two ever commit separately. This proves they do not.
    """
    user_id, token = _account()
    quote = _quote(api, token)

    from platform_core.public_api import idempotency as idem_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("crash after the hold, before the commit")

    monkeypatch.setattr(idem_mod, "complete", _boom)
    with pytest.raises(RuntimeError):
        api.post(f"{API_V1_PREFIX}/jobs",
                 json={"tool": TOOL, "quote": quote["quote"],
                       "input": quote["input"]},
                 headers=_auth(token, "crash-in-the-middle1"))

    assert _balance(user_id) == 100
    assert _rows(user_id, CREDIT_HOLD) == 0
    gen, db = _session()
    try:
        assert db.execute(sa.select(sa.func.count(Job.id)).where(
            Job.user_id == user_id)).scalar_one() == 0
        from platform_core.public_api.tables import ApiIdempotencyRecord
        assert db.execute(sa.select(sa.func.count(ApiIdempotencyRecord.id))
                          ).scalar_one() == 0
    finally:
        _close(gen)


def test_every_hold_in_the_ledger_has_a_job(api):
    """Ledger invariant, checked over everything this test file created."""
    _user_id, token = _account()
    for index in range(3):
        quote = _quote(api, token)
        api.post(f"{API_V1_PREFIX}/jobs",
                 json={"tool": TOOL, "quote": quote["quote"],
                       "input": quote["input"]},
                 headers=_auth(token, f"ledger-invariant-{index}0"))

    gen, db = _session()
    try:
        holds = db.execute(sa.select(CreditEntry).where(
            CreditEntry.kind == CREDIT_HOLD)).scalars().all()
        assert holds
        for entry in holds:
            assert entry.job_id
            assert db.get(Job, entry.job_id) is not None
    finally:
        _close(gen)


# ── Reading and cancelling ────────────────────────────────────────────────────

def test_listing_is_owner_scoped_and_paginated(api):
    alice_id, alice = _account()
    _bob_id, bob = _account()
    for index in range(3):
        quote = _quote(api, alice)
        api.post(f"{API_V1_PREFIX}/jobs",
                 json={"tool": TOOL, "quote": quote["quote"],
                       "input": quote["input"]},
                 headers=_auth(alice, f"alice-job-number-{index}"))

    listed = api.get(f"{API_V1_PREFIX}/jobs?limit=2", headers=_auth(alice)).json()
    assert len(listed["items"]) == 2 and listed["page"]["has_more"] is True

    assert api.get(f"{API_V1_PREFIX}/jobs", headers=_auth(bob)).json()["items"] == []

    bad = api.get(f"{API_V1_PREFIX}/jobs?status=nonsense", headers=_auth(alice))
    assert bad.status_code == 400


def test_one_account_cannot_read_or_cancel_another_accounts_job(api):
    _alice_id, alice = _account()
    _bob_id, bob = _account()
    quote = _quote(api, alice)
    job_id = api.post(f"{API_V1_PREFIX}/jobs",
                      json={"tool": TOOL, "quote": quote["quote"],
                            "input": quote["input"]},
                      headers=_auth(alice, "alices-private-job1")).json()["id"]

    assert api.get(f"{API_V1_PREFIX}/jobs/{job_id}",
                   headers=_auth(bob)).status_code == 404
    assert api.post(f"{API_V1_PREFIX}/jobs/{job_id}/cancel",
                    headers=_auth(bob)).status_code == 404
    # And a random id looks exactly the same to its own owner.
    assert api.get(f"{API_V1_PREFIX}/jobs/{uuid.uuid4()}",
                   headers=_auth(alice)).status_code == 404


def test_cancelling_refunds_once_and_is_idempotent(api):
    user_id, token = _account()
    quote = _quote(api, token, count=2)
    job_id = api.post(f"{API_V1_PREFIX}/jobs",
                      json={"tool": TOOL, "quote": quote["quote"],
                            "input": quote["input"]},
                      headers=_auth(token, "cancel-me-twice-key1")).json()["id"]
    assert _balance(user_id) == 90

    first = api.post(f"{API_V1_PREFIX}/jobs/{job_id}/cancel", headers=_auth(token))
    second = api.post(f"{API_V1_PREFIX}/jobs/{job_id}/cancel", headers=_auth(token))
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == "cancelled"
    assert _balance(user_id) == 100
    assert _rows(user_id, CREDIT_REFUND) == 1


def test_a_finished_job_reports_what_was_actually_charged(api):
    user_id, token = _account()
    quote = _quote(api, token, count=2)
    job_id = api.post(f"{API_V1_PREFIX}/jobs",
                      json={"tool": TOOL, "quote": quote["quote"],
                            "input": quote["input"]},
                      headers=_auth(token, "settle-me-please-k1")).json()["id"]

    gen, db = _session()
    try:
        from platform_core import credit, jobs as jobq

        job = db.get(Job, job_id)
        jobq.complete(db, job, {"text": "ok"})
        # Provider overshoot: Q84 caps what the customer pays at the hold.
        settlement = credit.quyet_toan(db, user_id, job_id, 40)
        db.commit()
        assert settlement.charged_credit == 10 and settlement.variance_credit == 30
    finally:
        _close(gen)

    body = api.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=_auth(token)).json()
    assert body["status"] == "succeeded"
    assert body["credit"] == {"held": 10, "charged": 10}
    assert _balance(user_id) == 90
    assert _rows(user_id, CREDIT_SETTLE) == 1


def test_a_cancel_after_completion_does_not_refund(api):
    user_id, token = _account()
    quote = _quote(api, token)
    job_id = api.post(f"{API_V1_PREFIX}/jobs",
                      json={"tool": TOOL, "quote": quote["quote"],
                            "input": quote["input"]},
                      headers=_auth(token, "race-cancel-vs-done1")).json()["id"]

    gen, db = _session()
    try:
        from platform_core import credit, jobs as jobq

        job = db.get(Job, job_id)
        jobq.complete(db, job, {"text": "ok"})
        credit.quyet_toan(db, user_id, job_id, 5)
        db.commit()
    finally:
        _close(gen)

    response = api.post(f"{API_V1_PREFIX}/jobs/{job_id}/cancel", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert _balance(user_id) == 95
    assert _rows(user_id, CREDIT_REFUND) == 0

    gen, db = _session()
    try:
        assert db.get(Job, job_id).status == JOB_DONE
    finally:
        _close(gen)


def test_cancel_requires_its_own_scope(api):
    _user_id, token = _account(scopes=(SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE,
                                       SCOPE_JOBS_READ))
    quote = _quote(api, token)
    job_id = api.post(f"{API_V1_PREFIX}/jobs",
                      json={"tool": TOOL, "quote": quote["quote"],
                            "input": quote["input"]},
                      headers=_auth(token, "no-cancel-scope-key1")).json()["id"]
    denied = api.post(f"{API_V1_PREFIX}/jobs/{job_id}/cancel", headers=_auth(token))
    assert denied.status_code == 403

    gen, db = _session()
    try:
        assert db.get(Job, job_id).status != JOB_CANCELLED
    finally:
        _close(gen)
