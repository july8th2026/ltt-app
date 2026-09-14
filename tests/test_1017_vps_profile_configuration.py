"""VPS V4 — backend credential references cannot fall across profiles."""
from types import SimpleNamespace

import pytest


def test_ovh_gateway_uses_only_its_explicit_reference(monkeypatch):
    from apps.vps.services import backend_factory, gateway
    monkeypatch.setenv("LTT_VPS_GATEWAY_HOST", "wrong-vultr-host")
    monkeypatch.setenv("LTT_OVH_GATEWAY_HOST", "ovh-test-host")
    monkeypatch.setenv("LTT_OVH_GATEWAY_SSH_KEY", "test-key-path")
    captured = []
    monkeypatch.setattr(gateway, "client_tu_moi_truong", lambda env=None:
                        captured.append(env) or SimpleNamespace())
    profile = SimpleNamespace(
        gateway_backend_type="nft", public_ip_backend_type="ovh_static_pool",
        network_config={"gateway_credential_ref": "LTT_OVH_GATEWAY",
                        "mapping_strategy": "ltt_nft_maps"})
    backend_factory.gateway_backend(profile)
    assert captured[0]["LTT_VPS_GATEWAY_HOST"] == "ovh-test-host"
    assert captured[0]["LTT_VPS_GATEWAY_SSH_KEY"] == "test-key-path"
    assert "wrong-vultr-host" not in captured[0].values()


def test_compute_profile_passes_explicit_tls_certificate_name(monkeypatch):
    from apps.vps.services import backend_factory, proxmox
    monkeypatch.setenv("LTT_VPS_PROXMOX_URL", "https://192.0.2.10:8006")
    monkeypatch.setenv("LTT_VPS_PROXMOX_TOKEN_ID", "operator@pve!vps")
    monkeypatch.setenv("LTT_VPS_PROXMOX_TOKEN_SECRET", "fixture-secret")
    monkeypatch.setenv("LTT_VPS_PROXMOX_CA", "fixture-ca.pem")
    monkeypatch.setenv("LTT_VPS_PROXMOX_TLS_NAME", "pve.example.test")
    captured = []
    monkeypatch.setattr(proxmox, "client_tu_moi_truong", lambda env:
                        captured.append(env) or SimpleNamespace())
    profile = SimpleNamespace(compute_backend_type="proxmox", compute_config={
        "credential_ref": "LTT_VPS_PROXMOX"})
    backend_factory.compute_backend(profile)
    assert captured[0]["LTT_VPS_PROXMOX_TLS_NAME"] == "pve.example.test"


def test_proxmox_client_mounts_exact_certificate_name():
    from apps.vps.services.proxmox import ProxmoxClient, ProxmoxConfig

    client = ProxmoxClient(ProxmoxConfig(
        base_url="https://192.0.2.10:8006",
        token_id="operator@pve!vps",
        token_secret="fixture-secret",
        ca_bundle="fixture-ca.pem",
        tls_name="pve.example.test",
    ))
    adapter = client._session.adapters["https://"]
    assert adapter.poolmanager.connection_pool_kw["assert_hostname"] == (
        "pve.example.test")


@pytest.mark.parametrize("tls_name", ["bad name", "-pve", "pve-", "pve..lan"])
def test_proxmox_tls_certificate_name_rejects_invalid_labels(tls_name):
    from apps.vps.services.proxmox import ChuaCauHinh, doc_cau_hinh

    with pytest.raises(ChuaCauHinh, match="TLS_NAME"):
        doc_cau_hinh({
            "LTT_ENV": "production",
            "LTT_VPS_PROXMOX_URL": "https://192.0.2.10:8006",
            "LTT_VPS_PROXMOX_TOKEN_ID": "operator@pve!vps",
            "LTT_VPS_PROXMOX_TOKEN_SECRET": "fixture-secret",
            "LTT_VPS_PROXMOX_CA": "fixture-ca.pem",
            "LTT_VPS_PROXMOX_TLS_NAME": tls_name,
        })


