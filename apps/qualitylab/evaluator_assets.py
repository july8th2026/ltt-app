"""Fail-closed verifier cho evaluator assets; tuyệt đối không tải mạng."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from platform_core.i18n import N_
from platform_core.runtime_paths import data_path

SCHEMA_VERSION = 1
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024 * 1024
LPIPS_REQUIRED_ROLES = {"linear_alex_v0.1", "backbone_alexnet"}
LPIPS_SOURCE = "https://github.com/richzhang/PerceptualSimilarity"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_filename(raw: object) -> str:
    value = str(raw or "").replace("\\", "/")
    path = Path(value)
    if not value or path.name != value or value in {".", ".."}:
        raise ValueError(N_("Tên evaluator artifact không hợp lệ."))
    return value


def verify_manifest(evaluator_key: str, root: Path | None = None) -> dict[str, Any]:
    """Verify manifest + bytes + SHA; trả reason an toàn, không trả local path."""
    key = str(evaluator_key or "").strip()
    if key != "lpips":
        return {"ready": False, "reason": "evaluator_not_provisionable", "artifacts": []}
    base = (root or Path(data_path("qualitylab", "models"))).resolve()
    evaluator_dir = (base / key).resolve()
    if evaluator_dir.parent != base:
        return {"ready": False, "reason": "unsafe_evaluator_path", "artifacts": []}
    manifest_path = evaluator_dir / "manifest.json"
    if not manifest_path.is_file():
        return {"ready": False, "reason": "manifest_missing", "artifacts": []}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(N_("Sai schema evaluator manifest."))
        if payload.get("evaluator") != key or payload.get("package_version") != "0.1.4":
            raise ValueError(N_("Evaluator hoặc package version không khớp registry."))
        if payload.get("source") != LPIPS_SOURCE or payload.get("license") != "BSD-2-Clause":
            raise ValueError(N_("Source hoặc license evaluator không khớp registry."))
        raw_artifacts = payload.get("artifacts")
        if not isinstance(raw_artifacts, list) or not raw_artifacts:
            raise ValueError(N_("Evaluator manifest không có artifact."))
        roles: set[str] = set()
        verified: list[dict[str, Any]] = []
        for raw in raw_artifacts:
            if not isinstance(raw, dict):
                raise ValueError(N_("Evaluator artifact phải là object."))
            role = str(raw.get("role") or "").strip()
            filename = _safe_filename(raw.get("filename"))
            expected_size = int(raw.get("bytes") or 0)
            expected_sha = str(raw.get("sha256") or "").lower()
            source_url = str(raw.get("source_url") or "").strip()
            artifact_license = str(raw.get("license") or "").strip()
            if (not role or role in roles or expected_size <= 0 or
                    expected_size > MAX_ARTIFACT_BYTES or len(expected_sha) != 64 or
                    not source_url.startswith("https://") or not artifact_license):
                raise ValueError(N_("Metadata evaluator artifact không hợp lệ."))
            artifact = (evaluator_dir / filename).resolve()
            if artifact.parent != evaluator_dir or not artifact.is_file():
                raise ValueError(N_("Thiếu evaluator artifact đã khai báo."))
            actual_size = artifact.stat().st_size
            if actual_size != expected_size or _sha256(artifact) != expected_sha:
                raise ValueError(N_("Evaluator artifact lệch bytes hoặc SHA-256."))
            roles.add(role)
            verified.append({"role": role, "bytes": actual_size, "sha256": expected_sha})
        if not LPIPS_REQUIRED_ROLES.issubset(roles):
            raise ValueError(N_("LPIPS thiếu linear weight hoặc AlexNet backbone."))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {"ready": False, "reason": type(exc).__name__, "artifacts": []}
    return {"ready": True, "reason": "verified", "artifacts": verified,
            "package_version": "0.1.4"}


def public_asset_status() -> dict[str, dict[str, Any]]:
    """Chỉ expose trạng thái/reason; không lộ đường dẫn máy hoặc filename."""
    result = verify_manifest("lpips")
    return {"lpips": {"ready": result["ready"], "reason": result["reason"],
                       "verified_artifacts": len(result["artifacts"])}}
