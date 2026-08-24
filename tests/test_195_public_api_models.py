"""EXT-03 — discovery: models, capabilities, and the schema chain.

An external developer has to be able to answer "what can I buy, with which
model, under what limits" from the API alone. Everything they must *not* learn
on the way — which vendor is behind an alias, what the real model id is, which
pool serves it — is the other half of every test here.
"""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits
from platform_core.public_api.catalog import (STABILITIES, build_catalog,
                                              build_models, capabilities_of,
                                              contract_hash, project_tool,
                                              require_model, require_tool)
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.scopes import (SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
                                             SCOPE_TOOLS_READ)
from platform_core.registry import (AppManifest, LoadedApp, RegistryError,
                                    ToolSpec, discover)
from server.api.inventory import API_V1_PREFIX

PEPPER = "models-test-pepper-" + "m" * 40
TOOL = "image.fixture"
OTHER = "image.fixture_two"


def _cost(params: dict) -> int:
    return 5


def _tool(name: str = TOOL, **contract_extra) -> ToolSpec:
    return ToolSpec(
        name=name, job_type=f"samplemodels.{name.split('.')[-1]}",
        description="Fixture tool.",
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 100},
            "model": {"type": "model_ref", "category": "image"},
        },
        returns={"image": "image"}, api_exposed=True,
        api_contract={
            "scopes": (SCOPE_JOBS_CREATE,),
            "models": {
                "swift": {"id": "vendor-model-swift-9",
                          "description": "Fast and cheap.",
                          "constraints": {"max_reference_images": 1}},
                "fine": {"id": "vendor-model-fine-9",
                         "description": "Slower, more detail.",
                         "stability": "beta"},
            },
            **contract_extra,
        })


def _manifest(*tools) -> AppManifest:
    specs = tools or (_tool(),)
    return AppManifest(
        slug="samplemodels", display_name="Sample", route_prefix="/samplemodels",
        job_types=tuple(spec.job_type for spec in specs), credit_cost=_cost,
        lifecycle="released", surface="customer", tools=specs)


def _fixture_apps():
    return [LoadedApp(manifest=_manifest(), router=None, error="")]


def _config(**overrides):
    return load_public_api_config({"LTT_PUBLIC_API": "1",
                                   "LTT_PUBLIC_API_TOOLS": TOOL, **overrides})


@pytest.fixture()
def api(tmp_path, monkeypatch):
    import platform_core.registry as registry_mod
    monkeypatch.setattr(registry_mod, "discover", _fixture_apps)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'models.db').as_posix()}")
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
        "LTT_SESSION_SECRET": "models-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL,
    })
    with TestClient(app) as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    limits.reset()
    dbmod.reset_engine()


def _token(scopes=(SCOPE_TOOLS_READ, SCOPE_JOBS_READ), allowed_tools=()):
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=f"m-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        _key, token = devkeys.issue(db, user_id=user.id, scopes=scopes,
                                    allowed_tools=allowed_tools,
                                    env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        return token
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── The model catalog ────────────────────────────────────────────────────────

def test_models_are_aggregated_from_the_tools_that_accept_them():
    catalog = build_catalog(_config(), apps=_fixture_apps())
    models = build_models(catalog)
    assert [model.name for model in models] == ["fine", "swift"]
    swift = require_model(models, "swift")
    assert swift.capability == "image"
    assert swift.tools == (TOOL,)
    assert swift.constraints == {"max_reference_images": 1}
    assert swift.stability == "stable"
    assert require_model(models, "fine").stability == "beta"


def test_a_model_used_by_two_tools_lists_both():
    apps = [LoadedApp(manifest=_manifest(_tool(), _tool(OTHER)), router=None,
                      error="")]
    catalog = build_catalog(_config(LTT_PUBLIC_API_TOOLS=f"{TOOL},{OTHER}"),
                            apps=apps)
    models = build_models(catalog)
    assert require_model(models, "swift").tools == (TOOL, OTHER)


def test_the_model_catalog_never_leaks_the_real_model_id_or_a_vendor():
    catalog = build_catalog(_config(), apps=_fixture_apps())
    document = json.dumps(
        {"models": [model.to_public_dict() for model in build_models(catalog)],
         "tools": [tool.to_public_dict() for tool in catalog]},
        ensure_ascii=False)
    for secret in ("vendor-model-swift-9", "vendor-model-fine-9", "samplemodels",
                   "samplemodels.fixture"):
        assert secret not in document, secret


