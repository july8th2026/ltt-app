"""P1: ToolSpec chỉ là metadata additive quanh app/job hiện hữu."""
from __future__ import annotations

import pytest

from platform_core.agent.tools import discover_tools, resolve_params_schema
from platform_core.registry import AppManifest, LoadedApp, RegistryError, ToolSpec, _validate


def _tool(**overrides):
    values = dict(
        name="image.generate",
        job_type="x.run",
        description="Sinh ảnh từ mô tả.",
        params_schema={"prompt": {"type": "string", "required": True}},
        returns={"image": "image"},
    )
    values.update(overrides)
    return ToolSpec(**values)


def _manifest(*tools):
    return AppManifest(
        slug="x", display_name="X", route_prefix="/x",
        job_types=("x.run",), credit_cost=lambda _params: 1, tools=tools,
    )


def _loaded(manifest):
    return LoadedApp(manifest=manifest)


def test_manifest_cu_khong_tools_van_hop_le():
    manifest = AppManifest(slug="x", display_name="X", route_prefix="/x")
    _validate(manifest, set(), set(), set(), set())
    assert manifest.tools == ()


def test_discover_tools_gom_metadata_manifest():
    tool = _tool()
    assert discover_tools(apps=[_loaded(_manifest(tool))]) == {tool.name: tool}


def test_trung_tool_name_bi_chan_som():
    with pytest.raises(RegistryError, match="tool name trùng"):
        _validate(_manifest(_tool(), _tool()), set(), set(), set(), set())


def test_job_type_khong_thuoc_app_bi_chan():
    with pytest.raises(RegistryError, match="job_type không thuộc app"):
        _validate(_manifest(_tool(job_type="other.run")), set(), set(), set(), set())


@pytest.mark.parametrize("schema", [
    {},
    {"x": {"type": "mystery"}},
    {"x": {"type": "enum", "source": "prompts/../../secret"}},
])
def test_schema_rong_kieu_la_va_source_path_traversal_bi_chan(schema):
    with pytest.raises(RegistryError):
        _validate(_manifest(_tool(params_schema=schema)), set(), set(), set(), set())


def test_depends_on_phai_tro_toi_model_ref():
    tool = _tool(params_schema={
        "model": {"type": "string"},
        "resolution": {"type": "enum", "depends_on": "model", "field": "resolutions"},
    })
    with pytest.raises(RegistryError, match="model_ref"):
        _validate(_manifest(tool), set(), set(), set(), set())


def test_resolve_enum_prompt_doc_dung_labels(tmp_path, monkeypatch):
    prompts = tmp_path / "x" / "prompts" / "style"
    prompts.mkdir(parents=True)
    (prompts / "_labels.json").write_text(
        '{"cinematic":"Điện ảnh","clean":"Tối giản"}', encoding="utf-8")
    tool = _tool(params_schema={
        "style": {"type": "enum", "source": "prompts/style"},
    })
    monkeypatch.setattr("platform_core.agent.tools.APPS_DIR", tmp_path)
    schema = resolve_params_schema(tool.name, apps=[_loaded(_manifest(tool))])
    assert schema["style"]["values"] == ["cinematic", "clean"]
    assert schema["style"]["options"][0]["label"] == "Điện ảnh"


def test_resolve_depends_on_model_capability():
    tool = _tool(params_schema={
        "model": {"type": "model_ref", "category": "video"},
        "resolution": {"type": "enum", "depends_on": "model", "field": "resolutions"},
    })
    schema = resolve_params_schema(
        tool.name, {"model": "mini"}, apps=[_loaded(_manifest(tool))],
        model_lookup=lambda model: {"resolutions": ("480p", "720p")} if model == "mini" else {},
    )
    assert schema["resolution"]["values"] == ["480p", "720p"]


def test_resolve_khong_lam_bien_doi_manifest():
    tool = _tool(params_schema={
        "model": {"type": "model_ref", "category": "video"},
        "resolution": {"type": "enum", "depends_on": "model", "field": "resolutions"},
    })
    resolve_params_schema(
        tool.name, {"model": "m"}, apps=[_loaded(_manifest(tool))],
        model_lookup=lambda _model: {"resolutions": ["720p"]},
    )
    assert "values" not in tool.params_schema["resolution"]
