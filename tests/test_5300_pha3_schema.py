"""Pha 3 -- schema: tach package khong lam vo import cu, va bang moi co du cot."""
from __future__ import annotations

import pytest

TEN_CU = (
    "OmmiResource", "OmmiResourceVariant", "OmmiTag", "OmmiResourceTag",
    "OmmiCollection", "OmmiCollectionItem", "OmmiResourceUsage",
    "OmmiMetaPrompt", "OmmiPromptSnippet", "OmmiStyle", "OmmiPromptVersion",
    "OmmiStoryboard", "OmmiScene", "OmmiSceneVersion",
)


@pytest.mark.parametrize("ten", TEN_CU)
def test_ten_lop_cu_van_import_duoc(ten):
    """Tach `tables.py` thanh package KHONG duoc lam vo mot import nao."""
    import apps.prompt_ai_ommi.tables as t
    assert hasattr(t, ten), f"mat {ten} sau khi tach package"


COT_BAT_BUOC = {
    "OmmiBrief": ("id", "owner_id", "project_id", "title", "story_vi", "goal",
                  "audience", "target_duration_sec", "target_scenes",
                  "aspect_ratio", "language", "style_id", "meta_prompt_id",
                  "character_id", "background_id", "referenced_variants",
                  "status", "free_iterations_used", "archived_at",
                  "created_at", "updated_at"),
    "OmmiCanh": ("id", "brief_id", "position", "title", "duration_seconds",
                 "summary", "prompt", "negative_prompt", "camera", "lighting",
                 "mood", "continuity", "selected_version", "created_at"),
    "OmmiIteration": ("id", "brief_id", "seq", "feedback", "prompt_sent",
                      "output", "job_id", "credit_charged", "was_free",
                      "verdict", "created_at"),
    "OmmiCharacter": ("id", "owner_id", "name", "gender", "age_range",
                      "face_description", "body_description",
                      "hair_description", "outfit_description", "personality",
                      "expression_style", "movement_style",
                      "fixed_prompt_block", "negative_notes",
                      "reference_variant_ids", "share_level", "archived_at",
                      "created_at", "updated_at"),
    "OmmiBackground": ("id", "owner_id", "name", "location_type",
                       "environment_description", "lighting_description",
                       "color_palette", "camera_feel", "important_objects",
                       "fixed_prompt_block", "negative_notes",
                       "reference_variant_ids", "share_level", "archived_at",
                       "created_at", "updated_at"),
}


@pytest.mark.parametrize("ten_lop,cot", sorted(COT_BAT_BUOC.items()))
def test_bang_moi_co_du_cot(ten_lop, cot):
    import apps.prompt_ai_ommi.tables as t
    lop = getattr(t, ten_lop, None)
    assert lop is not None, f"chua co model {ten_lop}"
    co = set(lop.__table__.columns.keys())
    thieu = [c for c in cot if c not in co]
    assert not thieu, f"{ten_lop} thieu cot: {thieu}"


def test_canh_khong_trung_vi_tri_trong_mot_brief():
    """Hai canh cung `position` trong mot brief la mot thu tu KHONG xac dinh."""
    import apps.prompt_ai_ommi.tables as t
    rang_buoc = {tuple(sorted(c.columns.keys()))
                 for c in t.OmmiCanh.__table__.constraints
                 if c.__class__.__name__ == "UniqueConstraint"}
    assert ("brief_id", "position") in rang_buoc


def test_iteration_khong_trung_seq_trong_mot_brief():
    import apps.prompt_ai_ommi.tables as t
    rang_buoc = {tuple(sorted(c.columns.keys()))
                 for c in t.OmmiIteration.__table__.constraints
                 if c.__class__.__name__ == "UniqueConstraint"}
    assert ("brief_id", "seq") in rang_buoc


def test_khung_hinh_storyboard_biet_no_ve_cho_canh_nao():
    """`ommi_scene` la KHUNG HINH; `canh_id` noi no ve cho canh kich ban nao.

    Khong co cot nay thi hai thu cung ten "canh" van khong lien ket duoc voi
    nhau -- dung con bo spec Sec 4.3 dang chua.
    """
    import apps.prompt_ai_ommi.tables as t
    assert "canh_id" in t.OmmiScene.__table__.columns.keys()
    assert t.OmmiScene.__table__.columns["canh_id"].nullable is True


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    """DB SQLite rieng cho tep test, tao du bang qua `load_app_tables()`."""
    monkeypatch.setenv(
        "LTT_DATABASE_URL",
        f"sqlite:///{(tmp_path / 'pha3-schema.db').as_posix()}")
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


def test_canh_id_truyen_vao_duoc_giu_nguyen(db_session):
    """Spec S-4 / plan §9b: `default=_uuid` KHONG duoc thay id da truyen vao.

    Binding cua pha 1 tro vao id cu (`payload["scenes"][].id`). Neu tao
    `OmmiCanh` ma sinh id MOI thi moi binding pha 1 tro vao hu khong.
    """
    from apps.prompt_ai_ommi.tables import OmmiCanh

    canh = OmmiCanh(id="scene_abc123", owner_id="u_1", brief_id="brief_1",
                    position=0)
    db_session.add(canh)
    db_session.commit()
    db_session.refresh(canh)

    assert canh.id == "scene_abc123"
    lay_lai = db_session.get(OmmiCanh, "scene_abc123")
    assert lay_lai is not None
    assert lay_lai.id == "scene_abc123"