#: Cụm được phép: `openai` ở đây là **tên một định dạng dây**, không phải nhà cung
#: cấp model ta bán lại. `text.chat` cố ý tương thích dây OpenAI — đó là **tính
#: năng bán cho khách**, và giấu nó đi làm tài liệu tệ hơn mà không bảo vệ gì
#: (ta không bán lại OpenAI).
#:
#: ⛔ Nhưng KHÔNG miễn trừ cả chuỗi. Chỉ bóc đúng những cụm dưới đây rồi mới dò —
#:    nên `openai` đứng một mình, hay đứng như một model/alias, VẪN đỏ.
#:    Lý lẽ đầy đủ ở `test_187::test_openai_may_be_NAMED_AS_A_FORMAT_but_never_AS_A_MODEL`.
CUM_DINH_DANG_DUOC_PHEP = ("openai format", "openai-compatible",
                           "openai compatible", "openai image_url")


def _boc_ten_dinh_dang(text: str) -> str:
    for cum in CUM_DINH_DANG_DUOC_PHEP:
        text = text.replace(cum, "<dinh-dang>")
    return text


def test_the_repository_catalog_leaks_no_vendor_name():
    """The same rule, against what this repository actually publishes."""
    everything = ",".join(sorted({
        tool.name for item in discover() if not item.error
        for tool in item.manifest.tools}))
    catalog = build_catalog(_config(LTT_PUBLIC_API_TOOLS=everything))
    document = json.dumps(
        {"models": [model.to_public_dict() for model in build_models(catalog)]},
        ensure_ascii=False).lower()
    # "stability" is a field name here, so the vendor is spelled the way the
    # company is — a leak detector that trips on its own schema gets deleted.
    document = _boc_ten_dinh_dang(document)
    for vendor in ("gemini", "openai", "byteplus", "google", "anthropic",
                   "stabilityai", "stability ai", "flash", "realesrgan",
                   "whisper"):
        assert vendor not in document, vendor


def test_a_model_alias_still_resolves_to_the_internal_id_internally():
    """The projection hides the id from callers, not from the invocation path."""
    catalog = build_catalog(_config(), apps=_fixture_apps())
    tool = require_tool(catalog, TOOL)
    assert tool.resolve_model("swift") == "vendor-model-swift-9"
    assert tool.resolve_model("nope") == ""
    assert tool.model_names() == ["fine", "swift"]


def test_capabilities_come_from_the_tool_names_themselves():
    catalog = build_catalog(_config(), apps=_fixture_apps())
    assert capabilities_of(catalog) == ["image"]
    assert require_tool(catalog, TOOL).capability == "image"


# ── Endpoints ────────────────────────────────────────────────────────────────

def test_listing_models_requires_the_catalog_scope(api):
    assert api.get(f"{API_V1_PREFIX}/models").status_code == 401
    denied = api.get(f"{API_V1_PREFIX}/models",
                     headers=_auth(_token(scopes=(SCOPE_JOBS_READ,))))
    assert denied.status_code == 403
    assert denied.json()["code"] == "missing_scope"


def test_the_models_endpoint_answers_with_aliases_and_capabilities(api):
    body = api.get(f"{API_V1_PREFIX}/models", headers=_auth(_token())).json()
    assert [entry["name"] for entry in body["items"]] == ["fine", "swift"]
    assert body["capabilities"] == ["image"]
    assert body["items"][1]["tools"] == [TOOL]
    # Price is deliberately absent: what a call costs depends on the whole
    # input, so a per-model number would be misleading. /quotes is the answer.
    assert "credit" not in body["items"][0] and "price" not in body["items"][0]


def test_one_model_can_be_fetched_and_an_unknown_one_is_a_flat_404(api):
    token = _token()
    found = api.get(f"{API_V1_PREFIX}/models/swift", headers=_auth(token))
    assert found.status_code == 200
    assert found.json()["stability"] in STABILITIES
    missing = api.get(f"{API_V1_PREFIX}/models/does-not-exist",
                      headers=_auth(token))
    assert missing.status_code == 404 and missing.json()["code"] == "not_found"


def test_models_can_be_filtered_by_capability(api):
    token = _token()
    hit = api.get(f"{API_V1_PREFIX}/models?capability=image",
                  headers=_auth(token)).json()
    assert len(hit["items"]) == 2
    miss = api.get(f"{API_V1_PREFIX}/models?capability=video",
                   headers=_auth(token)).json()
    assert miss["items"] == []


