"""Regression cho benchmark/capability gate UP-FEAT-001."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "benchmark_upscale_ai_detail", ROOT / "tools" / "benchmark_upscale_ai_detail.py")
assert SPEC and SPEC.loader
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)


def test_degradation_matrix_is_deterministic_and_distinct():
    array = np.tile(np.arange(64, dtype=np.uint8), (64, 1))
    source = Image.fromarray(np.stack((array, array, array), axis=2), "RGB")
    bicubic = np.asarray(BENCH._degrade(source, "bicubic", 1))
    blur = np.asarray(BENCH._degrade(source, "blur", 1))
    noise_a = np.asarray(BENCH._degrade(source, "noise", 20260803))
    noise_b = np.asarray(BENCH._degrade(source, "noise", 20260803))
    assert bicubic.shape == (16, 16, 3)
    assert not np.array_equal(bicubic, blur)
    assert not np.array_equal(bicubic, noise_a)
    assert np.array_equal(noise_a, noise_b)


def test_wdn_presence_does_not_fake_adjustable_denoise_feature():
    gates = BENCH._feature_gates([
        "realesr-general-x4v3", "realesr-general-wdn-x4v3", "realesrgan-x4plus"])
    assert gates["ai_detail"]["status"] == "DEFER"
    assert gates["denoise"]["status"] == "DEFER"
    assert "no adjustable -dn/DNI control" in gates["denoise"]["reason"]
    assert gates["deblur"]["status"] == "DEFER"


def test_benchmark_inventory_requires_complete_model_pair(tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    (models / "realesr-general-x4v3.param").write_text("p", encoding="ascii")
    assert BENCH._installed_models(tmp_path) == []
    (models / "realesr-general-x4v3.bin").write_bytes(b"b")
    assert BENCH._installed_models(tmp_path) == ["realesr-general-x4v3"]
