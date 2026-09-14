"""Plan-specific sellable capacity; no unknown backend limit is unlimited."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select

from apps.vps.cost import dia_tong_gb, lay_plan
from apps.vps.services import capacity
from apps.vps.tables import VpsGateway, VpsInstance


@dataclass(frozen=True)
class SellableCapacity:
    slots: int
    compute_slots: int
    ipv4_slots: int
    gateway_slots: int


def _limit(value: object) -> int:
    return value if type(value) is int and value >= 0 else 0


def effective_ipv4_slots(details: object, *, promised_without_ip: object = 0) -> int:
    """Count owned FREE rows plus one strictly configured replenishment slot."""
    if not isinstance(details, dict):
        return 0
    free = _limit(details.get("free"))
    replenishable = _limit(details.get("replenishable"))
    promised = _limit(promised_without_ip)
    return max(0, free + min(1, replenishable) - promised)


def sellable_slots(compute: capacity.SucChua, plan_id: str, *,
                   free_ipv4: object, gateway_slots: object,
                   extra_disk_gb: int = 0) -> SellableCapacity:
    """Use existing RAM/thin-storage/CPU policies, then intersect all limits."""
    ip_limit, gateway_limit = _limit(free_ipv4), _limit(gateway_slots)
    plan = lay_plan(plan_id)
    compute_limit = 0
    if (plan is not None and capacity.cho_phep_ban(
            compute, plan_id, extra_disk_gb).cho_phep):
        disk_per_vm = dia_tong_gb(plan_id, extra_disk_gb)
        limits = [compute.ram_mb_con // plan.ram_mb,
                  max(0, int(compute.dia_gb_ban_duoc * capacity.TRAN_BAN_CHONG)
                      - compute.dia_gb_da_hua) // disk_per_vm]
        # V4 requires measured CPU; unknown CPU is not infinite capacity.
        limits.append(max(0, int(compute.cpu_tong * capacity.TRAN_BAN_CHONG_CPU)
                          - compute.vcpu_da_hua) // plan.vcpu)
        compute_limit = min(limits)
    return SellableCapacity(min(compute_limit, ip_limit, gateway_limit),
                            compute_limit, ip_limit, gateway_limit)


def available_gateway_slots(db, profile_id: str) -> int:
    """Count all promises, including queued VMs without an address yet."""
    from apps.vps.services import mang

    gateways = db.execute(select(VpsGateway).where(
        VpsGateway.infrastructure_profile_id == profile_id,
        VpsGateway.dang_nhan_may_moi.is_(True))).scalars()
    slots = 0
    for gateway in gateways:
        promised = db.execute(select(func.count()).select_from(VpsInstance).where(
            VpsInstance.gateway_id == gateway.id,
            VpsInstance.trang_thai != "da_xoa")).scalar_one()
        slots += max(0, mang.so_dia_chi(gateway) - int(promised))
    return slots
