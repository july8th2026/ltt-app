"""EXT-17 — the frozen contract, the changelog, and a status page that is safe to publish.

Two acceptance criteria, and both are about what must be impossible:

* **a breaking change fails CI unless it was versioned or accepted on purpose** —
  proven by mutating the baseline in every way a client could notice and
  checking the gate step refuses each one;
* **no sensitive topology leaks** — proven by asking the public page for its
  whole body and searching it for the words the operator page is full of.

The third thing defended here is subtler: the checker must not be *decorative*.
A gate that passes everything is worse than no gate, because it is trusted.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import contract, keys as devkeys, limits
from platform_core.public_api.config import load_public_api_config

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs" / "PUBLIC_API" / "CONTRACT_BASELINE.json"
CHANGELOG = ROOT / "docs" / "PUBLIC_API" / "CHANGELOG.md"
MIGRATION = ROOT / "docs" / "PUBLIC_API" / "MIGRATION.md"

PEPPER = "version-test-pepper-" + "v" * 40
TOOL = "image.thumbnail"


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ver.db').as_posix()}")
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
        "LTT_SESSION_SECRET": "version-secret-value",
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


def _snapshot():
    """The snapshot as the checker builds it.

    Routes are passed in rather than imported by `contract.py`: that module
    lives in `platform_core`, which must not reach up into `server` — a rule
    `test_147_layering` enforces, and one my first version broke.
    """
    from server.api.inventory import API_V1_ROUTES

    return contract.snapshot(_config(), routes=API_V1_ROUTES)


def _config(tools: str = ""):
    from platform_core.registry import discover

    names = tools or ",".join(sorted(
        tool.name for item in discover() if not item.error
        for tool in item.manifest.tools if tool.api_exposed))
    return load_public_api_config({"LTT_PUBLIC_API": "1",
                                   "LTT_PUBLIC_API_TOOLS": names})


def _checker(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "tools/check_api_compat.py", *args], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace")


# ── The snapshot is a stable fact ────────────────────────────────────────────

def test_a_snapshot_is_the_same_every_time():
    """A checker whose input wobbles reports changes nobody made, and then
    everybody learns to ignore it."""
    assert _snapshot() == _snapshot()


def test_the_snapshot_covers_what_a_client_depends_on():
    snap = _snapshot()
    assert snap["api_version"] == "v1"
    assert snap["routes"] and snap["tools"] and snap["error_codes"]
    for body in snap["tools"].values():
        assert body["contract_hash"] and body["execution_mode"]
    assert snap["webhook"]["payload_version"] >= 1
    assert set(snap["webhook"]["payload_fields"]) >= {"job_id", "status"}


def test_the_committed_baseline_matches_the_code():
    """The whole mechanism rests on this file being true right now."""
    assert BASELINE.is_file(), "the baseline must be committed"
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    result = contract.compare(baseline, _snapshot())
    assert result.clean, [item.line() for item in result.differences]


# ── A breaking change fails CI ───────────────────────────────────────────────

BREAKING_MUTATIONS = {
    "a route disappears": lambda d: d["routes"].__setitem__(
        "GET /api/v1/ghost", {"authenticated": True, "in_schema": True,
                              "execution_mode": "SYNC", "deprecated_on": "",
                              "sunset_on": ""}),
    "a route starts needing auth": lambda d: d["routes"]["GET /api/v1/me"]
        .__setitem__("authenticated", False),
    "a tool disappears": lambda d: d["tools"].__setitem__(
        "image.ghost", {"contract_hash": "0" * 16,
                        "execution_mode": "ASYNC_JOB", "required_scopes": [],
                        "aliases": [], "deprecated": "", "models": []}),
    "a tool schema moves": lambda d: d["tools"][TOOL].__setitem__(
        "contract_hash", "0" * 16),
    "a tool needs a new scope": lambda d: d["tools"][TOOL].__setitem__(
        "required_scopes", []),
    "a tool changes execution mode": lambda d: d["tools"][TOOL].__setitem__(
        "execution_mode", "SYNC"),
    "an error code disappears": lambda d: d["error_codes"].__setitem__(
        "ghost_code", {"status": 418, "retry": "never"}),
    "an error code changes status": lambda d: d["error_codes"]["not_found"]
        .__setitem__("status", 410),
    "the webhook payload version moves": lambda d: d["webhook"].__setitem__(
        "payload_version", 0),
    "a webhook event disappears": lambda d: d["webhook"]["event_types"]
        .append("job.ghost"),
    "a webhook payload field disappears": lambda d: d["webhook"]
        ["payload_fields"].append("ghost_field"),
    "the api version moves": lambda d: d.__setitem__("api_version", "v0"),
    "a response header disappears": lambda d: d["headers"].append("X-Ghost"),
}


@pytest.mark.parametrize("name", sorted(BREAKING_MUTATIONS))
def test_every_kind_of_breaking_change_is_refused(name, tmp_path):
    """Each entry is a way a working integration could stop working.

    Run against the real checker, on the real baseline file, restored
    afterwards — a gate tested only through its library is a gate whose wiring
    nobody checked.
    """
    saved = BASELINE.read_text(encoding="utf-8")
    try:
        body = json.loads(saved)
        BREAKING_MUTATIONS[name](body)
        BASELINE.write_text(
            json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n", encoding="utf-8", newline="")
        result = _checker()
        assert result.returncode == 1, (
            f"{name} was not refused:\n{result.stdout}{result.stderr}")
        assert "PHA VO TUONG THICH" in result.stdout
    finally:
        BASELINE.write_text(saved, encoding="utf-8", newline="")


def test_an_additive_change_is_allowed():
    """A client that never asks for a new thing cannot notice it."""
    saved = BASELINE.read_text(encoding="utf-8")
    try:
        body = json.loads(saved)
        body["tools"].pop(TOOL)          # baseline knows less than the code
        BASELINE.write_text(
            json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n", encoding="utf-8", newline="")
        result = _checker()
        assert result.returncode == 0, result.stdout + result.stderr
        assert "CONG THEM" in result.stdout
    finally:
        BASELINE.write_text(saved, encoding="utf-8", newline="")


def test_accepting_a_change_rewrites_the_baseline():
    """`--accept` is not a way past the gate; it is a change a reviewer sees."""
    saved = BASELINE.read_text(encoding="utf-8")
    try:
        body = json.loads(saved)
        body["tools"][TOOL]["contract_hash"] = "0" * 16
        BASELINE.write_text(
            json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n", encoding="utf-8", newline="")
        assert _checker().returncode == 1

        accepted = _checker("--accept")
        assert accepted.returncode == 0
        assert _checker().returncode == 0
        # …and the file on disk really moved, which is what shows up in review.
        assert BASELINE.read_text(encoding="utf-8") != json.dumps(
            body, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    finally:
        BASELINE.write_text(saved, encoding="utf-8", newline="")


def test_a_stale_snapshot_format_is_refused_rather_than_compared():
    old = {"snapshot_version": 0, "api_version": "v1"}
    result = contract.compare(old, _snapshot())
    assert result.breaking
    assert "regenerate" in result.breaking[0].detail


def test_an_unclassified_field_change_defaults_to_safe():
    """Metadata moves are allowed; the classifier only calls things safe when
    it recognises them."""
    new = _snapshot()
    old = json.loads(json.dumps(new))
    old["tools"][TOOL]["deprecated"] = "2027-01-01"
    result = contract.compare(old, new)
    assert result.differences and not result.breaking


def test_the_checker_is_wired_into_the_gate():
    """A checker nobody runs is a comment."""
    source = (ROOT / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "check_api_compat.py" in source


# ── No sensitive topology leaks ──────────────────────────────────────────────

FORBIDDEN_ON_A_PUBLIC_PAGE = (
    "postgres", "postgresql", "sqlite", "cloudflare", "tunnel", "nssm",
    "gemini", "worker_id", "C:\\", "D:\\", "127.0.0.1", "localhost",
    "api_keys", "gpu_lease", "secrets/", "traceback",
)


def test_the_public_status_page_is_readable_without_an_account(portal):
    """A status page a customer cannot read during an incident does not exist."""
    answer = portal.get("/status/api")
    assert answer.status_code == 200, answer.text[:300]
    assert answer.headers.get("cache-control") == "no-store"


def test_the_public_status_page_names_no_internal_topology(portal):
    body = portal.get("/status/api").text.lower()
    for word in FORBIDDEN_ON_A_PUBLIC_PAGE:
        assert word.lower() not in body, f"public status page leaked {word!r}"


def test_the_operator_status_page_still_requires_an_operator(portal):
    answer = portal.get("/status", follow_redirects=False)
    assert answer.status_code in (302, 303, 307, 401, 403)


def test_the_public_page_groups_by_capability_not_by_tool(portal):
    from platform_core.public_api.status import public_status

    gen, db = _session()
    try:
        report = public_status(db, _config(TOOL))
    finally:
        _close(gen)

    assert report["capabilities"]
    line = report["capabilities"][0]
    assert line.capability == "image", "grouped by what a customer buys"
    assert TOOL in line.tools


def test_a_maintenance_switch_shows_on_the_public_page(portal):
    """The operator's own words, because they wrote them for a customer."""
    from platform_core.public_api import policy
    from platform_core.public_api.status import MAINTENANCE, public_status
    from platform_core.public_api.tables import KILL_MAINTENANCE

    gen, db = _session()
    try:
        policy.engage(db, scope=KILL_MAINTENANCE,
                      reason="đang nâng cấp cơ sở dữ liệu",
                      created_by="operator@example.com")
        db.commit()
        report = public_status(db, _config(TOOL))
    finally:
        _close(gen)

    assert report["overall"] == MAINTENANCE
    assert all(row.state == MAINTENANCE for row in report["capabilities"])
    assert "nâng cấp" in report["capabilities"][0].note

    body = portal.get("/status/api").text
    assert "nâng cấp cơ sở dữ liệu" in body


