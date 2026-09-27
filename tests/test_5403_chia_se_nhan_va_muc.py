"""xem_truoc/nhan/dat_muc_chia_se."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'cs2.db').as_posix()}")
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


A, B = "user-a", "user-b"


def _meta(db, owner=A, name="Meta cua toi", body="noi dung goc"):
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    row = OmmiMetaPrompt(owner_id=owner, name=name, body=body)
    db.add(row); db.commit()
    return row


def test_preview_shows_name_without_cloning(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    preview = svc.xem_truoc(db, code=share.code)
    assert preview["name"] == "Meta cua toi"
    assert preview["target_kind"] == "meta_prompt"


def test_revoked_code_is_rejected_by_preview_and_receive(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    svc.thu_hoi(db, code=share.code, owner_id=A)
    db.commit()
    with pytest.raises(svc.ShareError):
        svc.xem_truoc(db, code=share.code)
    with pytest.raises(svc.ShareError):
        svc.nhan(db, code=share.code, owner_id=B)


def test_expired_code_is_rejected(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    from apps.prompt_ai_ommi.tables import OmmiShareCode
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    share.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()
    with pytest.raises(svc.ShareError):
        svc.nhan(db, code=share.code, owner_id=B)


def test_receiving_clones_an_independent_copy_and_counts_a_use(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    copy = svc.nhan(db, code=share.code, owner_id=B)
    db.commit()
    assert copy.owner_id == B
    assert copy.body == "noi dung goc"
    assert copy.id != row.id
    assert share.uses == 1
    # Sua ban sao khong dung den ban goc.
    copy.body = "da sua"
    db.commit()
    assert db.get(type(row), row.id).body == "noi dung goc"


def test_max_uses_is_enforced(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt",
                        target_id=row.id, max_uses=1)
    db.commit()
    svc.nhan(db, code=share.code, owner_id=B)
    db.commit()
    with pytest.raises(svc.ShareError):
        svc.nhan(db, code=share.code, owner_id="user-c")


def test_only_admin_sets_catalog_level(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    with pytest.raises(svc.ShareError):
        svc.dat_muc_chia_se(db, target_kind="meta_prompt", item_id=row.id,
                            owner_id=A, is_admin=False, level="catalog")
    updated = svc.dat_muc_chia_se(db, target_kind="meta_prompt", item_id=row.id,
                                  owner_id=A, is_admin=True, level="catalog")
    db.commit()
    assert updated.share_level == "catalog"


def test_owner_sets_code_level_on_their_own_item(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    updated = svc.dat_muc_chia_se(db, target_kind="meta_prompt", item_id=row.id,
                                  owner_id=A, is_admin=False, level="code")
    db.commit()
    assert updated.share_level == "code"


def test_invalid_level_is_rejected(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    with pytest.raises(svc.ShareError):
        svc.dat_muc_chia_se(db, target_kind="meta_prompt", item_id=row.id,
                            owner_id=A, is_admin=True, level="cong-khai")
