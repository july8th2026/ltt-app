"""VPS V4 P1 — profile domain, default invariant and immutable instance pin."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from platform_core.db import Base


@pytest.fixture()
def db():
    # Register canonical platform tables first; xdist ordering must not make
    # this fixture pass only because another test imported them beforehand.
    import platform_core.models as _models  # noqa: F401
    # Import registers the app-owned tables on Base before create_all.
    from apps.vps import tables as _tables  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _profile(**overrides):
    from apps.vps.tables import VpsInfrastructureProfile

    values = {
        "slug": "ovh-sgp-prod",
        "name": "OVH SGP Production",
        "region": "sgp",
        "environment": "production",
        "status": "STANDBY",
        "accept_new": False,
        "is_default": False,
        "compute_backend_type": "proxmox",
        "public_ip_backend_type": "ovh_static_pool",
        "gateway_backend_type": "nft",
        "credential_ref": "LTT_OVH",
    }
    values.update(overrides)
    return VpsInfrastructureProfile(**values)


def _healthy(db: Session, profile_id: str, *, when: datetime | None = None):
    from apps.vps.profiles import REQUIRED_HEALTH_COMPONENTS
    from apps.vps.tables import VpsProfileHealth

    observed = when or datetime.now(timezone.utc)
    for component in REQUIRED_HEALTH_COMPONENTS:
        db.add(VpsProfileHealth(
            infrastructure_profile_id=profile_id,
            component=component,
            status="HEALTHY",
            observed_at=observed,
            generated_at=observed,
        ))
    db.commit()


def test_profile_states_are_exact_and_db_rejects_invalid_default(db):
    from apps.vps.profiles import PROFILE_STATES

    assert PROFILE_STATES == ("ACTIVE", "DRAINING", "STANDBY", "DISABLED")
    db.add(_profile(status="STANDBY", accept_new=False, is_default=True))
    with pytest.raises(IntegrityError):
        db.commit()


def test_database_allows_zero_or_one_default_never_two(db):
    first = _profile(status="ACTIVE", accept_new=True, is_default=True)
    db.add(first)
    db.commit()

    db.add(_profile(
        slug="ovh-sgp-second", name="second", status="ACTIVE",
        accept_new=True, is_default=True,
    ))
    with pytest.raises(IntegrityError):
        db.commit()


def test_service_refuses_stale_health_and_activates_after_fresh_preflight(db):
    from apps.vps.profiles import ProfileNotReady, activate_profile

    profile = _profile()
    db.add(profile)
    db.commit()
    _healthy(db, profile.id, when=datetime.now(timezone.utc) - timedelta(hours=1))

    with pytest.raises(ProfileNotReady, match="stale"):
        activate_profile(db, profile.id, make_default=True, max_age_seconds=60)
    db.rollback()

    # Latest observation for every component supersedes the stale generation.
    _healthy(db, profile.id)
    active = activate_profile(db, profile.id, make_default=True)
    assert (active.status, active.accept_new, active.is_default) == (
        "ACTIVE", True, True)


@pytest.mark.parametrize("timestamp_field", ["observed_at", "generated_at"])
def test_future_health_does_not_unlock_profile_activation(db, timestamp_field):
    from apps.vps.profiles import ProfileNotReady, activate_profile
    from apps.vps.tables import VpsProfileHealth

    profile = _profile()
    db.add(profile)
    db.commit()
    _healthy(db, profile.id)
    row = db.execute(select(VpsProfileHealth).where(
        VpsProfileHealth.infrastructure_profile_id == profile.id,
        VpsProfileHealth.component == "runtime")).scalar_one()
    setattr(row, timestamp_field, datetime.now(timezone.utc) + timedelta(hours=1))
    db.commit()
    with pytest.raises(ProfileNotReady, match="future"):
        activate_profile(db, profile.id)


def test_unhealthy_profile_still_reports_when_it_was_observed(db):
    from apps.vps.profiles import health_prerequisites
    from apps.vps.tables import VpsProfileHealth
    profile = _profile()
    db.add(profile)
    db.flush()
    observed = datetime.now(timezone.utc)
    db.add(VpsProfileHealth(
        infrastructure_profile_id=profile.id, component="compute",
        status="CRITICAL", observed_at=observed, generated_at=observed))
    db.commit()
    ready, reason, latest = health_prerequisites(db, profile.id)
    assert ready is False and "compute=CRITICAL" in reason
    assert latest is not None


def test_fresh_observation_of_old_generation_does_not_unlock_profile(db):
    from apps.vps.profiles import ProfileNotReady, activate_profile
    from apps.vps.tables import VpsProfileHealth

    profile = _profile()
    db.add(profile)
    db.commit()
    _healthy(db, profile.id)
    row = db.execute(select(VpsProfileHealth).where(
        VpsProfileHealth.infrastructure_profile_id == profile.id,
        VpsProfileHealth.component == "runtime")).scalar_one()
    row.generated_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()
    with pytest.raises(ProfileNotReady, match="stale"):
        activate_profile(db, profile.id)


def test_changing_default_does_not_repin_existing_instance(db):
    from apps.vps.profiles import activate_profile, pin_instance
    from apps.vps.tables import VpsInstance

    ovh = _profile()
    vultr = _profile(
        slug="vultr-sgp", name="Vultr SGP",
        public_ip_backend_type="vultr_reserved_ip",
        credential_ref="LTT_VULTR",
    )
    db.add_all([ovh, vultr])
    db.commit()
    _healthy(db, ovh.id)
    _healthy(db, vultr.id)
    activate_profile(db, ovh.id, make_default=True)

    instance = VpsInstance(
        user_id="owner", plan_id="nho", os_id="windows-server-2022",
        gateway_id="gateway-1",
    )
    pin_instance(instance, ovh)
    db.add(instance)
    db.commit()

    activate_profile(db, vultr.id, make_default=True)
    db.refresh(instance)
    assert instance.infrastructure_profile_id == ovh.id
    assert instance.profile_resolution_state == "PINNED"


def test_selector_uses_region_and_never_accepts_customer_profile_id(db):
    from apps.vps.profiles import ProfileNotReady, select_profile

    ovh = _profile()
    db.add(ovh)
    db.commit()
    _healthy(db, ovh.id)
    from apps.vps.profiles import activate_profile
    activate_profile(db, ovh.id, make_default=True)

    assert select_profile(db, region="sgp").id == ovh.id
    with pytest.raises(ProfileNotReady, match="region"):
        select_profile(db, region="vn")

    # There deliberately is no selector argument by provider/profile.
    with pytest.raises(TypeError):
        select_profile(db, region="sgp", profile_id=ovh.id)


def test_mutation_journal_idempotency_key_is_unique(db):
    from apps.vps.tables import VpsExternalMutation

    first = VpsExternalMutation(
        operation_id="op-1", instance_id="instance-1", profile_id="profile-1",
        step="VM_CREATE", idempotency_key="op-1:VM_CREATE",
    )
    second = VpsExternalMutation(
        operation_id="op-1", instance_id="instance-1", profile_id="profile-1",
        step="VM_CREATE", idempotency_key="op-1:VM_CREATE",
    )
    db.add(first)
    db.commit()
    db.add(second)
    with pytest.raises(IntegrityError):
        db.commit()


def test_seed_profiles_exist_but_migration_does_not_activate_unverified_ovh():
    from apps.vps.profiles import OVH_PROFILE_ID, VULTR_PROFILE_ID

    assert OVH_PROFILE_ID != VULTR_PROFILE_ID
    path = "alembic/versions/20260912_1000_vps_v4_profiles.py"
    source = open(path, encoding="utf-8").read()
    assert "OVH-SGP-PROD" in source
    assert "VULTR-SGP" in source
    assert '"STANDBY"' in source
    assert "vultr_id" in source and "NEEDS_REVIEW" in source
    assert "def downgrade" in source and "op.drop_table" in source


def test_models_expose_relational_profile_fields_not_secret_values():
    from apps.vps.tables import (VpsGateway, VpsInfrastructureProfile,
                                 VpsInstance, VpsIp)

    profile_columns = set(VpsInfrastructureProfile.__table__.columns.keys())
    assert {"status", "accept_new", "is_default", "credential_ref"} <= profile_columns
    assert not ({"api_key", "api_secret", "consumer_key", "password"} & profile_columns)
    assert "infrastructure_profile_id" in VpsInstance.__table__.columns
    assert "infrastructure_profile_id" in VpsGateway.__table__.columns
    assert {"infrastructure_profile_id", "backend_resource_id", "state"} <= set(
        VpsIp.__table__.columns.keys())


@pytest.fixture(scope="module")
def profile_pg():
    if os.environ.get("LTT_VPS_PG_TEST") != "1":
        pytest.skip("set LTT_VPS_PG_TEST=1 for an isolated real PostgreSQL schema")
    from tools import do_migration_tren_postgres as scratch
    from apps.vps.tables import VpsExternalMutation, VpsInfrastructureProfile, VpsIp
    live = scratch._doc_env("LTT_DATABASE_URL")
    if not live:
        pytest.skip("canonical PostgreSQL configuration is unavailable")
    name = "ltt_vps_v4_test_" + uuid.uuid4().hex
    url = scratch._url_nhap(live, name)
    scratch._dung_url(url, name, scratch._ten_csdl(live))
    scratch._tao_neu_thieu(url, name, live)
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    table = VpsInfrastructureProfile.__table__
    try:
        table.create(engine)
        VpsIp.__table__.create(engine)
        VpsExternalMutation.__table__.create(engine)
        yield engine
    finally:
        VpsExternalMutation.__table__.drop(engine, checkfirst=True)
        VpsIp.__table__.drop(engine, checkfirst=True)
        table.drop(engine, checkfirst=True)
        engine.dispose()


def test_real_postgres_profile_schema_and_default_invariant(profile_pg):
    with Session(profile_pg) as session:
        session.add(_profile(status="STANDBY", is_default=True))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(_profile(status="ACTIVE", accept_new=True, is_default=True))
        session.commit()
        session.add(_profile(slug="second", status="ACTIVE", accept_new=True, is_default=True))
        with pytest.raises(IntegrityError):
            session.commit()


def test_real_postgres_migration_up_down_preserves_legacy_rows(profile_pg, monkeypatch):
    import importlib.util
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    spec = importlib.util.spec_from_file_location(
        "vps_v4_migration", "alembic/versions/20260912_1000_vps_v4_profiles.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    schema = "vps_migration_" + uuid.uuid4().hex
    with profile_pg.begin() as connection:
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
        metadata = sa.MetaData()
        gateway = sa.Table("vps_gateway", metadata, sa.Column("id", sa.String(36), primary_key=True))
        instance = sa.Table("vps_instance", metadata,
                            sa.Column("id", sa.String(36), primary_key=True))
        ip = sa.Table("vps_ip", metadata,
                      sa.Column("id", sa.String(36), primary_key=True),
                      sa.Column("instance_id", sa.String(36)),
                      sa.Column("vultr_id", sa.String(128)),
                      sa.Column("legacy_marker", sa.String(32)))
        metadata.create_all(connection)
        connection.execute(gateway.insert(), {"id": "legacy-gateway"})
        connection.execute(instance.insert(), [{"id": "known"}, {"id": "ambiguous"}])
        connection.execute(ip.insert(), [
            {"id": "known-ip", "instance_id": "known", "vultr_id": "fixture-provider", "legacy_marker": "keep"},
            {"id": "ambiguous-ip", "instance_id": "ambiguous", "vultr_id": "", "legacy_marker": "keep-too"}])
        before = {table: [col["name"] for col in sa.inspect(connection).get_columns(table)]
                  for table in ("vps_gateway", "vps_instance", "vps_ip")}
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        journal_columns = {col["name"] for col in sa.inspect(connection).get_columns(
            "vps_external_mutation")}
        assert "provider_metadata" in journal_columns
        rows = connection.execute(sa.text(
            "SELECT id,infrastructure_profile_id,profile_resolution_state FROM vps_instance ORDER BY id")).all()
        assert rows == [("ambiguous", None, "NEEDS_REVIEW"),
                        ("known", migration.VULTR_PROFILE_ID, "PINNED")]
        assert connection.execute(sa.text(
            "SELECT count(*) FROM vps_infrastructure_profile WHERE status='STANDBY' AND NOT accept_new AND NOT is_default")).scalar_one() == 2
        migration.downgrade()
        assert {table: [col["name"] for col in sa.inspect(connection).get_columns(table)]
                for table in before} == before
        assert connection.execute(sa.select(ip.c.legacy_marker).order_by(ip.c.id)).scalars().all() == ["keep-too", "keep"]
        assert set(sa.inspect(connection).get_table_names()) == set(before)
        # Only this UUID schema in the isolated scratch DB is removed.
        metadata.drop_all(connection)
        connection.exec_driver_sql(f'DROP SCHEMA "{schema}"')


def test_real_postgres_concurrent_default_creation_has_exactly_one_winner(profile_pg):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy import delete, func
    from apps.vps.tables import VpsInfrastructureProfile
    with profile_pg.begin() as connection:
        connection.execute(delete(VpsInfrastructureProfile))
    barrier = Barrier(2)
    def compete(number):
        with Session(profile_pg) as session:
            session.add(_profile(slug=f"default-race-{number}", status="ACTIVE",
                                 accept_new=True, is_default=True))
            barrier.wait(timeout=10)
            try:
                session.commit()
                return "won"
            except IntegrityError:
                session.rollback()
                return "lost"
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(compete, (1, 2)))
    assert sorted(results) == ["lost", "won"]
    with Session(profile_pg) as session:
        assert session.execute(select(func.count()).select_from(VpsInfrastructureProfile).where(
            VpsInfrastructureProfile.is_default.is_(True))).scalar_one() == 1


def test_real_postgres_two_ip_allocators_each_get_a_distinct_free_row(profile_pg):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from apps.vps.services.backends.public_ip import OvhStaticIpPoolBackend
    from apps.vps.tables import VpsIp
    with Session(profile_pg) as session:
        profile = _profile(slug="ip-race")
        session.add(profile)
        session.flush()
        profile_id = profile.id
        session.add_all([VpsIp(id=f"race-ip-{n}", infrastructure_profile_id=profile_id,
                              gateway_id="fixture-gateway", dia_chi=f"192.0.2.{n}", state="FREE")
                         for n in (1, 2)])
        session.commit()
    barrier = Barrier(2)
    def reserve(number):
        with Session(profile_pg) as session:
            barrier.wait(timeout=10)
            resource = OvhStaticIpPoolBackend(session, profile_id).reserve(
                reservation_key=f"ip-race-{number}", label="fixture")
            session.commit()
            return resource.id
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, (1, 2)))
    assert set(results) == {"race-ip-1", "race-ip-2"}


def test_real_postgres_concurrent_intent_adopts_one_exact_row(profile_pg):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from types import SimpleNamespace
    from apps.vps.services import mutation_journal
    with Session(profile_pg) as session:
        profile = _profile(slug="intent-race")
        session.add(profile)
        session.commit()
        profile_id = profile.id
    barrier = Barrier(2)
    instance = SimpleNamespace(id="intent-instance", infrastructure_profile_id=profile_id)
    def create(_number):
        with Session(profile_pg) as session:
            barrier.wait(timeout=10)
            row = mutation_journal.intent(
                session, operation_id="same-operation", instance=instance,
                step="VM_CREATE", request={"vmid": 220})
            session.commit()
            return row.id
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, (1, 2)))
    assert len(set(results)) == 1
    from apps.vps.tables import VpsExternalMutation
    evidence = {"cart_id": "fixture-cart", "item_id": 77, "order_id": 9001,
                "baseline": ["192.0.2.10/32"], "phase": "ORDERED"}
    with Session(profile_pg) as session:
        row = session.get(VpsExternalMutation, results[0])
        row.provider_metadata = evidence
        session.commit()
    with Session(profile_pg) as session:
        assert session.get(VpsExternalMutation, results[0]).provider_metadata == evidence
