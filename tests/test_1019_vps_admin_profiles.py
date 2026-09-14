"""VPS profile admin uses platform operator auth, CSRF and safe evidence."""
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.
import re
from dataclasses import replace

import pytest

from tests.test_252_vps_giao_dien import (
    moi_truong,  # noqa: F401 -- imported pytest fixture
    _client, _dang_nhap, _tao_khach,
)


@pytest.fixture()
def admin_client(moi_truong, monkeypatch):
    from apps.vps import manifest
    from apps.vps.tables import VpsInfrastructureProfile
    from platform_core.models import User

    monkeypatch.setenv("LTT_VPS", "1")
    monkeypatch.setattr(manifest, "MANIFEST", replace(manifest.MANIFEST, enabled=True))
    uid = _tao_khach(moi_truong)
    gen = moi_truong.get_session()
    db = next(gen)
    db.get(User, uid).role = "admin"
    db.add(VpsInfrastructureProfile(
        id="profile-1", slug="ovh-test", name="OVH test", region="sgp",
        compute_backend_type="proxmox", public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH",
        provider_config={"api_secret": "never-render-this-value"}))
    db.commit()
    gen.close()
    client = _client()
    _dang_nhap(client)
    yield client
    client.close()


def test_vps_admin_guest_redirects_and_regular_customer_is_forbidden(moi_truong, monkeypatch):
    monkeypatch.setenv("LTT_VPS", "1")
    _tao_khach(moi_truong)
    with _client() as client:
        assert client.get("/vps/admin/cong-ha-tang").status_code == 303
        _dang_nhap(client)
        assert client.get("/vps/admin/cong-ha-tang").status_code == 403
        assert client.post("/vps/admin/profiles/profile-1/action", data={
            "action": "default"}).status_code == 403


def test_vps_admin_renders_real_profile_state_without_secret_values(admin_client):
    response = admin_client.get("/vps/admin/cong-ha-tang")
    assert response.status_code == 200
    assert "OVH test" in response.text
    assert "STANDBY" in response.text
    assert "Cổng hạ tầng" in response.text
    assert "never-render-this-value" not in response.text
    assert "api_secret" not in response.text
    assert "Compute health:" in response.text and "VM count:" in response.text
    assert "Available public IPs:" in response.text and "Provider: OVH" in response.text
    assert "LTTSTUDIOSAPP SHA" in response.text and "Machine B SHA" in response.text
    assert "Runtime generated_at" in response.text
    assert re.search(r'aria-current="true"[^>]*>.*?VPS', response.text, re.S)


def test_vps_admin_renders_only_validated_deploy_provenance(
    admin_client, moi_truong, monkeypatch,
):
    from datetime import datetime, timezone
    from apps.vps.tables import VpsProfileHealth
    from platform_core import dau_van_tay

    app_sha, machine_sha = "a" * 12, "b" * 40
    monkeypatch.setattr(dau_van_tay, "doc_da_cache", lambda: tuple({
        "commit": app_sha, "luc": "", "nguon": "fixture"}.items()))
    generated = datetime.now(timezone.utc)
    gen = moi_truong.get_session()
    db = next(gen)
    db.add(VpsProfileHealth(
        infrastructure_profile_id="profile-1", component="runtime",
        status="HEALTHY", generated_at=generated, observed_at=generated,
        provenance={"machine_b_sha": machine_sha,
                    "schema_versions": {"inventory": "2.0.0",
                                        "collector": "1.0.0"}}))
    db.commit()
    gen.close()

    response = admin_client.get("/vps/admin/cong-ha-tang")
    assert app_sha in response.text and machine_sha in response.text
    assert "collector=1.0.0" in response.text
    assert generated.isoformat() in response.text


def test_vps_admin_state_mutation_requires_csrf(admin_client):
    response = admin_client.post("/vps/admin/profiles/profile-1/action", data={
        "action": "disable"})
    assert response.status_code == 403
    assert "STANDBY" in admin_client.get("/vps/admin/cong-ha-tang").text


def test_vps_admin_refuses_default_without_health(admin_client):
    page = admin_client.get("/vps/admin/cong-ha-tang")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    response = admin_client.post("/vps/admin/profiles/profile-1/action", data={
        "action": "default", "csrf_token": token, "config_version": "1"})
    assert response.status_code == 409
    assert "STANDBY" in admin_client.get("/vps/admin/cong-ha-tang").text


def test_vps_admin_disable_is_audited_and_does_not_mutate_vm(admin_client, moi_truong):
    from platform_core.models import NhatKyAdmin
    from sqlalchemy import select
    page = admin_client.get("/vps/admin/cong-ha-tang")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    response = admin_client.post("/vps/admin/profiles/profile-1/action", data={
        "action": "disable", "csrf_token": token, "config_version": "1"})
    assert response.status_code == 303
    assert "DISABLED" in admin_client.get("/vps/admin/cong-ha-tang").text
    gen = moi_truong.get_session()
    db = next(gen)
    rows = db.execute(select(NhatKyAdmin).where(
        NhatKyAdmin.doi_tuong == "profile-1")).scalars().all()
    assert len(rows) == 1
    assert rows[0].hanh_dong == "vps_profile_disable"
    gen.close()


