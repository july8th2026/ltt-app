"""H31.3A — paired Upscale diagnostic và dataset privacy gate."""
from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image


def _pattern(size: int = 64) -> Image.Image:
    x = np.arange(size, dtype=np.uint8)
    grid_x, grid_y = np.meshgrid(x, x)
    array = np.stack((grid_x, grid_y, (grid_x ^ grid_y)), axis=2)
    return Image.fromarray(array, "RGB")


def test_dataset_manifest_is_versioned_hashed_and_requires_consent():
    from apps.qualitylab.datasets import validate_manifest

    valid = validate_manifest({
        "schema_version": 1, "app_slug": "upscalevideo",
        "dataset_version": "synthetic-v1",
        "items": [{
            "id": "sample-1", "reference_key": "quality-datasets/hr/1.png",
            "degraded_key": "quality-datasets/lr/1.png", "degradation": "bicubic",
            "license": "LTT synthetic", "owned_or_licensed": True,
            "production_data": False,
        }],
    })
    assert len(valid["manifest_sha256"]) == 64
    assert valid["items"][0]["consent_id"] == ""

    production = {**valid, "items": [{**valid["items"][0],
                                      "production_data": True,
                                      "consent_id": "", "retention_days": 0}]}
    production.pop("manifest_sha256", None)
    with pytest.raises(ValueError, match="consent"):
        validate_manifest(production)


def test_dataset_manifest_rejects_traversal_and_unlicensed_sample():
    from apps.qualitylab.datasets import validate_manifest

    base = {"schema_version": 1, "app_slug": "upscalevideo",
            "dataset_version": "v1"}
    with pytest.raises(ValueError, match="license"):
        validate_manifest({**base, "items": [{
            "id": "x", "reference_key": "hr.png", "degraded_key": "lr.png",
            "degradation": "blur", "license": "", "owned_or_licensed": False}]})
    with pytest.raises(ValueError, match="reference_key"):
        validate_manifest({**base, "items": [{
            "id": "x", "reference_key": "../private.png", "degraded_key": "lr.png",
            "degradation": "blur", "license": "owned", "owned_or_licensed": True}]})


def test_paired_diagnostic_beats_bicubic_without_claiming_pass(tmp_path):
    from apps.qualitylab.services.upscale import inspect_upscale_pair

    reference = _pattern(64)
    low = reference.resize((16, 16), Image.Resampling.BICUBIC)
    reference_path, candidate_path, low_path = (
        tmp_path / "reference.png", tmp_path / "candidate.png", tmp_path / "low.png")
    reference.save(reference_path); reference.save(candidate_path); low.save(low_path)

    dimensions, summary = inspect_upscale_pair(candidate_path, reference_path, low_path)
    by_key = {dimension.key: dimension for dimension in dimensions}
    assert by_key["paired_contract"].verdict == "PASS"
    assert by_key["full_reference"].verdict == "UNKNOWN"
    assert by_key["baseline"].verdict == "UNKNOWN"
    assert summary["candidate"]["psnr_db"] > summary["bicubic"]["psnr_db"]
    delta = {metric.key: metric for metric in by_key["baseline"].metrics}
    assert delta["psnr_delta_vs_bicubic"].value > 0
    assert delta["psnr_delta_vs_bicubic"].verdict == "UNKNOWN"


def test_paired_diagnostic_fails_dimension_mismatch(tmp_path):
    from apps.qualitylab.services.upscale import inspect_upscale_pair

    reference, candidate = tmp_path / "reference.png", tmp_path / "candidate.png"
    _pattern(64).save(reference); _pattern(32).save(candidate)
    dimensions, summary = inspect_upscale_pair(candidate, reference)
    assert dimensions[0].verdict == "FAIL"
    assert summary["candidate_shape"] != summary["reference_shape"]


def test_paired_job_hashes_all_inputs_and_cleans_ephemeral(tmp_path):
    from apps.qualitylab import jobs
    from platform_core.storage import LocalStorage, set_storage

    storage = LocalStorage(str(tmp_path / "storage")); set_storage(storage)
    reference = _pattern(64); low = reference.resize((16, 16), Image.Resampling.BICUBIC)
    keys = {
        "candidate": "qualitylab/u/ephemeral/candidate.png",
        "reference": "qualitylab/u/ephemeral/reference.png",
        "low": "qualitylab/u/ephemeral/low.png",
    }
    for role, image in (("candidate", reference), ("reference", reference), ("low", low)):
        stream = io.BytesIO(); image.save(stream, "PNG"); stream.seek(0)
        storage.put(keys[role], stream, "image/png")
    result = jobs.handle({
        "pack": "upscale_paired_diagnostic",
        "source_key": keys["candidate"], "source_name": "candidate.png",
        "reference_key": keys["reference"], "low_input_key": keys["low"],
        "ephemeral_keys": list(keys.values()),
    })
    artifact = result["report"]["source_artifact"]
    assert result["overall_verdict"] == "UNKNOWN"
    assert len(artifact["sha256"]) == 64
    assert len(artifact["reference_sha256"]) == 64
    assert len(artifact["low_input_sha256"]) == 64
    assert all(not storage.exists(key) for key in keys.values())


def test_quality_lab_ui_exposes_paired_inputs_without_release_claim():
    from pathlib import Path

    page = Path("apps/qualitylab/templates/qualitylab.html").read_text(encoding="utf-8")
    registry = Path("apps/qualitylab/registry.py").read_text(encoding="utf-8")
    # Upload đi qua macro dùng chung `o_chon_tep(id, name, ...)` (Golden UI) —
    # tên trường gửi lên là đối số thứ hai, không còn `name="..."` trần.
    assert '"ql-reference", "reference_file"' in page
    assert '"ql-low", "low_input_file"' in page
    assert "upscale_paired_diagnostic" in registry
    assert "chưa human-calibrated" in registry


def test_noncommercial_evaluators_are_explicitly_blocked():
    from apps.qualitylab.registry import EVALUATORS

    assert EVALUATORS["lpips"].enabled is False
    assert EVALUATORS["lpips"].status == "candidate"
    assert EVALUATORS["lpips"].license == "BSD-2-Clause"
    assert EVALUATORS["lpips"].model_sha256 == ""
    assert EVALUATORS["pyiqa"].enabled is False
    assert EVALUATORS["pyiqa"].status == "blocked"
    assert EVALUATORS["pyiqa"].license == "PolyForm Noncommercial 1.0.0"
    assert "BLOCKED" in EVALUATORS["pyiqa"].note
    assert EVALUATORS["dover_mobile"].enabled is False
    assert EVALUATORS["dover_mobile"].status == "blocked"
    assert EVALUATORS["dover_mobile"].license == "S-Lab License 1.0"
    assert "BLOCKED" in EVALUATORS["dover_mobile"].note
