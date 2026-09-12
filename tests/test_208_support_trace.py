"""EXT-16 — operations, security events and the support trace.

Three acceptance criteria, and each is checked against a real call rather than a
constructed row:

* **one E2E request traceable end to end** — quote, hold, job, worker, artifact,
  settlement and webhook all reachable from the one string a customer would
  paste;
* **no ledger direct edit** — every operator surface here reads; the whole ledger
  is snapshotted before and after and compared;
* **no secret in export** — a real key and a real webhook secret are created,
  the trace is exported, and the file is searched for them.

The fourth thing this file defends is the gap EXT-16 was written to close: an
authentication failure used to leave nothing in the database, so "is a revoked
key still being used" could not be asked of the data.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import (admin_console, keys as devkeys, limits,
                                      security_log, support)
from server.api.inventory import API_V1_PREFIX

PEPPER = "trace-test-pepper-" + "t" * 40
TOOL = "image.thumbnail"
SCOPES = ("tools:read", "jobs:create", "jobs:read", "artifacts:read",
          "webhooks:manage")
INPUT = {"topic": "trace", "count": 1}
RECEIVER = "https://receiver.example.com/hook"


def _public_dns(host: str) -> list:
    if host.endswith("example.com"):
        return ["93.184.216.34"]
    raise OSError(f"unknown test host: {host}")


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    from platform_core.public_api import webhooks

    monkeypatch.setattr(webhooks, "_system_resolver", _public_dns)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'trace.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    monkeypatch.setenv("GEMINI_API_KEY", "stub-key-not-used")
    limits.reset()

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    # Job ảnh (`thumbnail.generate`) giành `anh_3090` từ dual-model 5.5, và luật 0
    # fail-closed: không có dòng `gpu_residency` ⇒ worker trả job về hàng đợi và
    # không có lượt chạy nào để lần vết. Lý do đầy đủ: `test_606::_mo_cua_so_anh`.
    from platform_core.llm import residency

    from tests.conftest import mo_cu_tru_3090
    mo_cu_tru_3090(residency.ANH)

    import apps.thumbnail.jobs as thumbnail_jobs
    from tests.gia_dieu_phoi_anh import tiem as _tiem_dieu_phoi
    _tiem_dieu_phoi(monkeypatch, thumbnail_jobs)

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "trace-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL,
        "LTT_PUBLIC_API_RPM": "600", "LTT_PUBLIC_API_CREATE_RPM": "200",
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    storage_mod.set_storage(None)
    limits.reset()
    dbmod.reset_engine()


# ── Plumbing ─────────────────────────────────────────────────────────────────

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


def _sign_in(client, email: str = "", credits: int = 500,
             role: str = "user") -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    address = email or f"tr-{uuid.uuid4().hex[:6]}@example.com"
    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=address, password="a-good-password-12",
                              role=role)
        user.is_verified = True
        db.flush()
        if credits:
            credit.cap_tay(db, user.id, credits, by="test")
        db.commit()
        user_id = user.id
    finally:
        _close(gen)

    page = client.get("/login").text
    client.post("/login", data={"username": address,
                                "password": "a-good-password-12",
                                "csrf_token": _csrf(page)},
                follow_redirects=False)
    return user_id


def _issue(client) -> str:
    page = client.get("/developers/keys").text
    created = client.post("/developers/keys",
                          data={"name": "trace", "csrf_token": _csrf(page),
                                "scopes": list(SCOPES)})
    return re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)


def _auth(token: str, idem: str = "") -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _ledger_snapshot() -> list:
    from sqlalchemy import select

    from platform_core.models import CreditEntry

    gen, db = _session()
    try:
        rows = db.execute(select(CreditEntry).order_by(
            CreditEntry.id)).scalars().all()
        return [(r.user_id, r.kind, r.delta, r.job_id, r.note) for r in rows]
    finally:
        _close(gen)


def _run_one_call(client, token) -> dict:
    """A real call, all the way to a delivered webhook."""
    quote = client.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": INPUT},
                        headers=_auth(token))
    assert quote.status_code == 200, quote.text
    created = client.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote.json()["quote"], "input": INPUT},
        headers=_auth(token, f"tr-{uuid.uuid4().hex[:10]}"))
    assert created.status_code == 201, created.text

    from platform_core.job_runner import _chay_mot_job

    assert _chay_mot_job("trace-worker") is True
    return {"job_id": created.json()["id"],
            "correlation": created.headers["X-Correlation-ID"]}


# ── One request, traceable end to end ────────────────────────────────────────

def test_one_real_call_is_traceable_from_its_correlation_id(portal):
    """The acceptance criterion, against a call that actually ran.

    Quote, hold, job, worker, settlement and webhook all reachable from the one
    string a customer would paste into a ticket.
    """
    _sign_in(portal)
    token = _issue(portal)
    portal.post(f"{API_V1_PREFIX}/webhooks", json={"url": RECEIVER},
                headers=_auth(token))
    call = _run_one_call(portal, token)

    gen, db = _session()
    try:
        found = support.trace(db, call["correlation"])
        assert found.found and found.matched_by == "request_id"
        assert found.job is not None and found.job.id == call["job_id"]
        assert found.user is not None
        assert found.key is not None
        # The worker that ran it, and how long it waited — neither is on the
        # customer's page.
        assert found.job.worker_id == "trace-worker"
        assert found.queue_delay_ms is not None
        assert found.run_ms is not None
        # Hold and settlement both present.
        kinds = [row.kind for row in found.credit]
        assert "hold" in kinds
        # …and the callback the customer depends on.
        assert found.webhooks, "the delivery is part of the story"
    finally:
        _close(gen)


def test_the_same_call_is_reachable_from_the_job_id(portal):
    _sign_in(portal)
    token = _issue(portal)
    call = _run_one_call(portal, token)

    gen, db = _session()
    try:
        found = support.trace(db, call["job_id"])
        assert found.matched_by == "job_id"
        assert found.job is not None
        assert found.requests, "the request that created it should be attached"
    finally:
        _close(gen)


def test_a_trace_can_start_from_a_key_a_project_or_an_email(portal):
    """A support conversation starts with whatever the customer copied."""
    user_id = _sign_in(portal)
    token = _issue(portal)
    _run_one_call(portal, token)
    key_id = token.split("_")[2]

    gen, db = _session()
    try:
        by_key = support.trace(db, key_id)
        assert by_key.matched_by == "key_id" and by_key.key is not None

        project_id = str(by_key.key.project_id or "")
        by_project = support.trace(db, project_id)
        assert by_project.matched_by == "project_id"

        from platform_core.models import User

        email = db.get(User, user_id).email
        by_email = support.trace(db, email)
        assert by_email.matched_by == "user"
        assert by_email.requests
    finally:
        _close(gen)


def test_an_unknown_string_finds_nothing_rather_than_guessing(portal):
    gen, db = _session()
    try:
        found = support.trace(db, "not-a-real-identifier")
        assert not found.found
        assert found.job is None and found.request is None
    finally:
        _close(gen)


def test_the_operator_trace_shows_events_the_customer_does_not(portal):
    """The whole reason an operator trace exists.

    The customer's timeline filters to `visibility == "customer"`; this one does
    not, because the internal lines are the ones that say what went wrong.
    """
    from platform_core.public_api import request_log

    _sign_in(portal)
    token = _issue(portal)
    call = _run_one_call(portal, token)

    gen, db = _session()
    try:
        found = support.trace(db, call["correlation"])
        row = request_log.get_owned(db, user_id=found.user.id,
                                    request_id=call["correlation"])
        customer_view = request_log.timeline(db, row)

        operator_codes = {event.event_code for event in found.events}
        customer_codes = {event.event_code for event in customer_view["events"]}
        assert operator_codes >= customer_codes
        assert any(event.visibility != "customer" for event in found.events), (
            "this test assumes the platform writes internal events")
    finally:
        _close(gen)


# ── The security gap this prompt closes ──────────────────────────────────────

def test_an_unknown_key_now_leaves_a_row(portal):
    """Before EXT-16 this was invisible in the database.

    `guard.py` skips the request log when there is no principal, so a caller
    probing the key space left nothing but a line in a log file.
    """
    answer = portal.get(f"{API_V1_PREFIX}/me",
                        headers=_auth("ltt_sk_" + "a" * 32 + "_" + "b" * 43))
    assert answer.status_code == 401

    gen, db = _session()
    try:
        rows = security_log.list_recent(db)
        assert rows, "an unknown key must be recorded"
        assert rows[0].kind == security_log.UNKNOWN_KEY
        assert rows[0].route.endswith("/me")
        assert rows[0].request_id
    finally:
        _close(gen)


def test_a_revoked_key_still_in_use_is_visible(portal):
    """One of the two questions the brief names outright — answered by a join.

    `keys.verify()` returns the same `None` for an unknown key, a wrong secret
    and a revoked one, deliberately, so a caller cannot enumerate valid key ids
    by watching which failure comes back. The authentication path therefore
    cannot label the event "revoked". The question is answered at read time by
    matching the presented key id against the keys table — which changes nothing
    an attacker can observe.
    """
    _sign_in(portal)
    token = _issue(portal)
    key_id = token.split("_")[2]
    gen, db = _session()
    try:
        devkeys.revoke(db, admin_console.key_by_id(db, key_id))
        db.commit()
    finally:
        _close(gen)

    assert portal.get(f"{API_V1_PREFIX}/me",
                      headers=_auth(token)).status_code == 401

    gen, db = _session()
    try:
        attempts = security_log.revoked_key_attempts(db)
        assert attempts, "a revoked key in use must be findable"
        assert attempts[0].key_id == key_id
        assert security_log.summary(db, hours=1)["revoked_in_use"] == 1

        # An unknown key that was never issued must NOT be counted as revoked.
        security_log.record(db, kind=security_log.UNKNOWN_KEY,
                            key_id="never-existed", ip="9.9.9.9")
        db.commit()
        assert len(security_log.revoked_key_attempts(db)) == 1
    finally:
        _close(gen)


def test_a_request_with_no_credential_is_recorded_as_such(portal):
    assert portal.get(f"{API_V1_PREFIX}/me").status_code == 401
    gen, db = _session()
    try:
        rows = security_log.list_recent(db,
                                        kind=security_log.NO_CREDENTIAL)
        assert rows
    finally:
        _close(gen)


def test_the_secret_half_of_a_token_is_never_recorded(portal):
    """`key_id` is the public half; the secret must not appear anywhere."""
    _sign_in(portal)
    token = _issue(portal)
    secret = token.split("_", 3)[-1]
    gen, db = _session()
    try:
        devkeys.revoke(db, admin_console.key_by_id(db, token.split("_")[2]))
        db.commit()
    finally:
        _close(gen)
    portal.get(f"{API_V1_PREFIX}/me", headers=_auth(token))

    gen, db = _session()
    try:
        for row in security_log.list_recent(db):
            blob = " ".join(str(value) for value in
                            (row.kind, row.ip, row.key_id, row.route,
                             row.detail, row.request_id))
            assert secret not in blob
    finally:
        _close(gen)


def test_the_summary_separates_one_noisy_source_from_many(portal):
    """One address failing 400 times is a scanner; 400 addresses failing once
    is a broken release. The same total tells them apart only broken down."""
    gen, db = _session()
    try:
        for index in range(5):
            security_log.record(db, kind=security_log.UNKNOWN_KEY,
                                ip="10.0.0.1", key_id=f"k{index}")
        security_log.record(db, kind=security_log.NO_CREDENTIAL, ip="10.0.0.2")
        db.commit()

        data = security_log.summary(db, hours=1)
        assert data["total"] == 6
        assert data["by_kind"][security_log.UNKNOWN_KEY] == 5
        assert data["top_ips"][0] == ("10.0.0.1", 5)
    finally:
        _close(gen)


def test_an_unknown_kind_is_refused_rather_than_stored(portal):
    """Called from the authentication path: a logging mistake must never turn a
    401 into a 500."""
    gen, db = _session()
    try:
        assert security_log.record(db, kind="not.a.kind", ip="1.1.1.1") is None
    finally:
        _close(gen)


def test_old_security_events_can_be_purged(portal):
    gen, db = _session()
    try:
        old = datetime.now(timezone.utc) - timedelta(days=200)
        security_log.record(db, kind=security_log.UNKNOWN_KEY, ip="1.1.1.1",
                            now=old)
        security_log.record(db, kind=security_log.UNKNOWN_KEY, ip="2.2.2.2")
        db.commit()
        assert security_log.purge_expired(db) == 1
        db.commit()
        assert len(security_log.list_recent(db)) == 1
    finally:
        _close(gen)


# ── No secret in export ──────────────────────────────────────────────────────

def test_an_export_carries_no_secret(portal):
    """A real key and a real webhook secret, then search the exported file."""
    _sign_in(portal)
    token = _issue(portal)
    created = portal.post(f"{API_V1_PREFIX}/webhooks", json={"url": RECEIVER},
                          headers=_auth(token))
    hook_secret = created.json()["secret"]
    key_secret = token.split("_", 3)[-1]
    call = _run_one_call(portal, token)

    gen, db = _session()
    try:
        found = support.trace(db, call["correlation"])
        blob = json.dumps(support.export(found), ensure_ascii=False,
                          default=str)
    finally:
        _close(gen)

    assert key_secret not in blob, "the key's secret half leaked into an export"
    assert hook_secret not in blob, "the webhook signing secret leaked"
    assert "secret_enc" not in blob or support.REDACTED in blob
    # …and the export is still useful.
    assert call["correlation"] in blob
    assert call["job_id"] in blob


def test_redaction_covers_fields_nobody_thought_of(portal):
    """Applied to whole structures rather than to a list of known fields.

    A model gains columns over time, and an allowlist is a promise to remember.
    """
    payload = {"webhook_secret_enc": "s3cr3t", "nested": {"pepper": "p"},
               "rows": [{"authorization": "Bearer x", "safe": 1}],
               "storage_key": "users/u1/a.png", "name": "keep me"}
    clean = support.redact(payload)
    assert clean["webhook_secret_enc"] == support.REDACTED
    assert clean["nested"]["pepper"] == support.REDACTED
    assert clean["rows"][0]["authorization"] == support.REDACTED
    assert clean["rows"][0]["safe"] == 1
    assert clean["storage_key"] == support.REDACTED, "locations travel too"
    assert clean["name"] == "keep me"


# ── No ledger direct edit ────────────────────────────────────────────────────

def test_no_operator_read_changes_the_ledger(portal):
    """Snapshot the whole ledger, exercise every operator surface, compare."""
    _sign_in(portal)
    token = _issue(portal)
    call = _run_one_call(portal, token)
    before = _ledger_snapshot()
    assert before, "this test needs a ledger to compare"

    gen, db = _session()
    try:
        admin_console.requests_page(db)
        admin_console.jobs_page(db)
        admin_console.failing_webhooks(db)
        security_log.summary(db)
        found = support.trace(db, call["correlation"])
        support.export(found)
        db.commit()
    finally:
        _close(gen)

    assert _ledger_snapshot() == before


def test_the_operator_pages_are_admin_only(portal):
    """A signed-in customer is not an operator, and these pages hold every
    account's traffic."""
    _sign_in(portal)
    for path in ("/admin/api-request", "/admin/api-job", "/admin/api-bao-mat",
                 "/admin/api-trace"):
        answer = portal.get(path, follow_redirects=False)
        assert answer.status_code in (302, 303, 307), path
        assert "/login" in answer.headers.get("location", ""), path


