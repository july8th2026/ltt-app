"""Authoritative VM ownership readback before any mutation of an existing VM."""
from __future__ import annotations

from apps.vps.services import dinh_danh
from apps.vps.services.backends.compute import PROTECTED_VMIDS
from apps.vps.services.backends.contracts import BackendConflict


def _smbios_uuid(value: object) -> str:
    for part in str(value or "").split(","):
        key, separator, raw = part.partition("=")
        if separator and key.strip().lower() == "uuid":
            return raw.strip().lower()
    return ""


def owned_vm_exists(client, instance) -> bool:
    """Return False if absent; raise unless identity proves this exact DB owner."""
    if instance.vmid is None:
        return False
    vmid = int(instance.vmid)
    if vmid in PROTECTED_VMIDS:
        raise BackendConflict("protected VMID is outside VPS V4 mutation scope")
    rows = list(client.danh_sach_vm() or [])
    if not any(int(row.get("vmid") or 0) == vmid for row in rows):
        return False
    cfg = client._goi(
        "GET", f"/nodes/{client.config.node}/qemu/{vmid}/config") or {}
    expected_name = f"vps-{instance.id[:8]}"
    expected_uuid = dinh_danh.uuid_smbios(instance.id).lower()
    if (str(cfg.get("name") or "") != expected_name
            or _smbios_uuid(cfg.get("smbios1")) != expected_uuid):
        raise BackendConflict(
            "existing VM identity does not match the pinned VPS instance")
    return True
