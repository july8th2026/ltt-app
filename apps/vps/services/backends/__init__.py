"""Backend contracts and adapters for VPS infrastructure profiles."""

from apps.vps.services.backends.compute import ProxmoxComputeBackend
from apps.vps.services.backends.gateway import NftGatewayBackend
from apps.vps.services.backends.public_ip import (
    OvhStaticIpPoolBackend,
    VultrReservedIpBackend,
)

__all__ = [
    "NftGatewayBackend",
    "OvhStaticIpPoolBackend",
    "ProxmoxComputeBackend",
    "VultrReservedIpBackend",
]
