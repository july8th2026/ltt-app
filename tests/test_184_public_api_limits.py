"""Q92 / Prompt 08 — rate, quota, concurrency, capacity.

The property that matters most here is **isolation**: one abusive key must not
degrade anyone else. Everything else in this file is a specific way that could
fail — a shared bucket, a limit keyed by an address every caller shares behind
the tunnel, or an unbounded queue.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.models import CREDIT_HOLD, CreditEntry
from platform_core.public_api import keys as devkeys, limits
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.errors import ApiError
from platform_core.public_api.principal import Principal
from platform_core.public_api.scopes import (SCOPE_JOBS_CANCEL,
                                             SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
                                             SCOPE_TOOLS_READ)
from platform_core.registry import AppManifest, LoadedApp, ToolSpec
from server.api.inventory import API_V1_PREFIX

PEPPER = "limits-test-pepper-" + "u" * 40
TOOL = "text.limited"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_JOBS_CANCEL)


def _cost(params: dict) -> int:
    return 5


def _fixture_apps():
    tool = ToolSpec(
        name=TOOL, job_type="samplelim.generate", description="Fixture tool.",
        params_schema={"prompt": {"type": "string", "required": True,
                                  "max_length": 100}},
        returns={"text": "text"}, api_exposed=True,
        api_contract={"scopes": (SCOPE_JOBS_CREATE,)})
    manifest = AppManifest(
        slug="samplelim", display_name="Sample", route_prefix="/samplelim",
        job_types=("samplelim.generate",), credit_cost=_cost,
        lifecycle="released", surface="customer", tools=(tool,))
    gpu_manifest = AppManifest(
        slug="samplegpu", display_name="Sample GPU", route_prefix="/samplegpu",
        job_types=("samplegpu.render",), credit_cost=_cost, requires=("gpu",),
        lifecycle="released", surface="customer")
    return [LoadedApp(manifest=manifest, router=None, error=""),
            LoadedApp(manifest=gpu_manifest, router=None, error="")]


@pytest.fixture()
def make_api(tmp_path, monkeypatch):
    """Builds a client with configurable limits; resets counters per test."""
    import platform_core.registry as registry_mod
    monkeypatch.setattr(registry_mod, "discover", _fixture_apps)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'limits.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    clients = []

    def _build(**overrides):
        app = create_app(env={
            "LTT_ENV": "local-server-test",
            "LTT_SESSION_SECRET": "limits-secret-value",
            "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
            "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
            "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL, **overrides,
        })
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        return client

    try:
        yield _build
    finally:
        for client in clients:
            client.__exit__(None, None, None)
        from server.api import deps
        deps.set_principal_resolver(None)
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


def _account(credits: int = 1000):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"l-{uuid.uuid4().hex[:8]}@example.com",
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


def _create_job(api, token, idem):
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": {"prompt": "x"}},
                     headers=_auth(token))
    if quote.status_code != 200:
        return quote
    return api.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "quote": quote.json()["quote"],
                          "input": {"prompt": "x"}},
                    headers=_auth(token, idem))


# ── Configuration ─────────────────────────────────────────────────────────────

def test_limits_have_production_safe_defaults():
    config = load_public_api_config({})
    assert config.request_rpm == 120 and config.create_rpm == 20
    assert config.max_active_jobs == 5
    # A credit ceiling is a product decision, so it is off until someone sets it.
    assert config.daily_credit_limit == 0
    assert config.auth_failure_limit == 20


def test_class_concurrency_parsing_ignores_junk():
    config = load_public_api_config(
        {"LTT_PUBLIC_API_CLASS_CONCURRENCY": "gpu:2, ffmpeg:x , :3, api:0"})
    assert config.class_concurrency == {"gpu": 2, "api": 0}


def test_resource_class_comes_from_the_manifest_not_a_name():
    apps = {item.manifest.slug: item.manifest for item in _fixture_apps()}
    assert limits.resource_class(apps["samplegpu"]) == "gpu"
    assert limits.resource_class(apps["samplelim"]) == "api"


# ── Layer 1: authentication failures ──────────────────────────────────────────

def test_repeated_bad_credentials_are_throttled(make_api):
    api = make_api(LTT_PUBLIC_API_AUTH_FAILURES="3")
    bad = _auth("ltt_sk_" + "a" * 32 + "_" + "b" * 43)
    codes = [api.get(f"{API_V1_PREFIX}/me", headers=bad).status_code
             for _ in range(5)]
    assert codes[:3] == [401, 401, 401]
    assert 429 in codes
    assert limits.metrics().get("auth_failure_throttled")


def test_a_throttled_prober_does_not_lock_out_a_real_key(make_api):
    """Isolation: the failure counter must not become a global outage."""
    api = make_api(LTT_PUBLIC_API_AUTH_FAILURES="2")
    _user_id, good = _account()
    bad = _auth("ltt_sk_" + "c" * 32 + "_" + "d" * 43)
    for _ in range(4):
        api.get(f"{API_V1_PREFIX}/me", headers=bad)
    assert api.get(f"{API_V1_PREFIX}/me",
                   headers=_auth(good)).status_code == 200


# ── Layers 2 and 3: request and create rate ───────────────────────────────────

def test_one_key_exhausts_only_its_own_request_budget(make_api):
    api = make_api(LTT_PUBLIC_API_RPM="3")
    _noisy_id, noisy = _account()
    _quiet_id, quiet = _account()

    codes = [api.get(f"{API_V1_PREFIX}/me", headers=_auth(noisy)).status_code
             for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[-1] == 429

    # The well-behaved key is untouched — this is the acceptance criterion.
    assert api.get(f"{API_V1_PREFIX}/me", headers=_auth(quiet)).status_code == 200


def test_a_rate_limited_response_says_when_to_retry(make_api):
    api = make_api(LTT_PUBLIC_API_RPM="1")
    _user_id, token = _account()
    api.get(f"{API_V1_PREFIX}/me", headers=_auth(token))
    limited = api.get(f"{API_V1_PREFIX}/me", headers=_auth(token))
    assert limited.status_code == 429
    body = limited.json()
    assert body["code"] == "rate_limited"
    assert 1 <= body["retry_after"] <= 60
    assert limited.headers["content-type"].startswith("application/problem+json")


def test_creates_are_rationed_separately_from_reads(make_api):
    api = make_api(LTT_PUBLIC_API_CREATE_RPM="1", LTT_PUBLIC_API_RPM="100")
    user_id, token = _account()

    assert _create_job(api, token, "create-budget-one-01").status_code == 201
    blocked = _create_job(api, token, "create-budget-two-02")
    assert blocked.status_code == 429 and blocked.json()["code"] == "rate_limited"

    # Reads still work: the two budgets are independent.
    assert api.get(f"{API_V1_PREFIX}/jobs", headers=_auth(token)).status_code == 200
    # And the refused create charged nothing.
    gen, db = _session()
    try:
        holds = db.query(CreditEntry).filter(
            CreditEntry.user_id == user_id,
            CreditEntry.kind == CREDIT_HOLD).count()
        assert holds == 1
    finally:
        _close(gen)


def test_rate_limits_cannot_be_dodged_by_changing_endpoint(make_api):
    """The budget follows the key, not the path."""
    api = make_api(LTT_PUBLIC_API_RPM="2")
    _user_id, token = _account()
    assert api.get(f"{API_V1_PREFIX}/me", headers=_auth(token)).status_code == 200
    assert api.get(f"{API_V1_PREFIX}/tools", headers=_auth(token)).status_code == 200
    assert api.get(f"{API_V1_PREFIX}/jobs",
                   headers=_auth(token)).status_code == 429


def test_a_second_key_does_not_dodge_the_account_s_concurrency_cap(make_api):
    """Rotating or adding a key is not a way around the limit.

    Renamed at EXT-14. It used to be called "two keys each get their own request
    budget", and that premise was the hole the policy engine closed: an account
    wanting five times the rate just made five keys. Rates are now charged to
    the account as well as the key (see `test_206_policy_engine.py`), so the RPM
    here is raised out of the way — this test is about the *concurrency* cap,
    which was always per account, and the low RPM was incidental to it.
    """
    api = make_api(LTT_PUBLIC_API_RPM="100", LTT_PUBLIC_API_MAX_ACTIVE_JOBS="1")
    user_id, first = _account()
    gen, db = _session()
    try:
        _key, second = devkeys.issue(db, user_id=user_id, scopes=ALL_SCOPES,
                                     env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
    finally:
        _close(gen)

    assert _create_job(api, first, "first-key-job-0001").status_code == 201
    blocked = _create_job(api, second, "second-key-job-002")
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "concurrency_limited"


# ── Layer 4: concurrency and capacity ─────────────────────────────────────────

def test_active_jobs_are_capped_per_account(make_api):
    api = make_api(LTT_PUBLIC_API_MAX_ACTIVE_JOBS="2")
    user_id, token = _account()
    assert _create_job(api, token, "active-job-one-0001").status_code == 201
    assert _create_job(api, token, "active-job-two-0002").status_code == 201

    third = _create_job(api, token, "active-job-three-03")
    assert third.status_code == 429
    body = third.json()
    assert body["code"] == "concurrency_limited"
    assert body["active_jobs"] == 2 and body["limit"] == 2
    assert body["retry_after"] >= 1

    # Finishing one frees a slot — backpressure, not a permanent wall.
    from platform_core import credit, jobs as jobq
    from platform_core.models import Job

    gen, db = _session()
    try:
        job = db.query(Job).filter(Job.user_id == user_id).first()
        jobq.complete(db, job, {"text": "done"})
        credit.quyet_toan(db, user_id, job.id, 5)
        db.commit()
    finally:
        _close(gen)
    assert _create_job(api, token, "active-job-four-004").status_code == 201


def test_a_capacity_limited_create_never_holds_credit(make_api):
    api = make_api(LTT_PUBLIC_API_MAX_ACTIVE_JOBS="1")
    user_id, token = _account()
    _create_job(api, token, "capacity-first-0001")
    assert _create_job(api, token, "capacity-second-002").status_code == 429

    gen, db = _session()
    try:
        holds = db.query(CreditEntry).filter(
            CreditEntry.user_id == user_id,
            CreditEntry.kind == CREDIT_HOLD).count()
        assert holds == 1
    finally:
        _close(gen)


# ── Layer 5: daily credit ceiling ─────────────────────────────────────────────

def test_the_daily_credit_ceiling_stops_spending_before_the_hold(make_api):
    api = make_api(LTT_PUBLIC_API_DAILY_CREDIT="12",
                   LTT_PUBLIC_API_MAX_ACTIVE_JOBS="0")
    user_id, token = _account()
    assert _create_job(api, token, "ceiling-job-one-001").status_code == 201
    assert _create_job(api, token, "ceiling-job-two-002").status_code == 201

    stopped = _create_job(api, token, "ceiling-job-three-3")
    assert stopped.status_code == 429
    body = stopped.json()
    assert body["code"] == "quota_exceeded"
    assert body["spent_credit"] == 10 and body["limit"] == 12

    gen, db = _session()
    try:
        holds = db.query(CreditEntry).filter(
            CreditEntry.user_id == user_id,
            CreditEntry.kind == CREDIT_HOLD).count()
        assert holds == 2
    finally:
        _close(gen)


def test_a_refunded_job_gives_its_budget_back(make_api):
    api = make_api(LTT_PUBLIC_API_DAILY_CREDIT="10",
                   LTT_PUBLIC_API_MAX_ACTIVE_JOBS="0")
    user_id, token = _account()
    first = _create_job(api, token, "refund-budget-one-1")
    assert first.status_code == 201
    assert _create_job(api, token, "refund-budget-two-2").status_code == 201
    assert _create_job(api, token, "refund-budget-tre-3").status_code == 429

    api.post(f"{API_V1_PREFIX}/jobs/{first.json()['id']}/cancel",
             headers=_auth(token))
    # The cancelled job's credit came back, so the ceiling has room again.
    assert _create_job(api, token, "refund-budget-fou-4").status_code == 201


# ── Unit level ────────────────────────────────────────────────────────────────

def test_the_window_slides_rather_than_resetting_on_a_boundary():
    limits.reset()
    config = load_public_api_config({"LTT_PUBLIC_API_RPM": "2"})
    principal_key = "k" * 32
    limits.enforce_request_rate(key_id=principal_key, config=config)
    limits.enforce_request_rate(key_id=principal_key, config=config)
    with pytest.raises(ApiError) as raised:
        limits.enforce_request_rate(key_id=principal_key, config=config)
    assert raised.value.status == 429
    assert raised.value.extra["retry_after"] >= 1


def test_a_zero_limit_means_unlimited():
    limits.reset()
    config = load_public_api_config({"LTT_PUBLIC_API_RPM": "0"})
    for _ in range(50):
        limits.enforce_request_rate(key_id="unlimited", config=config)


def test_metrics_count_what_tripped():
    limits.reset()
    config = load_public_api_config({"LTT_PUBLIC_API_RPM": "1"})
    limits.enforce_request_rate(key_id="metric-key", config=config)
    with pytest.raises(ApiError):
        limits.enforce_request_rate(key_id="metric-key", config=config)
    assert limits.metrics()["request_rate_limited"] == 1


def test_the_ui_limiter_no_longer_keys_api_traffic_by_a_shared_address():
    """R3 from Prompt 01: behind the tunnel every peer is loopback."""
    from server.usage_rate_limit import _EXEMPT_PREFIXES

    assert "/api/v1" in _EXEMPT_PREFIXES


def test_provider_allocator_limits_are_a_different_layer():
    """`api_keys.rpm_limit` is the platform-to-provider budget, not a customer's."""
    from platform_core.models import ApiKey

    assert hasattr(ApiKey, "rpm_limit") and hasattr(ApiKey, "tpm_limit")
    config = load_public_api_config({"LTT_PUBLIC_API_RPM": "7"})
    assert config.request_rpm == 7
    assert not hasattr(config, "tpm_limit")
