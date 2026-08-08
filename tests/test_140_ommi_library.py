"""Thư viện OMMI — meta prompt, đoạn prompt, phong cách.

Chạy cùng bộ khẳng định cho cả ba loại (parametrize), vì cả ba dùng chung một
service. Bỏ sót một loại là cách lỗi lọt: module nguồn có ba manager riêng và
chúng đã lệch nhau.
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import library as svc

A = "user-a"
B = "user-b"
KINDS = ["meta", "snippet", "style"]


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'lib.db').as_posix()}")
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


def _make(db, kind, owner=A, name="Mục của tôi", body="noi dung goc"):
    row = svc.create(db, kind, owner_id=owner, name=name, body=body)
    db.commit()
    return row


def _catalog(db, kind, name="Mẫu chung"):
    model = svc.KINDS[kind]
    row = model(owner_id=None, name=name, body="mau chung", is_catalog=True)
    db.add(row)
    db.commit()
    return row


# ── sở hữu ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", KINDS)
def test_owner_reads_own_item(db, kind):
    row = _make(db, kind)
    assert svc.get_owned(db, kind, row.id, A).id == row.id


@pytest.mark.parametrize("kind", KINDS)
def test_other_user_cannot_read_or_write(db, kind):
    row = _make(db, kind)
    with pytest.raises(svc.LibraryNotFound):
        svc.get_owned(db, kind, row.id, B)
    with pytest.raises(svc.LibraryNotFound):
        svc.update(db, kind, item_id=row.id, owner_id=B, name="Cướp")
    with pytest.raises(svc.LibraryNotFound):
        svc.archive(db, kind, item_id=row.id, owner_id=B)


@pytest.mark.parametrize("kind", KINDS)
def test_missing_and_forbidden_look_the_same(db, kind):
    row = _make(db, kind)
    with pytest.raises(svc.LibraryNotFound) as forbidden:
        svc.get_owned(db, kind, row.id, B)
    with pytest.raises(svc.LibraryNotFound) as missing:
        svc.get_owned(db, kind, "khong-co", B)
    assert str(forbidden.value) == str(missing.value)


@pytest.mark.parametrize("kind", KINDS)
def test_listing_is_per_user(db, kind):
    _make(db, kind, A, "Của A")
    _make(db, kind, B, "Của B")
    rows, total = svc.list_items(db, kind, A)
    assert total == 1 and rows[0].name == "Của A"


# ── catalog ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", KINDS)
def test_catalog_is_separate_from_private(db, kind):
    _make(db, kind, A, "Riêng")
    _catalog(db, kind)
    private, private_total = svc.list_items(db, kind, A)
    shared, shared_total = svc.list_items(db, kind, A, catalog=True)
    assert [r.name for r in private] == ["Riêng"] and private_total == 1
    # Catalog chung gồm hai nguồn cùng chỉ-đọc đối với khách hàng: mẫu tích hợp
    # phát hành theo code và mẫu do admin xuất bản trong DB. Cả hai vẫn phải
    # tách tuyệt đối khỏi thư viện riêng của user.
    shared_names = [r.name for r in shared]
    assert "Mẫu chung" in shared_names
    assert "Riêng" not in shared_names
    assert shared_total == len(svc.list_builtins(kind)) + 1


@pytest.mark.parametrize("kind", KINDS)
def test_catalog_is_readable_but_not_owned(db, kind):
    item = _catalog(db, kind)
    assert svc.get_visible(db, kind, item.id, A).id == item.id
    with pytest.raises(svc.LibraryNotFound):
        svc.get_owned(db, kind, item.id, A)


@pytest.mark.parametrize("kind", KINDS)
def test_clone_gives_an_independent_copy(db, kind):
    item = _catalog(db, kind, "Mẫu gốc")
    copy = svc.clone_from_catalog(db, kind, item_id=item.id, owner_id=A)
    db.commit()
    assert copy.owner_id == A and copy.cloned_from_id == item.id

    svc.update(db, kind, item_id=copy.id, owner_id=A, body="da sua")
    db.commit()
    assert db.get(svc.KINDS[kind], item.id).body == "mau chung"


@pytest.mark.parametrize("kind", KINDS)
def test_a_private_item_cannot_be_cloned_by_a_stranger(db, kind):
    row = _make(db, kind, A)
    with pytest.raises(svc.LibraryNotFound):
        svc.clone_from_catalog(db, kind, item_id=row.id, owner_id=B)


@pytest.mark.parametrize("kind", KINDS)
def test_only_admin_publishes_to_catalog(db, kind):
    row = _make(db, kind, A)
    with pytest.raises(svc.LibraryError):
        svc.publish_to_catalog(db, kind, item_id=row.id, owner_id=A,
                               is_admin=False)
    published = svc.publish_to_catalog(db, kind, item_id=row.id, owner_id=A,
                                       is_admin=True)
    db.commit()
    assert published.owner_id is None and published.is_catalog is True
    # Bản gốc vẫn là của A, không bị "chuyển" đi đâu.
    assert db.get(svc.KINDS[kind], row.id).owner_id == A


# ── phiên bản ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", ["meta", "snippet"])
def test_changing_the_body_records_a_version(db, kind):
    row = _make(db, kind, body="ban dau")
    svc.update(db, kind, item_id=row.id, owner_id=A, body="ban hai",
               note="sua lai")
    db.commit()
    history = svc.versions(db, kind, row.id, A)
    assert [v.version for v in history] == [2, 1]
    assert history[0].body == "ban hai" and history[0].note == "sua lai"


@pytest.mark.parametrize("kind", ["meta", "snippet"])
def test_renaming_alone_does_not_make_a_version(db, kind):
    """Đổi mỗi tên mà cũng đẻ phiên bản thì lịch sử đầy rác và lần sửa có ý
    nghĩa bị chôn mất."""
    row = _make(db, kind)
    svc.update(db, kind, item_id=row.id, owner_id=A, name="Tên khác")
    db.commit()
    assert [v.version for v in svc.versions(db, kind, row.id, A)] == [1]


@pytest.mark.parametrize("kind", ["meta", "snippet"])
def test_versions_of_another_user_are_not_readable(db, kind):
    row = _make(db, kind, A)
    with pytest.raises(svc.LibraryNotFound):
        svc.versions(db, kind, row.id, B)


# ── kiểm tra dữ liệu vào ───────────────────────────────────────────────────

def test_unknown_kind_is_rejected(db):
    with pytest.raises(svc.LibraryError):
        svc.create(db, "khong-co-loai", owner_id=A, name="X")


@pytest.mark.parametrize("kind", KINDS)
def test_blank_name_is_rejected(db, kind):
    with pytest.raises(svc.LibraryError):
        svc.create(db, kind, owner_id=A, name="   ")


@pytest.mark.parametrize("kind", KINDS)
def test_archived_items_leave_the_default_listing(db, kind):
    row = _make(db, kind)
    svc.archive(db, kind, item_id=row.id, owner_id=A)
    db.commit()
    assert svc.list_items(db, kind, A)[1] == 0
    assert svc.list_items(db, kind, A, include_archived=True)[1] == 1


def test_counts_are_per_user_and_per_kind(db):
    _make(db, "meta", A)
    _make(db, "style", A)
    _make(db, "style", B)
    assert svc.counts(db, A) == {"meta": 1, "snippet": 0, "style": 1}
