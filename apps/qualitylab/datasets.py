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
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


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
        sample_id = str(raw.get("id") or "").strip()
        if not sample_id or sample_id in seen:
            raise ValueError(N_("Sample id rỗng hoặc bị trùng."))
        seen.add(sample_id)
        degradation = str(raw.get("degradation") or "")
        if degradation not in ALLOWED_DEGRADATIONS:
            raise ValueError(N_("Kiểu degradation chưa được hỗ trợ."))
        license_name = str(raw.get("license") or "").strip()
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
