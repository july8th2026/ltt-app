"""Public-IP adapters: proven Vultr dynamic IPs and OVH pre-owned pool."""
from __future__ import annotations

from datetime import datetime, timezone
import re

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from apps.vps.services.backends.contracts import (
    BackendCapabilities,
    BackendConflict,
    BackendHealth,
    CapacityExhausted,
    PublicIpResource,
)
from apps.vps.tables import VpsIp


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resource(row: VpsIp) -> PublicIpResource:
    return PublicIpResource(
        id=row.id,
        address=row.dia_chi,
        provider_id=row.backend_resource_id,
        state=row.state,
        instance_id=row.instance_id,
        reservation_token=row.reservation_token,
        metadata=dict(row.provider_metadata or {}),
    )


class VultrReservedIpBackend:
    """Thin adapter that preserves the existing Vultr client's safety behavior."""

    def __init__(self, client):
        self.client = client

    def reserve(self, *, reservation_key: str, label: str) -> PublicIpResource:
        # The current Vultr POST is deliberately non-retrying. Durable
        # idempotency/recovery lives in the mutation journal above this adapter.
        result = self.client.tao_ip(label)
        return PublicIpResource(
            id=str(result["id"]), address=str(result["dia_chi"]),
            provider_id=str(result["id"]), state="RESERVED",
            reservation_token=reservation_key,
            metadata={"label": str(result.get("nhan") or "")},
        )

    def bind(self, resource_id: str, target_id: str) -> None:
        self.client.gan_ip(resource_id, target_id)

    def unbind(self, resource_id: str, target_id: str) -> None:
        del target_id
        self.client.go_ip(resource_id)

    def release(self, resource_id: str, *, reservation_key: str) -> None:
        del reservation_key
        # `xoa_ip` performs the proven ownership-label readback before DELETE.
        self.client.xoa_ip(resource_id)

    def get(self, resource_id: str) -> PublicIpResource:
        row = self.client.doc_ip(resource_id)
        return PublicIpResource(
            id=str(row.get("id") or resource_id),
            address=str(row.get("subnet") or ""),
            provider_id=str(row.get("id") or resource_id), state="UNKNOWN",
            metadata={"label": str(row.get("label") or "")},
        )

    def list(self) -> list[PublicIpResource]:
        return [PublicIpResource(
            id=str(row.get("id") or ""), address=str(row.get("subnet") or ""),
            provider_id=str(row.get("id") or ""), state="UNKNOWN",
            metadata={"label": str(row.get("label") or "")},
        ) for row in self.client.danh_sach_ip()]

    def health(self) -> BackendHealth:
        self.client.tai_khoan()
        return BackendHealth("HEALTHY", "Vultr credentials accepted")

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(dynamic_acquisition=True, provider_binding=True)


