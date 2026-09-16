"""Gateway contract backed by the proven SSH/nft client."""
from __future__ import annotations

from apps.vps.services.backends.contracts import BackendConflict, BackendHealth


class NftGatewayBackend:
    def __init__(self, client):
        self.client = client

    def ensure_mapping(self, public_ip: str, private_ip: str) -> None:
        current = self.get_mapping(public_ip)
        if current is not None and current != private_ip:
            raise BackendConflict("refusing to overwrite another private mapping")
        self.client.mo_duong(public_ip, private_ip)
        if not self.verify_mapping(public_ip, private_ip):
            raise BackendConflict("gateway mapping read-back did not match")

    def remove_mapping(self, public_ip: str, private_ip: str) -> None:
        current = self.get_mapping(public_ip)
        if current is None:
            return
        if current != private_ip:
            raise BackendConflict(
                f"gateway maps public IP to wrong private address: {current}")
        self.client.dong_duong(public_ip, private_ip)
        if self.get_mapping(public_ip) is not None:
            raise BackendConflict("gateway mapping still exists after removal")

    def get_mapping(self, public_ip: str) -> str | None:
        return self.list_mappings().get(public_ip)

    def list_mappings(self) -> dict[str, str]:
        return dict(self.client.danh_sach_duong())

    def verify_mapping(self, public_ip: str, private_ip: str) -> bool:
        return self.get_mapping(public_ip) == private_ip

    def health(self) -> BackendHealth:
        if not self.client.con_song():
            return BackendHealth("CRITICAL", "gateway did not answer health probe")
        self.list_mappings()
        return BackendHealth("HEALTHY", "gateway and mapping inventory readable")
