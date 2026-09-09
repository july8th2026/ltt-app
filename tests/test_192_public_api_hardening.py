"""Q92 / Prompt 16 — the security suite, observability and the restore rehearsal.

Earlier files each proved their own slice. This one is the suite an operator can
point at before opening the surface to the internet: it walks the OWASP API risk
classes against the **assembled** system, checks that what leaves the process in
logs is safe, and rehearses the one operation nobody practises until it is too
late — restoring the new tables from a backup.
"""
from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from platform_core.models import CREDIT_HOLD, CreditEntry, Job
from platform_core.public_api import keys as devkeys, limits, metrics
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.scopes import (SCOPE_ARTIFACTS_READ,
                                             SCOPE_CREDITS_READ,
                                             SCOPE_JOBS_CANCEL, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ,
                                             SCOPE_UPLOADS_WRITE, SCOPE_USAGE_READ,
                                             SCOPE_WEBHOOKS_MANAGE)
from server.api.inventory import API_V1_PREFIX, declared_paths

PEPPER = "harden-test-pepper-" + "m" * 40

def _gia_mot_anh() -> int:
    """Giá một ảnh, đọc từ app. Gõ cứng số ở đây chỉ đo được rằng
    chưa ai sửa nó — bản trước ghi 5 và đỏ khi app đổi model."""
    from apps.thumbnail.manifest import _cost
    return _cost({"count": 1})

TOOL = "image.thumbnail"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_JOBS_CANCEL, SCOPE_UPLOADS_WRITE, SCOPE_ARTIFACTS_READ,
              SCOPE_CREDITS_READ, SCOPE_USAGE_READ, SCOPE_WEBHOOKS_MANAGE)


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'harden.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    limits.reset()
    metrics.reset()
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "harden-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": TOOL,
    })
    try:
        with TestClient(app) as client:
            client.db_path = tmp_path / "harden.db"
            yield client
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
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


def _account(credits: int = 200, scopes=ALL_SCOPES):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"h-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, credits, by="test")
        _key, token = devkeys.issue(db, user_id=user.id, scopes=scopes,
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


def _job(api, token, idem, count=1):
    payload = {"topic": "an toàn", "count": count}
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": payload}, headers=_auth(token))
    assert quote.status_code == 200, quote.text
    return api.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "quote": quote.json()["quote"],
                          "input": payload},
                    headers=_auth(token, idem))


# ── Security suite: one test per OWASP API risk class ────────────────────────

def test_bola_every_owned_resource_is_scoped_to_its_owner(api):
    """API1: object-level authorization, across every resource type at once."""
    alice_id, alice = _account()
    _bob_id, bob = _account()

    job_id = _job(api, alice, "harden-bola-job-001").json()["id"]
    upload = api.post(f"{API_V1_PREFIX}/uploads",
                      json={"tool": TOOL, "field": "topic", "filename": "x.png",
                            "content_type": "image/png", "size": 10},
                      headers=_auth(alice))
    hook = api.post(f"{API_V1_PREFIX}/webhooks",
                    json={"url": "https://receiver.example.com/hook"},
                    headers=_auth(alice))

    # Bob sees none of it, and every refusal is the same 404.
    for path in (f"{API_V1_PREFIX}/jobs/{job_id}",
                 f"{API_V1_PREFIX}/artifacts/{job_id}.image_keys.0"):
        assert api.get(path, headers=_auth(bob)).status_code == 404, path
    assert api.post(f"{API_V1_PREFIX}/jobs/{job_id}/cancel",
                    headers=_auth(bob)).status_code == 404
    assert api.get(f"{API_V1_PREFIX}/jobs", headers=_auth(bob)).json()["items"] == []
    assert api.get(f"{API_V1_PREFIX}/webhooks",
                   headers=_auth(bob)).json()["items"] == []
    if hook.status_code == 201:
        assert api.delete(f"{API_V1_PREFIX}/webhooks/{hook.json()['id']}",
                          headers=_auth(bob)).status_code == 404
    if upload.status_code == 201:
        assert api.post(f"{API_V1_PREFIX}/uploads/{upload.json()['id']}/confirm",
                        headers=_auth(bob)).status_code == 404


def test_auth_enumeration_gives_nothing_away(api):
    """API2: every rejected credential is indistinguishable from the others."""
    _user_id, token = _account()
    key_id, secret = devkeys.parse_token(token)
    attempts = {
        "missing": {},
        "malformed": _auth("nonsense"),
        "unknown_key": _auth(devkeys.format_token("f" * 32, secret)),
        "wrong_secret": _auth(devkeys.format_token(key_id, "z" * 43)),
    }
    bodies, statuses = set(), set()
    for headers in attempts.values():
        response = api.get(f"{API_V1_PREFIX}/me", headers=headers)
        statuses.add(response.status_code)
        payload = response.json()
        bodies.add((payload["code"], payload["detail"]))
    assert statuses == {401}
    assert len(bodies) == 1