def test_ovh_missing_gateway_reference_fails_closed():
    from apps.vps.services.backend_factory import gateway_backend
    from apps.vps.services.backends.contracts import BackendConflict
    profile = SimpleNamespace(
        gateway_backend_type="nft", public_ip_backend_type="ovh_static_pool",
        network_config={})
    with pytest.raises(BackendConflict, match="reference"):
        gateway_backend(profile)


def test_invalid_reference_is_not_a_secret_value(monkeypatch):
    from apps.vps.services.backend_factory import gateway_backend
    from apps.vps.services.backends.contracts import BackendConflict
    profile = SimpleNamespace(
        gateway_backend_type="nft", public_ip_backend_type="ovh_static_pool",
        network_config={"gateway_credential_ref": "not a canonical env name",
                        "mapping_strategy": "ltt_nft_maps"})
    with pytest.raises(BackendConflict):
        gateway_backend(profile)


@pytest.mark.parametrize("strategy", [None, "unknown"])
def test_ovh_gateway_cannot_use_unverified_mapping_driver(monkeypatch, strategy):
    from apps.vps.services import backend_factory, gateway
    from apps.vps.services.backends.contracts import UnsupportedCapability

    calls = []
    monkeypatch.setattr(gateway, "client_tu_moi_truong", lambda env=None:
                        calls.append(env) or SimpleNamespace())
    profile = SimpleNamespace(
        gateway_backend_type="nft", public_ip_backend_type="ovh_static_pool",
        network_config={"gateway_credential_ref": "LTT_OVH_GATEWAY",
                        "mapping_strategy": strategy})
    with pytest.raises(UnsupportedCapability, match="mapping"):
        backend_factory.gateway_backend(profile)
    assert calls == []


def test_ovh_gwnat_uses_explicit_compatible_client(monkeypatch):
    from apps.vps.services import backend_factory, gateway
    captured = []
    monkeypatch.setattr(gateway, "gwnat_client_tu_moi_truong", lambda env=None:
                        captured.append(env) or SimpleNamespace())
    profile = SimpleNamespace(
        gateway_backend_type="nft", public_ip_backend_type="ovh_static_pool",
        network_config={"gateway_credential_ref": "LTT_OVH_GATEWAY",
                        "mapping_strategy": "ovh_gwnat"})
    backend_factory.gateway_backend(profile)
    assert captured[0]["LTT_VPS_GATEWAY_GWNAT_HELPER"] == ""


def test_ovh_inventory_uses_only_canonical_credential_reference(monkeypatch):
    from apps.vps.services import backend_factory, ovh
    monkeypatch.setenv("LTT_OVH_APPLICATION_KEY", "fixture-ak")
    monkeypatch.setenv("LTT_OVH_APPLICATION_SECRET", "fixture-secret")
    monkeypatch.setenv("LTT_OVH_CONSUMER_KEY", "fixture-ck")
    monkeypatch.setenv("LTT_OVH_SERVICE_NAME", "fixture-service")
    captured = []
    monkeypatch.setattr(ovh, "client_tu_moi_truong", lambda env:
                        captured.append(env) or SimpleNamespace())
    profile = SimpleNamespace(
        public_ip_backend_type="ovh_static_pool", credential_ref="LTT_OVH")
    backend_factory.ovh_inventory_client(profile)
    assert captured[0]["LTT_OVH_APPLICATION_KEY"] == "fixture-ak"
    assert captured[0]["LTT_OVH_SERVICE_NAME"] == "fixture-service"
    assert "LTT_VULTR_API_KEY" not in captured[0]


def test_gwnat_client_reads_canonical_private_public_owner_rows():
    from apps.vps.services.gateway import GatewayConfig, GwnatGatewayClient
    calls = []
    client = GwnatGatewayClient(
        GatewayConfig(host="fixture", khoa="fixture"), helper="/sbin/ltt-gwnat",
        chay=lambda argv: calls.append(argv) or
        "10.50.0.11 203.0.113.11 VM100\n10.50.0.12 203.0.113.12 LTTMANAGED\n")
    assert client.danh_sach_duong() == {
        "203.0.113.11": "10.50.0.11", "203.0.113.12": "10.50.0.12"}
    client.mo_duong("203.0.113.13", "10.50.0.13")
    client.dong_duong("203.0.113.13", "10.50.0.13")
    assert calls == [
        ["/sbin/ltt-gwnat", "list"],
        ["/sbin/ltt-gwnat", "ensure", "203.0.113.13", "10.50.0.13"],
        ["/sbin/ltt-gwnat", "remove", "203.0.113.13", "10.50.0.13"],
    ]


