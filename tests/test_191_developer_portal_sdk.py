"""Q92 / Prompt 15 — developer portal, docs and SDKs.

Three properties worth a test each:

* the portal is a **session** surface, so every state-changing POST needs CSRF,
  every read is owner-scoped, and the key plaintext is shown exactly once;
* the docs cannot drift from the catalog, because the tool reference is
  generated from it and checked here;
* the SDKs retry the way the money contract requires — a chargeable POST only
  ever repeats with the same Idempotency-Key.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys
from server.api.inventory import API_V1_PREFIX

PEPPER = "portal-test-pepper-" + "n" * 40
PASSWORD = "a-good-password-12"
SDK_PYTHON = Path("sdk/python/ltt_public_api.py")
SDK_TS = Path("sdk/typescript/ltt-public-api.ts")
GUIDE = Path("docs/PUBLIC_API/DEVELOPER_GUIDE.md")


# ── Portal ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'portal.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "portal-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": "image.thumbnail",
    })
    try:
        # https base URL: the session cookie is `secure` outside development, so
        # over plain http the browser (and TestClient) would drop it and every
        # CSRF check would fail for a reason that has nothing to do with CSRF.
        with TestClient(app, base_url="https://testserver") as client:
            yield client
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        dbmod.reset_engine()


def _register(client, email: str) -> None:
    """Create a verified account and log this client in as it."""
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=email, password=PASSWORD)
        user.is_verified = True
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # The login form carries its own CSRF token, like every session POST.
    form = client.get("/login")
    response = client.post("/login", data={
        "username": email, "password": PASSWORD,
        "csrf_token": _csrf(form.text)}, follow_redirects=False)
    assert response.status_code in (302, 303), response.text


def _csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "the portal must issue a CSRF token"
    return match.group(1)


def test_the_portal_requires_a_login(portal):
    response = portal.get("/developers", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/developers"


def test_a_key_is_created_and_revealed_exactly_once(portal):
    _register(portal, "dev@example.com")
    page = portal.get("/developers/keys")
    assert page.status_code == 200

    created = portal.post("/developers/keys",
                          data={"name": "ci", "csrf_token": _csrf(page.text),
                                "scopes": ["tools:read", "jobs:create"]})
    assert created.status_code == 200
    secret = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text)
    assert secret, "the plaintext must appear on the creation response"
    token = secret.group(1)

    # A refresh must not bring it back — nothing on the server can reproduce it.
    again = portal.get("/developers/keys")
    assert token not in again.text
    assert token.split("_", 3)[2] in again.text      # the public key_id remains

    # And the key works against the API.
    me = portal.get(f"{API_V1_PREFIX}/me",
                    headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert sorted(me.json()["scopes"]) == ["jobs:create", "tools:read"]


def test_a_post_without_a_csrf_token_changes_nothing(portal):
    _register(portal, "csrf@example.com")
    before = portal.get("/developers").text

    forged = portal.post("/developers/keys", data={"name": "forged"},
                         follow_redirects=False)
    assert forged.status_code in (303, 200)
    assert "ltt_sk_" not in forged.text

    after = portal.get("/developers").text
    assert "forged" not in after
    assert before.count("<code>") == after.count("<code>")


def test_revoke_and_rotate_need_csrf_and_ownership(portal):
    _register(portal, "owner@example.com")
    page = portal.get("/developers")
    csrf = _csrf(page.text)
    created = portal.post("/developers/keys",
                          data={"name": "rotate-me", "csrf_token": csrf})
    key_id = re.search(r"<code>ltt_sk_([0-9a-f]{32})_", created.text).group(1)

    # Wrong token: nothing happens.
    portal.post(f"/developers/keys/{key_id}/revoke",
                data={"csrf_token": "not-the-token"}, follow_redirects=False)
    assert "active" in portal.get("/developers").text

    rotated = portal.post(f"/developers/keys/{key_id}/rotate",
                          data={"csrf_token": csrf})
    assert "ltt_sk_" in rotated.text          # a new secret, shown once

    revoked = portal.post(f"/developers/keys/{key_id}/revoke",
                          data={"csrf_token": csrf}, follow_redirects=False)
    assert revoked.status_code == 303


def test_one_account_cannot_see_or_touch_another_accounts_keys(portal):
    _register(portal, "alice@example.com")
    page = portal.get("/developers")
    created = portal.post("/developers/keys",
                          data={"name": "alice-key", "csrf_token": _csrf(page.text)})
    alice_key_id = re.search(r"<code>ltt_sk_([0-9a-f]{32})_", created.text).group(1)

    portal.get("/logout", follow_redirects=False)
    portal.cookies.clear()
    _register(portal, "bob@example.com")
    bob_page = portal.get("/developers")
    assert "alice-key" not in bob_page.text
    assert alice_key_id not in bob_page.text

    # Bob cannot revoke Alice's key even with his own valid CSRF token.
    portal.post(f"/developers/keys/{alice_key_id}/revoke",
                data={"csrf_token": _csrf(bob_page.text)}, follow_redirects=False)

    from platform_core.db import get_session
    from platform_core.public_api.tables import DeveloperApiKey
    import sqlalchemy as sa

    gen = get_session()
    db = next(gen)
    try:
        key = db.execute(sa.select(DeveloperApiKey).where(
            DeveloperApiKey.key_id == alice_key_id)).scalar_one()
        assert key.revoked_at is None
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_the_portal_never_shows_a_provider_credential(portal):
    """`api_keys` holds the platform's own vendor keys; customers see nothing."""
    from platform_core import api_keys as provider_keys
    from platform_core.db import get_session

    import os
    os.environ["LTT_TOKEN_ENCRYPTION_KEY"] = "portal-encryption-key-0123456789"
    gen = get_session()
    db = next(gen)
    try:
        provider_keys.tao_key(db, provider="gemini", credential="super-secret-value",
                             categories=["image"])
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    _register(portal, "curious@example.com")
    page = portal.get("/developers").text
    for leak in ("super-secret-value", "gemini", "provider", "credential_enc"):
        assert leak.lower() not in page.lower(), leak


