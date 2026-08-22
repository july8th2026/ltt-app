"""Q92 / Prompt 13 — wave 3: logical operations whose product is data.

Waves 1 and 2 returned files. These tools return a prompt package and a
storyboard, so this wave adds the missing half of the job contract — an inline
``result`` — and proves the two things that could go wrong with it: publishing
more of the handler's result than the contract declares, and letting a public
call reach the app's internal project machinery.

The two duration-priced candidates (`video.subtitle`, `video.short_clips`) are
deferred here for the same measured reason as `video.upscale` in wave 2, and the
reason is pinned by a test.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from platform_core.models import Job
from platform_core.public_api import keys as devkeys
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.scopes import (SCOPE_ARTIFACTS_READ,
                                             SCOPE_CREDITS_READ,
                                             SCOPE_JOBS_CANCEL, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ,
                                             SCOPE_UPLOADS_WRITE, SCOPE_USAGE_READ)
from platform_core.registry import discover
from server.api.inventory import API_V1_PREFIX

PEPPER = "wave3-test-pepper-" + "p" * 40
PUBLISHED = ("image.thumbnail", "image.generate", "image.upscale",
             "text.prompt_package", "story.storyboard")
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_JOBS_CANCEL, SCOPE_UPLOADS_WRITE, SCOPE_ARTIFACTS_READ,
              SCOPE_CREDITS_READ, SCOPE_USAGE_READ)
GOLDEN = Path(__file__).parent / "golden" / "public_api_catalog_v1.json"


def _config():
    return load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": ",".join(PUBLISHED)})


# ── What wave 3 opened ───────────────────────────────────────────────────────

def test_the_two_logical_operations_are_published():
    names = [tool.name for tool in build_catalog(_config())]
    assert "text.prompt_package" in names and "story.storyboard" in names
    # Compare against the golden entries **for wave 3's five tools**, not the
    # whole file. The two were the same set until 2026-08-22, when `image.ltt`
    # was added to the frozen inventory. What this test is actually asserting is
    # that wave 3's contracts have not drifted — asserting "and nothing else
    # exists" was an accident of the two sets coinciding, and it would fail every
    # time a later wave freezes a contract of its own.
    snapshot = {tool.name: tool.to_public_dict() for tool in build_catalog(_config())}
    golden = {entry["name"]: entry
              for entry in json.loads(GOLDEN.read_text(encoding="utf-8"))["tools"]}
    assert sorted(snapshot) == sorted(PUBLISHED)
    assert snapshot == {name: golden[name] for name in snapshot}


def test_the_internal_routing_switch_is_not_a_public_parameter():
    """`operation` picks a code path inside the app; a caller picks a tool."""
    catalog = {tool.name: tool for tool in build_catalog(_config())}
    for name in ("text.prompt_package", "story.storyboard"):
        properties = catalog[name].input_schema["properties"]
        assert "operation" not in properties
        assert "model" not in properties
        # A free-form JSON blob the project schema interprets — including
        # references — has no owner-checked public shape yet.
        assert "resources" not in properties


def test_only_the_logical_tools_are_exposed_not_the_app_surface():
    """Prompt AI has dozens of internal routes; the API publishes two tools."""
    app = next(item for item in discover()
               if item.manifest.slug == "prompt_ai_ommi")
    exposed = [tool.name for tool in app.manifest.tools if tool.api_exposed]
    assert sorted(exposed) == ["story.storyboard", "text.prompt_package"]

    # And the app owns database tables that no public route touches.
    assert app.manifest.table_prefix == "ommi"
    from server.api.inventory import API_V1_ROUTES

    paths = " ".join(route.path for route in API_V1_ROUTES)
    for internal in ("project", "ommi", "library", "resource"):
        assert internal not in paths


# ── The deferrals, with the measurement behind them ─────────────────────────

@pytest.mark.parametrize("slug,tool_name", [
    ("autosubvideo", "video.subtitle"),
    ("taoclipngan", "video.short_clips"),
])
def test_duration_priced_tools_stay_closed(slug, tool_name):
    """One root cause, three tools: the hold is topped up at run time.

    Their quote is computed from a `duration_s` the caller declares, and the
    worker raises the hold once it measures the real duration. A person picking
    a file on a page can live with that; a signed machine quote cannot (Q84).
    """
    app = next(item for item in discover() if item.manifest.slug == slug)
    tool = next(spec for spec in app.manifest.tools if spec.name == tool_name)
    assert tool.api_exposed is False
    assert "duration_s" in tool.params_schema

    source = Path(f"apps/{slug}/jobs.py").read_text(encoding="utf-8")
    assert "_dam_bao_giu_cho" in source
    assert "credit.giu_cho(db, user_id, need - held, job_id)" in source


def test_the_free_platform_funded_jobs_are_not_public():
    """Q50: transcribe/diarize/translate are 0-credit and platform-funded."""
    app = next(item for item in discover()
               if item.manifest.slug == "autosubvideo")
    from apps.autosubvideo.manifest import _cost

    for operation in ("transcribe", "diarize", "translate"):
        assert _cost({"operation": operation}) == 0
    # None of them is reachable: the app exposes no tool at all on the API.
    assert not any(tool.api_exposed for tool in app.manifest.tools)


# ── End to end ──────────────────────────────────────────────────────────────

@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'wave3.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "wave3-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": ",".join(PUBLISHED),
    })
    try:
        with TestClient(app) as client:
            yield client
    finally:
        from server.api import deps
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


def _account(credits: int = 200):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"s-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, credits, by="test")
        _key, token = devkeys.issue(db, user_id=user.id, scopes=ALL_SCOPES,
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


def _run(api, token, tool, payload, idem):
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": tool, "input": payload}, headers=_auth(token))
    assert quote.status_code == 200, quote.text
    created = api.post(f"{API_V1_PREFIX}/jobs",
                       json={"tool": tool, "quote": quote.json()["quote"],
                             "input": payload},
                       headers=_auth(token, idem))
    return quote.json(), created


def _finish(job_id, user_id, result):
    from platform_core import credit, jobs as jobq

    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        jobq.complete(db, job, result)
        credit.quyet_toan(db, user_id, job_id, credit.so_da_giu(db, job_id))
        db.commit()
    finally:
        _close(gen)


def test_a_prompt_package_comes_back_as_data(api):
    user_id, token = _account()
    quote, created = _run(api, token, "text.prompt_package",
                          {"title": "Bánh mì", "story": "Một tiệm bánh nhỏ.",
                           "scene_count": 6, "language": "vi"},
                          "wave3-package-00001")
    assert created.status_code == 201
    job_id = created.json()["id"]
    # 2 + ceil(6/3)*2 = 6 credits, from the app's own cost function.
    from apps.prompt_ai_ommi.manifest import _cost

    assert quote["credit"] == _cost({"operation": "director", "scene_count": 6}) == 6

    # The server, not the caller, chose the internal operation — and it chose
    # the declared default rather than leaving the handler to guess.
    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        assert job.params["operation"] == "director"
        assert job.params["owner_id"] == user_id
    finally:
        _close(gen)

    _finish(job_id, user_id, {
        "prompt_package": {"scenes": [{"prompt": "wide shot"}]},
        "master_prompt": "one master prompt",
        # A handler is free to add its own bookkeeping; the contract is not.
        "debug_trace": "internal/trace-42.log",
        "provider_request_id": "byteplus-req-99",
    })

    detail = api.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=_auth(token)).json()
    assert detail["status"] == "succeeded"
    assert detail["result"] == {
        "prompt_package": {"scenes": [{"prompt": "wide shot"}]},
        "master_prompt": "one master prompt"}
    # Undeclared result fields never leave the building.
    assert "debug_trace" not in json.dumps(detail)
    assert "byteplus" not in json.dumps(detail)
    assert detail["outputs"] == []


def test_a_hidden_parameter_is_filled_with_its_declared_default(api):
    """Regression: hiding `operation` once made the storyboard tool run — and
    charge — as the prompt-package generator, because the handler fell back to
    its own default instead of the one the tool declared."""
    _user_id, token = _account()
    _quote, created = _run(api, token, "story.storyboard",
                           {"title": "A", "story": "B", "scene_count": 4},
                           "wave3-default-00001")
    assert created.status_code == 201
    gen, db = _session()
    try:
        assert db.get(Job, created.json()["id"]).params["operation"] == "storyboard"
    finally:
        _close(gen)


def test_a_storyboard_is_priced_by_scene_count(api):
    from apps.prompt_ai_ommi.manifest import _cost

    _user_id, token = _account()
    small, _created = _run(api, token, "story.storyboard",
                           {"title": "A", "story": "B", "scene_count": 4},
                           "wave3-story-small01")
    big, _created2 = _run(api, token, "story.storyboard",
                          {"title": "A", "story": "B", "scene_count": 20},
                          "wave3-story-big0001")
    assert small["credit"] == _cost({"operation": "storyboard", "scene_count": 4})
    assert big["credit"] == _cost({"operation": "storyboard", "scene_count": 20})
    assert big["credit"] > small["credit"]


def test_usage_reconciles_for_a_data_tool(api):
    user_id, token = _account()
    _quote, created = _run(api, token, "text.prompt_package",
                           {"title": "A", "story": "B", "scene_count": 3},
                           "wave3-usage-000001")
    job_id = created.json()["id"]
    _finish(job_id, user_id, {"prompt_package": {}, "master_prompt": "x"})

    usage = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(token)).json()
    line = next(item for item in usage["items"] if item["job_id"] == job_id)
    assert line["tool"] == "text.prompt_package"
    assert line["credit"]["net_charged"] == usage["totals"]["net_charged_credit"]

    from platform_core.public_api import usage as usage_mod

    gen, db = _session()
    try:
        report = usage_mod.reconcile(db, user_id=user_id)
        assert report["ok"] is True
    finally:
        _close(gen)


def test_another_account_cannot_read_the_data_result(api):
    alice_id, alice = _account()
    _bob_id, bob = _account()
    _quote, created = _run(api, alice, "story.storyboard",
                           {"title": "A", "story": "B"}, "wave3-owner-000001")
    job_id = created.json()["id"]
    _finish(job_id, alice_id, {"storyboard": {"shots": ["secret plot"]},
                               "master_prompt": "x"})

    assert "secret plot" in api.get(f"{API_V1_PREFIX}/jobs/{job_id}",
                                    headers=_auth(alice)).text
    assert api.get(f"{API_V1_PREFIX}/jobs/{job_id}",
                   headers=_auth(bob)).status_code == 404


def test_input_limits_are_enforced_before_any_charge(api):
    user_id, token = _account()
    too_long = api.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": "text.prompt_package",
                              "input": {"title": "A", "story": "x" * 12001}},
                        headers=_auth(token))
    assert too_long.status_code == 400

    too_many = api.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": "story.storyboard",
                              "input": {"title": "A", "story": "B",
                                        "scene_count": 21}},
                        headers=_auth(token))
    assert too_many.status_code == 400

    from platform_core.models import CREDIT_HOLD, CreditEntry

    gen, db = _session()
    try:
        holds = db.execute(sa.select(sa.func.count(CreditEntry.id)).where(
            CreditEntry.user_id == user_id,
            CreditEntry.kind == CREDIT_HOLD)).scalar_one()
        assert holds == 0
    finally:
        _close(gen)


def test_cancelling_a_data_job_refunds(api):
    user_id, token = _account()
    _quote, created = _run(api, token, "text.prompt_package",
                           {"title": "A", "story": "B"}, "wave3-cancel-00001")
    api.post(f"{API_V1_PREFIX}/jobs/{created.json()['id']}/cancel",
             headers=_auth(token))
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 200
