"""tests/test_5506_bulk_variant_ops.py."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bulk.db').as_posix()}")
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


def _setup(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="X")
    v1 = rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice",
                          storage_key="k1")
    v2 = rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice",
                          storage_key="k2")
    db_session.commit()
    return r, v1, v2


def test_bulk_favorite_sets_the_flag_on_every_selected_id(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r, v1, v2 = _setup(db_session)
    result = rsvc.bulk_update(db_session, resource_id=r.id, owner_id="alice",
                              action="favorite", ids=[v1.id, v2.id], value=True)
    db_session.commit()
    assert result["updated"] == 2
    assert db_session.get(type(v1), v1.id).favorite is True
    assert db_session.get(type(v2), v2.id).favorite is True


def test_bulk_rating_rejects_out_of_range_values(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r, v1, _v2 = _setup(db_session)
    with pytest.raises(rsvc.ResourceError):
        rsvc.bulk_update(db_session, resource_id=r.id, owner_id="alice",
                         action="rating", ids=[v1.id], value=6)


def test_bulk_delete_removes_the_variants(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r, v1, v2 = _setup(db_session)
    result = rsvc.bulk_update(db_session, resource_id=r.id, owner_id="alice",
                              action="delete", ids=[v1.id])
    db_session.commit()
    assert result["updated"] == 1
    assert db_session.get(type(v1), v1.id) is None
    assert db_session.get(type(v2), v2.id) is not None


def test_bulk_ignores_ids_belonging_to_someone_else(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r, v1, _v2 = _setup(db_session)
    other = rsvc.create(db_session, owner_id="mallory", kind="prop", name="Y")
    stolen = rsvc.add_variant(db_session, resource_id=other.id, owner_id="mallory",
                              storage_key="kx")
    db_session.commit()
    result = rsvc.bulk_update(db_session, resource_id=r.id, owner_id="alice",
                              action="favorite", ids=[v1.id, stolen.id], value=True)
    assert result["updated"] == 1
    assert db_session.get(type(stolen), stolen.id).favorite is False


def test_bulk_rejects_unknown_action(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r, v1, _v2 = _setup(db_session)
    with pytest.raises(rsvc.ResourceError):
        rsvc.bulk_update(db_session, resource_id=r.id, owner_id="alice",
                         action="teleport", ids=[v1.id])


def test_bulk_caps_the_number_of_ids_processed_per_call(db_session):
    """⭐ Trần `BULK_MAX_IDS` là MỘT hằng số — bài này khoá hành vi CẮT, không
    khoá giá trị cụ thể (⛔ không gõ số vào assert): gửi nhiều hơn trần một
    chút, chỉ đúng-bằng-trần id đầu tiên được xử lý.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="Nhieu anh")
    ids = [rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice",
                            storage_key=f"k{i}").id
           for i in range(rsvc.BULK_MAX_IDS + 5)]
    db_session.commit()
    result = rsvc.bulk_update(db_session, resource_id=r.id, owner_id="alice",
                              action="favorite", ids=ids, value=True)
    assert result["updated"] == rsvc.BULK_MAX_IDS
