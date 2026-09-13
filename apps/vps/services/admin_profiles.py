"""App-owned operator actions; never migrate or mutate existing VM resources."""
from datetime import datetime, timezone
from dataclasses import dataclass
import re

from sqlalchemy import select

from apps.vps import profiles
from apps.vps.services import preflight
from apps.vps.tables import VpsInfrastructureProfile, VpsProfileHealth, VpsInstance, VpsIp


class AdminProfileConflict(RuntimeError):
    pass


@dataclass(frozen=True)
class AdminActionResult:
    profile: VpsInfrastructureProfile
    applied: bool
    findings: tuple = ()


def _configured_preflight(db, row) -> bool:
    try:
        return preflight.run_configured_profile_preflight(db, row).ready
    except Exception as exc:
        # A failing constructor must not retain a green old observation.
        row.accept_new = False
        row.is_default = False
        now = datetime.now(timezone.utc)
        for component in profiles.REQUIRED_HEALTH_COMPONENTS:
            db.add(VpsProfileHealth(
                infrastructure_profile_id=row.id, component=component,
                status="CRITICAL", observed_at=now, generated_at=now,
                summary=f"configured preflight unavailable ({type(exc).__name__})"))
        row.last_health_at = now
        return False


def test_connections(db, row) -> bool:
    """Probe three adapters independently; never copy remote error bodies."""
    from apps.vps.services import backend_factory
    probes = (
        ("compute", lambda: backend_factory.compute_backend(row).health()),
        ("ip", lambda: backend_factory.public_ip_backend(db, row).health()),
        ("gateway", lambda: backend_factory.gateway_backend(row).health()),
    )
    now = datetime.now(timezone.utc)
    statuses = []
    for component, probe in probes:
        try:
            status = str(probe().status or "UNKNOWN").upper()
            if status not in profiles.HEALTH_STATES:
                status = "UNKNOWN"
            summary = f"{component} connection probe returned {status}"
        except Exception as exc:
            status = "CRITICAL"
            summary = f"{component} connection unavailable ({type(exc).__name__})"
        statuses.append(status)
        db.add(VpsProfileHealth(
            infrastructure_profile_id=row.id, component=component,
            status=status, summary=summary, observed_at=now, generated_at=now,
            provenance={"config_version": row.config_version,
                        "probe": "connection_only"}))
    row.last_health_at = now
    ready = all(status == "HEALTHY" for status in statuses)
    if not ready:
        row.accept_new = False
        row.is_default = False
    db.flush()
    return ready


def _safe_sha(value) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if re.fullmatch(r"[0-9a-f]{7,64}", candidate) else "UNKNOWN"


