"""Q92 / Prompt 05 — public tool catalog, typed contracts, contract drift.

The expensive mistakes this file prevents:

* an internal or retired capability becoming callable because someone edited a
  manifest flag;
* a public contract that quietly republishes provider names, real model ids or
  internal prompt-library vocabulary;
* the published contract drifting from what the code serves, with nobody
  noticing until an integration breaks.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api.catalog import (app_may_be_public, build_catalog,
                                              project_tool, require_tool,
                                              visible_to)
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.errors import ApiError
from platform_core.public_api.principal import Principal
from platform_core.public_api.scopes import SCOPE_JOBS_CREATE, SCOPE_TOOLS_READ
from platform_core.registry import AppManifest, LoadedApp, RegistryError, ToolSpec, discover
from server.api.inventory import API_V1_PREFIX

GOLDEN = Path(__file__).parent / "golden" / "public_api_catalog_v1.json"


# ── Fixture manifests (never touch a real app's declaration) ──────────────────

def _tool(**overrides) -> ToolSpec:
    values = {
        "name": "image.sample",
        "job_type": "sample.generate",
        "description": "Sample tool.",
        "params_schema": {
            "prompt": {"type": "string", "required": True, "max_length": 4000},
            "model": {"type": "model_ref", "category": "image",
                      "providers": ["gemini"]},
            "style": {"type": "enum", "source": "prompts/phong_cach"},
            "aspect_ratio": {"type": "enum", "values": ["16:9", "1:1"],
                             "default": "16:9"},
            "count": {"type": "int", "min": 1, "max": 4, "default": 1},
            "image_key": {"type": "image", "required": False},
        },
        "returns": {"image_keys": "image[]", "prompt": "text"},
        "api_exposed": True,
        "api_contract": {
            "public_name": "image.sample",
            "models": {"standard": "gemini-2.5-flash-image",
                       "pro": "gemini-3-pro-image"},
            "enums": {"style": ["cinematic", "clean"]},
            "hidden": ("image_key",),
            "scopes": (SCOPE_JOBS_CREATE,),
        },
    }
    values.update(overrides)
    return ToolSpec(**values)


def _manifest(**overrides) -> AppManifest:
    values = {
        "slug": "sampleapp", "display_name": "Sample", "route_prefix": "/sample",
        "job_types": ("sample.generate",), "credit_cost": lambda params: 1,
        "lifecycle": "released", "surface": "customer", "tools": (_tool(),),
    }
    values.update(overrides)
    return AppManifest(**values)


def _loaded(manifest) -> list:
    return [LoadedApp(manifest=manifest, router=object(), error="")]


def _config(**env):
    return load_public_api_config({"LTT_PUBLIC_API": "1", **env})


# ── Gate 1: app disposition ───────────────────────────────────────────────────

@pytest.mark.parametrize("lifecycle", ["retired", "internal", "maintenance"])
def test_a_retired_internal_or_maintenance_app_is_never_public(lifecycle):
    manifest = _manifest(lifecycle=lifecycle)
    assert app_may_be_public(manifest) is False
    config = _config(LTT_PUBLIC_API_TOOLS="image.sample")
    assert build_catalog(config, _loaded(manifest)) == []


@pytest.mark.parametrize("surface", ["admin", "runtime"])
def test_an_admin_or_runtime_app_is_never_public(surface):
    manifest = _manifest(surface=surface)
    assert app_may_be_public(manifest) is False
    config = _config(LTT_PUBLIC_API_TOOLS="image.sample")
    assert build_catalog(config, _loaded(manifest)) == []


def test_a_failed_or_disabled_app_is_never_public():
    manifest = _manifest()
    assert app_may_be_public(manifest, error="ImportError: boom") is False
    assert app_may_be_public(_manifest(enabled=False)) is False


# ── Gate 2: the tool's own declaration ────────────────────────────────────────

def test_customer_visible_alone_does_not_publish_a_tool():
    """The exact trap Prompt 01 flagged: two different flags, two meanings."""
    quiet = _tool(customer_visible=True, api_exposed=False, api_contract={})
    manifest = _manifest(tools=(quiet,))
    config = _config(LTT_PUBLIC_API_TOOLS="image.sample")
    assert build_catalog(config, _loaded(manifest)) == []


def test_an_incomplete_public_contract_is_refused_at_load_time():
    """Fail-closed: refuse the manifest rather than publish a leaky contract."""
    from platform_core.registry import _validate

    def _load(tool):
        _validate(_manifest(tools=(tool,)), set(), set(), set(), set(), set())

    _load(_tool())      # the complete fixture is fine

    with pytest.raises(RegistryError, match="models"):
        _load(_tool(api_contract={**_tool().api_contract, "models": {}}))

    with pytest.raises(RegistryError, match="enums"):
        contract = dict(_tool().api_contract)
        contract.pop("enums")
        _load(_tool(api_contract=contract))

    with pytest.raises(RegistryError, match="scope"):
        _load(_tool(api_contract={**_tool().api_contract, "scopes": ("make:coffee",)}))

    with pytest.raises(RegistryError, match="public_name"):
        _load(_tool(api_contract={**_tool().api_contract, "public_name": "Nope!"}))

    with pytest.raises(RegistryError, match="khoá lạ"):
        _load(_tool(api_contract={**_tool().api_contract, "sneaky": True}))

    with pytest.raises(RegistryError, match="không tồn tại"):
        _load(_tool(api_contract={**_tool().api_contract, "hidden": ("nope",)}))

    with pytest.raises(RegistryError, match="api_exposed=False"):
        _load(_tool(api_exposed=False))


# ── Gate 3: the operator switch ───────────────────────────────────────────────

def test_a_tool_stays_private_until_an_operator_names_it():
    manifest = _manifest()
    assert build_catalog(_config(), _loaded(manifest)) == []
    published = build_catalog(_config(LTT_PUBLIC_API_TOOLS="image.sample"),
                              _loaded(manifest))
    assert [tool.name for tool in published] == ["image.sample"]


# ── Projection: what a customer is allowed to see ─────────────────────────────

def test_the_public_contract_hides_provider_and_internal_vocabulary():
    public = project_tool(_manifest(), _tool())
    document = json.dumps(public.to_public_dict())

    for leak in ("gemini", "gemini-2.5-flash-image", "prompts/phong_cach",
                 "sampleapp", "sample.generate", "model_ref"):
        assert leak not in document, leak

    # Model choice is published as aliases only.
    assert public.input_schema["properties"]["model"]["enum"] == ["pro", "standard"]
    assert public.resolve_model("standard") == "gemini-2.5-flash-image"
    assert public.resolve_model("gemini-2.5-flash-image") == ""


def test_source_backed_enums_publish_declared_values_only():
    public = project_tool(_manifest(), _tool())
    assert public.input_schema["properties"]["style"]["enum"] == ["cinematic", "clean"]
    assert public.input_schema["properties"]["aspect_ratio"]["enum"] == ["16:9", "1:1"]


def test_hidden_parameters_do_not_appear():
    public = project_tool(_manifest(), _tool())
    assert "image_key" not in public.input_schema["properties"]


def test_unknown_fields_are_rejected_not_ignored():
    """Silently dropping a misspelled parameter means paying for the wrong job."""
    public = project_tool(_manifest(), _tool())
    assert public.input_schema["additionalProperties"] is False
    assert public.input_schema["required"] == ["prompt"]


def test_outputs_are_described_as_artifacts_not_storage_keys():
    public = project_tool(_manifest(), _tool())
    assert public.output_schema["properties"]["image_keys"]["type"] == "artifact[]"
    assert public.output_schema["properties"]["prompt"]["type"] == "string"


def test_implementation_details_are_kept_but_never_published():
    public = project_tool(_manifest(), _tool())
    assert public.app_slug == "sampleapp" and public.job_type == "sample.generate"
    assert "app_slug" not in public.to_public_dict()
    assert "job_type" not in public.to_public_dict()


# ── Per-key narrowing and lookup ──────────────────────────────────────────────

def _principal(**overrides) -> Principal:
    values = {"key_id": "k" * 32, "user_id": "user-1",
              "scopes": frozenset({SCOPE_TOOLS_READ}),
              "allowed_tools": frozenset(), "request_id": "r"}
    values.update(overrides)
    return Principal(**values)


def test_a_key_allowlist_narrows_the_catalog():
    catalog = build_catalog(_config(LTT_PUBLIC_API_TOOLS="image.sample"),
                            _loaded(_manifest()))
    assert visible_to(catalog, _principal()) == catalog
    narrowed = _principal(allowed_tools=frozenset({"video.other"}))
    assert visible_to(catalog, narrowed) == []


def test_an_unavailable_tool_is_a_404_not_a_403():
    catalog = build_catalog(_config(LTT_PUBLIC_API_TOOLS="image.sample"),
                            _loaded(_manifest()))
    with pytest.raises(ApiError) as missing:
        require_tool(catalog, "video.social_import", _principal())
    assert missing.value.status == 404

    with pytest.raises(ApiError) as restricted:
        require_tool(catalog, "image.sample",
                     _principal(allowed_tools=frozenset({"other.tool"})))
    assert restricted.value.status == 403


# ── Live repository state ─────────────────────────────────────────────────────

def test_exposed_tools_match_the_published_contract(monkeypatch):
    """Contract drift guard.

    Wave prompts open tools deliberately, one at a time, and update the golden
    file in the same change. If this fails, somebody flipped `api_exposed`
    without publishing a contract for it — or removed one that customers may
    already be calling.
    """
    exposed = sorted(tool.name for item in discover() if not item.error
                     for tool in item.manifest.tools if tool.api_exposed)
    published = sorted(entry["name"]
                       for entry in json.loads(GOLDEN.read_text(encoding="utf-8"))["tools"])
    assert exposed == published


def test_catalog_matches_the_golden_contract_snapshot():
    everything = ",".join(sorted({
        tool.name for item in discover() if not item.error
        for tool in item.manifest.tools}))
    catalog = build_catalog(_config(LTT_PUBLIC_API_TOOLS=everything))
    snapshot = {"tools": [tool.to_public_dict() for tool in catalog]}
    assert snapshot == json.loads(GOLDEN.read_text(encoding="utf-8"))


# ── HTTP surface ──────────────────────────────────────────────────────────────

@pytest.fixture()
def api(tmp_path, monkeypatch):
    from platform_core.public_api import keys as devkeys

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'catalog.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, "catalog-test-pepper-" + "y" * 40)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "catalog-secret",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
    })
    try:
        with TestClient(app) as client:
            yield client
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        dbmod.reset_engine()


def _token(scopes=(SCOPE_TOOLS_READ,)) -> str:
    from platform_core.db import get_session
    from platform_core.public_api import keys as devkeys
    from platform_core.users import tao_nguoi_dung
    import uuid

    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=f"cat-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        _key, token = devkeys.issue(db, user_id=user.id, scopes=scopes)
        db.commit()
        return token
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_listing_tools_requires_a_key_and_the_right_scope(api):
    assert api.get(f"{API_V1_PREFIX}/tools").status_code == 401

    from platform_core.public_api.scopes import SCOPE_JOBS_READ
    wrong = _token(scopes=(SCOPE_JOBS_READ,))
    denied = api.get(f"{API_V1_PREFIX}/tools",
                     headers={"Authorization": f"Bearer {wrong}"})
    assert denied.status_code == 403
    assert denied.json()["code"] == "missing_scope"

    allowed = api.get(f"{API_V1_PREFIX}/tools",
                      headers={"Authorization": f"Bearer {_token()}"})
    assert allowed.status_code == 200
    body = allowed.json()
    # Nothing is exposed yet, and an empty catalog is a valid answer.
    assert body["items"] == []
    assert body["page"] == {"limit": 20, "offset": 0, "has_more": False}


def test_tool_listing_pagination_is_validated(api):
    headers = {"Authorization": f"Bearer {_token()}"}
    bad = api.get(f"{API_V1_PREFIX}/tools?limit=0", headers=headers)
    assert bad.status_code == 400 and bad.json()["code"] == "invalid_request"
    clamped = api.get(f"{API_V1_PREFIX}/tools?limit=100000", headers=headers)
    assert clamped.json()["page"]["limit"] == 100


def test_an_unpublished_tool_is_404_over_http(api):
    headers = {"Authorization": f"Bearer {_token()}"}
    response = api.get(f"{API_V1_PREFIX}/tools/video.social_import", headers=headers)
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert response.headers["content-type"].startswith("application/problem+json")


def test_public_openapi_documents_the_catalog_routes(api):
    document = api.get(f"{API_V1_PREFIX}/openapi.json").json()
    assert "/tools" in document["paths"]
    assert "/tools/{tool_name}" in document["paths"]
    # Still nothing internal.
    for internal in ("job_type", "app_slug", "gemini", "/taoanh"):
        assert internal not in json.dumps(document)
