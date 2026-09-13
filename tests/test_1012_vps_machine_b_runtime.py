"""VPS V4 P3 — strict, fail-closed consumer of Machine B runtime artifacts."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest


def _write_bundle(path, *, generated_at: str, health="healthy",
                  collector_result="success", output_generation=None,
                  inventory_version="2.0.0", source_revision=None):
    common = {"schema_version": "2.0.0", "generated_at": generated_at,
              "source": "test", "collector_version": "2.0.0"}
    if source_revision is not None:
        common["source_revision"] = source_revision
    inventory = {
        **common, "schema_version": inventory_version, "source": ["test"],
        "host": {}, "vmware": {},
        "proxmox": {"network": {}, "wireguard": {}},
        "gateway": {"reachable": True, "provider": "OVH", "host": "redacted"},
        "public_mappings": [], "orphan_mappings": [], "guests": [],
    }
    health_doc = {
        **common, "status": health,
        "domains": {"runtime": "healthy", "network": "healthy",
                    "storage": "healthy", "security": "healthy",
                    "data_protection": "critical"},
        "checks": [{"id": "runtime-test", "domain": "runtime",
                    "status": "pass", "value": 1, "unit": "bool",
                    "message": "ok"}],
    }
    capabilities = {
        **common, "pve": {"reachable": True, "version": "9.2.2"},
        "guests": {"count": 8}, "gateway": {"provider": "OVH", "reachable": True},
        **{key: {"supported": True, "configured": True, "verified": True}
           for key in ("nested_virtualization", "wireguard",
                       "per_guest_public_ipv4", "backup_outer", "restore_drill",
                       "qemu_guest_agent", "vm_firewall", "monitoring",
                       "dual_wan_pinned", "independent_backup", "pbs")},
    }
    collector = {
        "schema_version": "1.0.0", "last_attempt_at": generated_at,
        "started_at": generated_at, "result": collector_result,
        "exit_code": 0 if collector_result == "success" else 1,
        "error_category": "", "message": "ok",
        "output_generation": output_generation or generated_at,
    }
    if source_revision is not None:
        collector["source_revision"] = source_revision
    for name, payload in {
        "runtime-inventory.json": inventory,
        "runtime-health.json": health_doc,
        "runtime-capabilities.json": capabilities,
        "runtime-collector-status.json": collector,
    }.items():
        (path / name).write_text(json.dumps(payload), encoding="utf-8")


def test_coherent_fresh_bundle_is_healthy_even_when_backup_domain_is_critical(tmp_path):
    from apps.vps.services.machine_b_runtime import read_machine_b_runtime

    now = datetime.now(timezone.utc)
    _write_bundle(tmp_path, generated_at=now.isoformat(), health="critical")
    evidence = read_machine_b_runtime(tmp_path, now=now)
    assert evidence.status == "HEALTHY"
    assert evidence.machine_health == "CRITICAL"
    assert evidence.domains["network"] == "HEALTHY"
    assert evidence.domains["data_protection"] == "CRITICAL"


def test_stale_bundle_is_distinguished_and_cannot_be_called_healthy(tmp_path):
    from apps.vps.services.machine_b_runtime import read_machine_b_runtime

    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=1)
    _write_bundle(tmp_path, generated_at=old.isoformat())
    evidence = read_machine_b_runtime(tmp_path, now=now, max_age_seconds=60)
    assert evidence.status == "STALE"
    assert "stale" in evidence.reason


def test_mixed_generation_fails_closed(tmp_path):
    from apps.vps.services.machine_b_runtime import read_machine_b_runtime

    now = datetime.now(timezone.utc)
    _write_bundle(tmp_path, generated_at=now.isoformat())
    health_path = tmp_path / "runtime-health.json"
    health = json.loads(health_path.read_text(encoding="utf-8"))
    health["generated_at"] = (now - timedelta(seconds=1)).isoformat()
    health_path.write_text(json.dumps(health), encoding="utf-8")
    evidence = read_machine_b_runtime(tmp_path, now=now)
    assert evidence.status == "UNKNOWN"
    assert "generation" in evidence.reason


def test_collector_error_or_unsupported_schema_fails_closed(tmp_path):
    from apps.vps.services.machine_b_runtime import read_machine_b_runtime

    now = datetime.now(timezone.utc)
    _write_bundle(tmp_path, generated_at=now.isoformat(), collector_result="error")
    assert read_machine_b_runtime(tmp_path, now=now).status == "UNKNOWN"

    _write_bundle(tmp_path, generated_at=now.isoformat(), inventory_version="9.9.9")
    evidence = read_machine_b_runtime(tmp_path, now=now)
    assert evidence.status == "UNKNOWN"
    assert "schema" in evidence.reason


def test_missing_or_malformed_artifact_is_unknown_not_exception(tmp_path):
    from apps.vps.services.machine_b_runtime import read_machine_b_runtime

    assert read_machine_b_runtime(tmp_path).status == "UNKNOWN"
    (tmp_path / "runtime-inventory.json").write_text("not json", encoding="utf-8")
    assert read_machine_b_runtime(tmp_path).status == "UNKNOWN"


def test_success_label_with_nonzero_collector_exit_fails_closed(tmp_path):
    from apps.vps.services.machine_b_runtime import read_machine_b_runtime

    now = datetime.now(timezone.utc)
    _write_bundle(tmp_path, generated_at=now.isoformat())
    status_path = tmp_path / "runtime-collector-status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["exit_code"] = 1
    status_path.write_text(json.dumps(status), encoding="utf-8")
    evidence = read_machine_b_runtime(tmp_path, now=now)
    assert evidence.status == "UNKNOWN"
    assert "exit" in evidence.reason


@pytest.mark.parametrize("artifact,field,bad", [
    ("health", "domains", ["not-an-object"]),
    ("inventory", "proxmox", []),
    ("inventory", "public_mappings", {}),
    ("capabilities", "wireguard", False),
    ("health", "checks", {}),
])
def test_invalid_nested_shapes_are_unknown_not_exceptions(tmp_path, artifact, field, bad):
    from apps.vps.services.machine_b_runtime import read_machine_b_runtime

    now = datetime.now(timezone.utc)
    _write_bundle(tmp_path, generated_at=now.isoformat())
    path = tmp_path / f"runtime-{artifact}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = bad
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert read_machine_b_runtime(tmp_path, now=now).status == "UNKNOWN"


def test_machine_b_revision_requires_one_coherent_artifact_bundle(tmp_path):
    from apps.vps.services.machine_b_runtime import read_machine_b_runtime

    now = datetime.now(timezone.utc)
    revision = "a" * 40
    _write_bundle(tmp_path, generated_at=now.isoformat(), source_revision=revision)
    evidence = read_machine_b_runtime(tmp_path, now=now)
    assert evidence.status == "HEALTHY"
    assert evidence.provenance["machine_b_sha"] == revision

    path = tmp_path / "runtime-health.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_revision"] = "b" * 40
    path.write_text(json.dumps(payload), encoding="utf-8")
    evidence = read_machine_b_runtime(tmp_path, now=now)
    assert evidence.status == "UNKNOWN"
    assert "revision" in evidence.reason
