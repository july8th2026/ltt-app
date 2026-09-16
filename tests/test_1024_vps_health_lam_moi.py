"""VPS V4 R1 — health freshness follows the cadences that refresh it.

Measured 16/09: create selection demanded <=300 s health while nothing refreshed
it and the Machine B collector runs every 30 minutes, so every create was
refused "không nhận máy mới". These tests pin the fix: windows derived from the
producers' cadences, a periodic refresh that never demotes, and a strict window
kept for operator activation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

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


def _profile(db, **overrides):
    from apps.vps.tables import VpsInfrastructureProfile
    values = dict(
        id="profile-ovh", slug="ovh-sgp-prod", name="OVH-SGP-PROD",
        region="sgp", environment="production", status="ACTIVE",
        accept_new=True, is_default=True, compute_backend_type="proxmox",
        public_ip_backend_type="ovh_static_pool", gateway_backend_type="nft",
        credential_ref="LTT_OVH")
    values.update(overrides)
    row = VpsInfrastructureProfile(**values)
    db.add(row)
    db.commit()
    return row


def _health(db, profile_id, *, observed_ago, generated_ago, status="HEALTHY"):
    from apps.vps.profiles import REQUIRED_HEALTH_COMPONENTS
    from apps.vps.tables import VpsProfileHealth
    now = datetime.now(timezone.utc)
    for component in REQUIRED_HEALTH_COMPONENTS:
        db.add(VpsProfileHealth(
            infrastructure_profile_id=profile_id, component=component,
            status=status, observed_at=now - observed_ago,
            generated_at=now - generated_ago))
    db.commit()


def test_windows_are_wider_than_the_cadences_that_refresh_them():
    from apps.vps import profiles
    from apps.vps.manifest import MANIFEST

    assert MANIFEST.bao_tri_moi_giay == profiles.HEALTH_REFRESH_SECONDS
    assert profiles.HEALTH_MAX_AGE_SECONDS > 2 * profiles.HEALTH_REFRESH_SECONDS
    assert profiles.RUNTIME_MAX_AGE_SECONDS > 2 * profiles.RUNTIME_COLLECTOR_SECONDS
    assert profiles.ACTIVATION_MAX_AGE_SECONDS < profiles.HEALTH_MAX_AGE_SECONDS


def test_create_selection_accepts_health_between_two_collector_runs(db):
    from apps.vps.profiles import select_profile
    profile = _profile(db)
    # Observed one refresh ago, derived from a generation 50 minutes old: the
    # normal state between runs. The old 300 s window refused exactly this.
    _health(db, profile.id, observed_ago=timedelta(minutes=10),
            generated_ago=timedelta(minutes=50))
    assert select_profile(db, region="sgp").id == profile.id


@pytest.mark.parametrize("observed_ago,generated_ago", [
    (timedelta(minutes=30), timedelta(minutes=5)),     # refresh loop stopped
    (timedelta(minutes=5), timedelta(minutes=75)),     # collector/sync stopped
])
def test_create_selection_still_fails_closed_when_a_producer_stops(
        db, observed_ago, generated_ago):
    from apps.vps.profiles import ProfileNotReady, select_profile
    profile = _profile(db)
    _health(db, profile.id, observed_ago=observed_ago, generated_ago=generated_ago)
    with pytest.raises(ProfileNotReady):
        select_profile(db, region="sgp")


def test_operator_activation_keeps_the_strict_window(db):
    from apps.vps.profiles import ProfileNotReady, activate_profile
    profile = _profile(db, status="STANDBY", accept_new=False, is_default=False)
    _health(db, profile.id, observed_ago=timedelta(minutes=10),
            generated_ago=timedelta(minutes=10))
    with pytest.raises(ProfileNotReady, match="stale"):
        activate_profile(db, profile.id, make_default=True)


def test_reactivating_the_default_does_not_drop_it(db):
    from apps.vps.profiles import activate_profile
    profile = _profile(db)
    _health(db, profile.id, observed_ago=timedelta(seconds=5),
            generated_ago=timedelta(seconds=5))
    assert activate_profile(db, profile.id).is_default is True


def test_periodic_refresh_never_demotes_and_isolates_failures(db):
    from apps.vps import profiles
    from apps.vps.services import preflight
    from apps.vps.tables import VpsProfileHealth

    ovh = _profile(db)
    _profile(db, id="profile-vultr", slug="vultr-sgp", name="VULTR-SGP",
             status="STANDBY", accept_new=False, is_default=False)
    seen = []

    def broken(db_, row, *, demote_on_failure):
        seen.append((row.id, demote_on_failure))
        raise ConnectionError("provider says: secret-looking text")

    result = preflight.refresh_active_profiles(db, run=broken)
    assert result == {ovh.id: False}
    assert seen == [(ovh.id, False)]          # STANDBY is not probed
    db.refresh(ovh)
    assert (ovh.status, ovh.accept_new, ovh.is_default) == ("ACTIVE", True, True)
    rows = db.execute(select(VpsProfileHealth).where(
        VpsProfileHealth.infrastructure_profile_id == ovh.id)).scalars().all()
    assert {r.component for r in rows} == set(profiles.REQUIRED_HEALTH_COMPONENTS)
    assert all(r.status == "CRITICAL" and "secret" not in r.summary for r in rows)


def test_failed_periodic_preflight_keeps_default_but_closes_selection(db):
    from apps.vps.profiles import ProfileNotReady, select_profile
    from apps.vps.services.preflight import run_profile_preflight
    from apps.vps.services.machine_b_runtime import MachineBRuntimeEvidence

    profile = _profile(db)

    class _Down:
        def health(self):
            raise TimeoutError

        def capacity(self):
            raise TimeoutError

    runtime = MachineBRuntimeEvidence(
        "HEALTHY", generated_at=datetime.now(timezone.utc),
        domains={"network": "HEALTHY", "storage": "HEALTHY"})
    result = run_profile_preflight(
        db, profile, compute=_Down(), public_ip=_Down(), gateway=_Down(),
        runtime=runtime, demote_on_failure=False)
    db.commit()
    assert result.ready is False
    assert profile.accept_new is True and profile.is_default is True
    with pytest.raises(ProfileNotReady):
        select_profile(db, region="sgp")


def test_maintenance_refreshes_health_every_call_but_heavy_work_hourly(monkeypatch):
    from apps.vps import bao_tri
    from apps.vps.services import preflight

    calls = {"health": 0, "heavy": 0}

    class _Db:
        def rollback(self):
            pass

    def _session():
        yield _Db()

    monkeypatch.setattr("platform_core.db.get_session", _session)
    monkeypatch.setattr(preflight, "refresh_active_profiles",
                        lambda db: calls.__setitem__("health", calls["health"] + 1) or {"p": True})
    monkeypatch.setattr(bao_tri, "mot_luot",
                        lambda db: calls.__setitem__("heavy", calls["heavy"] + 1) or {})
    monkeypatch.setattr(bao_tri, "_luot_nang_cuoi", None)

    clock = iter([0.0, 600.0, 1200.0, 3601.0])
    for _ in range(4):
        bao_tri.chay(dong_ho=lambda: next(clock))
    assert calls == {"health": 4, "heavy": 2}


def test_health_refresh_failure_does_not_block_billing(monkeypatch):
    from apps.vps import bao_tri
    from apps.vps.services import preflight

    ran = []

    class _Db:
        def rollback(self):
            ran.append("rollback")

    def _session():
        yield _Db()

    def _boom(db):
        raise RuntimeError("db hiccup")

    monkeypatch.setattr("platform_core.db.get_session", _session)
    monkeypatch.setattr(preflight, "refresh_active_profiles", _boom)
    monkeypatch.setattr(bao_tri, "mot_luot", lambda db: ran.append("heavy") or {})
    monkeypatch.setattr(bao_tri, "_luot_nang_cuoi", None)
    bao_tri.chay(dong_ho=lambda: 0.0)
    assert ran == ["rollback", "heavy"]
