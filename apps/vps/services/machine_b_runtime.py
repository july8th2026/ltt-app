"""Strict read-only consumer for Machine B's versioned runtime artifacts.

The collector remains in LTT-VM-Promox. This module only verifies that a set of
published files belongs to one successful, fresh generation before exposing it
to VPS preflight.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARTIFACTS = {
    "inventory": "runtime-inventory.json",
    "health": "runtime-health.json",
    "capabilities": "runtime-capabilities.json",
    "collector": "runtime-collector-status.json",
}
SUPPORTED_SCHEMAS = {
    "inventory": "2.0.0",
    "health": "2.0.0",
    "capabilities": "2.0.0",
    "collector": "1.0.0",
}
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
_STATUS = {"healthy": "HEALTHY", "degraded": "DEGRADED", "critical": "CRITICAL"}


@dataclass(frozen=True)
class MachineBRuntimeEvidence:
    status: str
    reason: str = ""
    generated_at: datetime | None = None
    machine_health: str = "UNKNOWN"
    domains: dict[str, str] = field(default_factory=dict)
    inventory: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)


def _parse_time(raw: object) -> datetime:
    value = str(raw or "").strip()
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load(root: Path, name: str) -> dict[str, Any]:
    path = root / ARTIFACTS[name]
    resolved = path.resolve(strict=True)
    if resolved.parent != root.resolve(strict=True):
        raise ValueError(f"artifact escapes configured runtime directory: {name}")
    if resolved.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError(f"runtime artifact too large: {name}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"runtime artifact is not an object: {name}")
    return payload


def _unknown(reason: str, *, provenance: dict[str, Any] | None = None
             ) -> MachineBRuntimeEvidence:
    return MachineBRuntimeEvidence(
        "UNKNOWN", str(reason)[:300], provenance=dict(provenance or {}))


def read_machine_b_runtime(
    directory: str | Path,
    *,
    now: datetime | None = None,
    max_age_seconds: int = 300,
) -> MachineBRuntimeEvidence:
    """Read one coherent generation or return explicit UNKNOWN/STALE evidence."""
    root = Path(directory)
    try:
        docs = {name: _load(root, name) for name in ARTIFACTS}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _unknown(f"runtime artifact unavailable or malformed: {type(exc).__name__}")

    versions = {name: str(doc.get("schema_version") or "")
                for name, doc in docs.items()}
    unsupported = {name: version for name, version in versions.items()
                   if version != SUPPORTED_SCHEMAS[name]}
    provenance: dict[str, object] = {"schema_versions": versions}
    if unsupported:
        return _unknown(f"unsupported runtime schema: {unsupported}",
                        provenance=provenance)

    # A repository revision is usable evidence only when every artifact in the
    # atomic bundle carries the same value. A dev checkout HEAD or a collector
    # script digest is not a substitute for the deployed Machine B revision.
    source_revisions = [str(docs[name].get("source_revision") or "").lower()
                        for name in ARTIFACTS]
    present_revisions = [value for value in source_revisions if value]
    if present_revisions:
        if (len(present_revisions) != len(ARTIFACTS)
                or len(set(present_revisions)) != 1
                or not re.fullmatch(r"[0-9a-f]{7,64}", present_revisions[0])):
            return _unknown("runtime source revision is incomplete or inconsistent",
                            provenance=provenance)
        provenance["machine_b_sha"] = present_revisions[0]

    required = {
        "inventory": ("generated_at", "proxmox", "gateway", "public_mappings", "guests"),
        "health": ("generated_at", "status", "domains", "checks"),
        "capabilities": ("generated_at", "pve", "gateway", "wireguard"),
        "collector": ("result", "exit_code", "output_generation"),
    }
    for name, keys in required.items():
        missing = [key for key in keys if key not in docs[name]]
        if missing:
            return _unknown(f"runtime artifact {name} missing fields: {missing}",
                            provenance=provenance)

    shapes: dict[str, dict[str, type]] = {
        "inventory": {"proxmox": dict, "gateway": dict,
                      "public_mappings": list, "guests": list},
        "health": {"domains": dict, "checks": list},
        "capabilities": {"pve": dict, "gateway": dict, "wireguard": dict},
    }
    for name, fields in shapes.items():
        for field_name, expected in fields.items():
            if not isinstance(docs[name][field_name], expected):
                return _unknown(f"invalid runtime shape: {name}.{field_name}",
                                provenance=provenance)

    if str(docs["collector"].get("result")) != "success":
        return _unknown("collector result is not success", provenance=provenance)
    exit_code = docs["collector"].get("exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code != 0:
        return _unknown("collector exit code is not zero", provenance=provenance)

    try:
        generations = {
            _parse_time(docs[name].get("generated_at"))
            for name in ("inventory", "health", "capabilities")
        }
        output_generation = _parse_time(docs["collector"].get("output_generation"))
    except (TypeError, ValueError) as exc:
        return _unknown(f"invalid generation timestamp: {type(exc).__name__}",
                        provenance=provenance)
    generations.add(output_generation)
    if len(generations) != 1:
        return _unknown("runtime artifacts do not share one generation",
                        provenance=provenance)

    generated_at = next(iter(generations))
    current = _parse_time(now or datetime.now(timezone.utc))
    age = (current - generated_at).total_seconds()
    provenance["generated_at"] = generated_at.isoformat()
    provenance["collector_version"] = str(
        docs["inventory"].get("collector_version") or "")
    if age < -60:
        return _unknown("runtime generation is unexpectedly in the future",
                        provenance=provenance)
    if age > max_age_seconds:
        return MachineBRuntimeEvidence(
            "STALE", f"runtime generation is stale ({int(age)} seconds old)",
            generated_at=generated_at,
            machine_health=_STATUS.get(str(docs["health"].get("status")), "UNKNOWN"),
            domains={key: _STATUS.get(str(value), "UNKNOWN")
                     for key, value in dict(docs["health"].get("domains") or {}).items()},
            provenance=provenance,
        )

    domains = {key: _STATUS.get(str(value), "UNKNOWN")
               for key, value in dict(docs["health"].get("domains") or {}).items()}
    return MachineBRuntimeEvidence(
        "HEALTHY", generated_at=generated_at,
        machine_health=_STATUS.get(str(docs["health"].get("status")), "UNKNOWN"),
        domains=domains,
        inventory=dict(docs["inventory"]),
        capabilities=dict(docs["capabilities"]),
        provenance=provenance,
    )