def test_the_portal_shows_limits_balance_and_api_state(portal):
    """The numbers moved into sections (EXT-05); all of them are still one
    click from the overview, and the overview itself still answers the two
    questions that matter: what do I have left, and is anything wrong."""
    _register(portal, "limits@example.com")
    overview = portal.get("/developers").text
    assert "credit" in overview.lower()

    usage = portal.get("/developers/usage").text
    assert "120" in usage and "20" in usage        # request/create per minute

    tools = portal.get("/developers/tools").text
    assert "image.thumbnail" in tools              # published tools offered


# ── Docs ─────────────────────────────────────────────────────────────────────

def test_the_developer_guide_matches_the_catalog():
    """Generated from the same catalog the API serves — no drift by design."""
    result = subprocess.run(
        [sys.executable, "tools/build_public_api_docs.py", "--check"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_guide_documents_the_things_that_cost_money():
    text = GUIDE.read_text(encoding="utf-8")
    for topic in ("Idempotency-Key", "quote", "scope", "problem+json",
                  "retry_after", "webhook", "upload", "credit"):
        assert topic.lower() in text.lower(), topic
    # And about the sandbox that now does exist, including the part it cannot
    # prove: a mock says nothing about output quality (EXT-12).
    assert "ltt_tk" in text
    assert "không tiêu được credit" in text
    assert "chất lượng" in text


def test_the_guide_lists_every_published_tool():
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config
    from platform_core.registry import discover

    names = sorted(tool.name for item in discover() if not item.error
                   for tool in item.manifest.tools if tool.api_exposed)
    config = load_public_api_config({"LTT_PUBLIC_API": "1",
                                     "LTT_PUBLIC_API_TOOLS": ",".join(names)})
    text = GUIDE.read_text(encoding="utf-8")
    for tool in build_catalog(config):
        assert f"### `{tool.name}`" in text, tool.name


# ── SDKs ─────────────────────────────────────────────────────────────────────

@pytest.fixture()
def sdk_client(portal):
    """The Python SDK wired to the in-process app through its transport hook."""
    sys.path.insert(0, str(SDK_PYTHON.parent.resolve()))
    import importlib

    module = importlib.import_module("ltt_public_api")
    importlib.reload(module)

    _register(portal, f"sdk-{uuid.uuid4().hex[:6]}@example.com")
    page = portal.get("/developers")
    created = portal.post("/developers/keys",
                          data={"csrf_token": _csrf(page.text),
                                "scopes": ["tools:read", "jobs:read",
                                           "jobs:create", "credits:read"]})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)

    calls = []

    def transport(method, url, payload, headers):
        calls.append({"method": method, "url": url, "headers": dict(headers)})
        response = portal.request(method, url, content=payload, headers=headers)
        return response.status_code, dict(response.headers), response.content

    client = module.LttClient(base_url="https://testserver", api_key=token,
                              transport=transport)
    return module, client, calls


def test_the_python_sdk_talks_to_the_real_api(sdk_client):
    _module, client, _calls = sdk_client
    identity = client.me()
    assert identity["key_id"]
    assert client.balance()["balance"] == 0
    published = client.tools()["items"]
    assert [tool["name"] for tool in published] == ["image.thumbnail"]


def test_the_python_sdk_reuses_one_idempotency_key_across_retries(sdk_client):
    module, client, _calls = sdk_client

    # A 503 on the first attempt, then the real server: every attempt must carry
    # the *same* key. A fresh key on retry is how one timeout becomes two jobs.
    seen_keys = []
    original = client.transport

    def flaky(method, url, payload, headers):
        if method == "POST" and url.endswith("/jobs"):
            seen_keys.append(headers.get("Idempotency-Key"))
            if len(seen_keys) == 1:
                return 503, {}, b'{"code":"service_unavailable","retry_after":0}'
        return original(method, url, payload, headers)

    client.transport = flaky
    client.max_retries = 2
    quote = {"tool": "image.thumbnail", "quote": "not-a-real-token"}
    with pytest.raises(module.LttApiError) as raised:
        client.create_job(quote, {"topic": "x"})

    # The retry happened, it reused the key, and the failure the caller sees is
    # the server's real answer (a rejected quote), not the transient 503.
    assert len(seen_keys) == 2
    assert len(set(seen_keys)) == 1 and seen_keys[0]
    # EXT-02 named the cause: a rejected quote is `quote_invalid`, which the
    # registry marks as never worth retrying — unlike `quote_expired`.
    assert raised.value.code == "quote_invalid"


def test_the_python_sdk_verifies_a_webhook_signature(sdk_client):
    module, _client, _calls = sdk_client
    from platform_core.public_api import webhooks

    import time

    secret, body, event_id = "s" * 40, b'{"id":"abc"}', "abc"
    stamp = int(time.time())
    signature = webhooks.sign(secret, timestamp=stamp, event_id=event_id, body=body)

    assert module.verify_webhook(secret, timestamp=stamp, event_id=event_id,
                                 body=body, signature=signature)
    assert not module.verify_webhook(secret, timestamp=stamp, event_id=event_id,
                                     body=b'{"id":"abd"}', signature=signature)
    # A replayed delivery from an hour ago fails the freshness check.
    old = webhooks.sign(secret, timestamp=stamp - 3600, event_id=event_id, body=body)
    assert not module.verify_webhook(secret, timestamp=stamp - 3600,
                                     event_id=event_id, body=body, signature=old)


def test_the_typescript_sdk_keeps_the_same_money_contract():
    """No TS toolchain runs in this repo, so the contract is checked as text."""
    source = SDK_TS.read_text(encoding="utf-8")
    # One key per logical call, reused on retry.
    assert "Idempotency-Key" in source
    assert "idempotencyKey ?? crypto.randomUUID()" in source
    # Reads retry, the cancel write does not.
    assert 'retry: true' in source
    assert re.search(r"cancelJob\(jobId: string\) \{\s*return this\.request<Job>\("
                     r"\"POST\", `/jobs/\$\{encodeURIComponent\(jobId\)\}/cancel`\);",
                     source), "cancel must not be retried blindly"
    # Signature verification ships with the client.
    assert "verifyWebhook" in source and "crypto.subtle" in source
    # Constant-time comparison, not `===`.
    assert "mismatch |=" in source


def test_both_sdks_cover_the_documented_surface():
    python_source = SDK_PYTHON.read_text(encoding="utf-8")
    ts_source = SDK_TS.read_text(encoding="utf-8")
    for path in ("/me", "/tools", "/quotes", "/jobs", "/credits/balance",
                 "/artifacts/"):
        assert path in python_source, f"python sdk misses {path}"
        assert path in ts_source, f"typescript sdk misses {path}"
    # Uploads and webhooks are Python-side today; the guide says so.
    assert "/uploads" in python_source and "/webhooks" in python_source
