"""VPS V4 P5 — profile preflight is independent and fail-closed."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
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


def _profile(db):
    from apps.vps.tables import VpsInfrastructureProfile
    row = VpsInfrastructureProfile(
        id="profile-1", slug="ovh-sgp-prod", name="OVH-SGP-PROD",
        region="sgp", environment="production", status="STANDBY",
        accept_new=False, is_default=False, compute_backend_type="proxmox",
        public_ip_backend_type="ovh_static_pool", gateway_backend_type="nft",
        credential_ref="LTT_OVH",
    )
    db.add(row)
    db.commit()
    return row


@dataclass
class _Health:
    status: str
    summary: str = "ok"
    details: dict | None = None


class _Compute:
    def health(self):
        return _Health("HEALTHY")

    def capacity(self):
        return {"node": {"memory": {"total": 64 * 1024**3},
                         "cpuinfo": {"cpus": 20}},
                "storage": [{"content": "images", "total": 1000 * 1024**3,
                             "used": 100 * 1024**3}], "vms": []}


class _Ip:
    def health(self):
        return _Health("HEALTHY", details={"free": 1})

    def capabilities(self):
        return type("Caps", (), {"dynamic_acquisition": False})()


class _Gateway:
    def health(self):
        return _Health("HEALTHY", details={"available_slots": 20})


def _runtime(status="HEALTHY", network="HEALTHY", storage="HEALTHY"):
    from apps.vps.services.machine_b_runtime import MachineBRuntimeEvidence
    return MachineBRuntimeEvidence(
        status=status, generated_at=datetime.now(timezone.utc),
        machine_health="CRITICAL",
        domains={"runtime": "HEALTHY", "network": network, "storage": storage},
        provenance={"schema_versions": {"health": "2.0.0"}},
    )


def test_preflight_writes_six_fresh_components_and_can_activate(db):
    from apps.vps import profiles
    from apps.vps.services.preflight import run_profile_preflight
    from apps.vps.tables import VpsProfileHealth

    profile = _profile(db)
    result = run_profile_preflight(
        db, profile, compute=_Compute(), public_ip=_Ip(), gateway=_Gateway(),
        runtime=_runtime())
    db.commit()
    assert result.ready is True
    rows = db.execute(select(VpsProfileHealth).where(
        VpsProfileHealth.infrastructure_profile_id == profile.id)).scalars().all()
    assert {row.component for row in rows} == set(profiles.REQUIRED_HEALTH_COMPONENTS)
    assert all(row.status == "HEALTHY" for row in rows)
    profiles.activate_profile(db, profile.id, make_default=True)


@pytest.mark.parametrize("runtime_status,network,storage", [
    ("STALE", "HEALTHY", "HEALTHY"),
    ("HEALTHY", "CRITICAL", "HEALTHY"),
    ("HEALTHY", "HEALTHY", "CRITICAL"),
])
def test_preflight_fails_closed_on_runtime_network_or_storage(
        db, runtime_status, network, storage):
    from apps.vps.services.preflight import run_profile_preflight
    profile = _profile(db)
    result = run_profile_preflight(
        db, profile, compute=_Compute(), public_ip=_Ip(), gateway=_Gateway(),
        runtime=_runtime(runtime_status, network, storage))
    assert result.ready is False
    assert profile.accept_new is False and profile.is_default is False


def test_static_ip_capacity_zero_blocks_profile(db):
    from apps.vps.services.preflight import run_profile_preflight
    profile = _profile(db)
    ip = _Ip()
    ip.health = lambda: _Health("CRITICAL", details={"free": 0})
    result = run_profile_preflight(
        db, profile, compute=_Compute(), public_ip=ip, gateway=_Gateway(),
        runtime=_runtime())
    assert result.ready is False
    assert result.components["capacity"] == "CRITICAL"


@pytest.mark.parametrize("failure", ["ram", "cpu", "gateway", "invalid-ip"])
def test_readable_but_unsellable_capacity_blocks_activation(db, failure):
    from apps.vps.services.preflight import run_profile_preflight

    profile, compute, ip, gateway = _profile(db), _Compute(), _Ip(), _Gateway()
    payload = compute.capacity()
    if failure == "ram":
        payload["node"]["memory"]["total"] = 1024**3
    elif failure == "cpu":
        payload["node"]["cpuinfo"]["cpus"] = 0
    elif failure == "gateway":
        gateway.health = lambda: _Health("HEALTHY", details={"available_slots": 0})
    else:
        ip.health = lambda: _Health("HEALTHY", details={"free": "invalid"})
    compute.capacity = lambda: payload
    result = run_profile_preflight(db, profile, compute=compute, public_ip=ip,
                                   gateway=gateway, runtime=_runtime())
    assert not result.ready
    assert result.components["capacity"] == "CRITICAL"