def test_one_tool_off_degrades_its_capability_without_claiming_an_outage(portal):
    from platform_core.public_api import policy
    from platform_core.public_api.status import (DEGRADED, MAINTENANCE,
                                                 public_status)
    from platform_core.public_api.tables import KILL_TOOL

    gen, db = _session()
    try:
        policy.engage(db, scope=KILL_TOOL, subject="image.generate",
                      reason="upstream model degraded",
                      created_by="operator@example.com")
        db.commit()
        report = public_status(db, _config("image.generate,image.thumbnail"))
    finally:
        _close(gen)

    image = next(row for row in report["capabilities"]
                 if row.capability == "image")
    assert image.state == DEGRADED, "one of two tools off is not maintenance"
    assert image.state != MAINTENANCE


def test_an_expired_switch_stops_showing(portal):
    from platform_core.public_api import policy
    from platform_core.public_api.status import OPERATIONAL, public_status
    from platform_core.public_api.tables import ApiKillSwitch, KILL_MAINTENANCE

    gen, db = _session()
    try:
        row = policy.engage(db, scope=KILL_MAINTENANCE, reason="short window",
                            expires_at=datetime.now(timezone.utc)
                            + timedelta(minutes=5))
        db.commit()
        switch_id = row.id
        db.get(ApiKillSwitch, switch_id).expires_at = (
            datetime.now(timezone.utc) - timedelta(seconds=1))
        db.commit()
        report = public_status(db, _config(TOOL))
    finally:
        _close(gen)
    assert report["overall"] == OPERATIONAL


