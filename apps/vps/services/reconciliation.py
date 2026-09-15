"""Read-only, profile-scoped reconciliation across DB and three backends."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select

from apps.vps import profiles
from apps.vps.services.backends.compute import PROTECTED_VMIDS
from apps.vps.tables import VpsInstance, VpsIp


@dataclass(frozen=True)
class Finding:
    code: str
    instance_id: str = ""
    resource_id: str = ""
    detail: str = ""
    auto_delete: bool = False


@dataclass(frozen=True)
class ReconciliationResult:
    profile_id: str
    findings: tuple[Finding, ...]


def reconcile_profile(db, profile, *, compute, public_ip, gateway
                      ) -> ReconciliationResult:
    """Compare authoritative read-backs; never mutate or auto-delete anything."""
    instances = db.execute(select(VpsInstance).where(
        VpsInstance.infrastructure_profile_id == profile.id,
        VpsInstance.trang_thai != "da_xoa",
    )).scalars().all()
    ips = db.execute(select(VpsIp).where(
        VpsIp.infrastructure_profile_id == profile.id)).scalars().all()

    compute_rows = list((compute.capacity() or {}).get("vms") or [])
    provider_rows = list(public_ip.list() or [])
    mappings = dict(gateway.list_mappings() or {})
    findings: list[Finding] = []

    db_vmids = {int(row.vmid): row for row in instances if row.vmid is not None}
    # Compute may be shared by multiple profiles. A VM pinned to another profile
    # is not an orphan merely because it is outside this reconciliation slice.
    all_pinned_vmids = {int(vmid) for vmid in db.execute(
        select(VpsInstance.vmid).where(
            VpsInstance.profile_resolution_state == "PINNED",
            VpsInstance.trang_thai != "da_xoa",
            VpsInstance.vmid.is_not(None),
        )).scalars()}
    observed_vmids = {int(row.get("vmid") or 0): row for row in compute_rows}
    for vmid, instance in db_vmids.items():
        if vmid not in observed_vmids:
            findings.append(Finding("VM_MISSING", instance.id, str(vmid)))
    for vmid, observed in observed_vmids.items():
        if vmid in all_pinned_vmids or vmid in PROTECTED_VMIDS:
            continue
        if str(observed.get("name") or "").startswith("vps-"):
            findings.append(Finding("VM_ORPHAN", resource_id=str(vmid)))

    by_instance = {row.instance_id: row for row in ips if row.instance_id}
    by_provider = {row.provider_id or row.id: row for row in provider_rows}
    db_provider_ids = {row.backend_resource_id or row.vultr_id or row.id: row
                       for row in ips}
    counts = Counter(row.address for row in provider_rows)
    for address, count in counts.items():
        if count > 1:
            findings.append(Finding(
                "PUBLIC_IP_DUPLICATE", resource_id=address,
                detail=f"provider returned {count} records"))

    for instance in instances:
        row = by_instance.get(instance.id)
        if row is None:
            findings.append(Finding("PUBLIC_IP_MISSING", instance.id))
            continue
        provider_id = row.backend_resource_id or row.vultr_id or row.id
        observed = by_provider.get(provider_id)
        if observed is None:
            findings.append(Finding(
                "PUBLIC_IP_MISSING", instance.id, provider_id))
        elif observed.instance_id not in (None, "", instance.id):
            findings.append(Finding(
                "IP_BOUND_TO_WRONG_VM", instance.id, provider_id))

        actual_mapping = mappings.get(row.dia_chi)
        if actual_mapping is None:
            findings.append(Finding(
                "MAPPING_MISSING", instance.id, row.dia_chi))
        elif actual_mapping != instance.ip_noi_bo:
            findings.append(Finding(
                "MAPPING_WRONG", instance.id, row.dia_chi,
                f"observed private address {actual_mapping}"))

    for provider_id, observed in by_provider.items():
        if provider_id in db_provider_ids:
            continue
        label = str((observed.metadata or {}).get("label") or "")
        if (profile.public_ip_backend_type == "vultr_reserved_ip"
                and not label.startswith("ltt-vps-")):
            continue
        # OVH pool inventory is itself canonical only after import to DB; an
        # unknown address is therefore a finding, never a deletion request.
        findings.append(Finding(
            "PROVIDER_RESOURCE_ORPHAN", resource_id=provider_id))

    if profile.status == "ACTIVE" and not profiles.health_prerequisites(
            db, profile.id)[0]:
        findings.append(Finding("PROFILE_UNHEALTHY", resource_id=profile.id))
    return ReconciliationResult(profile.id, tuple(findings))
