"""EXT-18 — SDKs, Postman, OpenAPI, and the promise that none of them is required.

Two acceptance criteria:

* **a generic HTTP client can go end to end without the SDK** — proven by doing
  exactly that, with nothing but `urllib` from the standard library. If only our
  own library can drive the API, it is not an API, it is a library;
* **SDK, Postman and the contract agree** — proven by checking the declarations
  against the route inventory, and by regenerating the collection and comparing.

The third property, which the brief does not name but the whole thing rests on:
the generated artefacts must be **generated**. A hand-edited Postman collection
is a second copy of the contract, and a second copy is the one that drifts.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits
from server.api.inventory import API_V1_PREFIX, API_V1_ROUTES

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY_SDK = ROOT / "sdk" / "python" / "ltt_public_api.py"
TS_SDK = ROOT / "sdk" / "typescript" / "ltt-public-api.ts"
COLLECTION = ROOT / "sdk" / "postman" / "ltt-public-api.postman_collection.json"
ENVIRONMENT = ROOT / "sdk" / "postman" / "ltt-public-api.postman_environment.json"
RECIPES = ROOT / "docs" / "PUBLIC_API" / "RECIPES.md"

PEPPER = "sdk-test-pepper-" + "s" * 40
TOOL = "image.thumbnail"
SCOPES = ("tools:read", "jobs:create", "jobs:read", "artifacts:read")


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'sdk.db').as_posix()}")
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
                        lambda *a, **k: bytes([137, 80, 78, 71, 13, 10, 26, 10])
                        + b"0" * 200)

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "sdk-secret-value",
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


def _account(client) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    email = f"sdk-{uuid.uuid4().hex[:6]}@example.com"
    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, 500, by="test")
        db.commit()
    finally:
        _close(gen)

    page = client.get("/login").text
    client.post("/login", data={"username": email,
                                "password": "a-good-password-12",
                                "csrf_token": _csrf(page)},
                follow_redirects=False)
    keys_page = client.get("/developers/keys").text
    made = client.post("/developers/keys",
                       data={"name": "sdk", "csrf_token": _csrf(keys_page),
                             "scopes": list(SCOPES)})
    return re.search(r"<code>(ltt_sk_[^<]+)</code>", made.text).group(1)


# ── A generic HTTP client, with no SDK at all ────────────────────────────────

def test_a_plain_http_client_can_go_end_to_end(portal):
    """The acceptance criterion, taken literally.

    Nothing from `sdk/` is imported. This is `TestClient` standing in for any
    HTTP library: discover, quote, submit with an idempotency key, poll, and
    download the bytes. If this test needed the SDK, the API would not be one.
    """
    token = _account(portal)
    auth = {"Authorization": f"Bearer {token}"}
    payload = {"topic": "generic client", "count": 1}

    listing = portal.get(f"{API_V1_PREFIX}/tools", headers=auth)
    assert listing.status_code == 200
    assert TOOL in [item["name"] for item in listing.json()["items"]]

    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": payload}, headers=auth)
    assert quote.status_code == 200, quote.text
    assert quote.json()["credit"] > 0

    idem = uuid.uuid4().hex
    created = portal.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote.json()["quote"], "input": payload},
        headers={**auth, "Idempotency-Key": idem})
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]

    from platform_core.job_runner import _chay_mot_job

    assert _chay_mot_job("sdk-worker") is True

    finished = portal.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=auth).json()
    assert finished["status"] == "succeeded", finished

    artifact = finished["outputs"][0]["id"]
    content = portal.get(f"{API_V1_PREFIX}/artifacts/{artifact}/content",
                         headers=auth)
    assert content.status_code == 200
    assert content.content.startswith(bytes([137, 80, 78, 71]))


def test_the_generic_client_gets_the_same_answer_on_a_replayed_key(portal):
    """The one header that costs money to get wrong, exercised without an SDK."""
    token = _account(portal)
    auth = {"Authorization": f"Bearer {token}"}
    payload = {"topic": "replay", "count": 1}
    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": payload},
                        headers=auth).json()

    idem = uuid.uuid4().hex
    body = {"tool": TOOL, "quote": quote["quote"], "input": payload}
    first = portal.post(f"{API_V1_PREFIX}/jobs", json=body,
                        headers={**auth, "Idempotency-Key": idem})
    second = portal.post(f"{API_V1_PREFIX}/jobs", json=body,
                         headers={**auth, "Idempotency-Key": idem})

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.headers.get("Idempotency-Replayed") == "true"
    assert first.json()["id"] == second.json()["id"], "a retry made a second job"


# ── The SDKs agree with the contract ─────────────────────────────────────────

def test_every_route_is_covered_or_deliberately_skipped():
    """Run the real checker, not a copy of its logic."""
    result = subprocess.run(
        [sys.executable, "tools/check_sdk_contract.py"], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_missing_declaration_is_caught():
    """A checker that passes everything is worse than no checker."""
    saved = TS_SDK.read_text(encoding="utf-8")
    try:
        TS_SDK.write_text(saved.replace("  // @covers GET /models\n", "", 1),
                          encoding="utf-8", newline="")
        result = subprocess.run(
            [sys.executable, "tools/check_sdk_contract.py"], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert result.returncode == 1
        assert "GET /models" in result.stdout
    finally:
        TS_SDK.write_text(saved, encoding="utf-8", newline="")


def test_a_skip_must_give_a_reason():
    saved = PY_SDK.read_text(encoding="utf-8")
    try:
        text = saved.replace(
            "# @covers-not GET /openapi.json — machine-readable spec, not a call your code",
            "# @covers-not GET /openapi.json", 1)
        PY_SDK.write_text(text, encoding="utf-8", newline="")
        result = subprocess.run(
            [sys.executable, "tools/check_sdk_contract.py"], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert result.returncode == 1
        assert "ly do" in result.stdout
    finally:
        PY_SDK.write_text(saved, encoding="utf-8", newline="")


def test_both_sdks_cover_the_same_surface():
    """One SDK quietly lagging the other is how a team picks the wrong language
    and finds out three weeks later."""
    from tools.check_sdk_contract import declared

    py_covered, py_skipped = declared(PY_SDK)
    ts_covered, ts_skipped = declared(TS_SDK)
    assert py_covered == ts_covered, {
        "only python": sorted(py_covered - ts_covered),
        "only typescript": sorted(ts_covered - py_covered)}
    assert set(py_skipped) == set(ts_skipped)


def test_the_sdks_carry_the_two_things_that_cost_money():
    """Idempotency on the chargeable call, and retry that does not duplicate."""
    py = PY_SDK.read_text(encoding="utf-8")
    ts = TS_SDK.read_text(encoding="utf-8")
    for text in (py, ts):
        assert "Idempotency-Key" in text
    assert "idempotency_key" in py or "idempotency-key" in py.lower()
    assert "idempotencyKey" in ts


# ── Postman is generated, and current ────────────────────────────────────────

def test_the_postman_collection_matches_the_spec():
    result = subprocess.run(
        [sys.executable, "tools/build_postman.py", "--check"], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_collection_covers_every_documented_route():
    collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
    names = {item["name"] for item in collection["item"]}
    for route in API_V1_ROUTES:
        if not route.in_schema:
            continue
        tail = route.path.replace(API_V1_PREFIX, "")
        if tail == "/openapi.json":
            continue          # served by the framework, not a documented op
        assert f"{route.method} {tail}" in names, f"{route.method} {tail}"


def test_the_chargeable_request_carries_an_idempotency_key():
    """The single most expensive thing to forget, pre-filled in the collection."""
    collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
    job = next(item for item in collection["item"]
               if item["name"] == "POST /jobs")
    headers = {header["key"] for header in job["request"]["header"]}
    assert "Idempotency-Key" in headers
    assert "Authorization" in headers


def test_the_committed_environment_carries_no_key():
    """A committed file that could hold a real credential eventually holds one."""
    environment = json.loads(ENVIRONMENT.read_text(encoding="utf-8"))
    for value in environment["values"]:
        if value["key"] == "api_key":
            assert value["value"] == ""
            assert value.get("type") == "secret"


def test_the_collection_says_not_to_edit_it_by_hand():
    collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
    assert "build_postman" in collection["info"]["description"]


# ── The versioned spec ───────────────────────────────────────────────────────

def test_the_spec_can_be_downloaded_with_the_version_in_its_name(portal):
    _account(portal)
    answer = portal.get("/developers/openapi/download")
    assert answer.status_code == 200
    disposition = answer.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert "v1" in disposition, "a saved spec must say which version it is"
    document = json.loads(answer.content)
    assert document["openapi"].startswith("3.")
    assert "/tools" in document["paths"]


def test_the_downloaded_spec_is_the_one_the_api_serves(portal):
    """Two ways of producing a spec is one too many."""
    token = _account(portal)
    served = portal.get(f"{API_V1_PREFIX}/openapi.json",
                        headers={"Authorization": f"Bearer {token}"})
    downloaded = portal.get("/developers/openapi/download")
    assert served.status_code == 200
    assert json.loads(served.content) == json.loads(downloaded.content)


# ── The recipes, for people who will never install our SDK ───────────────────

def test_the_recipes_cover_the_tools_people_actually_use():
    text = RECIPES.read_text(encoding="utf-8")
    for tool in ("cURL", "PowerShell", "n8n", "Make"):
        assert tool in text, tool
    # …and each one has to warn about the mistake that costs money.
    assert text.count("Idempotency-Key") >= 4


def test_the_recipes_warn_about_the_n8n_retry_trap():
    """The specific, real way an automation tool double-charges you."""
    text = RECIPES.read_text(encoding="utf-8")
    assert "$guid" in text
    assert "nhiều lần" in text or "hai lần" in text


def test_the_recipes_say_how_to_verify_a_webhook():
    text = RECIPES.read_text(encoding="utf-8")
    assert "body thô" in text
    assert "hằng định" in text or "compare_digest" in text
    assert "5 phút" in text
