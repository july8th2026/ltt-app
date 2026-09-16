"""Independent, fail-closed health preflight for one infrastructure profile."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os

from apps.vps import profiles
from apps.vps.cost import PLANS
from apps.vps.services import backend_factory, provisioning
from apps.vps.services.sellable_capacity import (
    available_gateway_slots,
    effective_ipv4_slots,
    sellable_slots,
)
from apps.vps.services.machine_b_runtime import (
    MachineBRuntimeEvidence,
    read_machine_b_runtime,
)
from apps.vps.tables import VpsInfrastructureProfile, VpsProfileHealth


@dataclass(frozen=True)
class PreflightResult:
    ready: bool
    components: dict[str, str]
    summaries: dict[str, str]
    sellable: dict[str, int] = field(default_factory=dict)


def _status(value: object) -> str:
    candidate = str(value or "UNKNOWN").upper()
    return candidate if candidate in profiles.HEALTH_STATES else "UNKNOWN"


def _probe(callable_):
    try:
        return callable_()
    except Exception as exc:  # probe boundary: report class, never provider text
        return type("FailedHealth", (), {
            "status": "CRITICAL",
            "summary": f"probe failed ({type(exc).__name__})",
            "details": {},
        })()


def run_profile_preflight(
    db,
    profile: VpsInfrastructureProfile,
    *,
    compute,
    public_ip,
    gateway,
    runtime: MachineBRuntimeEvidence,
    demote_on_failure: bool = True,
) -> PreflightResult:
    """Measure all activation prerequisites and persist independent evidence.

    Operator preflight demotes a failing profile. The periodic refresh passes
    `demote_on_failure=False`: its red health rows already close selection, and
    demoting on one transient probe would need a human to re-activate sales.
    """
    compute_health = _probe(compute.health)
    ip_health = _probe(public_ip.health)
    gateway_health = _probe(gateway.health)
    capacity_probe = _probe(compute.capacity)

    compute_status = _status(compute_health.status)
    ip_status = _status(ip_health.status)
    gateway_status = _status(gateway_health.status)
    runtime_status = _status(runtime.status)
    network_status = (
        _status(runtime.domains.get("network"))
        if runtime_status == "HEALTHY" else runtime_status)
    storage_status = (
        _status(runtime.domains.get("storage"))
        if runtime_status == "HEALTHY" else runtime_status)

    capacity_status, capacity_summary = "CRITICAL", "sellable capacity unavailable"
    sellable = {}
    try:
        ip_details = dict(getattr(ip_health, "details", None) or {})
        gateway_details = dict(getattr(gateway_health, "details", None) or {})
        gateway_limit = gateway_details.get("available_slots")
        if gateway_limit is None:
            gateway_limit = available_gateway_slots(db, profile.id)
        measured = provisioning.suc_chua_hien_tai(
            db, capacity_probe["node"], capacity_probe["storage"], capacity_probe["vms"])
        ipv4_slots = effective_ipv4_slots(ip_details)
        sellable = {plan.id: sellable_slots(
            measured, plan.id, free_ipv4=ipv4_slots,
            gateway_slots=gateway_limit).slots for plan in PLANS}
        if any(sellable.values()):
            capacity_status = "HEALTHY"
            capacity_summary = "compute, IPv4 and gateway have sellable slots"
        else:
            capacity_summary = "no sellable slots across compute, IPv4 and gateway"
    except (TypeError, ValueError, KeyError, AttributeError):
        # Malformed provider payloads must not turn the whole health page into
        # an exception, or unknown capacity into a green activation gate.
        pass
    if storage_status != "HEALTHY":
        capacity_status = storage_status
        capacity_summary = "Machine B storage evidence is not healthy"

    components = {
        "compute": compute_status,
        "ip": ip_status,
        "gateway": gateway_status,
        "network": network_status,
        "capacity": capacity_status,
        "runtime": runtime_status,
    }
    summaries = {
        "compute": str(getattr(compute_health, "summary", ""))[:300],
        "ip": str(getattr(ip_health, "summary", ""))[:300],
        "gateway": str(getattr(gateway_health, "summary", ""))[:300],
        "network": "Machine B network evidence",
        "capacity": capacity_summary,
        "runtime": str(runtime.reason or "coherent fresh Machine B generation")[:300],
    }
    observed = datetime.now(timezone.utc)
    for component in profiles.REQUIRED_HEALTH_COMPONENTS:
        db.add(VpsProfileHealth(
            infrastructure_profile_id=profile.id,
            component=component,
            status=components[component],
            summary=summaries[component],
            provenance={**dict(runtime.provenance or {}), **(
                {"sellable_slots": sellable} if component == "capacity" else {})},
            generated_at=runtime.generated_at,
            observed_at=observed,
        ))
    ready = all(value == "HEALTHY" for value in components.values())
    if not ready and demote_on_failure:
        profile.accept_new = False
        profile.is_default = False
    profile.last_health_at = observed
    db.flush()
    return PreflightResult(ready, components, summaries, sellable)


def run_configured_profile_preflight(
    db, profile: VpsInfrastructureProfile, *, runtime_dir: str | None = None,
    demote_on_failure: bool = True,
) -> PreflightResult:
    """Construct configured adapters and consume Machine B artifacts read-only."""
    runtime_ref = str(profile.compute_config.get("runtime_ref") or "")
    if runtime_ref and not runtime_ref.startswith("LTT_"):
        directory = ""
    else:
        directory = (runtime_dir or (os.environ.get(runtime_ref, "") if runtime_ref else "")
                     or os.environ.get("LTT_VPS_MACHINE_B_RUNTIME", ""))
    runtime = read_machine_b_runtime(directory) if directory else MachineBRuntimeEvidence(
        "UNKNOWN", "Machine B runtime directory is not configured")
    if profile.public_ip_backend_type == "ovh_static_pool":
        provider = backend_factory.ovh_inventory_client(profile)
        if not provider.health():
            raise RuntimeError("OVH service ownership check failed")
    return run_profile_preflight(
        db, profile,
        compute=backend_factory.compute_backend(profile),
        public_ip=backend_factory.public_ip_backend(db, profile),
        gateway=backend_factory.gateway_backend(profile),
        runtime=runtime,
        demote_on_failure=demote_on_failure,
    )


def refresh_active_profiles(db, *, run=None) -> dict[str, bool]:
    """Periodic health refresh for every ACTIVE profile; never demotes.

    Each profile is isolated: a constructor/transport failure records CRITICAL
    rows for that profile only (selection closes) and the loop continues.
    """
    from sqlalchemy import select

    run = run or run_configured_profile_preflight
    ids = db.execute(select(VpsInfrastructureProfile.id).where(
        VpsInfrastructureProfile.status == "ACTIVE")).scalars().all()
    ket_qua: dict[str, bool] = {}
    for profile_id in ids:
        row = db.get(VpsInfrastructureProfile, profile_id)
        try:
            ket_qua[profile_id] = run(db, row, demote_on_failure=False).ready
            db.commit()
        except Exception as exc:  # boundary: report class, never provider text
            db.rollback()
            row = db.get(VpsInfrastructureProfile, profile_id)
            now = datetime.now(timezone.utc)
            for component in profiles.REQUIRED_HEALTH_COMPONENTS:
                db.add(VpsProfileHealth(
                    infrastructure_profile_id=row.id, component=component,
                    status="CRITICAL", observed_at=now, generated_at=now,
                    summary=f"periodic preflight unavailable ({type(exc).__name__})"))
            row.last_health_at = now
            db.commit()
            ket_qua[profile_id] = False
    return ket_qua
