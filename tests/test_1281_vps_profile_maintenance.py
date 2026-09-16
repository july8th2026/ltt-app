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
