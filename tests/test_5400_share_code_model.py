"""Model OmmiShareCode - vong doi mot ma chia se."""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'share.db').as_posix()}")
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


def test_defaults(db):
    from apps.prompt_ai_ommi.tables import OmmiShareCode
    row = OmmiShareCode(owner_id="u1", code="abc123", target_kind="meta_prompt",
                        target_id="m1")
    db.add(row)
    db.commit()
    assert row.uses == 0
    assert row.max_uses is None
    assert row.revoked_at is None


def test_code_is_unique(db):
    from apps.prompt_ai_ommi.tables import OmmiShareCode
    db.add(OmmiShareCode(owner_id="u1", code="dup12345678", target_kind="style",
                         target_id="s1"))
    db.commit()
    db.add(OmmiShareCode(owner_id="u2", code="dup12345678", target_kind="style",
                         target_id="s2"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
