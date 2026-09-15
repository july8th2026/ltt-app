"""Fail-closed reconciliation of OVH provider IPs into the local static pool."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from ipaddress import IPv4Address

from sqlalchemy import select

from apps.vps.tables import VpsGateway, VpsInstance, VpsIp


class InventoryConflict(RuntimeError):
    pass


@dataclass(frozen=True)
class InventorySyncResult:
    total: int
    free: int
    bound: int
    quarantined: int


def sync_ovh_static_pool(db, profile, *, provider, gateway) -> InventorySyncResult:
    """Upsert observations without ever turning ambiguous resources into FREE."""
    if profile.public_ip_backend_type != "ovh_static_pool":
        raise InventoryConflict("profile is not an OVH static pool")
    gateways = db.execute(select(VpsGateway).where(
        VpsGateway.infrastructure_profile_id == profile.id)).scalars().all()
    if len(gateways) != 1:
        raise InventoryConflict("profile must own exactly one gateway")
    gateway_row = gateways[0]
    observations = provider.list_additional_ipv4()
    expected_owner = provider.config.service_name
    usable = {}
    for item in observations:
        try:
            address = str(IPv4Address(item.address))
        except ValueError:
            raise InventoryConflict("provider returned invalid IPv4") from None
        if item.cidr != f"{address}/32":
            raise InventoryConflict("provider IPv4 CIDR does not match address")
        if address in usable:
            raise InventoryConflict("provider returned duplicate IPv4")
        if item.routed_to == expected_owner and item.kind == "failover":
            usable[address] = item
    mappings = dict(gateway.list_mappings() or {})
    now = datetime.now(timezone.utc)
    rows = db.execute(select(VpsIp).where(
        VpsIp.infrastructure_profile_id == profile.id).with_for_update()).scalars().all()
    by_address = {row.dia_chi: row for row in rows}
    instances = {row.id: row for row in db.execute(select(VpsInstance).where(
        VpsInstance.infrastructure_profile_id == profile.id)).scalars()}

    for address, observation in usable.items():
        row = by_address.get(address)
        if row is None:
            row = VpsIp(
                infrastructure_profile_id=profile.id, gateway_id=gateway_row.id,
                dia_chi=address, state="QUARANTINED")
            db.add(row)
            by_address[address] = row
        elif row.gateway_id != gateway_row.id:
            raise InventoryConflict("public IP belongs to another gateway")
        row.backend_resource_id = observation.cidr
        row.last_observed_at = now
        row.billing_mode = "pre_owned"
        row.provider_metadata = {
            "kind": observation.kind, "country": observation.country,
            "routed_to_expected_service": True,
        }
        actual_private = mappings.get(address)
        instance = instances.get(row.instance_id or "")
        if (row.state == "BOUND" and instance is not None
                and instance.ip_noi_bo and actual_private == instance.ip_noi_bo):
            continue
        if actual_private is None and row.state not in ("RESERVED", "BOUND"):
            row.state = "FREE"
            row.instance_id = None
            row.reservation_token = None
            row.reserved_at = None
            row.bound_at = None
        else:
            row.state = "QUARANTINED"

    for address, row in by_address.items():
        if address not in usable:
            row.state = "QUARANTINED"
            row.last_observed_at = now
    db.flush()
    states = [row.state for row in by_address.values()]
    return InventorySyncResult(
        total=len(states), free=states.count("FREE"), bound=states.count("BOUND"),
        quarantined=states.count("QUARANTINED"))
