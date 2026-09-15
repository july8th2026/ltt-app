"""Compute contract wrapper around the existing Proxmox client."""
from __future__ import annotations

from apps.vps.services import tac_vu
from apps.vps.services.backends.contracts import (
    BackendCapabilities,
    BackendHealth,
    BackendOperation,
    ProtectedResource,
)

PROTECTED_VMIDS = frozenset(range(100, 108))


def _mutable(vmid: int) -> int:
    value = int(vmid)
    if value in PROTECTED_VMIDS:
        raise ProtectedResource(f"VM{value} is protected by VPS V4 D07")
    return value


class ProxmoxComputeBackend:
    """Delegates to proven endpoints; orchestration journals returned UPIDs."""

    def __init__(self, client):
        self.client = client

    def create(self, vmid: int, *, config: dict) -> BackendOperation:
        return BackendOperation((str(self.client.tao_may(_mutable(vmid), **config)),))

    def configure(self, vmid: int, *, config: dict) -> BackendOperation:
        result = self.client.dat_cau_hinh(_mutable(vmid), **config)
        return BackendOperation((str(result),) if result else ())

    def start(self, vmid: int) -> BackendOperation:
        return BackendOperation((str(self.client.bat(_mutable(vmid))),))

    def stop(self, vmid: int) -> BackendOperation:
        return BackendOperation((str(self.client.tat_mem(_mutable(vmid))),))

    def restart(self, vmid: int) -> BackendOperation:
        value = _mutable(vmid)
        stop_id = str(self.client.tat_mem(value))
        tac_vu.cho_va_xac_minh(self.client, stop_id, value, "tat")
        start_id = str(self.client.bat(value))
        return BackendOperation((stop_id, start_id))

    def destroy(self, vmid: int) -> BackendOperation:
        return BackendOperation((str(self.client.xoa(_mutable(vmid), xoa_luon_dia=True)),))

    def status(self, vmid: int) -> dict:
        return dict(self.client.trang_thai_vm(int(vmid)) or {})

    def snapshot(self, vmid: int, name: str, *, description: str = "") -> BackendOperation:
        result = self.client.chup_anh(
            _mutable(vmid), str(name), mo_ta=str(description or ""))
        return BackendOperation((str(result),))

    def restore(self, vmid: int, name: str) -> BackendOperation:
        result = self.client.khoi_phuc_anh(_mutable(vmid), str(name))
        return BackendOperation((str(result),))

    def capacity(self) -> dict:
        return {
            "node": dict(self.client.trang_thai_node() or {}),
            "storage": list(self.client.kho_luu_tru() or []),
            "vms": list(self.client.danh_sach_vm() or []),
        }

    def health(self) -> BackendHealth:
        version = dict(self.client.phien_ban() or {})
        return BackendHealth("HEALTHY", "Proxmox API reachable", {"version": version})

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(snapshot=True, restore=True)
