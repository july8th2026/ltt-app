"""Resolve profile backend implementations without leaking drivers into jobs."""
from __future__ import annotations

import os
import re

from apps.vps.services.backends import (
    NftGatewayBackend,
    OvhStaticIpPoolBackend,
    ProxmoxComputeBackend,
    VultrReservedIpBackend,
)
from apps.vps.services.backends.contracts import BackendConflict, UnsupportedCapability


def _reference_environment(reference: str, canonical: str, suffixes: tuple[str, ...]
                           ) -> dict[str, str]:
    if not re.fullmatch(r"LTT_[A-Z0-9_]{1,100}", reference):
        raise BackendConflict("invalid canonical credential reference")
    result = {f"{canonical}_{suffix}": os.environ.get(
        f"{reference}_{suffix}", "") for suffix in suffixes}
    result["LTT_ENV"] = os.environ.get("LTT_ENV", "")
    return result


def compute_backend(profile):
    kind = str(getattr(profile, "compute_backend_type", "proxmox") or "")
    if kind == "proxmox":
        from apps.vps.services import proxmox
        config = dict(getattr(profile, "compute_config", None) or {})
        reference = str(config.get("credential_ref") or "LTT_VPS_PROXMOX")
        env = _reference_environment(reference, "LTT_VPS_PROXMOX", (
            "URL", "TOKEN_ID", "TOKEN_SECRET", "NODE", "CA", "TLS_BO_QUA"))
        return ProxmoxComputeBackend(proxmox.client_tu_moi_truong(env))
    raise UnsupportedCapability(f"unsupported compute backend: {kind}")


def public_ip_backend(db, profile):
    kind = str(getattr(profile, "public_ip_backend_type", "vultr_reserved_ip") or "")
    if kind == "ovh_static_pool":
        return OvhStaticIpPoolBackend(db, profile.id)
    if kind == "vultr_reserved_ip":
        from apps.vps.services import vultr
        reference = str(getattr(profile, "credential_ref", "") or "LTT_VULTR")
        env = _reference_environment(reference, "LTT_VULTR", ("API_KEY",))
        config = dict(getattr(profile, "provider_config", None) or {})
        env["LTT_VPS_VUNG"] = str(config.get("region") or getattr(
            profile, "region", "sgp"))
        return VultrReservedIpBackend(vultr.client_tu_moi_truong(env))
    raise UnsupportedCapability(f"unsupported public-IP backend: {kind}")


def gateway_backend(profile):
    kind = str(getattr(profile, "gateway_backend_type", "nft") or "")
    if kind == "nft":
        from apps.vps.services import gateway
        config = dict(getattr(profile, "network_config", None) or {})
        reference = str(config.get("gateway_credential_ref") or "")
        if not reference:
            if getattr(profile, "public_ip_backend_type", "") == "ovh_static_pool":
                raise BackendConflict("OVH gateway credential reference is required")
            reference = "LTT_VPS_GATEWAY"
        strategy = config.get("mapping_strategy")
        if (getattr(profile, "public_ip_backend_type", "") == "ovh_static_pool"
                and strategy != "ltt_nft_maps"):
            # The existing OVH gateway uses gwnat chains and anh-xa-ip.txt,
            # not the legacy driver's vao/ra maps. Never construct a mutating
            # client until an explicitly compatible strategy is configured.
            raise UnsupportedCapability("OVH gateway mapping strategy is not implemented")
        if strategy not in (None, "ltt_nft_maps"):
            raise UnsupportedCapability("unsupported gateway mapping strategy")
        env = _reference_environment(reference, "LTT_VPS_GATEWAY", (
            "HOST", "USER", "SSH_KEY", "NFT_TABLE", "KNOWN_HOSTS"))
        return NftGatewayBackend(gateway.client_tu_moi_truong(env))
    raise UnsupportedCapability(f"unsupported gateway backend: {kind}")


def router_backend(profile):
    """The DHCP/BW endpoint is explicit per profile, never another provider's."""
    from apps.vps.services import router
    config = dict(getattr(profile, "network_config", None) or {})
    reference = str(config.get("router_credential_ref") or "")
    if not reference:
        if getattr(profile, "public_ip_backend_type", "") == "ovh_static_pool":
            raise BackendConflict("OVH router credential reference is required")
        reference = "LTT_VPS_ROUTER"
    env = _reference_environment(reference, "LTT_VPS_ROUTER", (
        "HOST", "USER", "SSH_KEY", "KNOWN_HOSTS"))
    return router.client_tu_moi_truong(env)


def operation_error_types() -> tuple[type[Exception], ...]:
    """Narrow exception boundary for provider/network cleanup operations."""
    from apps.vps.services.gateway import GatewayError
    from apps.vps.services.vultr import VultrError
    from apps.vps.services.backends.contracts import BackendError
    return (BackendError, GatewayError, VultrError)