def test_a_restricted_key_sees_no_models_from_tools_it_cannot_call(api):
    """The model list is a projection of the *visible* catalog, not of the
    deployment: otherwise a narrowed key still learns the full menu."""
    token = _token(allowed_tools=("image.something-else",))
    body = api.get(f"{API_V1_PREFIX}/models", headers=_auth(token)).json()
    assert body["items"] == [] and body["capabilities"] == []


# ── Schema chain ─────────────────────────────────────────────────────────────

def _walk(schema: dict, path: str = "input"):
    """Yield (path, subschema) for the schema and every nested property."""
    yield path, schema
    for name, child in (schema.get("properties") or {}).items():
        yield from _walk(child, f"{path}.{name}")


def test_every_published_input_schema_is_well_formed_json_schema():
    everything = ",".join(sorted({
        tool.name for item in discover() if not item.error
        for tool in item.manifest.tools}))
    catalog = build_catalog(_config(LTT_PUBLIC_API_TOOLS=everything))
    allowed_types = {"object", "string", "integer", "number", "boolean",
                     "array", "artifact", "artifact[]"}
    for tool in catalog:
        schema = tool.input_schema
        assert schema["type"] == "object"
        # Unknown fields must be refused, not ignored: silently dropping a
        # misspelled parameter is how a caller pays for a job that did not do
        # what they asked.
        assert schema["additionalProperties"] is False, tool.name
        properties = schema.get("properties") or {}
        for name in schema.get("required", ()):
            assert name in properties, f"{tool.name}: required {name} not declared"
        for path, node in _walk(schema, tool.name):
            assert node.get("type") in allowed_types, f"{path}: {node.get('type')}"
            if "enum" in node:
                assert node["enum"], f"{path}: empty enum"
                assert len(set(map(str, node["enum"]))) == len(node["enum"])
        for name, node in (tool.output_schema.get("properties") or {}).items():
            assert node.get("type") in allowed_types, f"{tool.name}.{name}"


def test_every_model_ref_parameter_publishes_its_valid_values():
    """The acceptance criterion: no public model_ref without discoverable values."""
    for item in discover():
        if item.error:
            continue
        for tool in item.manifest.tools:
            if not tool.api_exposed:
                continue
            public = project_tool(item.manifest, tool)
            hidden = set((tool.api_contract or {}).get("hidden") or ())
            for param, schema in tool.params_schema.items():
                if schema.get("type") != "model_ref" or param in hidden:
                    continue
                published = public.input_schema["properties"][param]
                assert published["enum"], f"{public.name}.{param} has no values"
                assert published["enum"] == public.model_names()


def test_the_openapi_document_carries_every_tool_schema(api):
    document = api.get(f"{API_V1_PREFIX}/openapi.json").json()
    schemas = document["components"]["schemas"]
    assert f"Tool_{TOOL}_Input" in schemas
    assert f"Tool_{TOOL}_Output" in schemas
    catalog = build_catalog(_config(), apps=_fixture_apps())
    assert schemas[f"Tool_{TOOL}_Input"] == require_tool(catalog, TOOL).input_schema


def test_the_openapi_document_is_still_only_declared_routes(api):
    """Injecting schemas must not smuggle in a path."""
    from server.api.inventory import documented_paths

    document = api.get(f"{API_V1_PREFIX}/openapi.json").json()
    served = {(method.upper(), f"{API_V1_PREFIX}{path}")
              for path, methods in document["paths"].items()
              for method in methods}
    assert served == documented_paths()


# ── Contract hash ────────────────────────────────────────────────────────────

def test_the_contract_hash_covers_the_contract_and_not_itself():
    catalog = build_catalog(_config(), apps=_fixture_apps())
    body = require_tool(catalog, TOOL).to_public_dict()
    assert body["contract_hash"] == contract_hash(body)
    # Recomputing over the body *including* the hash would make it unverifiable.
    assert contract_hash(body) == contract_hash(
        {key: value for key, value in body.items() if key != "contract_hash"})


def test_the_contract_hash_changes_when_the_contract_does():
    catalog = build_catalog(_config(), apps=_fixture_apps())
    first = require_tool(catalog, TOOL).to_public_dict()["contract_hash"]

    changed = [LoadedApp(manifest=_manifest(_tool(description="…")),
                         router=None, error="")]
    second = require_tool(build_catalog(_config(), apps=changed),
                          TOOL).to_public_dict()["contract_hash"]
    assert first != second


def test_the_hash_a_caller_receives_is_the_hash_of_what_they_received(api):
    body = api.get(f"{API_V1_PREFIX}/tools/{TOOL}",
                   headers=_auth(_token())).json()
    assert body["contract_hash"] == contract_hash(body)


