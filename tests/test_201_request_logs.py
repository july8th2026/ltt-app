"""EXT-09 — request logs: a developer debugging their own calls.

The acceptance is specific: 401, 403, 409, 422, 429, 5xx and a failed job must
all be explainable afterwards. Everything else here defends the two properties
that make such a log safe to keep — it holds no payload, and it never shows one
account another account's traffic.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits, request_log
from platform_core.public_api.tables import ApiRequestLog
from server.api.inventory import API_V1_PREFIX

PEPPER = "requestlog-test-pepper-" + "r" * 40
TOOL = "image.thumbnail"
SCOPES = ("tools:read", "jobs:create", "jobs:read", "artifacts:read")


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'reqlog.db').as_posix()}")
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

    import apps.thumbnail.jobs as thumbnail_jobs
    monkeypatch.setattr(thumbnail_jobs, "_goi_gemini",
                        lambda *a, **k: b"\x89PNG\r\n\x1a\n" + b"0" * 100)

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "reqlog-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL,
        "LTT_PUBLIC_API_RPM": "40",
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


def _account(client, credits: int = 100, scopes=SCOPES):
    """A signed-in account with a key, the way a real developer starts."""
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    email = f"rl-{uuid.uuid4().hex[:6]}@example.com"
    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, credits, by="test")
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
                          data={"name": "logs", "csrf_token": _csrf(keys_page),
                                "scopes": list(scopes)})
    found = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text)
    assert found, "key creation did not reveal a token"
    return user_id, found.group(1)


def _auth(token, idem=""):
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _rows(user_id: str) -> list:
    gen, db = _session()
    try:
        return request_log.list_for(db, user_id=user_id, limit=100)
    finally:
        _close(gen)


def _quote(client, token, count=1):
    return client.post(f"{API_V1_PREFIX}/quotes",
                       json={"tool": TOOL,
                             "input": {"topic": "logs", "count": count}},
                       headers=_auth(token))


# ── Every failure class is explainable afterwards ───────────────────────────

def test_the_log_records_what_changed_or_refused_something(portal):
    """The recording rule, stated as behaviour.

    A row per request cost 177 rps → 42.6 rps on the load harness, and the
    volume was almost entirely successful polling — traffic a developer can
    already see, because the job explains itself. So: every failure, and every
    call that was not a read.
    """
    user_id, token = _account(portal)

    read = portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert read.status_code == 200
    assert _rows(user_id) == [], "a successful read is not worth a row"

    quote = _quote(portal, token)
    assert quote.status_code == 200
    rows = _rows(user_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.status == 200 and row.route.endswith("/quotes")
    assert row.request_id == quote.headers["X-Correlation-ID"]
    assert row.latency_ms >= 0

    # …and a failed read is recorded, because that is the one a developer comes
    # looking for.
    missing = portal.get(f"{API_V1_PREFIX}/jobs/nope", headers=_auth(token))
    assert missing.status_code == 404
    assert any(item.status == 404 for item in _rows(user_id))


def test_a_missing_scope_is_recorded_with_its_code(portal):
    user_id, token = _account(portal, scopes=("jobs:read",))
    denied = portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert denied.status_code == 403

    row = _rows(user_id)[0]
    assert row.status == 403 and row.code == "missing_scope"


def test_running_out_of_credit_is_recorded_as_its_own_code(portal):
    user_id, token = _account(portal, credits=1)
    quote = _quote(portal, token)
    refused = portal.post(f"{API_V1_PREFIX}/jobs",
                          json={"tool": TOOL, "quote": quote.json()["quote"],
                                "input": {"topic": "logs", "count": 1}},
                          headers=_auth(token, "reqlog-broke-1"))
    assert refused.status_code == 409

    codes = [row.code for row in _rows(user_id)]
    assert "insufficient_credit" in codes


def test_a_malformed_body_is_recorded(portal):
    user_id, token = _account(portal)
    bad = portal.post(f"{API_V1_PREFIX}/quotes",
                      json={"tool": TOOL, "input": {"nope": 1}},
                      headers=_auth(token))
    assert bad.status_code in (400, 422)
    assert _rows(user_id)[0].code in ("invalid_request", "unprocessable_request")


def test_hitting_the_rate_limit_is_recorded(portal):
    user_id, token = _account(portal)
    for _ in range(60):
        response = portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
        if response.status_code == 429:
            break
    assert response.status_code == 429
    assert any(row.status == 429 for row in _rows(user_id))


def test_a_call_with_no_credential_is_not_recorded_against_anyone(portal):
    """A row with no owner belongs to nobody and could only be shown to
    everybody. Anonymous failures stay in the operator's log."""
    user_id, token = _account(portal)
    _quote(portal, token)
    before = len(_rows(user_id))
    assert portal.get(f"{API_V1_PREFIX}/tools").status_code == 401

    gen, db = _session()
    try:
        from sqlalchemy import func, select
        total = int(db.execute(
            select(func.count(ApiRequestLog.id))).scalar_one())
    finally:
        _close(gen)
    assert len(_rows(user_id)) == before
    assert total == before


