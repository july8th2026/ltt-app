"""VPS V4 P2 — small backend contracts and provider-specific semantics."""
from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from platform_core.db import Base


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _profile(db: Session):
    from apps.vps.profiles import OVH_PROFILE_ID
    from apps.vps.tables import VpsInfrastructureProfile

    profile = VpsInfrastructureProfile(
        id=OVH_PROFILE_ID, slug="ovh-sgp-prod", name="OVH-SGP-PROD",
        region="sgp", environment="production", status="STANDBY",
        accept_new=False, is_default=False, compute_backend_type="proxmox",
        public_ip_backend_type="ovh_static_pool", gateway_backend_type="nft",
        credential_ref="LTT_OVH",
    )
    db.add(profile)
    db.commit()
    return profile


def test_ovh_static_pool_reserve_bind_unbind_release(db):
    from apps.vps.services.backends.public_ip import OvhStaticIpPoolBackend
    from apps.vps.tables import VpsIp

    profile = _profile(db)
    db.add(VpsIp(
        id="ip-row-1", infrastructure_profile_id=profile.id,
        gateway_id="gateway-1", dia_chi="203.0.113.10",
        backend_resource_id="ovh-resource-1", state="FREE",
        billing_mode="monthly", monthly_cost_minor=239,
    ))
    db.commit()

    backend = OvhStaticIpPoolBackend(db, profile.id)
    reserved = backend.reserve(reservation_key="op-1:IP", label="acceptance")
    assert reserved.address == "203.0.113.10"
    assert reserved.state == "RESERVED"
    assert backend.reserve(reservation_key="op-1:IP", label="ignored").id == reserved.id

    backend.bind(reserved.id, "instance-1")
    assert backend.get(reserved.id).state == "BOUND"
    backend.unbind(reserved.id, "instance-1")
    assert backend.get(reserved.id).state == "RESERVED"
    backend.release(reserved.id, reservation_key="op-1:IP")
    released = backend.get(reserved.id)
    assert released.state == "FREE" and released.instance_id is None


def test_ovh_static_pool_never_hands_same_ip_to_two_reservations(db):
    from apps.vps.services.backends.contracts import CapacityExhausted
    from apps.vps.services.backends.public_ip import OvhStaticIpPoolBackend
    from apps.vps.tables import VpsIp

    profile = _profile(db)
    db.add(VpsIp(
        infrastructure_profile_id=profile.id, gateway_id="gateway-1",
        dia_chi="203.0.113.11", backend_resource_id="ovh-resource-2", state="FREE",
    ))
    db.commit()
    backend = OvhStaticIpPoolBackend(db, profile.id)
    first = backend.reserve(reservation_key="worker-a", label="a")
    with pytest.raises(CapacityExhausted):
        backend.reserve(reservation_key="worker-b", label="b")
    assert backend.get(first.id).reservation_token == "worker-a"


def test_ovh_release_refuses_wrong_token_or_live_binding(db):
    from apps.vps.services.backends.contracts import BackendConflict
    from apps.vps.services.backends.public_ip import OvhStaticIpPoolBackend
    from apps.vps.tables import VpsIp

    profile = _profile(db)
    db.add(VpsIp(
        infrastructure_profile_id=profile.id, gateway_id="gateway-1",
        dia_chi="203.0.113.12", backend_resource_id="ovh-resource-3", state="FREE",
    ))
    db.commit()
    backend = OvhStaticIpPoolBackend(db, profile.id)
    row = backend.reserve(reservation_key="right", label="test")
    with pytest.raises(BackendConflict):
        backend.release(row.id, reservation_key="wrong")
    backend.bind(row.id, "instance-1")
    with pytest.raises(BackendConflict, match="BOUND"):
        backend.release(row.id, reservation_key="right")


class _VultrFake:
    def __init__(self):
        self.calls = []

    def tao_ip(self, label):
        self.calls.append(("tao_ip", label))
        return {"id": "vultr-ip-1", "dia_chi": "203.0.113.20", "nhan": "ltt-vps-x"}

    def gan_ip(self, resource_id, target_id):
        self.calls.append(("gan_ip", resource_id, target_id))

    def go_ip(self, resource_id):
        self.calls.append(("go_ip", resource_id))

    def xoa_ip(self, resource_id):
        self.calls.append(("xoa_ip", resource_id))

    def doc_ip(self, resource_id):
        return {"id": resource_id, "subnet": "203.0.113.20", "label": "ltt-vps-x"}

    def danh_sach_ip(self):
        return [self.doc_ip("vultr-ip-1")]

    def tai_khoan(self):
        return {"name": "configured"}


