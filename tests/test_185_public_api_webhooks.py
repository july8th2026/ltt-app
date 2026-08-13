"""Q92 / Prompt 09 — webhook outbox, signing, retry, SSRF.

Two things must hold no matter what a receiver does: a job settles regardless,
and a customer-supplied URL never becomes a way to reach inside the network.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from platform_core.models import CREDIT_SETTLE, CreditEntry, Job
from platform_core.public_api import keys as devkeys, outbox, webhooks
from platform_core.public_api.errors import ApiError
from platform_core.public_api.scopes import (SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
                                             SCOPE_TOOLS_READ,
                                             SCOPE_WEBHOOKS_MANAGE)
from platform_core.public_api.tables import (WEBHOOK_DEAD, WEBHOOK_DELIVERED,
                                             WEBHOOK_FAILED, WEBHOOK_PENDING,
                                             WebhookDelivery, WebhookSubscription)
from platform_core.registry import AppManifest, LoadedApp, ToolSpec
from server.api.inventory import API_V1_PREFIX

PEPPER = "hook-test-pepper-" + "t" * 40
TOOL = "text.hooked"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_WEBHOOKS_MANAGE)


def _fixture_apps():
    tool = ToolSpec(
        name=TOOL, job_type="samplehook.generate", description="Fixture tool.",
        params_schema={"prompt": {"type": "string", "required": True,
                                  "max_length": 100}},
        returns={"text": "text"}, api_exposed=True,
        api_contract={"scopes": (SCOPE_JOBS_CREATE,)})
    manifest = AppManifest(
        slug="samplehook", display_name="Sample", route_prefix="/samplehook",
        job_types=("samplehook.generate",), credit_cost=lambda params: 5,
        lifecycle="released", surface="customer", tools=(tool,))
    return [LoadedApp(manifest=manifest, router=None, error="")]


def _public_dns(host: str) -> list:
    """Resolve the fixture receivers without touching real DNS.

    The production path resolves for real and refuses a host it cannot resolve —
    correct, but it would make this suite depend on the network and on somebody
    else's DNS records.
    """
    if host.endswith("example.com"):
        return ["93.184.216.34"]
    raise OSError(f"unknown test host: {host}")


@pytest.fixture()
def api(tmp_path, monkeypatch):
    import platform_core.registry as registry_mod
    monkeypatch.setattr(registry_mod, "discover", _fixture_apps)
    monkeypatch.setattr(webhooks, "_system_resolver", _public_dns)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hooks.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "hook-encryption-key-0123456789")

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "hooks-secret-value",
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


def _account(credits: int = 500):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"h-{uuid.uuid4().hex[:8]}@example.com",
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


def _subscribe(api, token, url="https://receiver.example.com/hook", events=None):
    return api.post(f"{API_V1_PREFIX}/webhooks",
                    json={"url": url, "events": events or []},
                    headers=_auth(token))


def _job(api, token, idem="hook-job-key-000001"):
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": {"prompt": "x"}},
                     headers=_auth(token))
    return api.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "quote": quote.json()["quote"],
                          "input": {"prompt": "x"}},
                    headers=_auth(token, idem))


def _finish(job_id, user_id):
    """Finish a job exactly the way the worker does, webhooks included."""
    from platform_core import credit, jobs as jobq
    from platform_core.job_runner import _enqueue_webhooks

    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        jobq.complete(db, job, {"text": "done"})
        credit.quyet_toan(db, user_id, job_id, 5)
        _enqueue_webhooks(db, job)
        db.commit()
    finally:
        _close(gen)


# ── SSRF ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "http://example.com/hook",              # plain http
    "https://127.0.0.1/hook",               # loopback
    "https://localhost/hook",               # loopback by name
    "https://10.0.0.5/hook",                # private
    "https://192.168.1.10/hook",            # private
    "https://169.254.169.254/latest/meta",  # cloud metadata
    "https://[::1]/hook",                   # loopback v6
    "file:///etc/passwd",                   # not http at all
    "https://user:pass@example.com/hook",   # credentials in the URL
    "",                                     # nothing
])
def test_forbidden_targets_are_refused(api, url):
    _user_id, token = _account()
    assert _subscribe(api, token, url=url).status_code == 400


def test_every_resolved_address_must_be_public():
    """A host that answers with one public and one private address is refused."""
    with pytest.raises(ApiError):
        webhooks.validate_target(
            "https://sneaky.example.com/hook",
            resolver=lambda host: ["93.184.216.34", "127.0.0.1"])
    assert webhooks.validate_target(
        "https://good.example.com/hook",
        resolver=lambda host: ["93.184.216.34"])


def test_the_target_is_revalidated_on_every_attempt(api):
    """DNS can change after a subscription was created (rebinding)."""
    _user_id, token = _account()
    created = _subscribe(api, token)
    assert created.status_code == 201

    from platform_core.public_api.delivery import send_delivery

    gen, db = _session()
    try:
        subscription = db.get(WebhookSubscription, created.json()["id"])
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()), subscription_id=subscription.id,
            user_id=subscription.user_id, event_id="e" * 32,
            event_type=webhooks.EVENT_JOB_SUCCEEDED, job_id="",
            payload={"id": "e" * 32}, next_attempt_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc))
        with pytest.raises(ApiError):
            send_delivery(subscription, delivery,
                          resolver=lambda host: ["127.0.0.1"])
    finally:
        _close(gen)


def test_a_rejection_does_not_describe_the_internal_network():
    with pytest.raises(ApiError) as private:
        webhooks.validate_target("https://10.1.2.3/hook")
    with pytest.raises(ApiError) as loopback:
        webhooks.validate_target("https://127.0.0.1/hook")
    assert private.value.detail == loopback.value.detail


# ── Signing ───────────────────────────────────────────────────────────────────

def test_a_signature_covers_time_event_and_body():
    secret = "s" * 40
    body = b'{"id":"abc"}'
    stamp = int(time.time())
    signature = webhooks.sign(secret, timestamp=stamp, event_id="abc", body=body)

    assert webhooks.verify(secret, timestamp=stamp, event_id="abc", body=body,
                           signature=signature)
    # Any change to any of the three parts invalidates it.
    assert not webhooks.verify(secret, timestamp=stamp, event_id="abc",
                               body=b'{"id":"abd"}', signature=signature)
    assert not webhooks.verify(secret, timestamp=stamp, event_id="other",
                               body=body, signature=signature)
    assert not webhooks.verify("wrong" * 8, timestamp=stamp, event_id="abc",
                               body=body, signature=signature)
    # And a replay of an old delivery is outside the tolerance window.
    assert not webhooks.verify(secret, timestamp=stamp - 3600, event_id="abc",
                               body=body, signature=signature)


def test_the_secret_is_shown_once_and_never_listed(api):
    _user_id, token = _account()
    created = _subscribe(api, token)
    secret = created.json()["secret"]
    assert secret

    listed = api.get(f"{API_V1_PREFIX}/webhooks", headers=_auth(token)).json()
    assert "secret" not in str(listed)
    assert secret not in str(listed)

    # It is recoverable by the server (it has to sign with it) but encrypted.
    gen, db = _session()
    try:
        row = db.get(WebhookSubscription, created.json()["id"])
        assert row.secret_enc != secret
        from platform_core import secretbox

        assert secretbox.giai_ma(row.secret_enc) == secret
    finally:
        _close(gen)


# ── Outbox ────────────────────────────────────────────────────────────────────

def test_a_finished_job_queues_one_event_per_subscription(api):
    user_id, token = _account()
    _subscribe(api, token)
    _subscribe(api, token, url="https://second.example.com/hook")
    job_id = _job(api, token).json()["id"]
    _finish(job_id, user_id)

    gen, db = _session()
    try:
        rows = db.execute(sa.select(WebhookDelivery)).scalars().all()
        assert len(rows) == 2
        assert {row.event_type for row in rows} == {webhooks.EVENT_JOB_SUCCEEDED}
        assert {row.status for row in rows} == {WEBHOOK_PENDING}
        # One event id for one job state, whoever it goes to.
        assert len({row.event_id for row in rows}) == 1
        payload = rows[0].payload
        assert payload["data"]["job_id"] == job_id
        assert payload["data"]["tool"] == TOOL
        # Never the result or the parameters.
        assert "result" not in str(payload) and "prompt" not in str(payload)
    finally:
        _close(gen)


def test_enqueueing_twice_does_not_duplicate_the_event(api):
    """A reclaimed job or a retried settlement must not send twice."""
    user_id, token = _account()
    _subscribe(api, token)
    job_id = _job(api, token).json()["id"]
    _finish(job_id, user_id)

    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        assert outbox.enqueue_for_job(db, job) == 0
        db.commit()
        assert db.execute(sa.select(sa.func.count(WebhookDelivery.id))
                          ).scalar_one() == 1
    finally:
        _close(gen)


def test_only_subscribed_event_types_are_queued(api):
    user_id, token = _account()
    _subscribe(api, token, events=[webhooks.EVENT_JOB_FAILED])
    job_id = _job(api, token).json()["id"]
    _finish(job_id, user_id)

    gen, db = _session()
    try:
        assert db.execute(sa.select(sa.func.count(WebhookDelivery.id))
                          ).scalar_one() == 0
    finally:
        _close(gen)


def test_a_deleted_subscription_stops_receiving(api):
    user_id, token = _account()
    created = _subscribe(api, token)
    api.delete(f"{API_V1_PREFIX}/webhooks/{created.json()['id']}",
               headers=_auth(token))
    job_id = _job(api, token).json()["id"]
    _finish(job_id, user_id)

    gen, db = _session()
    try:
        assert db.execute(sa.select(sa.func.count(WebhookDelivery.id))
                          ).scalar_one() == 0
    finally:
        _close(gen)


# ── Delivery, retry and the dead state ────────────────────────────────────────

def test_a_receiver_that_is_down_never_affects_the_job(api):
    """The acceptance criterion: settlement does not wait for anybody."""
    user_id, token = _account()
    _subscribe(api, token)
    job_id = _job(api, token).json()["id"]
    _finish(job_id, user_id)

    def _explode(subscription, delivery):
        raise ConnectionError("receiver is down")

    gen, db = _session()
    try:
        report = outbox.deliver_due(db, sender=_explode)
        db.commit()
        assert report["attempted"] == 1 and report["failed"] == 1
        # The job is still done and still settled exactly once.
        assert db.get(Job, job_id).status == "done"
        settles = db.execute(sa.select(sa.func.count(CreditEntry.id)).where(
            CreditEntry.job_id == job_id,
            CreditEntry.kind == CREDIT_SETTLE)).scalar_one()
        assert settles == 1
    finally:
        _close(gen)


def test_retries_back_off_and_eventually_die(api):
    user_id, token = _account()
    _subscribe(api, token)
    job_id = _job(api, token).json()["id"]
    _finish(job_id, user_id)

    attempts = []

    def _refuse(subscription, delivery):
        attempts.append(delivery.attempts)
        return 500

    now = datetime.now(timezone.utc)
    gen, db = _session()
    try:
        for round_number in range(webhooks.MAX_ATTEMPTS + 2):
            # Jump forward past whatever backoff was scheduled.
            outbox.deliver_due(db, sender=_refuse,
                               now=now + timedelta(days=round_number))
            db.commit()
        delivery = db.execute(sa.select(WebhookDelivery)).scalar_one()
        assert delivery.attempts == webhooks.MAX_ATTEMPTS
        assert delivery.status == WEBHOOK_DEAD
        assert delivery.last_status_code == 500
        # It stops being retried once dead.
        assert outbox.claim_due(db, now=now + timedelta(days=30)) == []
    finally:
        _close(gen)


def test_backoff_grows_and_is_capped():
    now = datetime(2026, 8, 13, tzinfo=timezone.utc)
    delays = [(webhooks.next_attempt_at(attempt, now=now) - now).total_seconds()
              for attempt in range(1, 8)]
    assert delays[0] == webhooks.BASE_BACKOFF_S
    assert all(later >= earlier for earlier, later in zip(delays, delays[1:]))
    assert max(delays) <= webhooks.MAX_BACKOFF_S
    # Jitter spreads a thundering herd without moving the attempt earlier.
    jittered = webhooks.next_attempt_at(3, now=now, jitter=1.0)
    plain = webhooks.next_attempt_at(3, now=now, jitter=0.0)
    assert jittered > plain


def test_a_successful_delivery_is_recorded_and_not_repeated(api):
    user_id, token = _account()
    _subscribe(api, token)
    job_id = _job(api, token).json()["id"]
    _finish(job_id, user_id)

    seen = []

    def _accept(subscription, delivery):
        seen.append(delivery.event_id)
        return 200

    gen, db = _session()
    try:
        report = outbox.deliver_due(db, sender=_accept)
        db.commit()
        assert report["delivered"] == 1
        delivery = db.execute(sa.select(WebhookDelivery)).scalar_one()
        assert delivery.status == WEBHOOK_DELIVERED
        assert delivery.delivered_at is not None
        # A second pass finds nothing due.
        assert outbox.deliver_due(db, sender=_accept)["attempted"] == 0
        assert len(seen) == 1
    finally:
        _close(gen)


def test_one_bad_receiver_does_not_block_another(api):
    alice_id, alice = _account()
    bob_id, bob = _account()
    _subscribe(api, alice)
    _subscribe(api, bob, url="https://bob.example.com/hook")
    alice_job = _job(api, alice, "alice-hook-job-0001").json()["id"]
    bob_job = _job(api, bob, "bob-hook-job-000001").json()["id"]
    _finish(alice_job, alice_id)
    _finish(bob_job, bob_id)

    def _selective(subscription, delivery):
        if delivery.user_id == alice_id:
            raise TimeoutError("alice's receiver hangs")
        return 200

    gen, db = _session()
    try:
        report = outbox.deliver_due(db, sender=_selective)
        db.commit()
        assert report["delivered"] == 1 and report["failed"] == 1
    finally:
        _close(gen)


# ── History and ownership ─────────────────────────────────────────────────────

def test_delivery_history_is_owner_scoped(api):
    alice_id, alice = _account()
    _bob_id, bob = _account()
    _subscribe(api, alice)
    job_id = _job(api, alice).json()["id"]
    _finish(job_id, alice_id)

    mine = api.get(f"{API_V1_PREFIX}/webhooks/deliveries", headers=_auth(alice))
    assert mine.status_code == 200 and len(mine.json()["items"]) == 1
    assert mine.json()["items"][0]["job_id"] == job_id

    theirs = api.get(f"{API_V1_PREFIX}/webhooks/deliveries", headers=_auth(bob))
    assert theirs.json()["items"] == []


def test_one_account_cannot_delete_anothers_subscription(api):
    _alice_id, alice = _account()
    _bob_id, bob = _account()
    created = _subscribe(api, alice)
    assert api.delete(f"{API_V1_PREFIX}/webhooks/{created.json()['id']}",
                      headers=_auth(bob)).status_code == 404


def test_webhooks_need_their_own_scope(api):
    _user_id, token = _account()
    gen, db = _session()
    try:
        from platform_core.public_api import keys as keys_mod

        user_id = db.execute(sa.text(
            "SELECT user_id FROM developer_api_keys LIMIT 1")).scalar_one()
        _key, limited = keys_mod.issue(db, user_id=user_id,
                                       scopes=(SCOPE_JOBS_READ,),
                                       env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
    finally:
        _close(gen)
    assert _subscribe(api, limited).status_code == 403
    assert api.get(f"{API_V1_PREFIX}/webhooks",
                   headers=_auth(limited)).status_code == 403


def test_no_secret_reaches_the_logs(api, caplog):
    import logging

    _user_id, token = _account()
    with caplog.at_level(logging.DEBUG):
        created = _subscribe(api, token)
        secret = created.json()["secret"]
        job_id = _job(api, token).json()["id"]
        _finish(job_id, _user_id)

        def _explode(subscription, delivery):
            raise ConnectionError(f"failed talking to {subscription.url}")

        gen, db = _session()
        try:
            outbox.deliver_due(db, sender=_explode)
            db.commit()
        finally:
            _close(gen)

    captured = "\n".join(record.getMessage() for record in caplog.records)
    assert secret not in captured
    assert token not in captured
