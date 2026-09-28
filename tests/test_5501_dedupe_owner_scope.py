"""tests/test_5501_dedupe_owner_scope.py — ORM pha5 + dedupe theo owner_id.

Phần 1 (Task 2): xác nhận ORM đọc được cột mới `file_hash`/`favorite`/`rating`
trên `OmmiResourceVariant`, và hai bảng mới `OmmiTrash`/`OmmiImageJob` tồn tại.
Phần 2 (Task 3): `services/dedupe.py` — dedupe theo `(owner_id, file_hash)`,
⛔ không theo `file_hash` toàn cục.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'orm.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close()
    dbmod.reset_engine()


def test_variant_has_pha5_columns(db_session):
    from apps.prompt_ai_ommi.tables import OmmiResource, OmmiResourceVariant
    resource = OmmiResource(owner_id="o1", kind="character", name="X")
    db_session.add(resource); db_session.flush()
    variant = OmmiResourceVariant(
        resource_id=resource.id, owner_id="o1", storage_key="k",
        file_hash="a" * 64, favorite=True, rating=5)
    db_session.add(variant); db_session.commit()
    got = db_session.get(OmmiResourceVariant, variant.id)
    assert got.file_hash == "a" * 64
    assert got.favorite is True
    assert got.rating == 5


def test_trash_and_image_job_tables_exist(db_session):
    from apps.prompt_ai_ommi.tables import OmmiImageJob, OmmiTrash
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    trash = OmmiTrash(owner_id="o1", target_kind="resource", target_id="r1",
                      payload={"resource": {}}, deleted_at=now,
                      purge_after=now + timedelta(days=30))
    job = OmmiImageJob(owner_id="o1", params={}, status="queued")
    db_session.add_all([trash, job]); db_session.commit()
    assert db_session.get(OmmiTrash, trash.id) is not None
    assert db_session.get(OmmiImageJob, job.id).version == 1


def test_two_owners_uploading_the_same_bytes_get_two_variants(db_session):
    from apps.prompt_ai_ommi.services import dedupe, resources as rsvc
    data = b"\x89PNG" + b"\x00" * 100
    file_hash = dedupe.compute_file_hash(data)

    r1 = rsvc.create(db_session, owner_id="alice", kind="character", name="A")
    v1 = rsvc.add_variant(db_session, resource_id=r1.id, owner_id="alice",
                          storage_key="k1", file_hash=file_hash)

    r2 = rsvc.create(db_session, owner_id="bob", kind="character", name="B")
    v2 = rsvc.add_variant(db_session, resource_id=r2.id, owner_id="bob",
                          storage_key="k2", file_hash=file_hash)

    assert v1.id != v2.id
    assert dedupe.find_existing(db_session, owner_id="alice",
                                file_hash=file_hash).id == v1.id
    assert dedupe.find_existing(db_session, owner_id="bob",
                                file_hash=file_hash).id == v2.id


def test_same_owner_uploading_twice_finds_the_first_variant(db_session):
    from apps.prompt_ai_ommi.services import dedupe, resources as rsvc
    data = b"\x89PNG" + b"\x01" * 100
    file_hash = dedupe.compute_file_hash(data)

    r1 = rsvc.create(db_session, owner_id="alice", kind="character", name="A")
    v1 = rsvc.add_variant(db_session, resource_id=r1.id, owner_id="alice",
                          storage_key="k1", file_hash=file_hash)

    found = dedupe.find_existing(db_session, owner_id="alice",
                                 file_hash=file_hash)
    assert found is not None and found.id == v1.id