def test_failed_activation_persists_critical_health_and_closes_old_acceptance(
    admin_client, moi_truong, monkeypatch,
):
    from apps.vps.services import preflight
    from apps.vps.tables import VpsInfrastructureProfile, VpsProfileHealth
    from sqlalchemy import select

    gen = moi_truong.get_session()
    db = next(gen)
    row = db.get(VpsInfrastructureProfile, "profile-1")
    row.status, row.accept_new, row.is_default = "ACTIVE", True, True
    db.commit()
    gen.close()

    def broken(*args, **kwargs):
        raise RuntimeError("unsafe-provider-credential-value")

    monkeypatch.setattr(preflight, "run_configured_profile_preflight", broken)
    page = admin_client.get("/vps/admin/cong-ha-tang")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    response = admin_client.post("/vps/admin/profiles/profile-1/action", data={
        "action": "default", "csrf_token": token, "config_version": "1"})
    assert response.status_code == 409
    assert "unsafe-provider-credential-value" not in response.text
    gen = moi_truong.get_session()
    db = next(gen)
    row = db.get(VpsInfrastructureProfile, "profile-1")
    assert row.accept_new is False and row.is_default is False
    health = db.execute(select(VpsProfileHealth).where(
        VpsProfileHealth.infrastructure_profile_id == row.id)).scalars().all()
    assert len(health) == 6 and all(h.status == "CRITICAL" for h in health)
    assert all("unsafe-provider-credential-value" not in h.summary for h in health)
    gen.close()


def _save_payload(client):
    page = client.get("/vps/admin/cong-ha-tang")
    return {"csrf_token": re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1),
            "profile_id": "profile-1", "config_version": "1", "name": "Updated profile",
            "slug": "ovh-test", "region": "sgp", "ip_backend": "ovh_static_pool",
            "credential_ref": "LTT_OVH", "compute_ref": "LTT_VPS_PROXMOX",
            "runtime_ref": "LTT_OVH_MACHINE_B_RUNTIME",
            "gateway_ref": "LTT_OVH_GATEWAY", "router_ref": "LTT_OVH_ROUTER",
            "mapping_strategy": "ovh_gwnat"}


def test_profile_save_rejects_secret_value_and_stale_version(admin_client):
    data = _save_payload(admin_client)
    data["credential_ref"] = "fixture-secret-value"
    response = admin_client.post("/vps/admin/profiles/save", data=data)
    assert response.status_code == 400 and "fixture-secret-value" not in response.text
    data = _save_payload(admin_client)
    data["config_version"] = "0"
    assert admin_client.post("/vps/admin/profiles/save", data=data).status_code == 409
    data.pop("csrf_token")
    assert admin_client.post("/vps/admin/profiles/save", data=data).status_code == 403


def test_profile_save_invalidates_old_health_and_is_audited(admin_client, moi_truong):
    from apps.vps.tables import VpsProfileHealth, VpsInfrastructureProfile
    from platform_core.models import NhatKyAdmin
    from sqlalchemy import select
    assert admin_client.post("/vps/admin/profiles/save", data=_save_payload(admin_client)).status_code == 303
    gen = moi_truong.get_session()
    db = next(gen)
    row = db.get(VpsInfrastructureProfile, "profile-1")
    assert row.name == "Updated profile" and row.config_version == 2
    assert row.compute_config["runtime_ref"] == "LTT_OVH_MACHINE_B_RUNTIME"
    assert row.network_config["router_credential_ref"] == "LTT_OVH_ROUTER"
    assert not row.accept_new and not row.is_default
    assert db.execute(select(VpsProfileHealth.status).where(
        VpsProfileHealth.infrastructure_profile_id == row.id)).scalars().all() == ["UNKNOWN"] * 6
    assert db.execute(select(NhatKyAdmin.hanh_dong).where(
        NhatKyAdmin.doi_tuong == row.id)).scalars().all() == ["vps_profile_save"]
    gen.close()


def test_profile_save_cannot_retarget_existing_pinned_vm(admin_client, moi_truong):
    from apps.vps.tables import VpsInstance
    gen = moi_truong.get_session()
    db = next(gen)
    db.add(VpsInstance(id="pinned", user_id="fixture-owner", plan_id="vps-nho", os_id="win10",
                       gateway_id="fixture-gateway", infrastructure_profile_id="profile-1",
                       profile_resolution_state="PINNED"))
    db.commit()
    gen.close()
    assert admin_client.post("/vps/admin/profiles/save", data=_save_payload(admin_client)).status_code == 409


def test_admin_ip_inventory_is_read_only_and_sanitized(admin_client, moi_truong):
    from apps.vps.tables import VpsIp
    gen = moi_truong.get_session()
    db = next(gen)
    db.add(VpsIp(id="pool-row", infrastructure_profile_id="profile-1",
                 gateway_id="fixture-gateway", dia_chi="192.0.2.44",
                 state="QUARANTINED", provider_metadata={"token": "must-not-render"}))
    db.commit()
    gen.close()
    response = admin_client.get("/vps/admin/cong-ha-tang")
    assert response.status_code == 200
    assert "192.0.2.44" in response.text and "QUARANTINED" in response.text
    assert "must-not-render" not in response.text
    assert "provider_metadata" not in response.text


