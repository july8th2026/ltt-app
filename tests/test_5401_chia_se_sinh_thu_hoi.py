"""sinh_ma/thu_hoi - vong doi co ban cua mot ma chia se."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'cs.db').as_posix()}")
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


def _meta(db, owner=A, name="Meta cua toi"):
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    row = OmmiMetaPrompt(owner_id=owner, name=name, body="noi dung")
    db.add(row); db.commit()
    return row


def test_owner_can_generate_a_code(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt",
                        target_id=row.id)
    db.commit()
    assert len(share.code) <= 12 and share.code
    assert share.uses == 0


def test_stranger_cannot_generate_a_code_for_someone_elses_item(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db, A)
    with pytest.raises(svc.ShareNotFound):
        svc.sinh_ma(db, owner_id=B, target_kind="meta_prompt", target_id=row.id)


def test_unknown_target_kind_is_rejected(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    with pytest.raises(svc.ShareError):
        svc.sinh_ma(db, owner_id=A, target_kind="khong-co", target_id=row.id)


def test_owner_can_revoke_their_own_code(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    svc.thu_hoi(db, code=share.code, owner_id=A)
    db.commit()
    assert share.revoked_at is not None


def test_stranger_cannot_revoke_someone_elses_code(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    with pytest.raises(svc.ShareNotFound):
        svc.thu_hoi(db, code=share.code, owner_id=B)
    assert share.revoked_at is None


def test_admin_can_revoke_anyones_code(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    svc.thu_hoi(db, code=share.code, owner_id=B, is_admin=True)
    db.commit()
    assert share.revoked_at is not None