def test_a_failed_job_is_traceable_from_the_request_that_created_it(portal,
                                                                    monkeypatch):
    user_id, token = _account(portal)
    quote = _quote(portal, token)
    created = portal.post(f"{API_V1_PREFIX}/jobs",
                          json={"tool": TOOL, "quote": quote.json()["quote"],
                                "input": {"topic": "logs", "count": 1}},
                          headers=_auth(token, "reqlog-fail-1"))
    assert created.status_code == 201
    job_id = created.json()["id"]

    import apps.thumbnail.jobs as thumbnail_jobs
    monkeypatch.setattr(thumbnail_jobs, "_goi_gemini",
                        lambda *a, **k: (_ for _ in ()).throw(
                            RuntimeError("provider said no")))
    # A failed provider call is retried with a backoff, so one pass leaves the
    # job queued again and the next pass finds nothing until the delay expires.
    # Bring `next_run_at` forward instead of sleeping: the point of the test is
    # the terminal state, not the wait.
    from platform_core.job_runner import _chay_mot_job
    from platform_core.models import Job

    for _ in range(5):
        if not _chay_mot_job("reqlog-worker"):
            gen, db = _session()
            try:
                job = db.get(Job, job_id)
                if job.status != "queued":
                    break
                job.next_run_at = datetime.now(timezone.utc)
                db.commit()
            finally:
                _close(gen)
            continue

    row = next(item for item in _rows(user_id) if item.job_id == job_id)
    gen, db = _session()
    try:
        timeline = request_log.timeline(db, row)
    finally:
        _close(gen)
    assert timeline["job"] is not None and timeline["job"].status == "error"
    # The refund is part of the story, and it is in the ledger already.
    assert any(entry.delta > 0 for entry in timeline["credit"])


def test_a_finished_job_links_request_to_events_credit_and_artifacts(portal):
    user_id, token = _account(portal)
    quote = _quote(portal, token)
    created = portal.post(f"{API_V1_PREFIX}/jobs",
                          json={"tool": TOOL, "quote": quote.json()["quote"],
                                "input": {"topic": "logs", "count": 1}},
                          headers=_auth(token, "reqlog-ok-1"))
    assert created.status_code == 201
    from platform_core.job_runner import _chay_mot_job
    assert _chay_mot_job("reqlog-worker-2") is True

    row = next(item for item in _rows(user_id)
               if item.job_id == created.json()["id"])
    gen, db = _session()
    try:
        timeline = request_log.timeline(db, row)
    finally:
        _close(gen)
    assert timeline["job"].status == "done"
    assert timeline["artifacts"], "a finished image job has an artifact"
    assert any(entry.kind for entry in timeline["credit"])


def test_the_job_carries_the_request_id_that_created_it(portal):
    """Trace propagation: API → job → worker events, with no new identifier."""
    from platform_core.public_api.invocation import api_meta
    from platform_core.models import Job

    _user_id, token = _account(portal)
    quote = _quote(portal, token)
    created = portal.post(f"{API_V1_PREFIX}/jobs",
                          json={"tool": TOOL, "quote": quote.json()["quote"],
                                "input": {"topic": "logs", "count": 1}},
                          headers=_auth(token, "reqlog-trace-1"))
    gen, db = _session()
    try:
        job = db.get(Job, created.json()["id"])
        assert api_meta(job)["request_id"] == created.headers["X-Correlation-ID"]
    finally:
        _close(gen)


