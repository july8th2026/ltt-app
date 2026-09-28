"""Catalog model phải đủ dữ liệu để client từ chối sớm request chắc chắn sai."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.ltt_llm.manifest import MANIFEST
from apps.ltt_llm.ngan_sach import (ANH_BYTE_TOI_DA, SO_ANH_TOI_DA,
                                    TOKEN_ANH_TOI_DA, TOKEN_ANH_TOI_THIEU)
from platform_core.llm.anh_token import (DIEM_ANH_MOI_TOKEN_CANH,
                                        TOKEN_DAU_VISION)
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
        # 28/09: `max_images` DA GO (C4). Bon so duoi day cho client TU TINH
        # duoc chi phi ngu canh cua tung anh - thu that su quyet dinh mot
        # anh co lot hay khong.
        "image_pixels_per_token",
        "min_image_tokens",
        "max_image_tokens",
        "image_token_markers",
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
        for k in ("image_pixels_per_token", "min_image_tokens",
                  "max_image_tokens", "image_token_markers"):
            assert published[k] == manifest[k], k
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
    for k in ("image_pixels_per_token", "min_image_tokens",
              "max_image_tokens", "image_token_markers"):
        assert published[k] == 0, k
    assert published["max_image_bytes"] == 0
    assert published["accepted_image_schemes"] == []


def test_phep_chieu_khong_go_tay_tran_anh():
    """Phep chieu phai DOC manifest, khong go lai con so nao.

    28/09: bo so kiem da doi theo `constraints`. `SO_ANH_TOI_DA` da go khoi
    manifest (C4) nhung GIU o day: neu ai go tay lai `"max_images": 4` vao phep
    chieu thi phep nay phai do, chu khong phai im lang cho qua.
    """
    source = Path(api_tools.__file__).read_text(encoding="utf-8")
    assert f'"max_images": {SO_ANH_TOI_DA}' not in source
    assert f'"max_image_bytes": {ANH_BYTE_TOI_DA}' not in source
    for so in (DIEM_ANH_MOI_TOKEN_CANH ** 2, TOKEN_ANH_TOI_THIEU,
               TOKEN_ANH_TOI_DA, TOKEN_DAU_VISION):
        assert f": {so}" not in source, (
            f"phep chieu go tay so {so} thay vi doc tu manifest")


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
