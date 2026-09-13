"""VPS V4 P4 — provisioning uses only the instance's durable profile pin."""
from __future__ import annotations

import inspect
from types import SimpleNamespace

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


def _profile(db, *, profile_id="profile-1", status="ACTIVE", default=True):
    from apps.vps.tables import VpsInfrastructureProfile

    row = VpsInfrastructureProfile(
        id=profile_id, slug=profile_id, name=profile_id, region="sgp",
        environment="production", status=status,
        accept_new=status == "ACTIVE", is_default=default,
        compute_backend_type="proxmox",
        public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH",
    )
    db.add(row)
    db.commit()
    return row


def _instance(db, *, profile_id=None):
    from apps.vps.tables import VpsInstance

    row = VpsInstance(
        id="instance-1", user_id="owner", plan_id="vps-vua",
        os_id="winsrv2022-gui", gateway_id="gateway-1",
        infrastructure_profile_id=profile_id,
        profile_resolution_state="PINNED" if profile_id else "NEEDS_REVIEW",
    )
    db.add(row)
    db.commit()
    return row


def test_job_profile_loader_rejects_unpinned_and_disabled(db):
    from apps.vps import jobs

    instance = _instance(db)
    with pytest.raises(jobs.VpsJobError, match="NEEDS_REVIEW"):
        jobs._profile_for_job(db, instance)

    db.delete(instance)
    db.commit()
    profile = _profile(db, status="DISABLED", default=False)
    instance = _instance(db, profile_id=profile.id)
    with pytest.raises(jobs.VpsJobError, match="DISABLED"):
        jobs._profile_for_job(db, instance)


def test_job_profile_loader_ignores_new_default(db):
    from apps.vps import jobs

    original = _profile(db, profile_id="original", default=True)
    instance = _instance(db, profile_id=original.id)
    original.is_default = False
    replacement = _profile(db, profile_id="replacement", default=True)
    db.refresh(instance)
    assert jobs._profile_for_job(db, instance).id == "original"
    assert replacement.is_default is True


def test_jobs_core_no_longer_imports_provider_or_nft_driver_directly():
    from apps.vps import jobs

    source = inspect.getsource(jobs)
    assert "services import vultr" not in source
    assert "services import gateway" not in source
    assert "client_tu_moi_truong().mo_duong" not in source
    assert "client_tu_moi_truong().dong_duong" not in source


def test_mutation_journal_is_idempotent_and_sanitizes_external_error(db):
    from apps.vps.services import mutation_journal

    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    first = mutation_journal.intent(
        db, operation_id="provision:instance-1", instance=instance,
        step="VM_CREATE", request={"vmid": 210, "token_secret": "must-not-store"})
    db.commit()
    again = mutation_journal.intent(
        db, operation_id="provision:instance-1", instance=instance,
        step="VM_CREATE", request={"vmid": 210, "token_secret": "changed"})
    assert again.id == first.id
    assert "must-not-store" not in first.request_fingerprint
    assert "changed" not in again.request_fingerprint

    mutation_journal.needs_review(db, first, "provider response lost secret=abc")
    assert "secret=abc" not in first.last_error_detail
    assert first.state == "NEEDS_REVIEW"


def test_provision_rejects_unpinned_before_any_external_client(db, monkeypatch):
    from apps.vps import jobs
    instance = _instance(db)
    monkeypatch.setattr(jobs, "_mo_db", lambda: (db, type(
        "Gen", (), {"close": lambda self: None})()))
    monkeypatch.setattr(jobs, "client_tu_moi_truong", lambda: pytest.fail(
        "external client must not be created for unpinned instance"))
    with pytest.raises(jobs.VpsJobError, match="NEEDS_REVIEW"):
        jobs._tao_may({"instance_id": instance.id})