# ── What must never be in there ─────────────────────────────────────────────

def test_the_log_stores_no_payload_and_no_detail():
    columns = set(ApiRequestLog.__table__.columns.keys())
    for forbidden in ("body", "request_body", "response", "payload", "detail",
                      "input", "headers", "token"):
        assert forbidden not in columns, forbidden


def test_the_stored_row_carries_nothing_a_customer_typed(portal):
    """The topic is customer content; the row must not contain it."""
    user_id, token = _account(portal)
    secret_topic = "a-very-distinctive-customer-phrase"
    portal.post(f"{API_V1_PREFIX}/quotes",
                json={"tool": TOOL, "input": {"topic": secret_topic}},
                headers=_auth(token))
    for row in _rows(user_id):
        assert secret_topic not in str(
            {column: getattr(row, column)
             for column in ApiRequestLog.__table__.columns.keys()})


def test_the_log_never_contains_a_credential(portal):
    user_id, token = _account(portal)
    _quote(portal, token)
    for row in _rows(user_id):
        assert token not in str(row.__dict__)
        assert row.key_id and row.key_id in token   # public half only


# ── Tenant isolation ────────────────────────────────────────────────────────

def test_one_account_never_sees_another_accounts_requests(portal):
    first_id, first_token = _account(portal)
    _quote(portal, first_token)
    first_request = _rows(first_id)[0].request_id

    portal.post("/logout", data={}, follow_redirects=False)
    second_id, second_token = _account(portal)
    _quote(portal, second_token)

    assert all(row.user_id == second_id for row in _rows(second_id))
    page = portal.get("/developers/logs").text
    assert first_request not in page
    # …and the detail page refuses a request id that is not theirs.
    assert portal.get(f"/developers/logs/{first_request}",
                      follow_redirects=False).status_code == 404


# ── The page ────────────────────────────────────────────────────────────────

def test_the_log_page_lists_and_filters(portal):
    _user_id, token = _account(portal)
    _quote(portal, token)
    portal.get(f"{API_V1_PREFIX}/jobs/nope", headers=_auth(token))

    page = portal.get("/developers/logs").text
    assert "/api/v1/quotes" in page and "/api/v1/jobs/{job_id}" in page
    only_failures = portal.get("/developers/logs?status=4xx").text
    assert "not_found" in only_failures
    assert "/api/v1/quotes" not in only_failures


def test_the_detail_page_explains_what_to_do_about_the_code(portal):
    _user_id, token = _account(portal, scopes=("jobs:read",))
    denied = portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    detail = portal.get(
        f"/developers/logs/{denied.headers['X-Correlation-ID']}").text
    assert "missing_scope" in detail
    # The registry's advice, not a second copy written for the page.
    from platform_core.public_api.error_registry import spec_for
    assert spec_for("missing_scope").action[:40] in detail


def test_the_logs_section_is_linked_and_needs_a_session(portal):
    # Signed out first: logging out needs a CSRF token, and a test that fakes
    # the sign-out proves nothing about the signed-out case.
    assert portal.get("/developers/logs",
                      follow_redirects=False).status_code in (302, 303)
    _account(portal)
    assert 'href="/developers/logs"' in portal.get("/developers").text


# ── Retention ───────────────────────────────────────────────────────────────

def test_old_rows_are_purged_and_recent_ones_are_not(portal):
    user_id, token = _account(portal)
    _quote(portal, token)

    gen, db = _session()
    try:
        old = request_log.record(
            db, request_id="old-" + uuid.uuid4().hex, user_id=user_id,
            method="GET", route="/api/v1/me", status=200,
            now=datetime.now(timezone.utc) - timedelta(days=90))
        db.commit()
        removed = request_log.purge_expired(db)
        db.commit()
        assert removed == 1
        assert db.get(ApiRequestLog, old.id) is None
        assert request_log.list_for(db, user_id=user_id)
    finally:
        _close(gen)


def test_the_worker_prunes_the_request_log():
    """Retention that only exists as a function nobody calls is not retention."""
    from pathlib import Path

    source = Path("platform_core/job_runner.py").read_text(encoding="utf-8")
    assert "request_log.purge_expired" in source