def _deployment_provenance(health_rows) -> dict[str, str]:
    """Return only validated, operator-safe evidence for the running release."""
    from platform_core import dau_van_tay

    fingerprint = dict(dau_van_tay.doc_da_cache())
    runtime_health = next(
        (item for item in health_rows if item.component == "runtime"), None)
    runtime_provenance = dict(
        getattr(runtime_health, "provenance", None) or {})
    versions = runtime_provenance.get("schema_versions")
    if isinstance(versions, dict):
        schema_versions = ", ".join(
            f"{key}={value}" for key, value in sorted(versions.items())
            if re.fullmatch(r"[a-z_]{1,24}", str(key))
            and re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", str(value)))
    else:
        schema_versions = ""
    generated_at = getattr(runtime_health, "generated_at", None)
    if generated_at is not None and generated_at.tzinfo is None:
        # SQLite drops timezone metadata while PostgreSQL preserves it. The
        # runtime contract is UTC, so normalize the test/dev representation
        # rather than showing two timestamp shapes to operators.
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return {
        "app_sha": _safe_sha(fingerprint.get("commit")),
        "machine_b_sha": _safe_sha(runtime_provenance.get("machine_b_sha")),
        "schema_versions": schema_versions or "UNKNOWN",
        "runtime_generated_at": generated_at.isoformat() if generated_at else "UNKNOWN",
    }


def list_profiles(db) -> list[dict]:
    result = []
    for row in db.execute(select(VpsInfrastructureProfile).order_by(
            VpsInfrastructureProfile.name)).scalars():
        ready, reason, observed = profiles.health_prerequisites(db, row.id)
        ips = db.execute(select(VpsIp).where(
            VpsIp.infrastructure_profile_id == row.id).order_by(VpsIp.dia_chi)).scalars().all()
        health_rows = db.execute(select(VpsProfileHealth).where(
            VpsProfileHealth.infrastructure_profile_id == row.id).order_by(
                VpsProfileHealth.observed_at.desc())).scalars().all()
        component_health: dict[str, str] = {}
        for health in health_rows:
            component_health.setdefault(health.component, health.status)
        instances = db.execute(select(VpsInstance).where(
            VpsInstance.infrastructure_profile_id == row.id,
            VpsInstance.trang_thai != "da_xoa")).scalars().all()
        vm_count = len(instances)
        private_by_instance = {instance.id: instance.ip_noi_bo or ""
                               for instance in instances}
        compute_ref = _reference(row.compute_config.get("credential_ref", ""), optional=True)
        gateway_ref = _reference(row.network_config.get("gateway_credential_ref", ""), optional=True)
        router_ref = _reference(row.network_config.get("router_credential_ref", ""), optional=True)
        result.append({
            "id": row.id, "name": row.name, "slug": row.slug, "region": row.region,
            "status": row.status, "accept_new": row.accept_new,
            "is_default": row.is_default, "config_version": row.config_version,
            "ready": ready, "health_reason": reason, "health_at": observed,
            "health": {component: component_health.get(component, "UNKNOWN")
                       for component in profiles.REQUIRED_HEALTH_COMPONENTS},
            "vm_count": vm_count,
            "compute_backend": row.compute_backend_type,
            "ip_backend": row.public_ip_backend_type,
            "provider": ("OVH" if row.public_ip_backend_type == "ovh_static_pool"
                         else "Vultr" if row.public_ip_backend_type == "vultr_reserved_ip"
                         else "Unknown"),
            "available_ips": sum(ip.state == "FREE" for ip in ips),
            "gateway_backend": row.gateway_backend_type,
            "credential_ref": _reference(row.credential_ref, optional=True),
            "compute_ref": compute_ref,
            "runtime_ref": _reference(row.compute_config.get("runtime_ref", ""), optional=True),
            "gateway_ref": gateway_ref,
            "router_ref": router_ref,
            "credentials_configured": bool(
                _reference(row.credential_ref, optional=True) and compute_ref
                and gateway_ref and router_ref),
            "mapping_strategy": row.network_config.get("mapping_strategy")
                if row.network_config.get("mapping_strategy") in ("ovh_gwnat", "ltt_nft_maps") else "",
            "deployment": _deployment_provenance(health_rows),
            "ips": [{"address": ip.dia_chi, "state": ip.state,
                     "instance_id": ip.instance_id or "",
                     "private_ip": private_by_instance.get(ip.instance_id, "")}
                    for ip in ips],
        })
    return result


def _reference(value, *, optional=False):
    text = str(value or "")
    if re.fullmatch(r"LTT_[A-Z0-9_]{1,100}", text):
        return text
    if optional:
        return ""
    raise ValueError("credential references must be canonical environment variable names")


def save_profile(db, profile_id, *, config_version, name, slug, region,
                 ip_backend, credential_ref, compute_ref, runtime_ref,
                 gateway_ref, router_ref, mapping_strategy):
    """Create/edit non-secret references only; any edit invalidates old health."""
    values = {key: str(value or "").strip() for key, value in
              {"name": name, "slug": slug, "region": region}.items()}
    if (not values["name"] or len(values["name"]) > 120
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", values["slug"])
            or not re.fullmatch(r"[a-z0-9-]{1,32}", values["region"])
            or ip_backend not in ("ovh_static_pool", "vultr_reserved_ip")
            or mapping_strategy not in ("ovh_gwnat", "ltt_nft_maps")):
        raise ValueError("invalid profile configuration")
    refs = [_reference(value) for value in (
        credential_ref, compute_ref, runtime_ref, gateway_ref, router_ref)]
    row = None
    if profile_id:
        row = db.execute(select(VpsInfrastructureProfile).where(
            VpsInfrastructureProfile.id == profile_id).with_for_update()).scalar_one_or_none()
        if row is None:
            raise LookupError("profile not found")
        if row.config_version != config_version:
            raise AdminProfileConflict("profile version changed")
        pinned = db.execute(select(VpsInstance.id).where(
            VpsInstance.infrastructure_profile_id == row.id,
            VpsInstance.trang_thai != "da_xoa").limit(1)).scalar_one_or_none()
        if pinned and (row.region != values["region"] or row.public_ip_backend_type != ip_backend
                       or row.credential_ref != refs[0]
                       or row.compute_config.get("credential_ref", "") != refs[1]
                       or row.network_config.get("gateway_credential_ref", "") != refs[3]
                       or row.network_config.get("router_credential_ref", "") != refs[4]
                       or row.network_config.get("mapping_strategy", "") != mapping_strategy):
            raise AdminProfileConflict("pinned resources prohibit backend/identity reconfiguration")
    duplicate = db.execute(select(VpsInfrastructureProfile.id).where(
        VpsInfrastructureProfile.slug == values["slug"])).scalar_one_or_none()
    if duplicate and (row is None or duplicate != row.id):
        raise AdminProfileConflict("profile slug already exists")
    if row is None:
        row = VpsInfrastructureProfile(compute_backend_type="proxmox", gateway_backend_type="nft",
                                       status="STANDBY", accept_new=False, is_default=False)
        db.add(row)
        row.config_version = 0
    for key, value in values.items():
        setattr(row, key, value)
    row.public_ip_backend_type, row.credential_ref = ip_backend, refs[0]
    row.compute_config = {**dict(row.compute_config or {}), "credential_ref": refs[1],
                          "runtime_ref": refs[2]}
    row.network_config = {**dict(row.network_config or {}), "gateway_credential_ref": refs[3],
                          "router_credential_ref": refs[4], "mapping_strategy": mapping_strategy}
    row.accept_new = row.is_default = False
    if row.status == "ACTIVE":
        row.status = "STANDBY"
    row.config_version += 1
    db.flush()
    now = datetime.now(timezone.utc)
    for component in profiles.REQUIRED_HEALTH_COMPONENTS:
        db.add(VpsProfileHealth(infrastructure_profile_id=row.id, component=component,
                               status="UNKNOWN", summary="configuration changed; preflight required",
                               observed_at=now, generated_at=now,
                               provenance={"config_version": row.config_version}))
    db.flush()
    return row


def apply_action(db, profile_id: str, action: str, *, config_version: int):
    row = db.execute(select(VpsInfrastructureProfile).where(
        VpsInfrastructureProfile.id == profile_id).with_for_update()).scalar_one_or_none()
    if row is None:
        raise LookupError("profile not found")
    if row.config_version != config_version:
        raise AdminProfileConflict("profile version changed; reload before retrying")
    applied = True
    findings = ()
    increments_version = True
    if action == "preflight":
        _configured_preflight(db, row)
    elif action == "test_connection":
        applied = test_connections(db, row)
    elif action in ("activate", "default"):
        # Always perform a configured fresh probe before activation, including
        # the driver compatibility guard; stored green rows are not sufficient.
        if _configured_preflight(db, row):
            profiles.activate_profile(db, row.id, make_default=action == "default")
        else:
            applied = False
    elif action in ("standby", "drain", "disable"):
        row.accept_new = False
        row.is_default = False
        row.status = {"standby": "STANDBY", "drain": "DRAINING", "disable": "DISABLED"}[action]
    elif action == "reconcile":
        findings = tuple(run_reconciliation(db, row).findings)
        increments_version = False
    else:
        raise ValueError("unknown profile action")
    if increments_version:
        row.config_version += 1
    db.flush()
    return AdminActionResult(row, applied, findings)


def run_reconciliation(db, row):
    """Construct only this profile's adapters and perform a read-only compare."""
    from apps.vps.services import backend_factory, reconciliation
    return reconciliation.reconcile_profile(
        db, row,
        compute=backend_factory.compute_backend(row),
        public_ip=backend_factory.public_ip_backend(db, row),
        gateway=backend_factory.gateway_backend(row),
    )
