"""H31.3d2a — materializer phải kiểm chứng file và provenance trước khi copy."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest
from PIL import Image

SLICES = ("face", "text", "nature", "animation", "low-light", "motion")
DEGRADATIONS = ("bicubic", "blur", "noise", "compression", "mixed")
SPLITS = ("development", "calibration", "blind-regression")


def _image(path, color):
    Image.new("RGB", (24, 18), color).save(path)


def _intake_item(**overrides):
    item = {
        "id": "image-001",
        "reference_source": "reference.png",
        "degraded_source": "degraded.png",
        "degradation": "compression",
        "media_kind": "image",
        "split": "development",
        "slice": "text",
        "tags": ["synthetic", "test"],
        "license": "LTT synthetic fixture",
        "license_evidence_id": "fixture-generator-v1",
        "owned_or_licensed": True,
        "production_data": False,
    }
    item.update(overrides)
    return item


def _intake(item):
    return {
        "schema_version": 1,
        "app_slug": "upscalevideo",
        "dataset_version": "upscale-owned-v1",
        "items": [item],
    }


def test_materializer_probes_hashes_and_atomically_copies_without_source_paths(tmp_path):
    from apps.qualitylab.datasets import readiness_report
    from apps.qualitylab.materializer import materialize_dataset

    source = tmp_path / "source"
    source.mkdir()
    _image(source / "reference.png", "white")
    _image(source / "degraded.png", "gray")
    output = tmp_path / "dataset"
    manifest = materialize_dataset(_intake(_intake_item()), source, output)

    assert (output / "reference/image-001.png").is_file()
    assert (output / "degraded/image-001.png").is_file()
    on_disk = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk == manifest
    assert len(manifest["items"][0]["reference_sha256"]) == 64
    assert manifest["items"][0]["license_evidence_id"] == "fixture-generator-v1"
    assert "source" not in json.dumps(manifest)
    report = readiness_report(manifest)
    assert report["ready_for_human_calibration"] is False
    assert report["release_gate_eligible"] is False


def test_materializer_rejects_missing_license_evidence_and_source_escape(tmp_path):
    from apps.qualitylab.materializer import inspect_intake

    source = tmp_path / "source"
    source.mkdir()
    _image(source / "reference.png", "white")
    _image(source / "degraded.png", "gray")
    with pytest.raises(ValueError, match="license_evidence_id"):
        inspect_intake(_intake(_intake_item(license_evidence_id="")), source)
    with pytest.raises(ValueError, match="đường dẫn tương đối"):
        inspect_intake(_intake(_intake_item(reference_source="../outside.png")), source)


def test_materializer_rejects_fake_image_and_existing_destination(tmp_path):
    from apps.qualitylab.materializer import materialize_dataset

    source = tmp_path / "source"
    source.mkdir()
    (source / "reference.png").write_bytes(b"not-an-image")
    _image(source / "degraded.png", "gray")
    with pytest.raises(ValueError, match="không giải mã"):
        materialize_dataset(_intake(_intake_item()), source, tmp_path / "dataset")

    _image(source / "reference.png", "white")
    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(ValueError, match="ghi đè"):
        materialize_dataset(_intake(_intake_item()), source, destination)


def test_readiness_requires_real_counts_slices_degradations_splits_hash_and_license():
    from apps.qualitylab.datasets import readiness_report

    items = []
    for index in range(42):
        kind = "image" if index < 30 else "video"
        suffix = "png" if kind == "image" else "mp4"
        items.append({
            "id": f"{kind}-{index:03d}",
            "reference_key": f"reference/{kind}-{index:03d}.{suffix}",
            "degraded_key": f"degraded/{kind}-{index:03d}.{suffix}",
            "reference_sha256": "a" * 64,
            "degraded_sha256": "b" * 64,
            "degradation": DEGRADATIONS[index % len(DEGRADATIONS)],
            "media_kind": kind,
            "split": SPLITS[index % len(SPLITS)],
            "slice": SLICES[index % len(SLICES)],
            "license": "LTT owned fixture",
            "license_evidence_id": f"evidence-{index:03d}",
            "owned_or_licensed": True,
            "production_data": False,
        })
    result = readiness_report({
        "schema_version": 1,
        "app_slug": "upscalevideo",
        "dataset_version": "complete-v1",
        "items": items,
    })
    assert result["item_counts"] == {"image": 30, "video": 12}
    assert result["ready_for_human_calibration"] is True
    assert result["readiness_reasons"] == []
    assert result["release_gate_eligible"] is False


def test_dataset_cli_inspect_outputs_only_safe_coverage(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    _image(source / "reference.png", "white")
    _image(source / "degraded.png", "gray")
    intake = tmp_path / "intake.json"
    intake.write_text(json.dumps(_intake(_intake_item())), encoding="utf-8")
    result = subprocess.run([
        sys.executable, "tools/qualitylab_dataset.py", "inspect",
        "--intake", str(intake), "--source-root", str(source),
    ], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["item_count"] == 1
    assert payload["ready_for_human_calibration"] is False
    assert "reference.png" not in result.stdout
    assert str(source) not in result.stdout
