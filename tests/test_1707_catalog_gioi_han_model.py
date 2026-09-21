"""Catalog model phải đủ dữ liệu để client từ chối sớm request chắc chắn sai."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.ltt_llm.manifest import MANIFEST
from apps.ltt_llm.ngan_sach import ANH_BYTE_TOI_DA, SO_ANH_TOI_DA
from platform_core.public_api.config import load_public_api_config
from server.api import tools as api_tools


def _catalog_models(monkeypatch) -> dict:
    monkeypatch.setattr(api_tools, "require_scope", lambda _scope: lambda: None)
    app = FastAPI()
    config = load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "text.chat"}
    )
    api_tools.register_tool_routes(app, config, "catalog-test")
    with TestClient(app) as client:
        response = client.get("/models")
    assert response.status_code == 200, response.text
    return response.json()


def test_hai_shape_models_cong_bo_cung_mot_bo_gioi_han_tu_manifest(monkeypatch):
    body = _catalog_models(monkeypatch)
    items = {item["name"]: item for item in body["items"]}
    codex = {item["slug"]: item for item in body["models"]}
    source = MANIFEST.tools[0].api_contract["models"]

    assert set(items) == set(codex) == set(source)
    keys = {
        "max_input_tokens",
        "max_output_tokens",
        "context_window",
        "max_images",
        "max_image_bytes",
        "input_modalities",
        "accepted_image_schemes",
    }
    for name, spec in source.items():
        manifest = spec["constraints"]
        published = items[name]["constraints"]
        projected = codex[name]
        assert keys <= published.keys()
        assert {key: published[key] for key in keys} == {
            key: projected[key] for key in keys
        }
        assert published["context_window"] == manifest["context_window"]
        assert published["max_input_tokens"] == manifest["context_window"]
        assert published["max_output_tokens"] == manifest["max_output_tokens"]
        assert published["max_images"] == manifest["max_images"]
        assert published["max_image_bytes"] == manifest["max_image_bytes"]
        assert published["input_modalities"] == ["text", "image"]
        assert published["accepted_image_schemes"] == ["data"]


def test_model_text_cong_bo_khong_nhan_anh():
    model = SimpleNamespace(
        name="vision-nhung-text-only-fixture",
        description="Text only.",
        constraints={
            "context_window": 8_192,
            "max_output_tokens": 1_024,
            "reads_images": False,
        },
    )
    published = api_tools._dang_codex(model)
    assert published["max_input_tokens"] == 8_192
    assert published["input_modalities"] == ["text"]
    assert published["max_images"] == 0
    assert published["max_image_bytes"] == 0
    assert published["accepted_image_schemes"] == []


def test_phep_chieu_khong_go_tay_tran_anh():
    source = Path(api_tools.__file__).read_text(encoding="utf-8")
    assert f'"max_images": {SO_ANH_TOI_DA}' not in source
    assert f'"max_image_bytes": {ANH_BYTE_TOI_DA}' not in source


def test_khong_gan_tran_token_gia_vao_model_khong_phai_llm():
    class ImageModel:
        name = "image-fixture"
        description = "Image model."
        constraints = {"max_reference_images": 1}

        def to_public_dict(self):
            return {"name": self.name, "constraints": dict(self.constraints)}

    assert api_tools._dang_cong_khai(ImageModel())["constraints"] == {
        "max_reference_images": 1
    }
