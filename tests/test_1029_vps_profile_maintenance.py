"""P4 background work never routes a pinned VM through global credentials."""
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.
from types import SimpleNamespace

from tests.test_1013_vps_pinned_provisioning import db, _profile, _instance  # noqa: F401


def test_billing_suspend_uses_pinned_compute_not_global_client(db, monkeypatch):
    from apps.vps import bao_tri
    from apps.vps.services import backend_factory, dieu_khien
    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    calls = []
    monkeypatch.setattr(backend_factory, "compute_backend", lambda p:
                        SimpleNamespace(client="pinned-compute"))
    monkeypatch.setattr(dieu_khien, "treo", lambda session, vm, client, **kwargs:
                        calls.append((vm.id, client)))
    bao_tri._treo_va_tat(db, "wrong-global-compute")(instance, "expired")
    assert calls == [(instance.id, "pinned-compute")]
    profile.status, profile.accept_new, profile.is_default = "DISABLED", False, False
    db.commit()
    bao_tri._treo_va_tat(db, "wrong-global-compute")(instance, "expired")
    assert calls == [(instance.id, "pinned-compute")]


def test_periodic_reconciliation_is_independent_even_when_one_profile_fails(db, monkeypatch):
    from apps.vps import bao_tri
    from apps.vps.services import backend_factory, reconciliation
    from apps.vps.services.backends.contracts import BackendConflict
    _profile(db, profile_id="broken", default=False)
    _profile(db, profile_id="healthy", default=True)
    # 26/09/2026: vong doi chieu nay BO QUA ho so khong co may lan IP
    # (`bao_tri.co_gi_de_doi_chieu` — so cua ta khong co dong nao thi khong co gi
    # de so, xem test_4015). Fixture cu khong co may nao, nen ke tu do bai nay
    # khong con do dieu no noi la do: ca hai ho so bi bo qua va `called` rong.
    #
    # ⭐ Sua bang cach cho moi ho so MOT may that, chu khong bang cach tat cua —
    #    de cau hoi cua bai ("mot ho so hong co lam chet ho so kia khong") van
    #    con duoc hoi.
    from apps.vps.tables import VpsInstance
    for ma, ho_so in (("i-broken", "broken"), ("i-healthy", "healthy")):
        db.add(VpsInstance(
            id=ma, user_id="owner", plan_id="vps-vua", os_id="winsrv2022-gui",
            gateway_id="gateway-1", infrastructure_profile_id=ho_so,
            profile_resolution_state="PINNED"))
    db.commit()
    called = []
    monkeypatch.setattr(bao_tri, "_moc_doi_chieu", 0)
    def compute(profile):
        if profile.id == "broken":
            raise BackendConflict("fixture-secret-must-not-log")
        return profile.id
    monkeypatch.setattr(backend_factory, "compute_backend", compute)
    monkeypatch.setattr(backend_factory, "public_ip_backend", lambda session, p: p.id)
    monkeypatch.setattr(backend_factory, "gateway_backend", lambda p: p.id)
    def reconcile(session, profile, **kwargs):
        assert set(kwargs.values()) == {profile.id}
        called.append(profile.id)
        return SimpleNamespace(findings=())
    monkeypatch.setattr(reconciliation, "reconcile_profile", reconcile)
    assert bao_tri._doi_chieu_profiles(db) == 0
    assert called == ["healthy"]
