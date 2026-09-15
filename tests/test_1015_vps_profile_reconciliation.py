"""VPS V4 P6 — reconciliation is profile-scoped and never auto-deletes."""
from __future__ import annotations

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


def _rows(db):
    from apps.vps.tables import (
        VpsGateway, VpsInfrastructureProfile, VpsInstance, VpsIp,
    )
    profile = VpsInfrastructureProfile(
        id="profile-1", slug="ovh-sgp-prod", name="OVH",
        region="sgp", environment="production", status="STANDBY",
        accept_new=False, is_default=False, compute_backend_type="proxmox",
        public_ip_backend_type="ovh_static_pool", gateway_backend_type="nft",
        credential_ref="LTT_OVH",
    )
    gateway = VpsGateway(
        id="gateway-1", infrastructure_profile_id=profile.id,
        ten="gateway", vung="sgp", ip_cong_khai="203.0.113.1")
    instance = VpsInstance(
        id="instance-1", user_id="owner", plan_id="vps-vua",
        os_id="winsrv2022-gui", gateway_id=gateway.id, vmid=210,
        ip_noi_bo="10.50.0.210", trang_thai="dang_chay",
        infrastructure_profile_id=profile.id, profile_resolution_state="PINNED")
    ip = VpsIp(
        id="ip-1", infrastructure_profile_id=profile.id,
        gateway_id=gateway.id, dia_chi="203.0.113.10",
        backend_resource_id="provider-ip-1", state="BOUND",
        reservation_token="provision:instance-1:PUBLIC_IP",
        instance_id=instance.id)
    db.add_all([profile, gateway, instance, ip])
    db.commit()
    return profile


class _Compute:
    def __init__(self, vms):
        self.vms = vms

    def capacity(self):
        return {"node": {}, "storage": [], "vms": self.vms}


class _PublicIp:
    def __init__(self, rows):
        self.rows = rows

    def list(self):
        return self.rows


class _Gateway:
    def __init__(self, mappings):
        self.mappings = mappings

    def list_mappings(self):
        return self.mappings


def _resource(**overrides):
    from apps.vps.services.backends.contracts import PublicIpResource
    values = dict(
        id="ip-1", address="203.0.113.10", provider_id="provider-ip-1",
        state="BOUND", instance_id="instance-1", metadata={})
    values.update(overrides)
    return PublicIpResource(**values)


def test_reconciliation_reports_all_drift_without_mutating(db):
    from apps.vps.services.reconciliation import reconcile_profile
    profile = _rows(db)
    result = reconcile_profile(
        db, profile,
        compute=_Compute([{"vmid": 211, "name": "vps-orphan"}]),
        public_ip=_PublicIp([
            _resource(instance_id="someone-else"),
            _resource(id="provider-orphan", address="203.0.113.99",
                      provider_id="provider-orphan", state="BOUND",
                      instance_id="ghost", metadata={"label": "ltt-vps-ghost"}),
        ]),
        gateway=_Gateway({"203.0.113.10": "10.50.0.99"}),
    )
    codes = {finding.code for finding in result.findings}
    assert {"VM_MISSING", "VM_ORPHAN", "IP_BOUND_TO_WRONG_VM",
            "MAPPING_WRONG", "PROVIDER_RESOURCE_ORPHAN"} <= codes
    assert all(finding.auto_delete is False for finding in result.findings)
    assert db.get(type(profile), profile.id).status == "STANDBY"


def test_reconciliation_clean_when_three_backends_match(db):
    from apps.vps.services.reconciliation import reconcile_profile
    profile = _rows(db)
    result = reconcile_profile(
        db, profile,
        compute=_Compute([{"vmid": 210, "name": "vps-instance"}]),
        public_ip=_PublicIp([_resource()]),
        gateway=_Gateway({"203.0.113.10": "10.50.0.210"}),
    )
    assert result.findings == ()


def test_shared_compute_other_profile_instance_is_not_an_orphan(db):
    from apps.vps.services.reconciliation import reconcile_profile
    from apps.vps.tables import VpsInstance
    profile = _rows(db)
    db.add(VpsInstance(
        id="other-instance", user_id="other-owner", plan_id="vps-vua",
        os_id="winsrv2022-gui", gateway_id="other-gateway", vmid=211,
        infrastructure_profile_id="other-profile", profile_resolution_state="PINNED"))
    db.commit()
    result = reconcile_profile(
        db, profile, compute=_Compute([{"vmid": 210}, {"vmid": 211, "name": "vps-other"}]),
        public_ip=_PublicIp([_resource()]),
        gateway=_Gateway({"203.0.113.10": "10.50.0.210"}))
    assert not any(finding.code == "VM_ORPHAN" for finding in result.findings)
