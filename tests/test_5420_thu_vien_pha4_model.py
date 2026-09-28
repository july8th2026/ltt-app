"""Pha 4 PROMPT AI, Lan G — xac nhan cot/bang moi tren thu_vien.py.

Dai so: 5420-5449 (Lan G). Khac dai 5400-5419 (Lan F) va 5450-5469 (Lan M).

Khung schema (cot moi tren OmmiMetaPrompt/OmmiPromptSnippet/OmmiStyle + 4 lop
OmmiImageTemplate/OmmiStoryboardFramework/OmmiSample/OmmiProfile) da duoc Lan M
viet o Task 1-3 (commit 044dbfee, xem tests/test_5450_*). Bai nay la lop kiem
THU HAI, gan voi noi dung du lieu catalog ma Lan G nhap o Task 11-13, xac nhan
lai dung cac thuoc tinh ma services/nhap_mau_goc.py se dung toi.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tv4.db').as_posix()}")
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


def test_meta_prompt_has_pha4_columns(db):
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    row = OmmiMetaPrompt(owner_id="u1", name="X", body="Y")
    db.add(row)
    db.commit()
    assert row.target_format == "gemini_style"
    assert row.is_default is False
    assert row.placeholders == []
    assert row.share_level == "private"


def test_meta_prompt_owner_id_stays_nullable_for_catalog(db):
    """Co che catalog cu (owner_id NULL) khong bi Pha 4 thay the — bat bien
    #1 cua brief Lan G: hai co che song song, khong duoc lam vo mot ben."""
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    row = OmmiMetaPrompt(owner_id=None, name="Catalog", body="Y",
                         is_catalog=True, share_level="catalog")
    db.add(row)
    db.commit()
    assert row.owner_id is None
    assert row.share_level == "catalog"


def test_style_has_pha4_columns(db):
    from apps.prompt_ai_ommi.tables import OmmiStyle
    row = OmmiStyle(owner_id="u1", name="X")
    db.add(row)
    db.commit()
    assert row.parent_id is None
    assert row.provider_overrides == {}
    assert row.share_level == "private"


def test_snippet_has_share_level(db):
    from apps.prompt_ai_ommi.tables import OmmiPromptSnippet
    row = OmmiPromptSnippet(owner_id="u1", name="X")
    db.add(row)
    db.commit()
    assert row.share_level == "private"


def test_image_template_defaults_and_owner_not_null(db):
    from apps.prompt_ai_ommi.tables import OmmiImageTemplate
    row = OmmiImageTemplate(owner_id="admin-1", name="Mau",
                            prompt_text="{SUBJECT}", asset_type="character")
    db.add(row)
    db.commit()
    assert row.aspect == "1:1"
    assert row.output_mode == "grid"
    assert row.is_builtin is False
    assert row.share_level == "private"
    # Khac OmmiMetaPrompt/Snippet/Style: bang moi KHONG cho owner_id NULL
    # (spec S4.2 "moi bang: owner_id not null tru khi noi khac"; migration
    # b64a39da941d khai NOT NULL). Catalog o day dung is_builtin + share_level,
    # khong dung owner_id NULL.
    assert row.owner_id == "admin-1"
    assert row.placeholders == []


def test_storyboard_framework_defaults(db):
    from apps.prompt_ai_ommi.tables import OmmiStoryboardFramework
    row = OmmiStoryboardFramework(owner_id="admin-1", name="Khung")
    db.add(row)
    db.commit()
    assert row.default_aspect == "16:9"
    assert row.default_n_scenes == 3


def test_sample_and_profile_exist(db):
    from apps.prompt_ai_ommi.tables import OmmiSample, OmmiProfile
    sample = OmmiSample(owner_id="u1", title="Mau ket qua")
    profile = OmmiProfile(owner_id="u1", name="Ho so")
    db.add_all([sample, profile])
    db.commit()
    assert sample.actual_credit == 0
    assert profile.asset_tag_filter == []
