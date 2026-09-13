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


@pytest.mark.parametrize("strategy", [None, "ovh_gwnat", "unknown"])
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
