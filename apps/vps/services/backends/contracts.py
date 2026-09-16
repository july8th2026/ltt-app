"""Small, capability-honest contracts for VPS infrastructure implementations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class BackendError(RuntimeError):
    """Base error safe for orchestration classification."""


class BackendConflict(BackendError):
    """Observed external identity conflicts with the requested mutation."""


class CapacityExhausted(BackendError):
    """A backend has no safe resource available."""


class ProtectedResource(BackendError):
    """The requested mutation targets a protected production resource."""


class UnsupportedCapability(BackendError):
    """A backend deliberately does not implement an optional capability."""


@dataclass(frozen=True)
class BackendHealth:
    status: str
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BackendCapabilities:
    dynamic_acquisition: bool = False
    provider_binding: bool = False
    snapshot: bool = False
    restore: bool = False


@dataclass(frozen=True)
class BackendOperation:
    external_ids: tuple[str, ...]


@dataclass(frozen=True)
class PublicIpResource:
    id: str
    address: str
    provider_id: str
    state: str
    instance_id: str | None = None
    reservation_token: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ComputeBackend(Protocol):
    def create(self, vmid: int, *, config: dict) -> BackendOperation: ...
    def configure(self, vmid: int, *, config: dict) -> BackendOperation: ...
    def start(self, vmid: int) -> BackendOperation: ...
    def stop(self, vmid: int) -> BackendOperation: ...
    def restart(self, vmid: int) -> BackendOperation: ...
    def destroy(self, vmid: int) -> BackendOperation: ...
    def status(self, vmid: int) -> dict: ...
    def snapshot(self, vmid: int, name: str, *, description: str = "") -> BackendOperation: ...
    def restore(self, vmid: int, name: str) -> BackendOperation: ...
    def capacity(self) -> dict: ...
    def health(self) -> BackendHealth: ...


class PublicIpBackend(Protocol):
    def reserve(self, *, reservation_key: str, label: str) -> PublicIpResource: ...
    def bind(self, resource_id: str, target_id: str) -> None: ...
    def unbind(self, resource_id: str, target_id: str) -> None: ...
    def release(self, resource_id: str, *, reservation_key: str) -> None: ...
    def get(self, resource_id: str) -> PublicIpResource: ...
    def list(self) -> list[PublicIpResource]: ...
    def health(self) -> BackendHealth: ...
    def capabilities(self) -> BackendCapabilities: ...


class GatewayBackend(Protocol):
    def ensure_mapping(self, public_ip: str, private_ip: str) -> None: ...
    def remove_mapping(self, public_ip: str, private_ip: str) -> None: ...
    def get_mapping(self, public_ip: str) -> str | None: ...
    def list_mappings(self) -> dict[str, str]: ...
    def verify_mapping(self, public_ip: str, private_ip: str) -> bool: ...
    def health(self) -> BackendHealth: ...