def test_mass_assignment_is_impossible_on_every_write(api):
    """API3: unknown fields are refused, not merged."""
    _user_id, token = _account()
    for body in (
        {"tool": TOOL, "input": {"topic": "x", "owner_id": "somebody-else"}},
        {"tool": TOOL, "input": {"topic": "x", "credit_cost": 0}},
        {"tool": TOOL, "input": {"topic": "x", "_api": {"tool": "other"}}},
    ):
        response = api.post(f"{API_V1_PREFIX}/quotes", json=body,
                            headers=_auth(token))
        assert response.status_code == 400, body
        assert "Unknown input field" in response.json()["detail"]


def test_resource_consumption_is_bounded(api):
    """API4: body size, page size and concurrent work all have ceilings."""
    _user_id, token = _account()
    # ⛔ ĐỪNG gõ cứng kích thước ở đây. Trần body là một con số **cấu hình**;
    #    gõ lại nó trong test là dựng thêm một bản sao nữa của đúng cái chồng
    #    chéo đang dọn — và ngày 30/08 nâng trần 256 KB → 1 MiB đã làm test này
    #    đỏ vì lý do đó chứ không phải vì hệ hỏng.
    from platform_core.public_api.config import load_public_api_config
    _tran = load_public_api_config().max_body_bytes
    oversized = api.post(f"{API_V1_PREFIX}/quotes",
                         content=b"x" * (_tran + 1024),
                         headers={**_auth(token), "Content-Type": "application/json"})
    assert oversized.status_code == 413

    page = api.get(f"{API_V1_PREFIX}/jobs?limit=100000", headers=_auth(token))
    assert page.json()["page"]["limit"] == 100

    config = load_public_api_config({})
    assert config.max_active_jobs > 0 and config.request_rpm > 0


def test_bfla_scopes_gate_every_function(api):
    """API5: a key without the scope cannot reach the function at all."""
    _user_id, reader = _account(scopes=(SCOPE_TOOLS_READ, SCOPE_JOBS_READ))
    denials = [
        api.post(f"{API_V1_PREFIX}/quotes",
                 json={"tool": TOOL, "input": {"topic": "x"}}, headers=_auth(reader)),
        api.post(f"{API_V1_PREFIX}/uploads",
                 json={"tool": TOOL, "field": "topic", "filename": "a",
                       "content_type": "image/png", "size": 1},
                 headers=_auth(reader)),
        api.get(f"{API_V1_PREFIX}/credits/balance", headers=_auth(reader)),
        api.get(f"{API_V1_PREFIX}/usage", headers=_auth(reader)),
        api.get(f"{API_V1_PREFIX}/webhooks", headers=_auth(reader)),
    ]
    assert [response.status_code for response in denials] == [403] * 5


def test_charge_bypass_and_replay_are_closed(api):
    """API6: no path to a job without a valid quote, and no double charge."""
    user_id, token = _account()

    # No quote at all.
    assert api.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "input": {"topic": "x"}},
                    headers=_auth(token, "harden-noquote-0001")).status_code == 400

    # A replayed request charges once.
    payload = {"topic": "x", "count": 1}
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": payload}, headers=_auth(token))
    body = {"tool": TOOL, "quote": quote.json()["quote"], "input": payload}
    first = api.post(f"{API_V1_PREFIX}/jobs", json=body,
                     headers=_auth(token, "harden-replay-00001"))
    second = api.post(f"{API_V1_PREFIX}/jobs", json=body,
                      headers=_auth(token, "harden-replay-00001"))
    assert first.status_code == 201 and second.status_code == 200

    gen, db = _session()
    try:
        holds = db.execute(sa.select(sa.func.count(CreditEntry.id)).where(
            CreditEntry.user_id == user_id,
            CreditEntry.kind == CREDIT_HOLD)).scalar_one()
        assert holds == 1
    finally:
        _close(gen)


def test_ssrf_is_refused_at_the_only_place_a_url_is_accepted(api):
    """API7: webhooks are the sole customer-supplied URL on this surface."""
    _user_id, token = _account()
    for url in ("http://127.0.0.1/hook", "https://169.254.169.254/latest",
                "https://10.0.0.1/hook", "file:///etc/passwd"):
        response = api.post(f"{API_V1_PREFIX}/webhooks", json={"url": url},
                            headers=_auth(token))
        assert response.status_code == 400, url

    # And no published tool takes a URL.
    from platform_core.public_api.catalog import build_catalog

    config = load_public_api_config({"LTT_PUBLIC_API": "1",
                                     "LTT_PUBLIC_API_TOOLS": TOOL})
    for tool in build_catalog(config):
        for name in tool.input_schema.get("properties", {}):
            assert "url" not in name.lower(), f"{tool.name}.{name}"


