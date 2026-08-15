"""EXT-20 — certify every capability, and prove nothing was published by accident.

Two failure modes matter here, and they pull in opposite directions.

**Missing a capability** is a slow, quiet cost: an app nobody classified is an
app nobody decided about, and the decision then gets made by whoever next edits
a manifest.

**Publishing one by accident** is a fast, loud cost: a tool reachable with an
API key charges real credit, hits a real provider, and cannot be un-promised
once an integration depends on it.

`test_190` already holds the line at the *app* level. This file goes one level
finer — every **tool**, every **model alias**, every **execution mode** — and
then does the thing a document cannot do for itself: drives each published
operation end to end from outside, the way a customer would, and checks the
supporting surfaces it needs to be usable at all.

The end-to-end half runs on a **test-mode key**, which is why it can certify all
five operations including the GPU one without a provider, a GPU or a credit.
That is what EXT-12 was built for; this is it earning its keep.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from platform_core import registry
from platform_core.public_api import keys as devkeys, limits, webhooks
from server.api.inventory import API_V1_PREFIX

DOC = (Path(__file__).parent.parent / "docs" / "PUBLIC_API" /
       "APP_API_COVERAGE_FINAL.md")

PEPPER = "certification-pepper-" + "k" * 40

PUBLISHED = ("image.thumbnail", "image.generate", "image.upscale",
             "text.prompt_package", "story.storyboard")

#: A minimal, valid call for each published operation. `image.upscale` needs an
#: upload, which the fixture supplies.
INPUTS = {
    "image.thumbnail": {"topic": "how to certify an api", "count": 1},
    "image.generate": {"prompt": "a lighthouse at dawn", "count": 1},
    "image.upscale": {"preset": "fast"},
    "text.prompt_package": {"title": "The last train",
                            "story": "A courier misses the last train home.",
                            "scene_count": 2},
    "story.storyboard": {"title": "The last train",
                         "story": "A courier misses the last train home.",
                         "scene_count": 2},
}

SCOPES = ("tools:read", "jobs:create", "jobs:read", "artifacts:read",
          "uploads:write", "usage:read", "webhooks:manage")

PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 40)

RECEIVER = "https://receiver.example.com/certify"


# ── The document, read as data ───────────────────────────────────────────────

def _rows(section: str) -> list[list[str]]:
    """Every table row under a heading, as trimmed cells.

    The document is the deliverable, so the tests read it rather than a copy of
    it: a table nobody keeps current is worse than no table, because it reads
    like it is current.
    """
    text = DOC.read_text(encoding="utf-8")
    start = text.index(section)
    rest = text[start + len(section):]
    end = rest.find("\n## ")
    body = rest[:end] if end != -1 else rest
    out = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip().strip("`*") for c in line.strip("|").split("|")]
        if cells and cells[0].lower() not in {"app", "tool", "alias",
                                              "operation", "capability"}:
            out.append(cells)
    return out


def _all_tools():
    return [(a.manifest.slug, t)
            for a in registry.discover() for t in (a.manifest.tools or [])]


# ── Inventory: nothing without a decision ────────────────────────────────────

def test_the_document_classifies_every_app():
    slugs = {a.manifest.slug for a in registry.discover()}
    documented = {row[0] for row in _rows("## 1.")}
    assert documented == slugs, (
        f"undecided: {sorted(slugs - documented)}; "
        f"stale: {sorted(documented - slugs)}")


def test_the_document_classifies_every_tool_not_only_the_published_ones():
    names = {t.name for _slug, t in _all_tools()}
    documented = {row[0] for row in _rows("## 2.")}
    assert documented == names, (
        f"undecided: {sorted(names - documented)}; "
        f"stale: {sorted(documented - names)}")


def test_the_document_classifies_every_model_alias_and_names_what_is_behind_it():
    aliases = {}
    for _slug, tool in _all_tools():
        for alias, spec in (tool.api_contract.get("models") or {}).items():
            aliases[alias] = spec.get("id")
    rows = {row[0]: row for row in _rows("## 3.")}
    assert set(rows) == set(aliases), (
        f"undecided: {sorted(set(aliases) - set(rows))}; "
        f"stale: {sorted(set(rows) - set(aliases))}")
    for alias, vendor in aliases.items():
        assert vendor in " ".join(rows[alias]), (
            f"{alias} does not say which model it resolves to")


def test_every_published_tool_declares_an_execution_mode_the_platform_can_honour():
    from platform_core.public_api import protocol

    supported = set(getattr(protocol, "EXECUTION_MODES", (protocol.ASYNC_JOB,)))
    for _slug, tool in _all_tools():
        if not tool.api_exposed:
            continue
        mode = protocol.mode_of_tool(tool.api_contract)
        assert mode in supported, f"{tool.name} declares {mode!r}"


def test_a_capability_waiting_to_migrate_names_the_service_that_will_host_it():
    """A blocked capability with no home is a backlog item pretending to be a plan.

    "Migrate then expose" is only a decision if somebody can say *where*. Without
    a named home it reads as a promise, and promises without an owner are how a
    capability sits blocked for a year.
    """
    for row in _rows("## 1."):
        app, disposition = row[0], row[1]
        if "MIGRATE" not in disposition:
            continue
        home = row[2] if len(row) > 2 else ""
        assert home and home not in {"—", "-", "TBD", "?"}, (
            f"{app} is marked MIGRATE but names no home")
        assert len(home.split()) >= 2, (
            f"{app} names {home!r} as a home, which is a label not a plan")


def test_a_closed_capability_is_recorded_as_closed_rather_than_left_blank():
    """Every row says why. A blank reason reads as an oversight to the next reader."""
    for section in ("## 1.", "## 2."):
        for row in _rows(section):
            reason = row[-1]
            assert reason and reason not in {"—", "-", "TBD"}, (
                f"{row[0]} in {section} gives no reason")
            assert len(reason.split()) >= 4, (
                f"{row[0]} gives {reason!r}, which is a label not a reason")


# ── The running platform ─────────────────────────────────────────────────────

def _public_dns(host: str) -> list:
    if host.endswith("example.com"):
        return ["93.184.216.34"]
    raise OSError(f"unknown test host: {host}")


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    """The whole platform with every published tool switched on.

    The operator switch is opened to all five on purpose: the exposure sweep is
    only meaningful when the catalog is as wide as it can legitimately get. A
    sweep over an empty catalog passes and proves nothing.
    """
    monkeypatch.setattr(webhooks, "_system_resolver", _public_dns)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'cert.db').as_posix()}")
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

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "certification-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": ",".join(PUBLISHED),
        "LTT_PUBLIC_API_RPM": "600", "LTT_PUBLIC_API_CREATE_RPM": "300",
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

    email = f"cert-{uuid.uuid4().hex[:6]}@example.com"
    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, 500, by="test")
        db.commit()
        user_id = user.id
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
    return user_id


def _issue(client, mode: str = "test") -> str:
    page = client.get("/developers/keys").text
    created = client.post("/developers/keys",
                          data={"name": f"{mode} key", "mode": mode,
                                "csrf_token": _csrf(page),
                                "scopes": list(SCOPES)})
    found = re.search(r"<code>(ltt_[st]k_[^<]+)</code>", created.text)
    assert found, created.text[:400]
    return found.group(1)


def _auth(token: str, idem: str = "") -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _upload(client, token: str, tool: str, field: str) -> str:
    created = client.post(f"{API_V1_PREFIX}/uploads",
                          json={"tool": tool, "field": field,
                                "filename": "in.png",
                                "content_type": "image/png",
                                "size": len(PNG)},
                          headers=_auth(token))
    assert created.status_code == 201, created.text
    upload_id = created.json()["id"]
    client.post(f"{API_V1_PREFIX}/uploads/{upload_id}/content",
                files={"file": ("in.png", PNG, "image/png")},
                headers=_auth(token))
    client.post(f"{API_V1_PREFIX}/uploads/{upload_id}/confirm",
                headers=_auth(token))
    return upload_id


def _input_for(client, token: str, tool: str) -> dict:
    payload = dict(INPUTS[tool])
    if tool == "image.upscale":
        payload["image_key"] = _upload(client, token, tool, "image_key")
    return payload


@pytest.fixture()
def certified(portal):
    """Sign in once and hold a test-mode key for the whole certification."""
    _sign_in(portal)
    return portal, _issue(portal, "test")


# ── One certification per published operation ────────────────────────────────

@pytest.mark.parametrize("tool", PUBLISHED)
def test_the_operation_is_documented_well_enough_to_call_without_reading_our_code(
        certified, tool):
    client, token = certified
    listed = client.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert listed.status_code == 200, listed.text
    assert tool in [row["name"] for row in listed.json()["items"]]

    detail = client.get(f"{API_V1_PREFIX}/tools/{tool}", headers=_auth(token))
    assert detail.status_code == 200, detail.text
    body = detail.json()

    assert body["description"].strip(), f"{tool} publishes no description"
    assert body["required_scopes"], f"{tool} publishes no scope requirement"
    assert body["execution_mode"], f"{tool} publishes no execution mode"

    schema = body["input_schema"]
    assert schema.get("properties"), f"{tool} publishes an empty input schema"
    for name, spec in schema["properties"].items():
        assert spec.get("description", "").strip(), (
            f"{tool}.{name} is published with no description — a caller would "
            f"have to guess what it does")
    assert body["output_schema"].get("properties"), (
        f"{tool} publishes no output schema, so a caller cannot know what to "
        f"parse")


@pytest.mark.parametrize("tool", PUBLISHED)
def test_the_operation_quotes_a_price_before_it_charges_anything(certified, tool):
    client, token = certified
    payload = _input_for(client, token, tool)
    quoted = client.post(f"{API_V1_PREFIX}/quotes",
                         json={"tool": tool, "input": payload},
                         headers=_auth(token))
    assert quoted.status_code == 200, quoted.text
    body = quoted.json()
    assert body["credit"] >= 0
    assert body["quote"], f"{tool} returns no signed quote"


@pytest.mark.parametrize("tool", PUBLISHED)
def test_the_operation_runs_end_to_end_from_outside_and_returns_its_contract(
        certified, tool):
    """The certification proper: call it as a customer would, and check the
    result is shaped like the contract we published.

    On a test-mode key, so this exercises the real routing, the real worker and
    the real result plumbing without a provider, a GPU or a credit.
    """
    from platform_core.job_runner import _chay_mot_job

    client, token = certified
    payload = _input_for(client, token, tool)

    quoted = client.post(f"{API_V1_PREFIX}/quotes",
                         json={"tool": tool, "input": payload},
                         headers=_auth(token))
    assert quoted.status_code == 200, quoted.text

    created = client.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": tool, "quote": quoted.json()["quote"], "input": payload},
        headers=_auth(token, f"cert-{uuid.uuid4().hex[:10]}"))
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    assert created.json()["mode"] == "test"

    assert _chay_mot_job("certification-worker") is True

    finished = client.get(f"{API_V1_PREFIX}/jobs/{job_id}",
                          headers=_auth(token))
    assert finished.status_code == 200, finished.text
    body = finished.json()
    assert body["status"] == "succeeded", body

    contract = client.get(f"{API_V1_PREFIX}/tools/{tool}",
                          headers=_auth(token)).json()
    declared = contract["output_schema"]["properties"]
    result = body.get("result") or {}
    outputs = body.get("outputs") or []

    # The contract splits its outputs across two places: a field that names a
    # file arrives in `outputs` as a fetchable id, everything else arrives in
    # `result`. Certifying that split is the point — an integrator who looks in
    # the wrong one finds nothing and concludes the job produced nothing.
    for field, spec in declared.items():
        kind = str(spec.get("type") or "")
        if kind not in {"artifact", "artifact[]"}:
            assert field in result, (
                f"{tool} finished without {field!r} in `result`, which its "
                f"published output schema promises")
            continue
        ids = [item["id"] for item in outputs if item["field"] == field]
        assert ids, (
            f"{tool} declares {field!r} as a file but produced none")
        if kind == "artifact":
            assert len(ids) == 1, f"{tool}.{field} is one file, got {len(ids)}"
        for artifact_id in ids:
            fetched = client.get(f"{API_V1_PREFIX}/artifacts/{artifact_id}",
                                 headers=_auth(token))
            assert fetched.status_code == 200, fetched.text


@pytest.mark.parametrize("tool", PUBLISHED)
def test_the_operation_appears_in_usage_so_a_customer_can_reconcile_it(
        certified, tool):
    from platform_core.job_runner import _chay_mot_job

    client, token = certified
    payload = _input_for(client, token, tool)
    quoted = client.post(f"{API_V1_PREFIX}/quotes",
                         json={"tool": tool, "input": payload},
                         headers=_auth(token))
    client.post(f"{API_V1_PREFIX}/jobs",
                json={"tool": tool, "quote": quoted.json()["quote"],
                      "input": payload},
                headers=_auth(token, f"cert-u-{uuid.uuid4().hex[:8]}"))
    _chay_mot_job("certification-worker")

    usage = client.get(f"{API_V1_PREFIX}/usage", headers=_auth(token))
    assert usage.status_code == 200, usage.text
    assert tool in usage.text, f"{tool} ran but does not appear in usage"


@pytest.mark.parametrize("tool", PUBLISHED)
def test_a_second_identical_call_is_not_a_second_job(certified, tool):
    client, token = certified
    payload = _input_for(client, token, tool)
    quoted = client.post(f"{API_V1_PREFIX}/quotes",
                         json={"tool": tool, "input": payload},
                         headers=_auth(token)).json()
    key = f"cert-idem-{uuid.uuid4().hex[:8]}"
    first = client.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": tool, "quote": quoted["quote"],
                              "input": payload},
                        headers=_auth(token, key))
    second = client.post(f"{API_V1_PREFIX}/jobs",
                         json={"tool": tool, "quote": quoted["quote"],
                               "input": payload},
                         headers=_auth(token, key))
    assert first.status_code == 201, first.text
    assert second.status_code in (200, 201), second.text
    assert first.json()["id"] == second.json()["id"], (
        f"{tool} created a second job for a retried request")


@pytest.mark.parametrize("tool", PUBLISHED)
def test_the_operation_can_tell_a_webhook_when_it_finishes(certified, tool):
    from platform_core.db import get_session
    from platform_core.job_runner import _chay_mot_job
    from platform_core.public_api import outbox

    client, token = certified
    registered = client.post(f"{API_V1_PREFIX}/webhooks",
                             json={"url": RECEIVER, "events": ["job.succeeded"]},
                             headers=_auth(token))
    assert registered.status_code in (200, 201), registered.text

    payload = _input_for(client, token, tool)
    quoted = client.post(f"{API_V1_PREFIX}/quotes",
                         json={"tool": tool, "input": payload},
                         headers=_auth(token)).json()
    created = client.post(f"{API_V1_PREFIX}/jobs",
                          json={"tool": tool, "quote": quoted["quote"],
                                "input": payload},
                          headers=_auth(token, f"cert-w-{uuid.uuid4().hex[:8]}"))
    _chay_mot_job("certification-worker")

    gen = get_session()
    db = next(gen)
    try:
        queued = outbox.pending(db) if hasattr(outbox, "pending") else None
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    deliveries = client.get(f"{API_V1_PREFIX}/webhooks/deliveries",
                            headers=_auth(token))
    assert deliveries.status_code == 200, deliveries.text
    assert created.json()["id"] in deliveries.text or queued, (
        f"{tool} finished without queuing a delivery to a subscribed webhook")


@pytest.mark.parametrize("tool", PUBLISHED)
def test_the_operation_is_reachable_from_the_places_a_developer_looks(
        certified, tool):
    """Docs page, playground and pricing all offer it.

    Each of these is built by different code from the same catalog, so this is
    the check that the catalog really is the single source: a tool that is
    published but missing from the playground is published in name only.
    """
    client, _token = certified
    for path in ("/developers/tools", f"/developers/tools/{tool}",
                 "/developers/playground", "/developers/pricing"):
        page = client.get(path, follow_redirects=True)
        assert page.status_code == 200, f"{path} -> {page.status_code}"
        if path.endswith(tool) or path in ("/developers/tools",
                                           "/developers/playground"):
            assert tool in page.text, f"{tool} is missing from {path}"


def test_a_test_mode_job_may_store_its_input_even_though_it_holds_no_credit(
        certified):
    """Found by certifying `image.upscale`, the one operation that needs a file.

    The rule "no file without a credit hold" stops job inputs being used as free
    storage. A test-mode job never holds credit — that is the whole promise of a
    test key — so for every tool that takes a file the rule was not a bar but a
    wall, and the sandbox could not exercise the thing it exists to exercise.
    """
    from platform_core.job_runner import _chay_mot_job

    client, token = certified
    payload = _input_for(client, token, "image.upscale")
    quoted = client.post(f"{API_V1_PREFIX}/quotes",
                         json={"tool": "image.upscale", "input": payload},
                         headers=_auth(token)).json()
    created = client.post(f"{API_V1_PREFIX}/jobs",
                          json={"tool": "image.upscale",
                                "quote": quoted["quote"], "input": payload},
                          headers=_auth(token, f"cert-up-{uuid.uuid4().hex[:8]}"))
    assert created.status_code == 201, created.text
    assert _chay_mot_job("certification-worker") is True

    finished = client.get(f"{API_V1_PREFIX}/jobs/{created.json()['id']}",
                          headers=_auth(token)).json()
    assert finished["status"] == "succeeded", finished
    assert finished["credit"]["charged"] == 0, "a test key must not spend"


def test_a_live_job_still_cannot_store_a_file_without_holding_credit():
    """The other half. Relaxing the rule for test mode must not relax it at all
    for live mode, where it is the only thing standing between job inputs and
    free unbounded storage.
    """
    from platform_core import upload_sessions

    class _Job:
        id = "job-without-a-hold"
        user_id = "u"
        app_slug = "upscalevideo"
        params: dict = {}

    assert upload_sessions._la_job_thu(_Job()) is False, (
        "a job with no API meta must not be mistaken for a test job")

    from platform_core.public_api.invocation import API_META_KEY

    live = _Job()
    live.params = {API_META_KEY: {"mode": "live"}}
    assert upload_sessions._la_job_thu(live) is False, (
        "a live job must still meet the credit-hold rule")


# ── Nothing published by accident ────────────────────────────────────────────

def test_no_closed_tool_is_named_on_any_surface_a_customer_can_reach(certified):
    """The sweep, run with the operator switch as wide as it legitimately goes.

    Surfaces are built by different code — the OpenAPI document, the docs pages,
    the playground, the status page — so each is a separate chance to leak a
    name that no decision covers.
    """
    client, token = certified
    closed = sorted({t.name for _slug, t in _all_tools() if not t.api_exposed})
    assert closed, "the sweep is meaningless if every tool is published"

    surfaces = ["/api/v1/openapi.json", "/api/v1/capabilities",
                "/developers", "/developers/tools", "/developers/playground",
                "/developers/pricing", "/status/api"]
    for path in surfaces:
        body = client.get(path, follow_redirects=True).text
        leaked = [name for name in closed if name in body]
        assert not leaked, f"{path} names closed tools: {leaked}"

    for path in (f"{API_V1_PREFIX}/tools", f"{API_V1_PREFIX}/models"):
        body = client.get(path, headers=_auth(token)).text
        leaked = [name for name in closed if name in body]
        assert not leaked, f"{path} names closed tools: {leaked}"


def test_a_closed_tool_cannot_be_called_even_by_name(certified):
    client, token = certified
    closed = [t.name for _slug, t in _all_tools() if not t.api_exposed]
    for name in closed[:6]:
        answered = client.post(f"{API_V1_PREFIX}/quotes",
                               json={"tool": name, "input": {}},
                               headers=_auth(token))
        assert answered.status_code == 404, (
            f"{name} is not published but quoting it returned "
            f"{answered.status_code}")


def test_no_vendor_model_id_reaches_a_customer_surface(certified):
    """Aliases exist so a vendor change is not a breaking change.

    If the raw id leaks anywhere a customer reads, integrations start pinning to
    it and the alias stops being a layer of insulation.
    """
    client, token = certified
    vendor_ids = sorted({spec.get("id")
                         for _slug, tool in _all_tools()
                         for spec in (tool.api_contract.get("models")
                                      or {}).values()
                         if spec.get("id")})
    assert vendor_ids, "no aliases declared, so this proves nothing"

    for path in ("/api/v1/openapi.json", "/developers/tools",
                 "/developers/playground"):
        body = client.get(path, follow_redirects=True).text
        leaked = [v for v in vendor_ids if v in body]
        assert not leaked, f"{path} exposes vendor ids: {leaked}"

    for path in (f"{API_V1_PREFIX}/tools", f"{API_V1_PREFIX}/models"):
        body = client.get(path, headers=_auth(token)).text
        leaked = [v for v in vendor_ids if v in body]
        assert not leaked, f"{path} exposes vendor ids: {leaked}"


def test_every_published_model_alias_belongs_to_a_published_tool(certified):
    client, token = certified
    tools = {row["name"] for row in
             client.get(f"{API_V1_PREFIX}/tools",
                        headers=_auth(token)).json()["items"]}
    models = client.get(f"{API_V1_PREFIX}/models", headers=_auth(token)).json()
    assert models["items"], "no models published, so this proves nothing"
    for row in models["items"]:
        owners = set(row.get("tools") or ())
        assert owners <= tools, (
            f"model {row['name']} is offered for unpublished tools: "
            f"{sorted(owners - tools)}")
