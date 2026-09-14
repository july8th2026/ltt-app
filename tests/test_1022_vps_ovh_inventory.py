"""OVH read-only inventory is signed, ownership-checked and fail-closed."""
from types import SimpleNamespace

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


def _profile_and_gateway(db):
    from apps.vps.tables import VpsGateway, VpsInfrastructureProfile
    profile = VpsInfrastructureProfile(
        id="profile-1", slug="ovh", name="OVH", region="sgp",
        compute_backend_type="proxmox", public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH")
    gateway = VpsGateway(
        id="gateway-1", infrastructure_profile_id=profile.id, ten="OVH gateway",
        vung="sgp", ip_cong_khai="192.0.2.1")
    db.add_all((profile, gateway))
    db.commit()
    return profile, gateway


def _observation(address, *, owner="service-1"):
    from apps.vps.services.ovh import OvhIpObservation
    return OvhIpObservation(
        cidr=f"{address}/32", address=address, kind="failover", country="sg",
        routed_to=owner)


def test_sync_quarantines_live_baseline_and_only_frees_unmapped_ip(db):
    from apps.vps.services.inventory_sync import sync_ovh_static_pool
    from apps.vps.tables import VpsIp
    profile, gateway_row = _profile_and_gateway(db)
    provider = SimpleNamespace(
        config=SimpleNamespace(service_name="service-1"),
        list_additional_ipv4=lambda: [
            _observation("192.0.2.10"), _observation("192.0.2.11")])
    gateway = SimpleNamespace(
        list_mappings=lambda: {"192.0.2.10": "10.50.0.11"})
    result = sync_ovh_static_pool(
        db, profile, provider=provider, gateway=gateway)
    db.commit()
    rows = {row.dia_chi: row for row in db.execute(select(VpsIp)).scalars()}
    assert (result.total, result.free, result.bound, result.quarantined) == (2, 1, 0, 1)
    assert rows["192.0.2.10"].state == "QUARANTINED"
    assert rows["192.0.2.11"].state == "FREE"
    assert all(row.gateway_id == gateway_row.id for row in rows.values())
    assert rows["192.0.2.11"].provider_metadata == {
        "kind": "failover", "country": "sg", "routed_to_expected_service": True}


def test_sync_preserves_only_exact_observed_bound_ownership(db):
    from apps.vps.services.inventory_sync import sync_ovh_static_pool
    from apps.vps.tables import VpsInstance, VpsIp
    profile, gateway_row = _profile_and_gateway(db)
    instance = VpsInstance(
        id="instance-1", user_id="owner", plan_id="vps-nho", os_id="win10",
        gateway_id=gateway_row.id, infrastructure_profile_id=profile.id,
        profile_resolution_state="PINNED", ip_noi_bo="10.50.0.20")
    row = VpsIp(
        infrastructure_profile_id=profile.id, gateway_id=gateway_row.id,
        dia_chi="192.0.2.20", state="BOUND", instance_id=instance.id)
    db.add_all((instance, row))
    db.commit()
    provider = SimpleNamespace(
        config=SimpleNamespace(service_name="service-1"),
        list_additional_ipv4=lambda: [_observation("192.0.2.20")])
    exact = SimpleNamespace(list_mappings=lambda: {
        "192.0.2.20": "10.50.0.20"})
    assert sync_ovh_static_pool(db, profile, provider=provider, gateway=exact).bound == 1
    wrong = SimpleNamespace(list_mappings=lambda: {
        "192.0.2.20": "10.50.0.99"})
    assert sync_ovh_static_pool(db, profile, provider=provider, gateway=wrong).quarantined == 1
    assert row.state == "QUARANTINED"


@pytest.mark.parametrize("observations", [
    [_observation("192.0.2.30"), _observation("192.0.2.30")],
    [SimpleNamespace(cidr="192.0.2.31/24", address="192.0.2.31",
                     kind="failover", country="sg", routed_to="service-1")],
])
def test_sync_rejects_duplicate_or_inconsistent_provider_inventory(db, observations):
    from apps.vps.services.inventory_sync import InventoryConflict, sync_ovh_static_pool
    profile, _ = _profile_and_gateway(db)
    provider = SimpleNamespace(config=SimpleNamespace(service_name="service-1"),
                               list_additional_ipv4=lambda: observations)
    with pytest.raises(InventoryConflict):
        sync_ovh_static_pool(
            db, profile, provider=provider,
            gateway=SimpleNamespace(list_mappings=lambda: {}))


def test_ovh_client_signs_get_and_filters_non_additional_ipv4(monkeypatch):
    from apps.vps.services.ovh import OvhClient, OvhConfig
    calls = []

    def transport(method, url, headers):
        calls.append((method, url, headers))
        if url.endswith("/auth/time"):
            return 2_000_000_000
        if url.endswith("/vps"):
            return ["service-1"]
        if url.endswith("/ip"):
            return ["192.0.2.40/32", "2001:db8::1/128"]
        return {"type": "failover", "country": "sg",
                "routedTo": {"serviceName": "service-1"}}

    monkeypatch.setattr("apps.vps.services.ovh.time.time", lambda: 2_000_000_000)
    client = OvhClient(OvhConfig(
        application_key="fixture-ak", application_secret="fixture-secret",
        consumer_key="fixture-ck", service_name="service-1"), transport=transport)
    assert client.health() is True
    assert [row.address for row in client.list_additional_ipv4()] == ["192.0.2.40"]
    signed = [headers for _, url, headers in calls if not url.endswith("/auth/time")]
    assert signed and all(headers["X-Ovh-Signature"].startswith("$1$") for headers in signed)
    assert all("fixture-secret" not in str(headers) for headers in signed)
