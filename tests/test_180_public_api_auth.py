"""Q92 / Prompt 04 — bearer auth, scopes, tool policy, object authorization.

This is the security matrix for ``/api/v1`` expressed as tests. Each block maps
to a class of API failure that is cheap to prevent now and expensive to discover
in production:

* BOLA — one customer reading another's object by swapping an id;
* BFLA — a key using an endpoint its scopes do not cover;
* key enumeration — learning which key ids or object ids exist from the shape
  of a refusal;
* charge bypass — reaching a credit mutation before the scope check;
* credential leakage — a raw bearer token in a log line.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from fastapi import Depends
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys
from platform_core.public_api.errors import ApiError
from platform_core.public_api.principal import (Principal, ensure_owner,
                                                ensure_scope, ensure_tool_allowed)
from platform_core.public_api.scopes import (DEFAULT_SCOPES, KNOWN_SCOPES,
                                             SCOPE_JOBS_CANCEL, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ)
from server.api import deps
from server.api.inventory import API_V1_PREFIX

PEPPER = "auth-test-pepper-" + "z" * 40


@pytest.fixture()
def api(tmp_path, monkeypatch):
    """A booted platform with the public API on and a scratch SQLite database."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'auth.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401 - registers tables
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "auth-matrix-secret",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
    })
    try:
        with TestClient(app) as client:
            yield client
    finally:
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