def _ip_context(db, monkeypatch, *, state="RESERVED"):
    from apps.vps import jobs
    from apps.vps.services import backend_factory
    from apps.vps.services.backends import OvhStaticIpPoolBackend
    from apps.vps.tables import VpsGateway, VpsIp
    from types import SimpleNamespace

    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    instance.ip_noi_bo = "10.51.0.60"
    gateway = VpsGateway(
        id="gateway-1", ten="test", vung="sgp", ip_cong_khai="192.0.2.1",
        infrastructure_profile_id=profile.id, cho_phep_ip_rieng=True)
    ip = VpsIp(
        id="pool-row-1", gateway_id=gateway.id, dia_chi="192.0.2.10",
        infrastructure_profile_id=profile.id, backend_resource_id="provider-ip-1",
        instance_id=instance.id, state=state,
        reservation_token=f"provision:{instance.id}:PUBLIC_IP")
    db.add_all([gateway, ip])
    db.commit()
    mappings = []
    external_mappings = {}
    def ensure(public, private):
        mappings.append(("ensure", (public, private)))
        external_mappings[public] = private
    monkeypatch.setattr(backend_factory, "public_ip_backend", lambda session, p:
                        OvhStaticIpPoolBackend(session, p.id))
    monkeypatch.setattr(backend_factory, "gateway_backend", lambda p:
                        SimpleNamespace(
                            ensure_mapping=ensure,
                            verify_mapping=lambda public, private: external_mappings.get(public) == private,
                            remove_mapping=lambda *args: mappings.append(("remove", args))))
    return jobs, profile, instance, gateway, ip, mappings


def test_retry_after_ip_persist_binds_reserved_ip_before_mapping(db, monkeypatch):
    jobs, profile, instance, gateway, ip, mappings = _ip_context(db, monkeypatch)
    assert jobs._cap_ip_cong_khai(
        db, instance, gateway, instance.ip_noi_bo, profile) == ip.dia_chi
    db.refresh(ip)
    assert ip.state == "BOUND"
    assert mappings == [("ensure", (ip.dia_chi, instance.ip_noi_bo))]


def test_ovh_cleanup_uses_pool_row_id_not_provider_resource_id(db, monkeypatch):
    jobs, profile, instance, gateway, ip, mappings = _ip_context(
        db, monkeypatch, state="BOUND")
    jobs._tra_ip_cong_khai(db, instance, profile)
    db.commit()
    db.refresh(ip)
    assert ip.state == "FREE"
    assert ip.instance_id is None
    assert ip.reservation_token is None
    assert mappings == [("remove", (ip.dia_chi, instance.ip_noi_bo))]


def test_quarantined_ip_cannot_be_reopened_by_provision_retry(db, monkeypatch):
    jobs, profile, instance, gateway, ip, mappings = _ip_context(
        db, monkeypatch, state="QUARANTINED")
    with pytest.raises(jobs.VpsJobError, match="QUARANTINED"):
        jobs._cap_ip_cong_khai(db, instance, gateway, instance.ip_noi_bo, profile)
    assert mappings == []


def test_ambiguous_cleanup_retains_both_addresses_and_safe_evidence(db, monkeypatch):
    from apps.vps.services import backend_factory
    from apps.vps.services.backends.contracts import BackendConflict
    from apps.vps.services.mutation_coordinator import MutationNeedsReview
    from apps.vps.tables import VpsEvent
    from sqlalchemy import select
    from types import SimpleNamespace
    jobs, profile, instance, gateway, ip, mappings = _ip_context(
        db, monkeypatch, state="BOUND")
    def fail(*args):
        raise BackendConflict("credential=do-not-persist-fixture")
    monkeypatch.setattr(backend_factory, "gateway_backend", lambda p:
                        SimpleNamespace(remove_mapping=fail))
    with pytest.raises(MutationNeedsReview):
        jobs._tra_ip_cong_khai(db, instance, profile)
    db.refresh(ip)
    assert ip.state == "QUARANTINED" and ip.instance_id == instance.id
    with pytest.raises(MutationNeedsReview):
        jobs._nha_tai_nguyen(db, instance)
    assert instance.ip_noi_bo == "10.51.0.60"
    events = db.execute(select(VpsEvent)).scalars().all()
    assert events and "do-not-persist" not in str([event.chi_tiet for event in events])


