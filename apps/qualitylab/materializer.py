"""Materialize dataset được cấp quyền vào thư mục ngoài repo, theo kiểu fail-closed."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from apps.qualitylab.datasets import validate_manifest
from apps.qualitylab.services.media import inspect_media, kind_for_name
from platform_core.i18n import N_


def _source_path(root: Path, value: object, label: str) -> Path:
    raw = str(value or "").replace("\\", "/").strip()
    relative = Path(raw)
    if not raw or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(N_(f"{label} phải là đường dẫn tương đối an toàn."))
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(N_(f"{label} nằm ngoài source root.")) from exc
    if not resolved.is_file():
        raise ValueError(N_(f"{label} không tồn tại hoặc không phải file."))
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe(path: Path, expected_kind: str, label: str) -> dict[str, Any]:
    extension_kind = kind_for_name(path.name)
    if extension_kind != expected_kind:
        raise ValueError(N_(f"{label} có phần mở rộng không khớp media_kind."))
    actual_kind, dimensions, metadata = inspect_media(path, {})
    if actual_kind != expected_kind or any(item.verdict == "FAIL" for item in dimensions):
        raise ValueError(N_(f"{label} không giải mã được hoặc sai media_kind."))
    return metadata


def inspect_intake(payload: dict[str, Any], source_root: Path) -> dict[str, Any]:
    """Validate nguồn thật và dựng manifest deterministic nhưng chưa ghi file."""
    if payload.get("schema_version") != 1 or payload.get("app_slug") != "upscalevideo":
        raise ValueError(N_("Dataset intake phải dùng schema v1 cho Upscale."))
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError(N_("Dataset intake chưa có sample."))

    normalized_items: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError(N_("Sample intake phải là object."))
        evidence_id = str(raw.get("license_evidence_id") or "").strip()
        if not evidence_id:
            raise ValueError(N_("Sample thiếu license_evidence_id có thể kiểm toán."))
        media_kind = str(raw.get("media_kind") or "image")
        reference = _source_path(source_root, raw.get("reference_source"),
                                 "reference_source")
        degraded = _source_path(source_root, raw.get("degraded_source"),
                                "degraded_source")
        reference_metadata = _probe(reference, media_kind, "reference_source")
        degraded_metadata = _probe(degraded, media_kind, "degraded_source")
        sample_id = str(raw.get("id") or "").strip()
        reference_key = f"reference/{sample_id}{reference.suffix.lower()}"
        degraded_key = f"degraded/{sample_id}{degraded.suffix.lower()}"
        normalized_items.append({
            **raw,
            "reference_key": reference_key,
            "degraded_key": degraded_key,
            "reference_sha256": _sha256(reference),
            "degraded_sha256": _sha256(degraded),
        })
        probes.append({
            "id": sample_id,
            "reference_source": reference,
            "degraded_source": degraded,
            "reference_key": reference_key,
            "degraded_key": degraded_key,
            "reference_metadata": reference_metadata,
            "degraded_metadata": degraded_metadata,
        })
    manifest = validate_manifest({
        "schema_version": 1,
        "app_slug": "upscalevideo",
        "dataset_version": payload.get("dataset_version"),
        "items": normalized_items,
    })
    return {"manifest": manifest, "probes": probes}


def materialize_dataset(payload: dict[str, Any], source_root: Path,
                        output_root: Path) -> dict[str, Any]:
    """Copy atomically; không ghi đè dataset cũ và không giữ absolute path."""
    inspected = inspect_intake(payload, source_root)
    destination = output_root.resolve()
    if destination.exists():
        raise ValueError(N_("Output dataset đã tồn tại; không được ghi đè."))
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".qualitylab-stage-",
                                    dir=str(destination.parent)))
    try:
        for probe in inspected["probes"]:
            for source_label, key_label in (("reference_source", "reference_key"),
                                             ("degraded_source", "degraded_key")):
                target = staging / probe[key_label]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(probe[source_label], target)
        manifest_path = staging / "manifest.json"
        manifest_path.write_text(json.dumps(inspected["manifest"], ensure_ascii=False,
                                             sort_keys=True, indent=2) + "\n",
                                 encoding="utf-8")
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return inspected["manifest"]