@pytest.mark.parametrize("inventory", [
    "10.50.0.11 203.0.113.11\n",
    "10.50.0.11 203.0.113.11 A\n10.50.0.12 203.0.113.11 B\n",
    "10.50.0.11 203.0.113.11 A\n10.50.0.11 203.0.113.12 B\n",
])
def test_gwnat_client_rejects_malformed_or_duplicate_inventory(inventory):
    from apps.vps.services.gateway import GatewayConfig, GatewayError, GwnatGatewayClient
    client = GwnatGatewayClient(
        GatewayConfig(host="fixture", khoa="fixture"),
        helper="/usr/local/sbin/ltt-gwnat", chay=lambda argv: inventory)
    with pytest.raises(GatewayError):
        client.danh_sach_duong()


def test_router_profile_reference_is_explicit_and_does_not_fall_back(monkeypatch):
    from apps.vps.services import backend_factory, router
    from apps.vps.services.backends.contracts import BackendConflict
    monkeypatch.setenv("LTT_OVH_ROUTER_HOST", "pinned-router")
    monkeypatch.setenv("LTT_VPS_ROUTER_HOST", "wrong-global-router")
    captured = []
    monkeypatch.setattr(router, "client_tu_moi_truong", lambda env:
                        captured.append(env) or SimpleNamespace())
    profile = SimpleNamespace(public_ip_backend_type="ovh_static_pool", network_config={})
    with pytest.raises(BackendConflict):
        backend_factory.router_backend(profile)
    profile.network_config = {"router_credential_ref": "LTT_OVH_ROUTER"}
    backend_factory.router_backend(profile)
    assert captured[0]["LTT_VPS_ROUTER_HOST"] == "pinned-router"
    assert "wrong-global-router" not in captured[0].values()


def test_ssh_requires_existing_host_key_and_configured_known_hosts(monkeypatch, tmp_path):
    from apps.vps.services import ssh_lenh, gateway
    captured = []
    monkeypatch.setattr(ssh_lenh.subprocess, "run", lambda argv, **kwargs:
                        captured.append(argv) or SimpleNamespace(returncode=0, stdout="ok", stderr=""))
    hosts = str(tmp_path / "canonical-known-hosts")
    ssh_lenh.chay_ssh(ssh_lenh.DichDen(host="fixture", khoa="fixture", known_hosts=hosts), ["true"])
    gateway.GatewayClient(gateway.GatewayConfig(host="fixture", khoa="fixture", known_hosts=hosts))._chay_that(["true"])
    assert len(captured) == 2
    for argv in captured:
        assert "StrictHostKeyChecking=yes" in argv
        assert f"UserKnownHostsFile={hosts}" in argv
        assert not any("accept-new" in arg for arg in argv)


def test_ssh_failures_never_echo_remote_output(monkeypatch):
    from apps.vps.services import ssh_lenh, gateway
    marker = "credential-fixture-must-not-escape"
    failed = SimpleNamespace(returncode=23, stdout=marker, stderr=marker)
    monkeypatch.setattr(ssh_lenh.subprocess, "run", lambda *args, **kwargs: failed)
    with pytest.raises(ssh_lenh.SshLenhError) as ssh_error:
        ssh_lenh.chay_ssh(ssh_lenh.DichDen(host="fixture", khoa="fixture"), ["false"])
    monkeypatch.setattr(gateway.subprocess, "run", lambda *args, **kwargs: failed)
    with pytest.raises(gateway.GatewayError) as gateway_error:
        gateway.GatewayClient(gateway.GatewayConfig(host="fixture", khoa="fixture"))._chay_that(["false"])
    assert marker not in str(ssh_error.value)
    assert marker not in str(gateway_error.value)