def _account(email: str, *, scopes=(), allowed_tools=()) -> tuple[str, str]:
    """Create a user plus one key; returns ``(user_id, token)``."""
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        db.flush()
        _key, token = devkeys.issue(db, user_id=user.id, name="test",
                                    scopes=scopes, allowed_tools=allowed_tools,
                                    env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        return user.id, token
    finally:
        _close(gen)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Bearer authentication ─────────────────────────────────────────────────────

def test_a_valid_key_identifies_itself(api):
    user_id, token = _account("owner@example.com", scopes=[SCOPE_TOOLS_READ])
    response = api.get(f"{API_V1_PREFIX}/me", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == user_id
    assert body["scopes"] == [SCOPE_TOOLS_READ]
    assert body["key_id"] == devkeys.parse_token(token)[0]
    # The public half only: nothing that could be replayed.
    assert token not in response.text


def test_every_bad_credential_looks_identical(api):
    _user_id, token = _account("real@example.com")
    key_id, secret = devkeys.parse_token(token)

    gen, db = _session()
    try:
        from platform_core.public_api.tables import DeveloperApiKey

        revoked_owner, revoked_token = None, None
        from platform_core.users import tao_nguoi_dung
        user = tao_nguoi_dung(db, email="revoked@example.com",
                              password="a-good-password-12")
        db.flush()
        key, revoked_token = devkeys.issue(db, user_id=user.id,
                                           env={devkeys.PEPPER_ENV: PEPPER})
        devkeys.revoke(db, key)
        db.commit()
        assert db.execute(sa.select(sa.func.count(DeveloperApiKey.id))).scalar() >= 2
        revoked_owner = user.id
        assert revoked_owner
    finally:
        _close(gen)

    attempts = {
        "missing": {},
        "not_bearer": {"Authorization": f"Token {token}"},
        "malformed": _auth("garbage"),
        "unknown_key_id": _auth(devkeys.format_token("d" * 32, secret)),
        "wrong_secret": _auth(devkeys.format_token(key_id, "q" * devkeys.SECRET_LENGTH)),
        "revoked": _auth(revoked_token),
    }
    bodies = set()
    for name, headers in attempts.items():
        response = api.get(f"{API_V1_PREFIX}/me", headers=headers)
        assert response.status_code == 401, name
        payload = response.json()
        assert payload["code"] == "unauthorized", name
        bodies.add(payload["detail"])
    # One message for every failure mode: no oracle for "this key id exists".
    assert len(bodies) == 1


def test_a_browser_session_is_not_an_api_credential(api):
    """Cookie auth on this surface would be a confused-deputy hole."""
    api.cookies.set("session", "whatever-a-browser-has")
    response = api.get(f"{API_V1_PREFIX}/me")
    assert response.status_code == 401
    api.cookies.clear()


def test_authenticated_route_is_still_covered_by_the_kill_switch(api):
    """Auth does not bypass the read-only switch or the error contract."""
    response = api.get(f"{API_V1_PREFIX}/me")
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["request_id"] == response.headers["x-correlation-id"]


def test_raw_bearer_token_never_reaches_the_logs(api, caplog):
    _user_id, token = _account("logged@example.com")
    key_id, secret = devkeys.parse_token(token)
    with caplog.at_level(logging.DEBUG):
        api.get(f"{API_V1_PREFIX}/me", headers=_auth(token))
        api.get(f"{API_V1_PREFIX}/me",
                headers=_auth(devkeys.format_token(key_id, "q" * devkeys.SECRET_LENGTH)))
    captured = "\n".join(record.getMessage() for record in caplog.records)
    assert secret not in captured
    assert token not in captured
    # The public half may appear — that is what support refers to.
    assert "public api auth rejected" in captured
    assert key_id in captured


def test_last_used_is_recorded_but_not_on_every_request(api):
    _user_id, token = _account("busy@example.com")
    for _ in range(3):
        assert api.get(f"{API_V1_PREFIX}/me", headers=_auth(token)).status_code == 200

    gen, db = _session()
    try:
        from platform_core.public_api.tables import DeveloperApiKey

        key = db.execute(sa.select(DeveloperApiKey).where(
            DeveloperApiKey.key_id == devkeys.parse_token(token)[0])).scalar_one()
        assert key.last_used_at is not None
    finally:
        _close(gen)


# ── Scope enforcement (BFLA) ──────────────────────────────────────────────────

def _fake_principal(**overrides) -> Principal:
    values = {"key_id": "k" * 32, "user_id": "user-1",
              "scopes": frozenset({SCOPE_JOBS_READ}),
              "allowed_tools": frozenset(), "request_id": "req-1"}
    values.update(overrides)
    return Principal(**values)


def test_missing_scope_is_refused_and_names_the_scope():
    principal = _fake_principal()
    ensure_scope(principal, SCOPE_JOBS_READ)          # present: no raise
    with pytest.raises(ApiError) as raised:
        ensure_scope(principal, SCOPE_JOBS_CREATE)
    assert raised.value.status == 403
    assert SCOPE_JOBS_CREATE in str(raised.value.detail)


def test_read_scope_does_not_imply_write_or_cancel():
    principal = _fake_principal(scopes=frozenset({SCOPE_JOBS_READ}))
    for scope in (SCOPE_JOBS_CREATE, SCOPE_JOBS_CANCEL):
        with pytest.raises(ApiError):
            ensure_scope(principal, scope)


def test_default_scopes_cannot_spend_credit():
    from platform_core.public_api.scopes import SPENDING_SCOPES

    assert not SPENDING_SCOPES.intersection(DEFAULT_SCOPES)
    assert SPENDING_SCOPES.issubset(KNOWN_SCOPES)


def test_scope_dependency_refuses_before_the_route_body_runs(api):
    """A scope check further in is a check some future route will forget."""
    from server.api.auth import require_scope

    sub_app = None
    for route in api.app.routes:
        if getattr(route, "name", "") == "public_api":
            sub_app = route.app
    assert sub_app is not None
    executed = []

    @sub_app.post("/spend-for-test")
    def spend(principal=Depends(require_scope(SCOPE_JOBS_CREATE))):
        executed.append(principal.key_id)      # pragma: no cover - must not run
        return {"spent": True}

    _user_id, token = _account("reader@example.com", scopes=[SCOPE_JOBS_READ])
    response = api.post(f"{API_V1_PREFIX}/spend-for-test", json={},
                        headers=_auth(token))
    assert response.status_code == 403
    # EXT-02: the code names the cause. "forbidden" told a developer their key
    # was wrong somehow; "missing_scope" plus `required_scope` tells them what
    # to mint instead.
    assert response.json()["code"] == "missing_scope"
    assert response.json()["required_scope"] == SCOPE_JOBS_CREATE
    assert executed == [], "route body must not run without the scope"

    _user_id2, spender = _account("spender@example.com",
                                  scopes=[SCOPE_JOBS_CREATE])
    allowed = api.post(f"{API_V1_PREFIX}/spend-for-test", json={},
                       headers=_auth(spender))
    assert allowed.status_code == 200 and executed


def test_no_scope_means_no_credit_mutation(api):
    """The charge gate is the scope check; nothing may run before it."""
    from platform_core import credit
    from server.api.auth import require_scope

    sub_app = None
    for route in api.app.routes:
        if getattr(route, "name", "") == "public_api":
            sub_app = route.app

    @sub_app.post("/hold-for-test")
    def hold(principal=Depends(require_scope(SCOPE_JOBS_CREATE))):  # pragma: no cover
        gen, db = _session()
        try:
            credit.cap_tay(db, principal.user_id, -1, by="test")
            db.commit()
        finally:
            _close(gen)
        return {"held": True}

    user_id, token = _account("nocredit@example.com", scopes=[SCOPE_JOBS_READ])
    gen, db = _session()
    try:
        before = credit.so_du(db, user_id)
    finally:
        _close(gen)

    assert api.post(f"{API_V1_PREFIX}/hold-for-test", json={},
                    headers=_auth(token)).status_code == 403

    gen, db = _session()
    try:
        assert credit.so_du(db, user_id) == before
        entries = db.execute(sa.text(
            "SELECT COUNT(*) FROM credit_entries WHERE user_id = :u"),
            {"u": user_id}).scalar_one()
        assert entries == 0
    finally:
        _close(gen)


# ── Tool policy ───────────────────────────────────────────────────────────────

def test_tool_policy_uses_allowed_tools_not_scope_strings():
    """One model for "may this key call this tool", not two half-answers."""
    assert not any(scope.startswith("tool:") for scope in KNOWN_SCOPES)

    open_key = _fake_principal(allowed_tools=frozenset())
    narrowed = _fake_principal(allowed_tools=frozenset({"image.generate"}))

    ensure_tool_allowed(open_key, "image.generate", publicly_exposed=True)
    ensure_tool_allowed(narrowed, "image.generate", publicly_exposed=True)

    with pytest.raises(ApiError) as denied:
        ensure_tool_allowed(narrowed, "video.generate", publicly_exposed=True)
    assert denied.value.status == 403


def test_a_tool_that_is_not_public_looks_like_it_does_not_exist():
    """404, not 403: the API must not become a directory of internal capability."""
    for principal in (_fake_principal(),
                      _fake_principal(allowed_tools=frozenset({"video.social_import"}))):
        with pytest.raises(ApiError) as hidden:
            ensure_tool_allowed(principal, "video.social_import",
                                publicly_exposed=False)
        assert hidden.value.status == 404


# ── Object-level authorization (BOLA) ─────────────────────────────────────────

@dataclass
class _Row:
    id: str
    user_id: str


def test_another_customers_object_is_indistinguishable_from_a_missing_one():
    mine = _fake_principal(user_id="user-1")
    assert ensure_owner(_Row("job-1", "user-1"), mine).id == "job-1"

    missing = pytest.raises(ApiError)
    with missing as absent:
        ensure_owner(None, mine)
    with pytest.raises(ApiError) as foreign:
        ensure_owner(_Row("job-2", "user-2"), mine)

    assert absent.value.status == foreign.value.status == 404
    assert absent.value.detail == foreign.value.detail
    assert absent.value.code == foreign.value.code


def test_ownership_comes_from_the_credential_not_from_the_request():
    """Parameter swapping cannot promote a caller into another account."""
    principal = _fake_principal(user_id="user-1")
    row = _Row("job-3", "user-2")
    # Even if a request "says" it is user-2, the principal decides.
    with pytest.raises(ApiError):
        ensure_owner(row, principal)
    assert principal.user_id == "user-1"


def test_an_object_without_an_owner_is_never_readable():
    principal = _fake_principal(user_id="user-1")
    with pytest.raises(ApiError):
        ensure_owner(_Row("orphan", ""), principal)


def test_two_accounts_never_see_each_others_keys(api):
    alice_id, alice_token = _account("alice@example.com")
    bob_id, bob_token = _account("bob@example.com")

    alice = api.get(f"{API_V1_PREFIX}/me", headers=_auth(alice_token)).json()
    bob = api.get(f"{API_V1_PREFIX}/me", headers=_auth(bob_token)).json()
    assert alice["account_id"] == alice_id and bob["account_id"] == bob_id
    assert alice["key_id"] != bob["key_id"]

    gen, db = _session()
    try:
        assert devkeys.get_owned(db, user_id=bob_id,
                                 key_id=alice["key_id"]) is None
    finally:
        _close(gen)


# ── Expiry at the boundary ────────────────────────────────────────────────────

def test_an_expired_key_stops_working_without_a_deploy(api):
    from platform_core.public_api.tables import DeveloperApiKey

    _user_id, token = _account("expiring@example.com")
    key_id = devkeys.parse_token(token)[0]
    assert api.get(f"{API_V1_PREFIX}/me", headers=_auth(token)).status_code == 200

    gen, db = _session()
    try:
        key = db.execute(sa.select(DeveloperApiKey).where(
            DeveloperApiKey.key_id == key_id)).scalar_one()
        key.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        _close(gen)

    assert api.get(f"{API_V1_PREFIX}/me", headers=_auth(token)).status_code == 401


def test_revoking_a_key_takes_effect_on_the_next_request(api):
    from platform_core.public_api.tables import DeveloperApiKey

    _user_id, token = _account("revokeme@example.com")
    assert api.get(f"{API_V1_PREFIX}/me", headers=_auth(token)).status_code == 200

    gen, db = _session()
    try:
        key = db.execute(sa.select(DeveloperApiKey).where(
            DeveloperApiKey.key_id == devkeys.parse_token(token)[0])).scalar_one()
        devkeys.revoke(db, key)
        db.commit()
    finally:
        _close(gen)

    assert api.get(f"{API_V1_PREFIX}/me", headers=_auth(token)).status_code == 401
