"""EXT-10 — webhook console: resend, test, rotate, and the rules behind them.

The dangerous operation here is resend. A support conversation that ends in
"just resend it" must not be able to re-run work, re-charge a customer, or make
a receiver process the same event twice — and those are three different
mistakes, so they get three different tests.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import (keys as devkeys, limits, webhook_console,
                                      webhooks)
from platform_core.public_api.tables import (WEBHOOK_DEAD, WEBHOOK_PENDING,
                                             WebhookDelivery,
                                             WebhookSubscription)
from server.api.inventory import API_V1_PREFIX

PEPPER = "console-test-pepper-" + "c" * 40
TOOL = "image.thumbnail"
RECEIVER = "https://receiver.example.com/hook"


def _public_dns(host: str) -> list:
    """Resolve the test receiver without depending on somebody else's DNS.

    The production path resolves for real and refuses a host it cannot resolve;
    the SSRF rules themselves are exercised with explicit resolvers below.
    """
    if host.endswith("example.com"):
        return ["93.184.216.34"]
    raise OSError(f"unknown test host: {host}")


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setattr(webhooks, "_system_resolver", _public_dns)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'console.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY",
                       "console-encryption-key-0123456789")
    monkeypatch.setenv("GEMINI_API_KEY", "stub-key-not-used")
    limits.reset()

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())

    import apps.thumbnail.jobs as thumbnail_jobs
    from tests.gia_dieu_phoi_anh import tiem as _tiem_dieu_phoi
    _tiem_dieu_phoi(monkeypatch, thumbnail_jobs)

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "console-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL,
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    storage_mod.set_storage(None)
    limits.reset()
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


def _csrf(html: str) -> str:
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def _account(client, scopes=("tools:read", "jobs:create", "jobs:read",
                             "webhooks:manage")):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    email = f"wc-{uuid.uuid4().hex[:6]}@example.com"
    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, 200, by="test")
        db.commit()
        user_id = user.id
    finally:
        _close(gen)

    page = client.get("/login").text
    client.post("/login", data={"username": email,
                                "password": "a-good-password-12",
                                "csrf_token": _csrf(page)},
                follow_redirects=False)
    keys_page = client.get("/developers/keys").text
    created = client.post("/developers/keys",
                          data={"name": "console", "csrf_token": _csrf(keys_page),
                                "scopes": list(scopes)})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)
    return user_id, token


def _subscribe(client, token, url: str = RECEIVER):
    response = client.post(f"{API_V1_PREFIX}/webhooks",
                           json={"url": url},
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code in (200, 201), response.text
    return response.json()


def _delivery_rows(user_id: str) -> list:
    gen, db = _session()
    try:
        return webhook_console.deliveries_for(db, user_id=user_id)
    finally:
        _close(gen)


def _post(client, path: str) -> None:
    page = client.get("/developers/webhooks").text
    client.post(path, data={"csrf_token": _csrf(page)}, follow_redirects=False)


# ── Resend ───────────────────────────────────────────────────────────────────

def _finished_job_with_delivery(client, token, user_id):
    """One real job that ran, and the delivery its terminal state queued."""
    quote = client.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": {"topic": "hook", "count": 1}},
                        headers={"Authorization": f"Bearer {token}"}).json()
    created = client.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote["quote"],
              "input": {"topic": "hook", "count": 1}},
        headers={"Authorization": f"Bearer {token}",
                 "Idempotency-Key": f"console-{uuid.uuid4().hex[:8]}"})
    assert created.status_code == 201
    from platform_core.job_runner import _chay_mot_job
    assert _chay_mot_job("console-worker") is True
    rows = _delivery_rows(user_id)
    assert rows, "a finished job queues a delivery"
    return created.json()["id"], rows[0]


def test_resend_reuses_the_event_id_and_payload(portal):
    user_id, token = _account(portal)
    _subscribe(portal, token)
    _job_id, delivery = _finished_job_with_delivery(portal, token, user_id)
    before = {"event_id": delivery.event_id,
              "payload": dict(delivery.payload or {})}

    _post(portal, f"/developers/webhooks/deliveries/{delivery.id}/resend")

    after = _delivery_rows(user_id)[0]
    assert after.id == delivery.id, "the row is reused, not copied"
    assert after.event_id == before["event_id"]
    assert after.status == WEBHOOK_PENDING and after.attempts == 0
    # The receiver deduplicates on the event id; a fresh id would defeat that.
    assert after.payload["id"] == before["payload"]["id"]
    assert after.payload["type"] == before["payload"]["type"]
    assert after.payload["_resends"] == 1


def test_resend_touches_neither_the_job_nor_the_ledger(portal):
    """The rule that makes 'just resend it' safe to say out loud."""
    import sqlalchemy as sa
    from platform_core.models import CreditEntry, Job

    user_id, token = _account(portal)
    _subscribe(portal, token)
    job_id, delivery = _finished_job_with_delivery(portal, token, user_id)

    def _snapshot():
        gen, db = _session()
        try:
            job = db.get(Job, job_id)
            ledger = db.execute(sa.select(CreditEntry).where(
                CreditEntry.user_id == user_id).order_by(
                    CreditEntry.created_at)).scalars().all()
            return (job.status, job.attempts,
                    [(entry.kind, entry.delta) for entry in ledger])
        finally:
            _close(gen)

    before = _snapshot()
    _post(portal, f"/developers/webhooks/deliveries/{delivery.id}/resend")
    assert _snapshot() == before


def test_a_dead_delivery_can_be_revived(portal):
    """The case the button exists for: the receiver was down all afternoon."""
    user_id, token = _account(portal)
    _subscribe(portal, token)
    _job_id, delivery = _finished_job_with_delivery(portal, token, user_id)

    gen, db = _session()
    try:
        row = db.get(WebhookDelivery, delivery.id)
        row.status = WEBHOOK_DEAD
        row.attempts = webhooks.MAX_ATTEMPTS
        db.commit()
    finally:
        _close(gen)

    _post(portal, f"/developers/webhooks/deliveries/{delivery.id}/resend")
    after = _delivery_rows(user_id)[0]
    assert after.status == WEBHOOK_PENDING and after.attempts == 0


def test_resend_is_rate_limited(portal):
    user_id, token = _account(portal)
    _subscribe(portal, token)
    _job_id, delivery = _finished_job_with_delivery(portal, token, user_id)

    gen, db = _session()
    try:
        row = db.get(WebhookDelivery, delivery.id)
        payload = dict(row.payload or {})
        payload["_resends"] = webhook_console.RESEND_LIMIT_PER_HOUR
        payload["_resent_at"] = datetime.now(timezone.utc).isoformat()
        row.payload = payload
        db.commit()
        with pytest.raises(webhook_console.WebhookConsoleError):
            webhook_console.resend(db, row)
    finally:
        _close(gen)


def test_resend_only_works_on_your_own_delivery(portal):
    first_id, first_token = _account(portal)
    _subscribe(portal, first_token)
    _job_id, delivery = _finished_job_with_delivery(portal, first_token, first_id)

    portal.post("/logout", data={}, follow_redirects=False)
    _second_id, _second_token = _account(portal)
    _post(portal, f"/developers/webhooks/deliveries/{delivery.id}/resend")

    after = _delivery_rows(first_id)[0]
    assert "_resends" not in (after.payload or {})


# ── Test event ───────────────────────────────────────────────────────────────

def test_a_test_event_says_it_is_a_test_and_costs_nothing(portal):
    import sqlalchemy as sa
    from platform_core.models import CreditEntry, Job

    user_id, token = _account(portal)
    subscription = _subscribe(portal, token)

    gen, db = _session()
    try:
        jobs_before = int(db.execute(
            sa.select(sa.func.count(Job.id))).scalar_one())
        ledger_before = int(db.execute(
            sa.select(sa.func.count(CreditEntry.id))).scalar_one())
    finally:
        _close(gen)

    _post(portal, f"/developers/webhooks/{subscription['id']}/test")

    rows = _delivery_rows(user_id)
    assert len(rows) == 1
    event = rows[0]
    assert event.event_type == webhook_console.EVENT_TEST
    assert event.job_id == ""
    assert "test event" in event.payload["data"]["message"].lower()

    gen, db = _session()
    try:
        assert int(db.execute(
            sa.select(sa.func.count(Job.id))).scalar_one()) == jobs_before
        assert int(db.execute(
            sa.select(sa.func.count(CreditEntry.id))).scalar_one()) == ledger_before
    finally:
        _close(gen)


def test_a_test_event_goes_through_the_real_delivery_path(portal):
    """Otherwise it proves nothing about the wiring it is meant to prove."""
    user_id, token = _account(portal)
    subscription = _subscribe(portal, token)
    _post(portal, f"/developers/webhooks/{subscription['id']}/test")

    sent = []

    def _sender(sub, delivery, **kwargs):
        sent.append((sub.url, delivery.event_type, delivery.payload))
        return 200

    from platform_core.public_api import outbox

    gen, db = _session()
    try:
        report = outbox.deliver_due(db, sender=_sender)
        db.commit()
    finally:
        _close(gen)
    assert report["delivered"] == 1
    assert sent and sent[0][0] == RECEIVER
    assert sent[0][1] == webhook_console.EVENT_TEST


# ── Rotation ─────────────────────────────────────────────────────────────────

def test_rotation_signs_with_both_secrets_during_the_grace_window(portal):
    user_id, token = _account(portal)
    created = _subscribe(portal, token)
    old_secret = created["secret"]

    page = portal.get("/developers/webhooks").text
    response = portal.post(
        f"/developers/webhooks/{created['id']}/rotate",
        data={"csrf_token": _csrf(page)}, follow_redirects=False)
    # The secret must not travel in the URL: history, Referer and access logs
    # all keep query strings. It comes back on the next render, once.
    assert "secret=" not in response.headers["location"]
    shown = portal.get("/developers/webhooks").text
    new_secret = re.search(r"<code>([A-Za-z0-9_-]{20,})</code>", shown).group(1)
    assert new_secret and new_secret != old_secret
    # …and it is gone on the next load.
    assert new_secret not in portal.get("/developers/webhooks").text

    _post(portal, f"/developers/webhooks/{created['id']}/test")

    captured = {}

    def _sender(sub, delivery, **kwargs):
        from platform_core.public_api import delivery as delivery_mod
        captured["headers"] = delivery_mod.build_headers(sub, delivery)
        return 200

    from platform_core.public_api import outbox

    gen, db = _session()
    try:
        outbox.deliver_due(db, sender=_sender)
        db.commit()
    finally:
        _close(gen)

    headers = captured["headers"]
    signature = headers[webhooks.SIGNATURE_HEADER]
    body = webhooks.canonical_body(_delivery_rows(user_id)[0].payload)
    stamp = int(headers[webhooks.TIMESTAMP_HEADER])
    event_id = headers[webhooks.EVENT_HEADER]
    # A receiver that already switched verifies…
    assert webhooks.verify(new_secret, timestamp=stamp, event_id=event_id,
                           body=body, signature=signature)
    # …and one that has not yet switched still verifies.
    assert webhooks.verify(old_secret, timestamp=stamp, event_id=event_id,
                           body=body, signature=signature)


def test_the_old_secret_stops_working_after_the_window(portal):
    _user_id, token = _account(portal)
    created = _subscribe(portal, token)

    gen, db = _session()
    try:
        subscription = db.get(WebhookSubscription, created["id"])
        webhook_console.rotate_secret(db, subscription)
        db.commit()
        assert webhook_console.grace_secret(subscription) is not None
        later = datetime.now(timezone.utc) + webhook_console.ROTATION_GRACE \
            + timedelta(minutes=1)
        assert webhook_console.grace_secret(subscription, now=later) is None
    finally:
        _close(gen)


# ── Disable ──────────────────────────────────────────────────────────────────

def test_disabling_keeps_the_history_and_stops_new_events(portal):
    user_id, token = _account(portal)
    created = _subscribe(portal, token)
    _job_id, _delivery = _finished_job_with_delivery(portal, token, user_id)
    before = len(_delivery_rows(user_id))

    _post(portal, f"/developers/webhooks/{created['id']}/disable")

    gen, db = _session()
    try:
        subscription = db.get(WebhookSubscription, created["id"])
        assert subscription is not None, "disabled, not deleted"
        assert subscription.enabled is False
    finally:
        _close(gen)
    assert len(_delivery_rows(user_id)) == before

    # A later job queues nothing for a disabled endpoint.
    _finished_job_with_delivery(portal, token, user_id)
    assert len(_delivery_rows(user_id)) == before


# ── SSRF regression ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "http://receiver.example.com/hook",     # plain http
    "https://127.0.0.1/hook",
    "https://[::1]/hook",
    "https://169.254.169.254/latest/meta-data/",
])
def test_the_console_cannot_reach_an_internal_target(portal, url):
    """Every console operation ends in a request we make; the guard is the
    same one subscription creation uses, and it is checked again here."""
    _user_id, token = _account(portal)
    refused = portal.post(f"{API_V1_PREFIX}/webhooks", json={"url": url},
                          headers={"Authorization": f"Bearer {token}"})
    assert refused.status_code == 400, url


def test_a_resend_revalidates_the_target_before_sending(portal, monkeypatch):
    """The URL was safe when it was registered; it is checked again on the way
    out, because DNS can be repointed after the fact."""
    from platform_core.public_api import delivery as delivery_mod

    user_id, token = _account(portal)
    _subscribe(portal, token)
    _job_id, delivery = _finished_job_with_delivery(portal, token, user_id)
    _post(portal, f"/developers/webhooks/deliveries/{delivery.id}/resend")

    seen = []
    monkeypatch.setattr(
        webhooks, "validate_target",
        lambda url, **kwargs: seen.append(url))
    try:
        delivery_mod.send_delivery(
            _subscription_of(user_id), _delivery_rows(user_id)[0],
            resolver=lambda host: ["203.0.113.10"])
    except Exception:                          # noqa: BLE001 - no real receiver
        pass
    assert seen and seen[0] == RECEIVER


def _subscription_of(user_id: str):
    gen, db = _session()
    try:
        import sqlalchemy as sa
        return db.execute(sa.select(WebhookSubscription).where(
            WebhookSubscription.user_id == user_id)).scalars().first()
    finally:
        _close(gen)


# ── The page ─────────────────────────────────────────────────────────────────

def test_the_console_documents_the_event_catalog_and_the_signature(portal):
    _account(portal)
    page = portal.get("/developers/webhooks").text
    for fragment in ("job.succeeded", "job.failed", "job.cancelled",
                     webhook_console.EVENT_TEST, webhooks.SIGNATURE_HEADER,
                     webhooks.TIMESTAMP_HEADER, webhooks.EVENT_HEADER,
                     "hmac"):
        assert fragment in page, fragment


def test_the_console_explains_ordering_and_duplicates(portal):
    _account(portal)
    page = portal.get("/developers/webhooks").text.lower()
    assert "thứ tự" in page and "trùng" in page


def test_the_console_never_shows_a_stored_secret(portal):
    _user_id, token = _account(portal)
    created = _subscribe(portal, token)
    page = portal.get("/developers/webhooks").text
    assert created["secret"] not in page


def test_every_console_write_needs_a_csrf_token(portal):
    user_id, token = _account(portal)
    created = _subscribe(portal, token)
    _job_id, delivery = _finished_job_with_delivery(portal, token, user_id)

    for path in (f"/developers/webhooks/{created['id']}/test",
                 f"/developers/webhooks/{created['id']}/rotate",
                 f"/developers/webhooks/{created['id']}/disable",
                 f"/developers/webhooks/deliveries/{delivery.id}/resend"):
        portal.post(path, data={}, follow_redirects=False)

    rows = _delivery_rows(user_id)
    assert len(rows) == 1 and rows[0].event_type != webhook_console.EVENT_TEST
    gen, db = _session()
    try:
        assert db.get(WebhookSubscription, created["id"]).enabled is True
    finally:
        _close(gen)
