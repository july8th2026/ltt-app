"""EXT-08 — the playground: the same API, from a form.

The three things that must be true are the three ways a playground normally
goes wrong: it grows a private execution path that skips policy, it hands the
page a credential the customer was told they could not recover, or it quietly
runs work for free. Each has a test here.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.registry import discover
from server.api.inventory import API_V1_PREFIX, declared_paths

PEPPER = "playground-test-pepper-" + "g" * 40
SCRIPT = Path(__file__).resolve().parent.parent / "server" / "static" / "dev_playground.js"


def _live_catalog():
    names = ",".join(sorted({tool.name for item in discover() if not item.error
                             for tool in item.manifest.tools}))
    return build_catalog(load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": names}))


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'playground.db').as_posix()}")
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
        "LTT_SESSION_SECRET": "playground-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "image.thumbnail",
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    storage_mod.set_storage(None)
    limits.reset()
    dbmod.reset_engine()


def _csrf(html: str) -> str:
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def _sign_in(client) -> None:
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    email = f"pg-{uuid.uuid4().hex[:6]}@example.com"
    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, 200, by="test")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    page = client.get("/login").text
    client.post("/login", data={"username": email,
                                "password": "a-good-password-12",
                                "csrf_token": _csrf(page)},
                follow_redirects=False)


# ── No private execution path ────────────────────────────────────────────────

def test_the_portal_has_no_route_that_runs_a_tool(portal):
    """The playground must not become a second road to the chargeable path.

    Every way to spend credit stays on `/api/v1`, where the quote, the
    idempotency key, the limits and the ledger already live.
    """
    _sign_in(portal)
    routes = [route.path for route in portal.app.routes
              if str(getattr(route, "path", "")).startswith("/developers")]
    for path in routes:
        assert "run" not in path and "execute" not in path, path
        assert "quote" not in path, path


def test_the_page_talks_to_the_public_api_and_nothing_else():
    source = SCRIPT.read_text(encoding="utf-8")
    called = set(re.findall(r'fetch\("([^"]+)"', source))
    called |= set(re.findall(r'fetch\("(/api/v1[^"]*)"', source))
    for target in called:
        assert target.startswith("/api/v1"), target
    # …and every path it builds exists in the route inventory.
    declared = {re.sub(r"\{[a-z_]+\}", "{x}", path)
                for _method, path in declared_paths()}
    for path in re.findall(r'"/(?:api/v1)?(/[a-z/]+)"', source):
        candidate = re.sub(r"\{[a-z_]+\}", "{x}", API_V1_PREFIX + path)
        if candidate.endswith(("/quotes", "/jobs", "/uploads")):
            assert candidate in declared, path


# ── No raw key recovery ──────────────────────────────────────────────────────

def test_the_page_never_contains_a_key_and_never_stores_one(portal):
    """The customer was told a key cannot be recovered. That has to stay true."""
    _sign_in(portal)
    keys_page = portal.get("/developers/keys").text
    created = portal.post("/developers/keys", data={
        "name": "playground", "csrf_token": _csrf(keys_page),
        "scopes": ["tools:read", "jobs:create", "jobs:read", "artifacts:read"]})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)

    page = portal.get("/developers/playground").text
    assert token not in page
    assert "ltt_sk_" not in page.replace("ltt_sk_…", "")
    # The field is a password input and the script keeps the value in memory.
    assert 'id="pg-key" type="password"' in page
    # Comments stripped first: the file *explains* that it never uses these,
    # and a scan that trips on its own documentation is a scan people delete.
    source = re.sub(r"/\*.*?\*/", "", SCRIPT.read_text(encoding="utf-8"),
                    flags=re.S)
    source = re.sub(r"^\s*//.*$", "", source, flags=re.M)
    for forbidden in ("localStorage", "sessionStorage", "document.cookie"):
        assert forbidden not in source, forbidden


def test_the_server_never_receives_the_key_from_the_page(portal):
    """Nothing in the page posts back to the portal, so there is nothing for a
    portal handler to log, store or leak."""
    _sign_in(portal)
    page = portal.get("/developers/playground").text
    assert 'action="/developers' not in page.split('id="playground"')[1]


# ── The form is generated from the published contract ───────────────────────

def test_the_form_is_built_from_the_same_catalog_the_api_serves(portal):
    _sign_in(portal)
    page = portal.get("/developers/playground").text
    embedded = json.loads(
        re.search(r'id="pg-catalog">(.*?)</script>', page, re.S).group(1))
    published = [tool.to_public_dict() for tool in _live_catalog()
                 if tool.name == "image.thumbnail"]
    assert embedded == published


def test_the_page_offers_only_tools_this_deployment_publishes(portal):
    _sign_in(portal)
    page = portal.get("/developers/playground").text
    assert "image.thumbnail" in page
    # Published by the repository, but switched off on this deployment.
    assert "image.generate" not in page


def test_the_page_says_the_run_costs_real_credit(portal):
    """There is no free mode, and pretending otherwise would be the bypass."""
    _sign_in(portal)
    page = portal.get("/developers/playground").text
    assert "credit thật" in page
    source = SCRIPT.read_text(encoding="utf-8")
    assert "/quotes" in source and "/jobs" in source


# ── Idempotency and inspection ───────────────────────────────────────────────

def test_the_page_generates_an_idempotency_key_and_reuses_it_per_call():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "Idempotency-Key" in source
    # Generated once per call…
    assert "state.idempotencyKey = uuid()" in source.replace(
        "(state.idempotencyKey = uuid())", "state.idempotencyKey = uuid()")
    # …and thrown away when the input changes, because that is a different call
    # and replaying the old answer would be wrong.
    assert "state.idempotencyKey = null" in source


def test_the_inspector_shows_only_headers_a_caller_should_act_on():
    source = SCRIPT.read_text(encoding="utf-8")
    safe = re.search(r'var safe = \[(.*?)\];', source, re.S).group(1)
    shown = set(re.findall(r'"([A-Za-z-]+)"', safe))
    assert shown == {"X-Correlation-ID", "X-LTT-API-Version", "Retry-After",
                     "Idempotency-Replayed", "Location"}
    # Nothing that would echo a credential back onto the page.
    assert "Authorization" not in safe


def test_the_page_explains_the_modes_nobody_can_try_yet(portal):
    _sign_in(portal)
    page = portal.get("/developers/playground").text
    assert "STREAM" in page and "BATCH" in page
    assert "ASYNC_JOB" in page


# ── The area ─────────────────────────────────────────────────────────────────

def test_the_playground_is_linked_from_the_area(portal):
    _sign_in(portal)
    assert 'href="/developers/playground"' in portal.get("/developers").text


def test_the_script_is_cache_busted(portal):
    """A changed script must reach a browser, not wait out a Cloudflare TTL."""
    _sign_in(portal)
    page = portal.get("/developers/playground").text
    assert re.search(r'/static/dev_playground\.js\?v=[0-9a-f]+', page)


def test_the_playground_needs_a_session(portal):
    response = portal.get("/developers/playground", follow_redirects=False)
    assert response.status_code in (302, 303)


def test_a_deployment_with_no_published_tool_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "playground-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "",
    })
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/developers/playground")
        assert page.status_code == 200
        assert "chưa mở công cụ nào" in page.text
        assert 'id="playground"' not in page.text
    from server.api import deps
    deps.set_principal_resolver(None)
    limits.reset()
    dbmod.reset_engine()


# ── The semantics the page relies on are the API's, not its own ─────────────

def test_running_from_a_form_is_the_same_call_as_running_from_a_server(portal):
    """What the page does, done here with plain requests: identical outcome.

    If these two ever diverge, the playground is lying to whoever trusts it.
    """
    _sign_in(portal)
    keys_page = portal.get("/developers/keys").text
    created = portal.post("/developers/keys", data={
        "name": "same-path", "csrf_token": _csrf(keys_page),
        "scopes": ["tools:read", "jobs:create", "jobs:read"]})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)
    auth = {"Authorization": f"Bearer {token}"}
    payload = {"topic": "playground parity", "count": 1}

    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": "image.thumbnail", "input": payload},
                        headers=auth)
    assert quote.status_code == 200
    key = str(uuid.uuid4())
    first = portal.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": "image.thumbnail",
                              "quote": quote.json()["quote"], "input": payload},
                        headers={**auth, "Idempotency-Key": key})
    assert first.status_code == 201

    # Pressing Run twice with the same input replays rather than charging again
    # — the behaviour the page depends on by reusing its key.
    again = portal.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": "image.thumbnail",
                              "quote": quote.json()["quote"], "input": payload},
                        headers={**auth, "Idempotency-Key": key})
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
    assert again.headers.get("Idempotency-Replayed") == "true"