def test_unreadable_vm_inventory_does_not_authorize_existing_vm_mutation():
    from apps.vps import jobs
    from apps.vps.services.proxmox import ProxmoxError
    class Client:
        def danh_sach_vm(self):
            raise ProxmoxError("inventory unavailable")
    with pytest.raises(ProxmoxError):
        jobs._vm_da_ton_tai(Client(), 210)


def test_worker_failure_log_never_copies_remote_exception_body(db, caplog):
    from apps.vps import jobs
    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    marker = "credential=fixture-secret-must-not-log"
    jobs._danh_dau_loi(db, instance.id, RuntimeError(marker))
    assert marker not in caplog.text
    assert "RuntimeError" in caplog.text


def test_vm_create_is_journaled_and_retry_observes_identity(db, monkeypatch):
    from apps.vps import jobs
    from apps.vps.services import dinh_danh
    from apps.vps.tables import VpsExternalMutation
    from sqlalchemy import select
    from types import SimpleNamespace
    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    instance.vmid = 210
    db.commit()
    class Client:
        config = SimpleNamespace(node="node")
        exists = False
        create_calls = 0
        def danh_sach_vm(self):
            return [{"vmid": 210}] if self.exists else []
        def _goi(self, method, path):
            return {"name": "vps-instance",
                    "smbios1": dinh_danh.smbios1(instance.id)}
        def tao_may(self, vmid, **config):
            row = db.execute(select(VpsExternalMutation).where(
                VpsExternalMutation.state == "REQUESTED")).scalar_one()
            assert row.state == "REQUESTED" and row.attempts == 1
            self.create_calls += 1
            self.exists = True
            return "UPID:fixture"
    client = Client()
    monkeypatch.setattr(jobs, "_cho_tac_vu", lambda *args, **kwargs: None)
    config = {"name": "vps-instance", "smbios1": dinh_danh.smbios1(instance.id)}
    jobs._tao_vm_co_journal(db, instance, client, config, None)
    jobs._tao_vm_co_journal(db, instance, client, config, None)
    row = db.execute(select(VpsExternalMutation)).scalar_one()
    assert row.state == "OBSERVED" and client.create_calls == 1
    client.exists = False
    jobs._tao_vm_co_journal(
        db, instance, client, config, None, operation_id="rebuild:fixture-op")
    assert client.create_calls == 2


def test_dhcp_journal_refuses_to_overwrite_another_mac(db):
    from apps.vps import jobs
    from apps.vps.services.mutation_coordinator import MutationNeedsReview
    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    instance.ip_noi_bo = "10.51.0.60"
    db.commit()
    class Router:
        calls = []
        def danh_sach_dat_cho(self):
            return {"bc:24:11:00:00:01": instance.ip_noi_bo}
        def doc_bang_thong(self):
            return {}
        def dat_cho(self, *args, **kwargs):
            self.calls.append("dhcp")
        def theo_doi_bang_thong(self, *args):
            self.calls.append("bandwidth")
    router = Router()
    with pytest.raises(MutationNeedsReview):
        jobs._dat_cho_co_journal(db, instance, router)
    assert router.calls == []