# ── Aliases and deprecation ──────────────────────────────────────────────────

def test_a_renamed_tool_still_answers_to_its_old_name():
    apps = [LoadedApp(manifest=_manifest(_tool(aliases=("image.old_name",))),
                      router=None, error="")]
    catalog = build_catalog(_config(), apps=apps)
    assert require_tool(catalog, "image.old_name").name == TOOL
    # …but the alias is not a second catalog entry.
    assert [tool.name for tool in catalog] == [TOOL]
    assert require_tool(catalog, TOOL).to_public_dict()["aliases"] == [
        "image.old_name"]


def test_an_alias_that_shadows_the_real_name_is_refused():
    from platform_core.registry import _validate_api_contract

    manifest = _manifest(_tool(aliases=(TOOL,)))
    with pytest.raises(RegistryError):
        _validate_api_contract(manifest, manifest.tools[0])


def test_a_deprecated_model_must_name_its_replacement():
    from platform_core.registry import _validate_api_contract

    tool = ToolSpec(
        name=TOOL, job_type="samplemodels.fixture", description="Fixture.",
        params_schema={"model": {"type": "model_ref"}}, returns={"image": "image"},
        api_exposed=True,
        api_contract={"scopes": (SCOPE_JOBS_CREATE,),
                      "models": {"old": {"id": "x", "stability": "deprecated"}}})
    manifest = _manifest(tool)
    with pytest.raises(RegistryError) as raised:
        _validate_api_contract(manifest, tool)
    assert "deprecated" in str(raised.value)


def test_a_replacement_must_be_a_model_that_exists():
    from platform_core.registry import _validate_api_contract

    tool = ToolSpec(
        name=TOOL, job_type="samplemodels.fixture", description="Fixture.",
        params_schema={"model": {"type": "model_ref"}}, returns={"image": "image"},
        api_exposed=True,
        api_contract={"scopes": (SCOPE_JOBS_CREATE,),
                      "models": {"old": {"id": "x", "stability": "deprecated",
                                         "replaced_by": "ghost"}}})
    manifest = _manifest(tool)
    with pytest.raises(RegistryError):
        _validate_api_contract(manifest, tool)


def test_a_model_alias_cannot_carry_an_undeclared_key():
    from platform_core.registry import _validate_api_contract

    tool = ToolSpec(
        name=TOOL, job_type="samplemodels.fixture", description="Fixture.",
        params_schema={"model": {"type": "model_ref"}}, returns={"image": "image"},
        api_exposed=True,
        api_contract={"scopes": (SCOPE_JOBS_CREATE,),
                      "models": {"one": {"id": "x", "provider": "acme"}}})
    manifest = _manifest(tool)
    with pytest.raises(RegistryError) as raised:
        _validate_api_contract(manifest, tool)
    # The point of the closed key set: `provider` must never become publishable
    # by somebody adding a field to a manifest.
    assert "provider" in str(raised.value)


def test_a_model_alias_without_an_internal_id_is_refused():
    from platform_core.registry import _validate_api_contract

    tool = ToolSpec(
        name=TOOL, job_type="samplemodels.fixture", description="Fixture.",
        params_schema={"model": {"type": "model_ref"}}, returns={"image": "image"},
        api_exposed=True,
        api_contract={"scopes": (SCOPE_JOBS_CREATE,),
                      "models": {"one": {"description": "no id"}}})
    manifest = _manifest(tool)
    with pytest.raises(RegistryError):
        _validate_api_contract(manifest, tool)


def test_the_repository_publishes_a_model_for_every_alias_it_advertises():
    """Live check: the deployment's own aliases all survive the projection."""
    everything = ",".join(sorted({
        tool.name for item in discover() if not item.error
        for tool in item.manifest.tools}))
    catalog = build_catalog(_config(LTT_PUBLIC_API_TOOLS=everything))
    models = {model.name for model in build_models(catalog)}
    for tool in catalog:
        assert set(tool.model_names()) <= models, tool.name
    # `image.generate` publishes these three. `pro` was closed on 2026-08-23 for a
    # commercial reason, not a technical one: its provider cost is 35.2 credits an
    # image while the platform charged 16 (taoanh) and 5 (thumbnail, flat price
    # regardless of model). See CHANGELOG.md and tests/test_261.
    assert {"standard", "standard-lite", "enhanced"} <= models
    assert "pro" not in models, "bac pro da dong — xem CHANGELOG 2026-08-23"