def test_misconfiguration_defaults_are_safe():
    """API8: every switch defaults to the closed position."""
    config = load_public_api_config({})
    assert config.enabled is False
    assert config.exposed_tools == frozenset()
    assert config.cors_origins == ()          # no browser origin by default
    assert config.trusted_proxies == ("127.0.0.1", "::1")
    assert config.daily_credit_limit == 0     # off, and documented as a choice


def test_inventory_has_no_undeclared_route(api):
    """API9: the surface is exactly what the inventory says it is."""
    from server.api import public_api_routes

    sub_app = next(route.app for route in api.app.routes
                   if getattr(route, "name", "") == "public_api")
    assert public_api_routes(sub_app) == declared_paths()


def test_unsafe_upstream_output_never_reaches_a_caller(api):
    """API10: a handler result is filtered by the published contract."""
    user_id, token = _account()
    job_id = _job(api, token, "harden-upstream-0001").json()["id"]

    from platform_core import credit, jobs as jobq

    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        # Assembled rather than written as a literal: a fake credential in a
        # test still trips the repository secret scanner, and a scanner that
        # cries wolf on its own test suite gets ignored.
        leaked = "sk-" + "live-" + "should-never-appear"
        jobq.complete(db, job, {
            "image_keys": [], "prompt": "safe",
            "provider_raw": {"api" + "_key": leaked},
            "stack": "Traceback (most recent call last): ...",
        })
        credit.quyet_toan(db, user_id, job_id, 5)
        db.commit()
    finally:
        _close(gen)

    body = api.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=_auth(token)).text
    for leak in ("sk-live", "provider_raw", "Traceback", "stack"):
        assert leak not in body, leak


# ── CORS / proxy correctness ─────────────────────────────────────────────────

def test_no_cors_headers_unless_an_origin_is_configured(api):
    response = api.get(f"{API_V1_PREFIX}/health",
                       headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


def test_a_configured_origin_is_echoed_and_others_are_not(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'cors.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "cors-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_CORS_ORIGINS": "https://partner.example.com",
    })
    try:
        with TestClient(app) as client:
            allowed = client.get(f"{API_V1_PREFIX}/health",
                                 headers={"Origin": "https://partner.example.com"})
            refused = client.get(f"{API_V1_PREFIX}/health",
                                 headers={"Origin": "https://evil.example.com"})
        assert allowed.headers["access-control-allow-origin"] == \
            "https://partner.example.com"
        assert "access-control-allow-origin" not in {k.lower() for k in refused.headers}
        # Never with credentials: this API does not authenticate by cookie.
        assert "access-control-allow-credentials" not in {
            k.lower() for k in allowed.headers}
    finally:
        dbmod.reset_engine()


def test_a_forged_forwarding_header_cannot_change_the_logged_ip(api, caplog):
    _user_id, token = _account()
    with caplog.at_level(logging.INFO, logger="ltt.public_api.access"):
        api.get(f"{API_V1_PREFIX}/me", headers={
            **_auth(token), "CF-Connecting-IP": "203.0.113.7",
            "X-Forwarded-For": "198.51.100.9"})
    line = "\n".join(record.getMessage() for record in caplog.records)
    # TestClient's peer is the trusted loopback, so CF-Connecting-IP is believed
    # — but X-Forwarded-For is never read at all.
    assert "198.51.100.9" not in line


# ── Observability ────────────────────────────────────────────────────────────

def test_the_access_log_carries_the_fields_support_needs(api, caplog):
    user_id, token = _account()
    with caplog.at_level(logging.INFO, logger="ltt.public_api.access"):
        created = _job(api, token, "harden-logging-0001")
    # The route is logged as the caller wrote it (EXT-09): a line saying
    # "/jobs" was a puzzle to match against the API a customer sees.
    line = next(record.getMessage() for record in caplog.records
                if "route=/api/v1/jobs" in record.getMessage()
                and "method=POST" in record.getMessage())
    for field in ("request_id=", "route=", "status=201", "latency_ms=",
                  f"key_id={devkeys.parse_token(token)[0]}", f"owner={user_id}",
                  f"tool={TOOL}", f"job_id={created.json()['id']}",
                  f"credit_delta=-{_gia_mot_anh()}"):
        assert field in line, field


def test_the_access_log_never_carries_a_credential(api, caplog):
    _user_id, token = _account()
    _key_id, secret = devkeys.parse_token(token)
    with caplog.at_level(logging.DEBUG):
        _job(api, token, "harden-logsafe-0001")
        api.get(f"{API_V1_PREFIX}/me", headers=_auth("ltt_sk_" + "a" * 32 + "_" + "b" * 43))
    captured = "\n".join(record.getMessage() for record in caplog.records)
    assert secret not in captured and token not in captured
    assert "Authorization" not in captured