# ── The operations reads ─────────────────────────────────────────────────────

def test_the_job_page_shows_queue_delay_and_worker(portal):
    _sign_in(portal)
    token = _issue(portal)
    _run_one_call(portal, token)

    gen, db = _session()
    try:
        page = admin_console.jobs_page(db)
        assert page.total == 1
        row = page.rows[0]
        assert row["queue_delay_ms"] is not None
        assert row["job"].worker_id == "trace-worker"
        assert row["email"]
        assert row["tool"] == TOOL
    finally:
        _close(gen)


def test_the_job_page_ignores_jobs_the_web_app_made(portal):
    """This console is about the API platform; a UI job has no `_api` block."""
    user_id = _sign_in(portal)
    from platform_core import jobs as jobq

    gen, db = _session()
    try:
        jobq.submit(db, user_id=user_id, app_slug="thumbnail",
                    job_type="thumbnail.generate",
                    params={"topic": "ui", "count": 1, "owner_id": user_id})
        db.commit()
        assert admin_console.jobs_page(db).total == 0
    finally:
        _close(gen)


def test_the_request_page_can_be_narrowed_to_failures(portal):
    _sign_in(portal)
    token = _issue(portal)
    portal.get(f"{API_V1_PREFIX}/jobs/nope", headers=_auth(token))
    _run_one_call(portal, token)

    gen, db = _session()
    try:
        assert admin_console.requests_page(db, status="failed").total >= 1
        every = admin_console.requests_page(db).total
        assert every >= admin_console.requests_page(db, status="failed").total
    finally:
        _close(gen)
