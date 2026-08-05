"""Kho tài nguyên OMMI — tầng service.

Phần lớn file này là các cách user B thử chạm vào dữ liệu của user A. Đó là
trọng tâm, không phải phần phụ: module nguồn để mọi khách hàng dùng chung một
namespace, và lỗi loại đó chỉ lộ ra khi có người thứ hai.
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import resources as svc
from apps.prompt_ai_ommi.tables import OmmiResource, OmmiResourceVariant

A = "user-a"
B = "user-b"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ommi.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


def _make(db, owner, name="Nhân vật A", kind="character"):
    row = svc.create(db, owner_id=owner, kind=kind, name=name)
    db.commit()
    return row


# ── sở hữu ─────────────────────────────────────────────────────────────────

def test_owner_reads_own_resource(db):
    row = _make(db, A)
    assert svc.get_owned(db, row.id, A).id == row.id


def test_other_user_cannot_read_resource(db):
    row = _make(db, A)
    with pytest.raises(svc.ResourceNotFound):
        svc.get_owned(db, row.id, B)


def test_missing_and_forbidden_are_indistinguishable(db):
    """Hai trường hợp phải ném CÙNG một lỗi. Nếu 'của người khác' báo khác
    'không tồn tại' thì người đi dò ID vẫn biết được bản ghi nào có thật."""
    row = _make(db, A)
    with pytest.raises(svc.ResourceNotFound) as forbidden:
        svc.get_owned(db, row.id, B)
    with pytest.raises(svc.ResourceNotFound) as missing:
        svc.get_owned(db, "khong-co-that", B)
    assert str(forbidden.value) == str(missing.value)


def test_other_user_cannot_update_or_archive(db):
    row = _make(db, A)
    with pytest.raises(svc.ResourceNotFound):
        svc.update(db, resource_id=row.id, owner_id=B, name="Đã bị sửa")
    with pytest.raises(svc.ResourceNotFound):
        svc.archive(db, resource_id=row.id, owner_id=B)
    assert db.get(OmmiResource, row.id).name == "Nhân vật A"


def test_listing_never_leaks_across_users(db):
    _make(db, A, "Của A")
    _make(db, B, "Của B")
    rows, total = svc.list_resources(db, A)
    assert total == 1
    assert [r.name for r in rows] == ["Của A"]


def test_counts_are_per_user(db):
    _make(db, A, "A1", "character")
    _make(db, A, "A2", "background")
    _make(db, B, "B1", "character")
    assert svc.count_by_kind(db, A) == {"character": 1, "background": 1,
                                        "prop": 0, "vehicle": 0, "misc": 0}


# ── catalog ────────────────────────────────────────────────────────────────

def _catalog_item(db, name="Mẫu chung"):
    row = OmmiResource(owner_id=None, kind="character", name=name)
    db.add(row)
    db.commit()
    return row


def test_catalog_is_readable_by_anyone_but_owned_by_no_one(db):
    item = _catalog_item(db)
    assert svc.get_visible(db, item.id, A).id == item.id
    assert svc.get_visible(db, item.id, B).id == item.id
    # Đọc được không có nghĩa là sửa được.
    with pytest.raises(svc.ResourceNotFound):
        svc.get_owned(db, item.id, A)


def test_catalog_is_hidden_from_the_library_unless_asked(db):
    _catalog_item(db)
    _, total = svc.list_resources(db, A)
    assert total == 0
    _, with_catalog = svc.list_resources(db, A, include_catalog=True)
    assert with_catalog == 1


def test_clone_gives_the_user_their_own_copy(db):
    item = _catalog_item(db, "Mẫu gốc")
    db.add(OmmiResourceVariant(resource_id=item.id, owner_id=None,
                               storage_key="catalog/a.png"))
    db.commit()

    copy = svc.clone_from_catalog(db, resource_id=item.id, owner_id=A)
    db.commit()

    assert copy.id != item.id and copy.owner_id == A
    svc.update(db, resource_id=copy.id, owner_id=A, name="Bản của tôi")
    db.commit()
    # Sửa bản sao không đụng tới mẫu gốc.
    assert db.get(OmmiResource, item.id).name == "Mẫu gốc"
    assert len(svc.variants(db, copy.id, A)) == 1


def test_a_private_resource_cannot_be_cloned_as_a_catalog_item(db):
    """Nếu clone không kiểm `owner_id IS NULL` thì bất kỳ ai biết ID cũng sao
    chép được tài nguyên riêng của người khác — rò rỉ đúng thứ ta đang chặn."""
    row = _make(db, A)
    with pytest.raises(svc.ResourceNotFound):
        svc.clone_from_catalog(db, resource_id=row.id, owner_id=B)


# ── ảnh, nhãn, bộ sưu tập ──────────────────────────────────────────────────

def test_first_variant_becomes_the_cover(db):
    row = _make(db, A)
    first = svc.add_variant(db, resource_id=row.id, owner_id=A,
                            storage_key="ommi/a/1.png")
    svc.add_variant(db, resource_id=row.id, owner_id=A,
                    storage_key="ommi/a/2.png")
    db.commit()
    assert db.get(OmmiResource, row.id).cover_variant_id == first.id


def test_removing_the_cover_promotes_the_next_variant(db):
    row = _make(db, A)
    first = svc.add_variant(db, resource_id=row.id, owner_id=A,
                            storage_key="ommi/a/1.png")
    second = svc.add_variant(db, resource_id=row.id, owner_id=A,
                             storage_key="ommi/a/2.png")
    db.commit()
    svc.remove_variant(db, variant_id=first.id, owner_id=A)
    db.commit()
    assert db.get(OmmiResource, row.id).cover_variant_id == second.id


def test_other_user_cannot_attach_or_remove_variants(db):
    row = _make(db, A)
    mine = svc.add_variant(db, resource_id=row.id, owner_id=A,
                           storage_key="ommi/a/1.png")
    db.commit()
    with pytest.raises(svc.ResourceNotFound):
        svc.add_variant(db, resource_id=row.id, owner_id=B,
                        storage_key="ommi/b/x.png")
    with pytest.raises(svc.ResourceNotFound):
        svc.remove_variant(db, variant_id=mine.id, owner_id=B)


def test_tags_are_scoped_per_user(db):
    a_row = _make(db, A, "Của A")
    b_row = _make(db, B, "Của B")
    svc.set_tags(db, resource_id=a_row.id, owner_id=A, names=["hero", "hero"])
    svc.set_tags(db, resource_id=b_row.id, owner_id=B, names=["hero"])
    db.commit()
    a_tags = svc.tags_of(db, a_row.id, A)
    b_tags = svc.tags_of(db, b_row.id, B)
    assert [t.name for t in a_tags] == ["hero"]
    # Cùng tên nhưng là hai bản ghi khác nhau — không dùng chung nhãn.
    assert a_tags[0].id != b_tags[0].id


def test_collection_rejects_a_resource_owned_by_someone_else(db):
    mine = _make(db, A, "Của A")
    theirs = _make(db, B, "Của B")
    collection = svc.create_collection(db, owner_id=A, name="Bộ của tôi")
    db.commit()
    with pytest.raises(svc.ResourceNotFound):
        svc.set_collection_items(db, collection_id=collection.id, owner_id=A,
                                 resource_ids=[mine.id, theirs.id])


def test_other_user_cannot_touch_a_collection(db):
    collection = svc.create_collection(db, owner_id=A, name="Bộ của tôi")
    db.commit()
    with pytest.raises(svc.ResourceNotFound):
        svc.get_owned_collection(db, collection.id, B)


# ── kiểm tra dữ liệu vào ───────────────────────────────────────────────────

def test_kind_must_be_one_of_the_five_groups(db):
    with pytest.raises(svc.ResourceError):
        svc.create(db, owner_id=A, kind="khong-co-loai-nay", name="X")


def test_name_cannot_be_blank(db):
    with pytest.raises(svc.ResourceError):
        svc.create(db, owner_id=A, kind="character", name="   ")


def test_archived_resources_leave_the_default_listing(db):
    row = _make(db, A)
    svc.archive(db, resource_id=row.id, owner_id=A)
    db.commit()
    _, total = svc.list_resources(db, A)
    assert total == 0
    _, with_archived = svc.list_resources(db, A, include_archived=True)
    assert with_archived == 1
