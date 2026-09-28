"""tests/test_5502_thung_rac_restore_purge.py — xoá thật, khôi phục đúng, purge sạch.

⭐ Bất biến trung tâm của tệp này: xoá → thùng rác → khôi phục PHẢI là một
VÒNG KÍN — `khôi_phục(xoá(x))` cho lại ĐÚNG `x`, kiểm TỪNG TRƯỜNG chứ không
chỉ kiểm `id` tồn tại. Một vòng làm rơi `rating`/`file_hash`/`favorite` vẫn
"khôi phục thành công" nếu chỉ kiểm `id` — bài `test_restore_round_trips_
every_field_not_just_the_id` tồn tại để bắt đúng lớp lỗi đó.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'trash.db').as_posix()}")
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


def test_delete_moves_to_trash_and_restore_brings_back_the_same_row(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc, thung_rac
    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="Kiem")
    rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice",
                     storage_key="k1")
    original_id = r.id
    db_session.commit()

    trash = thung_rac.delete_resource(db_session, resource_id=original_id,
                                      owner_id="alice")
    db_session.commit()

    with pytest.raises(rsvc.ResourceNotFound):
        rsvc.get_owned(db_session, original_id, "alice")

    restored = thung_rac.restore(db_session, trash_id=trash.id, owner_id="alice")
    db_session.commit()

    assert restored.id == original_id
    again = rsvc.get_owned(db_session, original_id, "alice")
    assert again.name == "Kiem"
    assert len(rsvc.variants(db_session, original_id, "alice")) == 1


def test_restore_round_trips_every_field_not_just_the_id(db_session):
    """⭐ Bất biến vòng kín — kiểm TỪNG TRƯỜNG của resource lẫn variant.

    Một cài đặt chỉ giữ `id` mà quên `rating`/`file_hash`/`favorite` vẫn làm
    bài `test_delete_moves_to_trash_and_restore_brings_back_the_same_row`
    (chỉ kiểm `name`) đi qua — đây là bài bắt đúng lớp thiếu đó.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc, thung_rac
    r = rsvc.create(db_session, owner_id="alice", kind="character", name="Nhan vat A",
                    description="Mo ta", prompt_text="prompt goc",
                    attributes={"mau_toc": "den"})
    v = rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice",
                         storage_key="k1", label="Anh 1", width=800, height=600,
                         bytes_size=12345, file_hash="f" * 64)
    v.favorite = True
    v.rating = 4
    db_session.commit()
    original_resource_id, original_variant_id = r.id, v.id

    trash = thung_rac.delete_resource(db_session, resource_id=original_resource_id,
                                      owner_id="alice")
    db_session.commit()

    restored = thung_rac.restore(db_session, trash_id=trash.id, owner_id="alice")
    db_session.commit()

    assert restored.id == original_resource_id
    assert restored.kind == "character"
    assert restored.name == "Nhan vat A"
    assert restored.description == "Mo ta"
    assert restored.prompt_text == "prompt goc"
    assert restored.attributes == {"mau_toc": "den"}

    variants = rsvc.variants(db_session, original_resource_id, "alice")
    assert len(variants) == 1
    got = variants[0]
    assert got.id == original_variant_id
    assert got.label == "Anh 1"
    assert got.storage_key == "k1"
    assert got.width == 800 and got.height == 600
    assert got.bytes_size == 12345
    assert got.file_hash == "f" * 64
    assert got.favorite is True
    assert got.rating == 4


def test_purge_removes_expired_entries_and_their_files(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc, thung_rac

    class _FakeStorage:
        def __init__(self):
            self.deleted = []

        def delete(self, key):
            self.deleted.append(key)

    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="Cu")
    rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice",
                     storage_key="stale-key")
    db_session.commit()
    trash = thung_rac.delete_resource(db_session, resource_id=r.id,
                                      owner_id="alice", purge_after_days=1)
    db_session.commit()

    future = datetime.now(timezone.utc) + timedelta(days=2)
    storage = _FakeStorage()
    result = thung_rac.purge_expired(db_session, now=future, storage=storage)
    db_session.commit()

    assert result["da_xoa_ban"] == 1
    assert storage.deleted == ["stale-key"]
    with pytest.raises(rsvc.ResourceNotFound):
        # Đã purge — restore không còn hiệu lực.
        thung_rac.restore(db_session, trash_id=trash.id, owner_id="alice")


def test_purge_leaves_no_orphan_variant_rows(db_session):
    """⭐ Sau purge, KHÔNG hàng `OmmiResourceVariant` nào còn trỏ tới resource
    đã mất — kiểm bằng một truy vấn đếm, không suy từ việc `delete_resource`
    "đã xoá variant trước". Đây là bất biến cấu trúc, không phải hành vi ngẫu
    nhiên của cài đặt hiện tại.
    """
    from sqlalchemy import select
    from apps.prompt_ai_ommi.services import resources as rsvc, thung_rac
    from apps.prompt_ai_ommi.tables import OmmiResourceVariant

    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="Bi mo coi")
    rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice", storage_key="k1")
    rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice", storage_key="k2")
    resource_id = r.id
    db_session.commit()

    thung_rac.delete_resource(db_session, resource_id=resource_id, owner_id="alice",
                              purge_after_days=0)
    db_session.commit()
    future = datetime.now(timezone.utc) + timedelta(seconds=1)
    thung_rac.purge_expired(db_session, now=future)
    db_session.commit()

    orphan_count = db_session.execute(
        select(OmmiResourceVariant.id)
        .where(OmmiResourceVariant.resource_id == resource_id)
    ).scalars().all()
    assert orphan_count == []


def test_restore_reflects_the_current_trash_payload_deterministically(db_session):
    """⭐ Ca tiêm lỗi: xoá x, SỬA payload trong thùng rác, khôi phục.

    `restore()` không giữ cache nào ngoài `OmmiTrash.payload` — nó dựng lại
    ĐÚNG những gì đang nằm trong `payload` TẠI THỜI ĐIỂM gọi, không phải bản
    chụp cũ hơn. Hành vi này là CHỦ Ý (ghi trong docstring của `restore()`):
    ai sửa `payload` sau khi xoá thì bản sửa đó thắng — không có merge, không
    có "giữ bản gốc". Bài này khẳng định tính DỨT KHOÁT đó thay vì để nó là
    một chi tiết cài đặt không ai kiểm.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc, thung_rac
    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="Ten goc")
    db_session.commit()
    trash = thung_rac.delete_resource(db_session, resource_id=r.id, owner_id="alice")
    db_session.commit()

    # Mô phỏng một thao tác ngoài luồng sửa trực tiếp payload trong thùng rác.
    trash.payload = {**trash.payload,
                     "resource": {**trash.payload["resource"], "name": "Ten da sua"}}
    db_session.commit()

    restored = thung_rac.restore(db_session, trash_id=trash.id, owner_id="alice")
    db_session.commit()
    assert restored.name == "Ten da sua"


def test_restore_rejects_a_ticket_that_is_not_yours(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc, thung_rac
    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="X")
    db_session.commit()
    trash = thung_rac.delete_resource(db_session, resource_id=r.id, owner_id="alice")
    db_session.commit()
    with pytest.raises(rsvc.ResourceNotFound):
        thung_rac.restore(db_session, trash_id=trash.id, owner_id="mallory")
