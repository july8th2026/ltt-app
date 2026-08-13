"""Q92 — Public API kernel: mounting, kill switches, error contract, inventory.

These tests hold four properties that are cheap to break later:

1. the surface is **off** unless an operator turns it on, and turning it on does
   not move any existing route;
2. every failure on ``/api/v1`` is problem+json with a request id — including
   the ones no handler was written for;
3. the read-only switch stops writes without touching reads or the UI;
4. no route exists on ``/api/v1`` that is not in the declared inventory.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api.config import (DEFAULT_MAX_BODY_BYTES,
                                             MAX_MAX_BODY_BYTES,
                                             load_public_api_config)
from platform_core.public_api.errors import (ApiError, ApiProblem,
                                             GENERIC_INTERNAL_DETAIL,
                                             PROBLEM_CONTENT_TYPE,
                                             problem_for_status, scrub_detail)
from platform_core.public_api.pagination import (MAX_PAGE_LIMIT, Page, PageRequest)
from server.api.inventory import API_V1_PREFIX, declared_paths, documented_paths

BASE_ENV = {
    "LTT_ENV": "local-server-test",
    "LTT_SESSION_SECRET": "public-api-kernel-secret",
    "LTT_ADMIN_USERNAME": "",
    "LTT_ADMIN_PASSWORD_HASH": "",
}


def _app(**overrides):
    from server.app import create_app

    return create_app(env={**BASE_ENV, **overrides})


def _app_with_api(**overrides):
    """Build the platform app and hand back the mounted public sub-app.

    Tests that need a throwaway endpoint must add it to the sub-application:
    a route on the parent would not be part of the public surface at all, so it
    would prove nothing about the guards this surface applies.
    """
    app = _app(LTT_PUBLIC_API="1", **overrides)
    for route in app.routes:
        if getattr(route, "name", "") == "public_api":
            return app, route.app
    raise AssertionError("public API sub-application was not mounted")


@pytest.fixture()
def enabled_client():
    with TestClient(_app(LTT_PUBLIC_API="1")) as client:
        yield client


# ── Configuration and kill switches ───────────────────────────────────────────

def test_public_api_is_disabled_by_default():
    config = load_public_api_config({})
    assert config.enabled is False
    assert config.read_only is False
    assert config.exposed_tools == frozenset()
    assert config.writes_allowed() is False


def test_no_tool_is_exposed_without_an_explicit_allowlist():
    config = load_public_api_config({"LTT_PUBLIC_API": "1"})
    assert config.tool_exposed("image.thumbnail") is False

    config = load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "image.thumbnail, video.generate"})
    assert config.tool_exposed("image.thumbnail") is True
    assert config.tool_exposed("video.generate") is True
    assert config.tool_exposed("video.social_import") is False


def test_body_limit_is_clamped_and_survives_garbage():
    assert load_public_api_config({}).max_body_bytes == DEFAULT_MAX_BODY_BYTES
    huge = load_public_api_config({"LTT_PUBLIC_API_MAX_BODY_BYTES": "999999999999"})
    assert huge.max_body_bytes == MAX_MAX_BODY_BYTES
    junk = load_public_api_config({"LTT_PUBLIC_API_MAX_BODY_BYTES": "abc"})
    assert junk.max_body_bytes == DEFAULT_MAX_BODY_BYTES


def test_disabled_api_serves_no_routes_but_still_answers_json():
    with TestClient(_app()) as client:
        response = client.get(f"{API_V1_PREFIX}/health")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_CONTENT_TYPE)
    assert response.json()["code"] == "not_found"


def test_enabling_the_api_does_not_move_existing_ui_routes():
    with TestClient(_app()) as off, TestClient(_app(LTT_PUBLIC_API="1")) as on:
        for path in ("/health/ready", "/login", "/"):
            before = off.get(path, follow_redirects=False)
            after = on.get(path, follow_redirects=False)
            assert before.status_code == after.status_code, path
            assert before.headers.get("content-type") == after.headers.get("content-type")


# ── Kernel endpoints ──────────────────────────────────────────────────────────

def test_health_and_capabilities_expose_nothing_internal(enabled_client):
    health = enabled_client.get(f"{API_V1_PREFIX}/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "api_version": "v1"}
    assert health.headers["cache-control"] == "no-store"

    capabilities = enabled_client.get(f"{API_V1_PREFIX}/capabilities")
    assert capabilities.status_code == 200
    body = capabilities.json()
    assert body["api_version"] == "v1" and body["read_only"] is False
    # Feature areas of the version, never the deployment's published tool list
    # and never the kernel's own endpoints.
    assert body["capabilities"] == ["tools", "quotes", "jobs", "uploads",
                                    "artifacts", "webhooks", "credits", "usage"]
    assert not {"health", "me", "capabilities"} & set(body["capabilities"])
    body = capabilities.text.lower()
    for leak in ("gemini", "seedance", "postgres", "r2", "c:\\", "/data/", "secret"):
        assert leak not in body


def test_every_api_response_carries_a_correlation_id(enabled_client):
    ok = enabled_client.get(f"{API_V1_PREFIX}/health")
    missing = enabled_client.get(f"{API_V1_PREFIX}/nope")
    assert ok.headers["x-correlation-id"]
    assert missing.json()["request_id"] == missing.headers["x-correlation-id"]


# ── Error contract ────────────────────────────────────────────────────────────

def test_unknown_api_path_is_problem_json(enabled_client):
    response = enabled_client.get(f"{API_V1_PREFIX}/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_CONTENT_TYPE)
    body = response.json()
    assert body["type"] == "/errors/not_found"
    assert body["status"] == 404 and body["code"] == "not_found"
    assert body["instance"] == f"{API_V1_PREFIX}/does-not-exist"


def test_wrong_method_is_problem_json(enabled_client):
    response = enabled_client.post(f"{API_V1_PREFIX}/health")
    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"


def test_app_nested_api_keeps_the_q88_contract():
    """The Q88 shape must not change just because a new surface exists."""
    from fastapi import APIRouter, HTTPException

    app = _app(LTT_PUBLIC_API="1")
    router = APIRouter()

    @router.get("/sample/api/fail")
    def sample_fail():
        raise HTTPException(status_code=422, detail="actionable")

    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/sample/api/fail")
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert "problem" not in response.headers["content-type"]
    assert response.json()["detail"] == "actionable"


def test_unhandled_exception_never_leaks_internals():
    app, api = _app_with_api()

    @api.get("/boom-for-test")
    def boom():
        raise RuntimeError("secret-token-abc123 at C:\\LTTPlatform\\secrets\\app.env")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"{API_V1_PREFIX}/boom-for-test")
    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == GENERIC_INTERNAL_DETAIL
    assert "secret-token-abc123" not in response.text
    assert "Traceback" not in response.text
    assert "LTTPlatform" not in response.text


def test_validation_detail_drops_input_and_ctx():
    problem = ApiProblem(status=422, code="unprocessable_request", detail=[
        {"type": "value_error", "msg": "bad", "loc": ("body", "prompt"),
         "input": {"prompt": "customer content"}, "ctx": {"error": ValueError("x")}},
    ])
    entry = problem.to_dict()["detail"][0]
    assert "input" not in entry and "ctx" not in entry
    assert entry["msg"] == "bad"


def test_server_side_errors_never_echo_their_cause():
    problem = problem_for_status(500, "psycopg2: password=hunter2")
    assert problem.to_dict()["detail"] == GENERIC_INTERNAL_DETAIL


def test_scrub_detail_is_shared_with_the_q88_handler():
    from server.app import _json_error_detail

    payload = [{"msg": "x", "input": {"a": 1}, "ctx": {"e": ValueError("y")}}]
    assert _json_error_detail(payload) == scrub_detail(payload) == [{"msg": "x"}]


# ── Read-only kill switch ─────────────────────────────────────────────────────

def test_read_only_mode_stops_writes_and_leaves_reads_and_ui_alone():
    app, api = _app_with_api(LTT_PUBLIC_API_READ_ONLY="1")

    @api.post("/write-for-test")
    def write():  # pragma: no cover - must never execute in read-only mode
        return {"written": True}

    with TestClient(app) as client:
        read = client.get(f"{API_V1_PREFIX}/health")
        write_attempt = client.post(f"{API_V1_PREFIX}/write-for-test", json={})
        ui = client.get("/login")
    assert read.status_code == 200
    assert write_attempt.status_code == 503
    assert write_attempt.json()["code"] == "read_only"
    assert write_attempt.headers["x-correlation-id"]
    assert ui.status_code == 200
    assert ui.headers["content-type"].startswith("text/html")


def test_capabilities_reports_read_only_state():
    with TestClient(_app(LTT_PUBLIC_API="1", LTT_PUBLIC_API_READ_ONLY="1")) as client:
        assert client.get(f"{API_V1_PREFIX}/capabilities").json()["read_only"] is True


# ── Body limit ────────────────────────────────────────────────────────────────

def test_oversized_declared_body_is_refused_before_it_is_read():
    app, api = _app_with_api(LTT_PUBLIC_API_MAX_BODY_BYTES="1024")

    @api.post("/echo-for-test")
    def echo():  # pragma: no cover - the guard rejects before the handler
        return {"ok": True}

    with TestClient(app) as client:
        response = client.post(f"{API_V1_PREFIX}/echo-for-test",
                               content=b"x" * 4096,
                               headers={"content-type": "application/json"})
    assert response.status_code == 413
    body = response.json()
    assert body["code"] == "payload_too_large"
    assert body["limit_bytes"] == 1024


# ── Principal placeholder ─────────────────────────────────────────────────────

def test_principal_resolution_is_deny_all_with_no_resolver_installed():
    """Fail-closed default. Prompt 04 installs the database-backed resolver."""
    from server.api import deps

    class _Request:
        headers = {"authorization": "Bearer whatever"}

    previous = deps.current_resolver()
    deps.set_principal_resolver(None)
    try:
        with pytest.raises(ApiError) as raised:
            deps.resolve_principal(_Request(), None)
        assert raised.value.status == 401
    finally:
        deps.set_principal_resolver(previous)


def test_principal_never_reads_the_browser_session():
    """A logged-in browser must not be able to spend credit through the API."""
    from server.api import deps

    captured = {}

    class _Session(dict):
        def __getitem__(self, key):  # pragma: no cover - must not be called
            captured["read"] = key
            return super().__getitem__(key)

    class _Request:
        headers = {}
        session = _Session({"sid": "browser-session"})

    previous = deps.current_resolver()
    deps.set_principal_resolver(lambda request, db: None)
    try:
        with pytest.raises(ApiError):
            deps.resolve_principal(_Request(), None)
    finally:
        deps.set_principal_resolver(previous)
    assert captured == {}
    assert deps.bearer_token(_Request()) == ""


def test_bearer_token_parsing_is_case_insensitive_and_trims():
    from server.api import deps

    class _Request:
        headers = {"authorization": "bearer   abc.def  "}

    assert deps.bearer_token(_Request()) == "abc.def"


# ── Trusted proxy / client IP ─────────────────────────────────────────────────

def test_forwarding_headers_are_only_believed_from_a_trusted_peer():
    from server.api.context import client_ip

    class _Client:
        def __init__(self, host):
            self.host = host

    class _Request:
        def __init__(self, host, headers):
            self.client = _Client(host)
            self.headers = headers

    trusted = ("127.0.0.1", "::1")
    spoofed = _Request("203.0.113.9", {"cf-connecting-ip": "1.2.3.4",
                                       "x-forwarded-for": "5.6.7.8"})
    assert client_ip(spoofed, trusted) == "203.0.113.9"

    tunnelled = _Request("127.0.0.1", {"cf-connecting-ip": "1.2.3.4"})
    assert client_ip(tunnelled, trusted) == "1.2.3.4"

    no_header = _Request("127.0.0.1", {})
    assert client_ip(no_header, trusted) == "127.0.0.1"

    assert client_ip(tunnelled, ()) == "127.0.0.1"


# ── Pagination primitives ─────────────────────────────────────────────────────

def test_pagination_has_a_hard_ceiling_and_rejects_nonsense():
    assert PageRequest.parse().limit == 20
    assert PageRequest.parse(limit=100000).limit == MAX_PAGE_LIMIT
    assert PageRequest.parse(limit="5", offset="10") == PageRequest(limit=5, offset=10)
    for bad in ({"limit": "-1"}, {"limit": "0"}, {"limit": "abc"},
                {"offset": "-3"}, {"offset": 10_000_000}):
        with pytest.raises(ApiError):
            PageRequest.parse(**bad)


def test_page_uses_one_extra_row_to_report_has_more():
    request = PageRequest(limit=2, offset=4)
    assert request.fetch_limit == 3
    full = Page.of([1, 2, 3], request).to_dict()
    assert full["items"] == [1, 2]
    assert full["page"] == {"limit": 2, "offset": 4, "has_more": True, "next_offset": 6}
    last = Page.of([1], request).to_dict()
    assert last["items"] == [1] and last["page"]["has_more"] is False
    assert "next_offset" not in last["page"]


# ── Route inventory ───────────────────────────────────────────────────────────

def test_mounted_routes_match_the_declared_inventory_exactly():
    from server.api import public_api_routes

    _app_instance, api = _app_with_api()
    assert public_api_routes(api) == declared_paths()


def test_public_openapi_lists_only_declared_public_routes(enabled_client):
    document = enabled_client.get(f"{API_V1_PREFIX}/openapi.json").json()
    # Paths in the document are relative to the mount; the prefix is carried in
    # `servers`, which is what a generated client concatenates.
    base = document["servers"][0]["url"]
    assert base == API_V1_PREFIX
    published = {(method.upper(), f"{base}{path}")
                 for path, operations in document["paths"].items()
                 for method in operations}
    assert published == documented_paths()


def test_public_openapi_does_not_describe_the_control_plane(enabled_client):
    document = enabled_client.get(f"{API_V1_PREFIX}/openapi.json").text
    for internal in ("/login", "/admin", "/health/ready", "/taovideo", "/agent"):
        assert internal not in document