def test_admin_syncs_ovh_inventory_as_quarantined_without_changing_version(
    admin_client, moi_truong, monkeypatch,
):
    from apps.vps.services import backend_factory
    from apps.vps.services.ovh import OvhIpObservation
    from apps.vps.tables import VpsGateway, VpsInfrastructureProfile, VpsIp
    from platform_core.models import NhatKyAdmin
    from sqlalchemy import select
    from types import SimpleNamespace
    gen = moi_truong.get_session()
    db = next(gen)
    db.add(VpsGateway(
        id="ovh-gateway", infrastructure_profile_id="profile-1", ten="OVH fixture",
        vung="sgp", ip_cong_khai="192.0.2.1"))
    db.commit()
    gen.close()
    provider = SimpleNamespace(
        config=SimpleNamespace(service_name="service-1"),
        list_additional_ipv4=lambda: [OvhIpObservation(
            cidr="192.0.2.70/32", address="192.0.2.70", kind="failover",
            country="sg", routed_to="service-1")])
    monkeypatch.setattr(backend_factory, "ovh_inventory_client", lambda row: provider)
    monkeypatch.setattr(backend_factory, "gateway_backend", lambda row:
                        SimpleNamespace(list_mappings=lambda: {
                            "192.0.2.70": "10.50.0.11"}))
    page = admin_client.get("/vps/admin/cong-ha-tang")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    response = admin_client.post("/vps/admin/profiles/profile-1/action", data={
        "action": "sync_ip_inventory", "csrf_token": token, "config_version": "1"})
    assert response.status_code == 303
    gen = moi_truong.get_session()
    db = next(gen)
    row = db.execute(select(VpsIp)).scalar_one()
    profile = db.get(VpsInfrastructureProfile, "profile-1")
    assert row.state == "QUARANTINED" and profile.config_version == 1
    assert db.execute(select(NhatKyAdmin.hanh_dong).where(
        NhatKyAdmin.doi_tuong == "profile-1")).scalars().all() == [
            "vps_profile_sync_ip_inventory"]
    gen.close()


def test_admin_reconciliation_is_csrf_audited_and_renders_safe_codes(
    admin_client, moi_truong, monkeypatch,
):
    from apps.vps.services import admin_profiles
    from types import SimpleNamespace
    marker = "unsafe-remote-detail-must-not-render"
    monkeypatch.setattr(admin_profiles, "run_reconciliation", lambda db, row:
                        SimpleNamespace(findings=(SimpleNamespace(
                            code="VM_MISSING", instance_id="instance-safe",
                            resource_id="", detail=marker),)))
    page = admin_client.get("/vps/admin/cong-ha-tang")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    response = admin_client.post("/vps/admin/profiles/profile-1/action", data={
        "action": "reconcile", "csrf_token": token, "config_version": "1"})
    assert response.status_code == 200 and "VM_MISSING" in response.text
    assert marker not in response.text
    from platform_core.models import NhatKyAdmin
    from sqlalchemy import select
    gen = moi_truong.get_session()
    db = next(gen)
    assert db.execute(select(NhatKyAdmin.hanh_dong)).scalars().all() == [
        "vps_profile_reconcile"]
    gen.close()


def test_connection_probe_is_independent_safe_and_fail_closed(
    admin_client, moi_truong, monkeypatch,
):
    from apps.vps.services import backend_factory
    from apps.vps.tables import VpsInfrastructureProfile, VpsProfileHealth
    from sqlalchemy import select
    from types import SimpleNamespace
    healthy = SimpleNamespace(health=lambda: SimpleNamespace(status="HEALTHY"))
    monkeypatch.setattr(backend_factory, "compute_backend", lambda row: healthy)
    monkeypatch.setattr(backend_factory, "public_ip_backend", lambda db, row: healthy)
    monkeypatch.setattr(backend_factory, "ovh_inventory_client", lambda row:
                        SimpleNamespace(health=lambda: True))
    def failed_gateway(row):
        raise RuntimeError("credential=unsafe-marker")
    monkeypatch.setattr(backend_factory, "gateway_backend", failed_gateway)
    page = admin_client.get("/vps/admin/cong-ha-tang")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    response = admin_client.post("/vps/admin/profiles/profile-1/action", data={
        "action": "test_connection", "csrf_token": token, "config_version": "1"})
    assert response.status_code == 409 and "unsafe-marker" not in response.text
    gen = moi_truong.get_session()
    db = next(gen)
    row = db.get(VpsInfrastructureProfile, "profile-1")
    health = db.execute(select(VpsProfileHealth).order_by(
        VpsProfileHealth.component)).scalars().all()
    assert [(item.component, item.status) for item in health] == [
        ("compute", "HEALTHY"), ("gateway", "CRITICAL"), ("ip", "HEALTHY")]
    assert all("unsafe-marker" not in item.summary for item in health)
    assert row.accept_new is False and row.is_default is False
    gen.close()