class OvhStaticIpPoolBackend:
    """Race-safe allocator for Additional IPs already routed to the OVH gateway.

    Allocation stays transactional in the local pool. Q125 acquisition is a
    separate journaled service because provider checkout has a different state
    machine from reserving an already-owned row.
    """

    def __init__(self, db: Session, profile, *, acquisition_probe=None):
        self.db = db
        self.profile_id = str(getattr(profile, "id", profile))
        self._acquisition_probe = acquisition_probe
        self._acquisition_ceiling = 0
        self._accepted_contracts = ()
        # Controlled one-IP rollout uses ONLY the explicitly adopted cart. New
        # cart creation remains unavailable through production capacity.
        self.auto_acquire = False
        config = dict(getattr(profile, "provider_config", None) or {})
        network = dict(getattr(profile, "network_config", None) or {})
        contracts = config.get("accepted_contract_fingerprints")
        contracts_valid = (isinstance(contracts, list) and 0 < len(contracts) <= 10
                           and all(isinstance(value, str)
                                   and re.fullmatch(r"[0-9a-f]{64}", value)
                                   for value in contracts))
        if (config.get("auto_acquire") is True and config.get("adopt_ip_cart_id")
                and contracts_valid
                and network.get("mapping_strategy") == "ovh_gwnat"
                and getattr(profile, "status", "DISABLED") != "DISABLED"
                and acquisition_probe is not None):
            from apps.vps.services.ovh_acquisition import acquisition_policy
            try:
                _, self._acquisition_ceiling = acquisition_policy(profile)
            except BackendConflict:
                # Policy not resolvable (auto_acquire off or profile moved):
                # leave auto-acquisition disabled rather than guess a ceiling.
                pass
            else:
                self.auto_acquire = True
                # `contracts_valid` already proved a non-empty list; `or ()` only
                # tells the type checker what the guard above established.
                self._accepted_contracts = tuple(contracts or ())

    def reserve(self, *, reservation_key: str, label: str) -> PublicIpResource:
        if not reservation_key:
            raise BackendConflict("reservation key is required")
        existing = self.db.execute(
            select(VpsIp).where(
                VpsIp.infrastructure_profile_id == self.profile_id,
                VpsIp.reservation_token == reservation_key,
            )
        ).scalar_one_or_none()
        if existing is not None:
            if existing.state not in ("RESERVED", "BOUND"):
                raise BackendConflict("reservation is quarantined or no longer active")
            return _resource(existing)

        # SKIP LOCKED is effective on production PostgreSQL. The conditional
        # UPDATE remains the final arbiter and also makes SQLite tests truthful.
        candidates = self.db.execute(
            select(VpsIp.id)
            .where(
                VpsIp.infrastructure_profile_id == self.profile_id,
                VpsIp.state == "FREE",
            )
            .order_by(VpsIp.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        ).scalars().all()
        now = _now()
        for row_id in candidates:
            candidate = self.db.get(VpsIp, row_id)
            if candidate is None:
                continue
            metadata = {**dict(candidate.provider_metadata or {}),
                        "allocation_label": str(label or "")[:80]}
            try:
                with self.db.begin_nested():
                    result = self.db.execute(
                        update(VpsIp)
                        .where(VpsIp.id == row_id, VpsIp.state == "FREE")
                        .values(
                            state="RESERVED", reservation_token=reservation_key,
                            reserved_at=now,
                            provider_metadata=metadata,
                        )
                    )
                    changed = getattr(result, "rowcount", 0)
            except IntegrityError:
                predecessor = self.db.execute(select(VpsIp).where(
                    VpsIp.infrastructure_profile_id == self.profile_id,
                    VpsIp.reservation_token == reservation_key)).scalar_one_or_none()
                if predecessor is None or predecessor.state not in ("RESERVED", "BOUND"):
                    raise BackendConflict("concurrent reservation requires review") from None
                return _resource(predecessor)
            if changed == 1:
                self.db.flush()
                reserved = self.db.get(VpsIp, row_id)
                if reserved is None:
                    raise BackendConflict("reserved public IP disappeared")
                return _resource(reserved)
        raise CapacityExhausted("OVH static public-IP pool has no FREE address")

    def _locked(self, resource_id: str) -> VpsIp:
        row = self.db.execute(
            select(VpsIp).where(
                VpsIp.id == resource_id,
                VpsIp.infrastructure_profile_id == self.profile_id,
            ).with_for_update()
        ).scalar_one_or_none()
        if row is None:
            raise BackendConflict("public IP does not belong to this profile")
        return row

    def bind(self, resource_id: str, target_id: str) -> None:
        row = self._locked(resource_id)
        if row.state == "BOUND" and row.instance_id == target_id:
            return
        if row.state != "RESERVED" or row.instance_id not in (None, target_id):
            raise BackendConflict(f"cannot bind public IP in state {row.state}")
        row.instance_id = target_id
        row.state = "BOUND"
        row.bound_at = _now()
        self.db.flush()

    def unbind(self, resource_id: str, target_id: str) -> None:
        row = self._locked(resource_id)
        if row.state == "RESERVED" and row.instance_id is None:
            return
        if row.state != "BOUND" or row.instance_id != target_id:
            raise BackendConflict("public IP is bound to a different instance")
        row.instance_id = None
        row.state = "RESERVED"
        row.bound_at = None
        self.db.flush()

    def release(self, resource_id: str, *, reservation_key: str) -> None:
        row = self._locked(resource_id)
        if row.reservation_token != reservation_key:
            raise BackendConflict("reservation token does not own public IP")
        if row.state == "BOUND":
            raise BackendConflict("cannot release BOUND public IP; unbind first")
        if row.state == "QUARANTINED":
            raise BackendConflict("cannot release QUARANTINED public IP")
        row.state = "FREE"
        row.reservation_token = None
        row.reserved_at = None
        row.instance_id = None
        self.db.flush()

    def get(self, resource_id: str) -> PublicIpResource:
        return _resource(self._locked(resource_id))

    def list(self) -> list[PublicIpResource]:
        rows = self.db.execute(
            select(VpsIp).where(
                VpsIp.infrastructure_profile_id == self.profile_id)
            .order_by(VpsIp.dia_chi)
        ).scalars().all()
        return [_resource(row) for row in rows]

    def health(self) -> BackendHealth:
        rows = self.list()
        free = sum(row.state == "FREE" for row in rows)
        quarantined = sum(row.state == "QUARANTINED" for row in rows)
        replenishable = 0
        if self.auto_acquire and self._acquisition_probe is not None:
            try:
                quote = self._acquisition_probe()
                if (type(quote.quantity) is int and quote.quantity == 1
                        and quote.currency == "USD"
                        and type(quote.with_tax_minor) is int
                        and 0 < quote.with_tax_minor <= self._acquisition_ceiling
                        and quote.contract_fingerprints == self._accepted_contracts):
                    replenishable = 1
            except Exception:
                # Health is a read-only boundary; provider replies can contain
                # credential URLs/bodies and must never reach its summary.
                pass
        status = "HEALTHY" if free > 0 or replenishable else "CRITICAL"
        return BackendHealth(
            status, f"{free} FREE public IP(s)",
            {"free": free, "replenishable": replenishable,
             "quarantined": quarantined, "total": len(rows)},
        )

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            dynamic_acquisition=self.auto_acquire, provider_binding=False)