def test_dhcp_and_bandwidth_retry_reads_back_without_repeat(db):
    from apps.vps import jobs
    from apps.vps.services import dinh_danh
    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    instance.ip_noi_bo = "10.51.0.60"
    db.commit()
    class Router:
        reservations, counters, calls = {}, {}, []
        def danh_sach_dat_cho(self):
            return self.reservations
        def doc_bang_thong(self):
            return self.counters
        def dat_cho(self, mac, ip, ten=""):
            self.calls.append("dhcp")
            self.reservations[mac] = ip
        def theo_doi_bang_thong(self, ip):
            self.calls.append("bandwidth")
            self.counters[ip] = (0, 0)
    router = Router()
    jobs._dat_cho_co_journal(db, instance, router)
    jobs._dat_cho_co_journal(db, instance, router)
    assert router.reservations[dinh_danh.mac(instance.id).lower()] == instance.ip_noi_bo
    assert router.calls == ["dhcp", "bandwidth"]


def test_vm_config_and_boot_are_read_back_before_retry(db, monkeypatch):
    from apps.vps import jobs
    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    instance.vmid = 210
    db.commit()
    class Client:
        config = SimpleNamespace(node="node")
        vm_config, status, calls = {}, "stopped", []
        def _goi(self, method, path):
            return self.vm_config
        def dat_cau_hinh(self, vmid, **config):
            self.calls.append("config")
            self.vm_config.update({key: value for key, value in config.items()
                                   if value != "delete"})
            for key, value in config.items():
                if value == "delete": self.vm_config.pop(key, None)
        def trang_thai_vm(self, vmid):
            return {"status": self.status}
        def bat(self, vmid):
            self.calls.append("boot")
            self.status = "running"
            return "UPID:boot"
    client = Client()
    monkeypatch.setattr(jobs.tac_vu, "cho_va_xac_minh",
                        lambda client, upid, vmid, expected, **kwargs: client.status)
    desired = {"cores": 2, "memory": 4096,
               "name": "vps-instance", "vga": "std",
               "net0": "virtio=BC:24:11:AA:BB:CC,bridge=vmbr1", "net1": "delete"}
    jobs._cau_hinh_vm_co_journal(db, instance, client, desired)
    jobs._cau_hinh_vm_co_journal(db, instance, client, desired)
    assert jobs._bat_vm_co_journal(db, instance, client, None) == "chay"
    assert jobs._bat_vm_co_journal(db, instance, client, None) == "chay"
    assert client.calls == ["config", "boot"]


def test_vm_destroy_is_journaled_and_absence_prevents_repeat(db, monkeypatch):
    from apps.vps import jobs
    from apps.vps.services import dinh_danh
    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    instance.vmid = 210
    db.commit()
    class Client:
        config = SimpleNamespace(node="node")
        exists, calls = True, []
        def danh_sach_vm(self):
            return [{"vmid": 210}] if self.exists else []
        def _goi(self, method, path):
            return {"name": "vps-instance",
                    "smbios1": dinh_danh.smbios1(instance.id)}
        def xoa(self, vmid):
            self.calls.append("destroy")
            self.exists = False
            return "UPID:destroy"
    client = Client()
    monkeypatch.setattr(jobs, "_tat_de_xoa", lambda *args, **kwargs: None)
    monkeypatch.setattr(jobs, "_cho_tac_vu", lambda *args, **kwargs: None)
    jobs._xoa_vm_co_journal(db, instance, client, operation_id="destroy:fixture")
    jobs._xoa_vm_co_journal(db, instance, client, operation_id="destroy:fixture")
    assert client.calls == ["destroy"]


def test_pinned_dhcp_cleanup_failure_does_not_allow_address_reuse(db, monkeypatch):
    from apps.vps import jobs
    from apps.vps.services import backend_factory, router
    from apps.vps.services.mutation_coordinator import MutationNeedsReview
    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    instance.ip_noi_bo = "10.51.0.60"
    db.commit()
    class FailedRouter:
        def go_cho(self, *args):
            raise router.RouterError("credential=must-not-log")
    monkeypatch.setattr(backend_factory, "router_backend", lambda profile: FailedRouter())
    with pytest.raises(MutationNeedsReview):
        jobs._go_cho_dhcp(instance, profile)
    assert instance.ip_noi_bo == "10.51.0.60"
