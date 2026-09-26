"""Bang `ommi_handoff` dung mot lan, het han 30 phut (spec Pha 2 Sec 4.2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ommi-handoff.db').as_posix()}")
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


def test_roundtrip_insert_and_read_back(db_session):
    from apps.prompt_ai_ommi.tables import OmmiHandoff
    now = datetime.now(timezone.utc)
    row = OmmiHandoff(project_id="proj_1", scene_id="scene_1",
                      target_app_slug="taovideo",
                      payload={"prompt": "xin chao", "refs": [], "skipped": [],
                               "skipped_over_limit": 0,
                               "params": {"model": "seedance-2.0-mini"},
                               "tag_map": {}},
                      expires_at=now + timedelta(minutes=30))
    db_session.add(row)
    db_session.commit()
    got = db_session.get(OmmiHandoff, row.id)
    assert got is not None
    assert got.used_at is None
    assert got.payload["prompt"] == "xin chao"
    assert got.target_app_slug == "taovideo"


def test_ten_bang_mang_tien_to_cua_manifest(db_session):
    """G-1: registry tu choi nap neu ten bang lech `table_prefix`."""
    from apps.prompt_ai_ommi.manifest import MANIFEST
    from apps.prompt_ai_ommi.tables import OmmiHandoff
    assert OmmiHandoff.__tablename__.startswith(f"{MANIFEST.table_prefix}_")
