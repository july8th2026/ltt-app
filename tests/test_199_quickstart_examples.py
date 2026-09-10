"""EXT-07 — the quickstart: a fresh integration that actually completes.

Two failure modes are worth testing here and only two. An example that no longer
matches the schema is worse than no example, because a developer trusts it and
loses an afternoon. And an example carrying a real credential is a leak that
ships with the documentation.
"""
from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import examples, keys as devkeys, limits
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.registry import (AppManifest, LoadedApp, ToolSpec, discover)
from server.api.inventory import API_V1_PREFIX, declared_paths

PEPPER = "quickstart-test-pepper-" + "q" * 40


def _live_catalog():
    names = ",".join(sorted({tool.name for item in discover() if not item.error
                             for tool in item.manifest.tools}))
    return build_catalog(load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": names}))


def _snippets(tool) -> dict:
    return {
        "curl_quote": examples.curl_quote(tool),
        "curl_submit": examples.curl_submit(tool),
        "python": examples.python_snippet(tool),
        "typescript": examples.typescript_snippet(tool),
        "powershell": examples.powershell_snippet(tool),
        "http": examples.raw_http_snippet(tool),
    }


# ── Examples match the schema they claim to call ─────────────────────────────

def _violations(payload: dict, schema: dict) -> list:
    """A small schema check: the published contract is a narrow subset of JSON
    Schema, so a dependency to validate it would be more surface than value."""
    problems = []
    properties = schema.get("properties") or {}
    for name in schema.get("required", ()):
        if name not in payload:
            problems.append(f"missing required {name}")
    for name, value in payload.items():
        if name not in properties:
            problems.append(f"unknown field {name}")
            continue
        spec = properties[name]
        placeholder = isinstance(value, str) and value.startswith("<")
        expected = spec.get("type")
        if not placeholder:
            if expected == "integer" and not isinstance(value, int):
                problems.append(f"{name} should be an integer")
            if expected == "string" and not isinstance(value, str):
                problems.append(f"{name} should be a string")
            if spec.get("enum") and value not in spec["enum"]:
                problems.append(f"{name}={value!r} is not in the enum")
            if isinstance(value, str) and "maxLength" in spec:
                if len(value) > spec["maxLength"]:
                    problems.append(f"{name} is longer than maxLength")
            if isinstance(value, int) and "minimum" in spec:
                if value < spec["minimum"]:
                    problems.append(f"{name} below minimum")
            if isinstance(value, int) and "maximum" in spec:
                if value > spec["maximum"]:
                    problems.append(f"{name} above maximum")
    return problems


def test_every_example_payload_validates_against_its_own_tool_schema():
    for tool in _live_catalog():
        payload = examples.example_input(tool)
        assert not _violations(payload, tool.input_schema), tool.name


def test_the_example_payload_would_be_accepted_by_the_real_submit_path():
    """The same validation the chargeable route runs, not a lookalike."""
    from platform_core.public_api.invocation import validate_public_input

    for tool in _live_catalog():
        # The whole payload, exactly as the page prints it. Media ids are only
        # resolved to real uploads later, so a placeholder id is a valid input
        # as far as this layer is concerned — which is the layer that decides
        # whether a caller pasting the example gets a 400.
        validate_public_input(tool, examples.example_input(tool))


def test_every_snippet_only_calls_endpoints_that_exist():
    declared = {path for _method, path in declared_paths()}
    for tool in _live_catalog():
        for label, snippet in _snippets(tool).items():
            for path in set(re.findall(r"/api/v1/[a-z/{}_]+", snippet)):
                clean = path.rstrip("/")
                # Snippets use readable placeholders; the inventory uses the
                # route's own parameter names.
                normalised = re.sub(r"\{[a-z_]+\}", "{x}", clean)
                known = {re.sub(r"\{[a-z_]+\}", "{x}", item)
                         for item in declared}
                assert normalised in known, f"{tool.name}/{label}: {path}"


def test_no_snippet_contains_anything_that_looks_like_a_key():
    """A credential in an example ships with the documentation forever."""
    for tool in _live_catalog():
        for label, snippet in _snippets(tool).items():
            assert "ltt_sk_" not in snippet.replace("ltt_sk_…", ""), label
            # …and every snippet must read the key from the environment.
            assert examples.ENV_API_KEY in snippet, f"{tool.name}/{label}"


def test_the_chargeable_snippets_carry_an_idempotency_key():
    for tool in _live_catalog():
        snippets = _snippets(tool)
        for label in ("curl_submit", "python", "typescript", "powershell",
                      "http"):
            assert "Idempotency-Key" in snippets[label], f"{tool.name}/{label}"
        # …and the quote call does not pretend to need one.
        assert "Idempotency-Key" not in snippets["curl_quote"]


def test_the_environment_variables_are_named_once_and_used_everywhere():
    assert (examples.ENV_API_KEY, examples.ENV_BASE_URL) == ("LTT_API_KEY",
                                                             "LTT_BASE_URL")
    names = {name for name, _sample, _why in examples.ENV_VARS}
    assert names == {"LTT_API_KEY", "LTT_BASE_URL", "LTT_PROJECT_ID"}
    for _shell, snippet in examples.SHELL_EXPORTS:
        assert "LTT_BASE_URL" in snippet and "LTT_API_KEY" in snippet


def test_a_required_parameter_without_an_example_gets_a_placeholder():
    tool = ToolSpec(
        name="text.placeheld", job_type="samplehold.run", description="Fixture.",
        params_schema={"needed": {"type": "string", "required": True}},
        returns={"text": "text"}, api_exposed=True,
        api_contract={"scopes": ("jobs:create",),
                      "params": {"needed": {"description": "Say something."}}})
    manifest = AppManifest(
        slug="samplehold", display_name="S", route_prefix="/samplehold",
        job_types=("samplehold.run",), credit_cost=lambda p: 1,
        lifecycle="released", surface="customer", tools=(tool,))
    catalog = build_catalog(
        load_public_api_config({"LTT_PUBLIC_API": "1",
                                "LTT_PUBLIC_API_TOOLS": "text.placeheld"}),
        apps=[LoadedApp(manifest=manifest, router=None, error="")])
    # A made-up value reads like advice; "<string>" reads like an instruction.
    assert examples.example_input(catalog[0]) == {"needed": "<string>"}


# ── The page ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'quickstart.db').as_posix()}")
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
    from tests.gia_dieu_phoi_anh import tiem as _tiem_dieu_phoi
    _tiem_dieu_phoi(monkeypatch, thumbnail_jobs)

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "quickstart-secret-value",
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


def _sign_in(client) -> str:
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    email = f"qs-{uuid.uuid4().hex[:6]}@example.com"
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
    return email


def test_the_quickstart_page_shows_the_path_and_the_variables(portal):
    _sign_in(portal)
    page = portal.get("/developers/quickstart").text
    for fragment in ("LTT_BASE_URL", "LTT_API_KEY", "LTT_PROJECT_ID",
                     "PowerShell", "cmd.exe", "n8n", "Make",
                     "/api/v1/quotes", "/api/v1/jobs", "Idempotency-Key"):
        assert fragment in page, fragment


def test_the_quickstart_is_one_click_from_the_area(portal):
    _sign_in(portal)
    assert 'href="/developers/quickstart"' in portal.get("/developers").text


def test_the_page_offers_a_snippet_for_the_published_tool(portal):
    import html

    _sign_in(portal)
    page = html.unescape(portal.get("/developers/quickstart").text)
    assert '"tool": "image.thumbnail"' in page
    assert "How to fix a leaking tap" in page          # declared example value


# ── The acceptance criterion: a fresh integration completes ──────────────────

def test_a_developer_who_follows_the_quickstart_gets_a_result(portal):
    """Portal → key → env → tools → quote → job → artifact, in that order.

    This is the whole promise of EXT-07 expressed as a test: if any step of the
    documented path stops working, this fails.
    """
    _sign_in(portal)

    # Step 1-2: create the key exactly as the page says to.
    keys_page = portal.get("/developers/keys").text
    created = portal.post("/developers/keys", data={
        "name": "quickstart", "csrf_token": _csrf(keys_page),
        "scopes": ["tools:read", "jobs:create", "jobs:read", "artifacts:read"]})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)
    auth = {"Authorization": f"Bearer {token}"}

    # Step 4: discover.
    tools = portal.get(f"{API_V1_PREFIX}/tools", headers=auth).json()
    published = [item["name"] for item in tools["items"]]
    assert "image.thumbnail" in published

    # Step 6: quote, then submit with an idempotency key.
    catalog_tool = next(item for item in _live_catalog()
                        if item.name == "image.thumbnail")
    payload = examples.example_input(catalog_tool)
    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": "image.thumbnail", "input": payload},
                        headers=auth)
    assert quote.status_code == 200, quote.text
    assert quote.json()["credit"] > 0

    job = portal.post(f"{API_V1_PREFIX}/jobs",
                      json={"tool": "image.thumbnail",
                            "quote": quote.json()["quote"], "input": payload},
                      headers={**auth, "Idempotency-Key": str(uuid.uuid4())})
    assert job.status_code == 201, job.text

    # Step 7: the job runs and its artifact is fetchable.
    from platform_core.job_runner import _chay_mot_job

    assert _chay_mot_job("quickstart-worker") is True

    finished = portal.get(f"{API_V1_PREFIX}/jobs/{job.json()['id']}",
                          headers=auth).json()
    assert finished["status"] == "succeeded", finished
    #  is a list of artifact descriptors, one per produced file.
    artifact = finished["outputs"][0]["id"]
    detail = portal.get(f"{API_V1_PREFIX}/artifacts/{artifact}", headers=auth)
    assert detail.status_code == 200, detail.text
