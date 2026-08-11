"""Hợp đồng dataset Quality Lab; chỉ lưu key/metadata, không nhét media vào JSON."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from platform_core.i18n import N_

MAX_ITEMS = 500
ALLOWED_DEGRADATIONS = {"bicubic", "blur", "noise", "compression", "mixed"}
ALLOWED_MEDIA_KINDS = {"image", "video"}
ALLOWED_SPLITS = {"development", "calibration", "blind-regression"}
REQUIRED_SLICES = {"face", "text", "nature", "animation", "low-light", "motion"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAMPLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def _safe_key(value: object, label: str) -> str:
    key = str(value or "").replace("\\", "/").strip("/")
    if not key or ".." in key.split("/") or ":" in key:
        raise ValueError(N_(f"{label} không hợp lệ."))
    return key


def _safe_sha256(value: object, label: str) -> str:
    digest = str(value or "").lower().strip()
    if digest and not _SHA256.fullmatch(digest):
        raise ValueError(N_(f"{label} phải là SHA-256 hợp lệ."))
    return digest


def _safe_tags(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 12:
        raise ValueError(N_("tags phải là list tối đa 12 mục."))
    tags: list[str] = []
    for raw in value:
        tag = str(raw or "").strip().lower()
        if not tag or len(tag) > 40 or tag in tags:
            raise ValueError(N_("tag rỗng, trùng hoặc quá dài."))
        tags.append(tag)
    return tags


def _safe_sample_id(value: object) -> str:
    sample_id = str(value or "").strip()
    if not _SAMPLE_ID.fullmatch(sample_id):
        raise ValueError(N_("Sample id chỉ được gồm chữ, số, dấu chấm, gạch ngang hoặc gạch dưới."))
    return sample_id


def validate_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != 1:
        raise ValueError(N_("Dataset manifest phải dùng schema_version=1."))
    if payload.get("app_slug") != "upscalevideo":
        raise ValueError(N_("Dataset này không thuộc pack Upscale."))
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= MAX_ITEMS:
        raise ValueError(N_("Dataset phải có từ 1 đến 500 sample."))
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError(N_("Sample dataset phải là object."))
        sample_id = _safe_sample_id(raw.get("id"))
        if sample_id in seen:
            raise ValueError(N_("Sample id rỗng hoặc bị trùng."))
        seen.add(sample_id)
        degradation = str(raw.get("degradation") or "")
        if degradation not in ALLOWED_DEGRADATIONS:
            raise ValueError(N_("Kiểu degradation chưa được hỗ trợ."))
        license_name = str(raw.get("license") or "").strip()
        license_evidence_id = str(raw.get("license_evidence_id") or "").strip()
        if not license_name or not bool(raw.get("owned_or_licensed")):
            raise ValueError(N_("Sample chưa có bằng chứng sở hữu/license."))
        production = bool(raw.get("production_data"))
        consent_id = str(raw.get("consent_id") or "").strip()
        retention_days = int(raw.get("retention_days") or 0)
        if production and (not consent_id or retention_days <= 0):
            raise ValueError(N_("Dữ liệu production thiếu consent hoặc retention."))
        media_kind = str(raw.get("media_kind") or "image")
        if media_kind not in ALLOWED_MEDIA_KINDS:
            raise ValueError(N_("media_kind chưa được hỗ trợ."))
        split = str(raw.get("split") or "development")
        if split not in ALLOWED_SPLITS:
            raise ValueError(N_("Dataset split chưa được hỗ trợ."))
        items.append({
            "id": sample_id,
            "reference_key": _safe_key(raw.get("reference_key"), "reference_key"),
            "degraded_key": _safe_key(raw.get("degraded_key"), "degraded_key"),
            "degradation": degradation,
            "media_kind": media_kind,
            "split": split,
            "slice": str(raw.get("slice") or "general")[:80],
            "tags": _safe_tags(raw.get("tags")),
            "reference_sha256": _safe_sha256(
                raw.get("reference_sha256"), "reference_sha256"),
            "degraded_sha256": _safe_sha256(
                raw.get("degraded_sha256"), "degraded_sha256"),
            "license": license_name[:160],
            "license_evidence_id": license_evidence_id[:160],
            "owned_or_licensed": True,
            "production_data": production,
            "consent_id": consent_id[:160] if production else "",
            "retention_days": retention_days if production else 0,
        })
    normalized = {
        "schema_version": 1,
        "app_slug": "upscalevideo",
        "dataset_version": str(payload.get("dataset_version") or "").strip()[:80],
        "items": items,
    }
    if not normalized["dataset_version"]:
        raise ValueError(N_("Thiếu dataset_version."))
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    normalized["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return normalized


def readiness_report(payload: dict[str, Any]) -> dict[str, Any]:
    """Kiểm tra độ phủ MVP; không biến độ phủ thành release verdict."""
    manifest = validate_manifest(payload)
    items = manifest["items"]
    kinds = {kind: sum(item["media_kind"] == kind for item in items)
             for kind in sorted(ALLOWED_MEDIA_KINDS)}
    slices = {item["slice"] for item in items}
    degradations = {item["degradation"] for item in items}
    splits = {item["split"] for item in items}
    reasons: list[str] = []
    if kinds["image"] < 30:
        reasons.append("image_items<30")
    if kinds["video"] < 12:
        reasons.append("video_items<12")
    reasons.extend(f"missing_slice:{value}" for value in sorted(REQUIRED_SLICES - slices))
    reasons.extend(f"missing_degradation:{value}"
                   for value in sorted(ALLOWED_DEGRADATIONS - degradations))
    reasons.extend(f"missing_split:{value}" for value in sorted(ALLOWED_SPLITS - splits))
    if any(not item["reference_sha256"] or not item["degraded_sha256"] for item in items):
        reasons.append("artifact_hash_missing")
    if any(not item["license_evidence_id"] for item in items):
        reasons.append("license_evidence_missing")
    return {
        "dataset_version": manifest["dataset_version"],
        "manifest_sha256": manifest["manifest_sha256"],
        "item_counts": kinds,
        "missing_slices": sorted(REQUIRED_SLICES - slices),
        "missing_degradations": sorted(ALLOWED_DEGRADATIONS - degradations),
        "missing_splits": sorted(ALLOWED_SPLITS - splits),
        "ready_for_human_calibration": not reasons,
        "readiness_reasons": reasons,
        "release_gate_eligible": False,
    }