def test_vultr_adapter_preserves_proven_client_operations():
    from apps.vps.services.backends.public_ip import VultrReservedIpBackend

    client = _VultrFake()
    backend = VultrReservedIpBackend(client)
    resource = backend.reserve(reservation_key="op-2", label="machine-2")
    backend.bind(resource.id, "gateway-provider-id")
    backend.unbind(resource.id, "gateway-provider-id")
    backend.release(resource.id, reservation_key="op-2")
    assert client.calls == [
        ("tao_ip", "machine-2"),
        ("gan_ip", "vultr-ip-1", "gateway-provider-id"),
        ("go_ip", "vultr-ip-1"),
        ("xoa_ip", "vultr-ip-1"),
    ]
    assert backend.capabilities().dynamic_acquisition is True


class _GatewayFake:
    def __init__(self, mappings=None):
        self.mappings = dict(mappings or {})
        self.removed = []

    def mo_duong(self, public, private):
        self.mappings[public] = private

    def dong_duong(self, public, private):
        self.removed.append((public, private))
        self.mappings.pop(public, None)

    def danh_sach_duong(self):
        return dict(self.mappings)

    def con_song(self):
        return True


def test_gateway_backend_reads_back_and_never_removes_wrong_mapping():
    from apps.vps.services.backends.contracts import BackendConflict
    from apps.vps.services.backends.gateway import NftGatewayBackend

    client = _GatewayFake()
    backend = NftGatewayBackend(client)
    backend.ensure_mapping("203.0.113.30", "10.50.0.210")
    assert backend.verify_mapping("203.0.113.30", "10.50.0.210") is True

    client.mappings["203.0.113.30"] = "10.50.0.99"
    with pytest.raises(BackendConflict, match="wrong private"):
        backend.remove_mapping("203.0.113.30", "10.50.0.210")
    assert client.removed == []


def test_gateway_ensure_refuses_to_overwrite_another_private_mapping():
    from apps.vps.services.backends.contracts import BackendConflict
    from apps.vps.services.backends.gateway import NftGatewayBackend
    client = _GatewayFake({"203.0.113.30": "10.50.0.99"})
    with pytest.raises(BackendConflict):
        NftGatewayBackend(client).ensure_mapping("203.0.113.30", "10.50.0.210")
    assert client.mappings["203.0.113.30"] == "10.50.0.99"


@dataclass
class _ComputeFake:
    calls: list

    def tao_may(self, vmid, **config):
        self.calls.append(("create", vmid, config))
        return "UPID:create"

    def dat_cau_hinh(self, vmid, **config):
        self.calls.append(("configure", vmid, config))
        return "UPID:configure"

    def bat(self, vmid):
        self.calls.append(("start", vmid))
        return "UPID:start"

    def tat_mem(self, vmid):
        self.calls.append(("stop", vmid))
        return "UPID:stop"

    def xoa(self, vmid, **kwargs):
        self.calls.append(("destroy", vmid, kwargs))
        return "UPID:destroy"

    def trang_thai_vm(self, vmid):
        return {"vmid": vmid, "status": "stopped"}

    def phien_ban(self):
        return {"version": "test"}


@pytest.mark.parametrize("method", ["create", "configure", "start", "stop", "destroy"])
def test_compute_backend_protects_vm100_to_vm107(method):
    from apps.vps.services.backends.compute import ProxmoxComputeBackend
    from apps.vps.services.backends.contracts import ProtectedResource

    backend = ProxmoxComputeBackend(_ComputeFake([]))
    kwargs = {"config": {}} if method in {"create", "configure"} else {}
    with pytest.raises(ProtectedResource):
        getattr(backend, method)(103, **kwargs)


def test_compute_backend_wraps_existing_client_without_provider_leak():
    from apps.vps.services.backends.compute import ProxmoxComputeBackend

    fake = _ComputeFake([])
    backend = ProxmoxComputeBackend(fake)
    op = backend.create(210, config={"memory": 4096})
    assert op.external_ids == ("UPID:create",)
    assert fake.calls == [("create", 210, {"memory": 4096})]


def test_ovh_backend_source_contains_no_vultr_assumption():
    source = open("apps/vps/services/backends/public_ip.py", encoding="utf-8").read()
    ovh_source = source.split("class OvhStaticIpPoolBackend", 1)[1]
    assert "vultr_id" not in ovh_source.lower()
