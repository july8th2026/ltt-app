"""Public-IP adapters: proven Vultr dynamic IPs and OVH pre-owned pool."""
from __future__ import annotations

from datetime import datetime, timezone

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

    It never orders or deletes provider resources. Acquisition is a separate,
    audited operator operation because checkout has billing consequences.
    """

    def __init__(self, db: Session, profile_id: str):
        self.db = db
        self.profile_id = profile_id

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
            try:
                with self.db.begin_nested():
                    result = self.db.execute(
                        update(VpsIp)
                        .where(VpsIp.id == row_id, VpsIp.state == "FREE")
                        .values(
                            state="RESERVED", reservation_token=reservation_key,
                            reserved_at=now,
                            provider_metadata={"allocation_label": str(label or "")[:80]},
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
        status = "HEALTHY" if free > 0 else "CRITICAL"
        return BackendHealth(
            status, f"{free} FREE public IP(s)",
            {"free": free, "quarantined": quarantined, "total": len(rows)},
        )

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(dynamic_acquisition=False, provider_binding=False)
