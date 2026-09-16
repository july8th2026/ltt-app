"""Gateway contract backed by the proven SSH/nft client."""
from __future__ import annotations

from apps.vps.services.backends.contracts import BackendConflict, BackendHealth


#: Health probe attempts before CRITICAL. Measured 16/09: one transient failure
#: at 17:14 closed sales for a whole 10-minute refresh cycle, while 5/5 probes
#: under the same account succeeded in 1.4–2.1 s right after (R13). A retry is
#: read-only (`health`, `list`), so it can never repeat a mutation.
HEALTH_ATTEMPTS = 3
HEALTH_RETRY_DELAY_S = 2.0


class NftGatewayBackend:
    def __init__(self, client, *, sleep=None):
        self.client = client
        import time
        self._sleep = sleep or time.sleep

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
        last_exc: Exception | None = None
        for attempt in range(HEALTH_ATTEMPTS):
            if attempt:
                self._sleep(HEALTH_RETRY_DELAY_S)
            try:
                if not self.client.con_song():
                    last_exc = None
                    continue
                self.list_mappings()
                return BackendHealth("HEALTHY", "gateway and mapping inventory readable")
            except Exception as exc:  # probe boundary; re-raised after retries
                last_exc = exc
        if last_exc is not None:
            raise last_exc
        return BackendHealth("CRITICAL", "gateway did not answer health probe")