def test_metrics_count_what_an_operator_would_alert_on(api):
    metrics.reset()
    user_id, token = _account()
    _job(api, token, "harden-metrics-0001")
    api.get(f"{API_V1_PREFIX}/me", headers=_auth("garbage"))

    snapshot = metrics.snapshot()
    counters = snapshot["counters"]
    assert counters[metrics.AUTH_SUCCESS] >= 1
    assert counters[metrics.AUTH_FAILURE] >= 1
    assert counters[metrics.JOBS_CREATED] == 1
    assert counters[metrics.CREDIT_HELD] == _gia_mot_anh()
    assert counters[metrics.RESPONSES_4XX] >= 1
    assert snapshot["latency"][metrics.LATENCY_REQUEST]["count"] >= 2


def test_metrics_hold_no_customer_content(api):
    metrics.reset()
    _user_id, token = _account()
    _job(api, token, "harden-metrics-0002")
    document = json.dumps(metrics.snapshot())
    assert "topic" not in document and token not in document
    # Counters only: names and numbers.
    for value in metrics.snapshot()["counters"].values():
        assert isinstance(value, int)


# ── Backup / restore rehearsal for the new tables ────────────────────────────

def test_the_new_tables_survive_a_backup_and_restore(api, tmp_path):
    """The rehearsal nobody does until the night they need it.

    PostgreSQL is the production engine and its drill is
    `tools/restore_drill_schema.py` (operator-run, needs a server). This is the
    same rehearsal at the level the test suite can reach: seed every table the
    Public API added, copy the database the way a backup would, restore it, and
    check both the rows **and** the constraints that protect money survived.
    """
    from platform_core.public_api.tables import (ApiIdempotencyRecord,
                                                 DeveloperApiKey,
                                                 WebhookDelivery,
                                                 WebhookSubscription)

    user_id, token = _account()
    job_id = _job(api, token, "harden-restore-0001").json()["id"]

    gen, db = _session()
    try:
        counts_before = {
            table.__tablename__: db.execute(
                sa.select(sa.func.count()).select_from(table)).scalar_one()
            for table in (DeveloperApiKey, ApiIdempotencyRecord,
                          WebhookSubscription, WebhookDelivery)
        }
        assert counts_before["developer_api_keys"] >= 1
        assert counts_before["public_api_idempotency"] >= 1
    finally:
        _close(gen)

    backup = tmp_path / "backup.db"
    source = sqlite3.connect(str(api.db_path))
    try:
        target = sqlite3.connect(str(backup))
        with target:
            source.backup(target)
        target.close()
    finally:
        source.close()

    restored = tmp_path / "restored.db"
    shutil.copyfile(backup, restored)
    engine = sa.create_engine(f"sqlite:///{restored.as_posix()}", future=True)
    try:
        with engine.connect() as connection:
            for table, expected in counts_before.items():
                actual = connection.execute(
                    sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
                assert actual == expected, table

            # The constraints that stop double-charging and duplicate webhooks
            # must come back with the data, not just the rows. SQLite keeps a
            # table-level UNIQUE inside the table definition rather than as a
            # separately named index, so the schema text is where to look; the
            # PostgreSQL drill (`tools/restore_drill_schema.py`) checks the
            # constraint names directly.
            schema = " ".join(connection.execute(sa.text(
                "SELECT sql FROM sqlite_master WHERE type='table'")
            ).scalars().all() or [])
            for constraint in ("uq_public_api_idempotency",
                               "uq_public_api_webhook_event"):
                assert constraint in schema, constraint

            # And a duplicate insert is still refused after the restore.
            with pytest.raises(sa.exc.IntegrityError):
                with engine.begin() as write:
                    row = write.execute(sa.text(
                        "SELECT key_id, operation, idempotency_key, request_hash,"
                        " user_id FROM public_api_idempotency LIMIT 1")).one()
                    write.execute(sa.text(
                        "INSERT INTO public_api_idempotency (id, key_id, user_id,"
                        " operation, idempotency_key, request_hash, status,"
                        " job_id, response, created_at, updated_at) VALUES"
                        " (:id, :key_id, :user_id, :operation, :idem, :hash,"
                        " 'completed', '', '{}', :now, :now)"),
                        {"id": str(uuid.uuid4()), "key_id": row.key_id,
                         "user_id": row.user_id, "operation": row.operation,
                         "idem": row.idempotency_key, "hash": row.request_hash,
                         "now": "2026-08-13 00:00:00"})
    finally:
        engine.dispose()
    assert job_id