# ── The written record ───────────────────────────────────────────────────────

def test_the_changelog_answers_the_question_a_customer_has():
    text = CHANGELOG.read_text(encoding="utf-8")
    for marker in ("BREAKING", "ADDED", "DEPRECATED", "CONTRACT_BASELINE.json"):
        assert marker in text
    # It has to say how a breaking change is *allowed* to happen, or the rule
    # lives only in somebody's head.
    assert "check_api_compat.py --accept" in text


def test_the_migration_page_is_explicit_about_being_empty():
    """An empty deprecation page can mean "nothing is deprecated" or "nobody
    updated this", and those are very different to somebody deciding whether to
    integrate."""
    text = MIGRATION.read_text(encoding="utf-8")
    assert "chưa có gì bị ngừng hỗ trợ" in text.lower()
    assert "Deprecation" in text and "Sunset" in text


def test_nothing_is_deprecated_yet_and_the_docs_agree():
    """If a route ever gains a sunset date, this test makes somebody update the
    page that promises there is none."""
    from server.api.inventory import API_V1_ROUTES

    dated = [route for route in API_V1_ROUTES
             if route.deprecated_on or route.sunset_on]
    text = MIGRATION.read_text(encoding="utf-8")
    if dated:
        for route in dated:
            assert route.path in text, (
                f"{route.path} has a sunset date but MIGRATION.md does not "
                f"mention it")
    else:
        assert "*(chưa có)*" in text


def test_the_webhook_payload_version_is_declared_next_to_the_payload():
    """A version a receiver parses on must live where the payload is built."""
    from platform_core.public_api import webhooks

    payload = webhooks.build_payload(
        event_id=uuid.uuid4().hex, event_type=webhooks.EVENT_JOB_SUCCEEDED,
        job_id="j1", tool=TOOL, status="succeeded")
    assert set(payload["data"]) == set(webhooks.PAYLOAD_FIELDS)
    assert webhooks.PAYLOAD_VERSION == 1
