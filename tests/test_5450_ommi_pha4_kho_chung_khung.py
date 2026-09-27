"""Pha 4 PROMPT AI, Lan M — khung schema kho chung + thu vien.

Dai so: 5450-5469 (Lan M). ⛔ Khac dai 5400-5419 (Lan F) va 5420-5449 (Lan G).

Pham vi Task 1-3 cua Lan M: xac nhan tien de, migration
`20260927_1842_ommi_pha4_kho_chung.py` (share_level + 4 bang moi), va cot
share_level da co tren OmmiCharacter/OmmiBackground/OmmiPose tu Pha 3. Noi
dung du lieu catalog (12 meta prompt/21 image template/...) la viec cua Lan G
(services/nhap_mau_goc.py) — KHONG kiem o day.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'pha4_khung.db').as_posix()}")
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


# ── Alembic: mot head duy nhat (G-5) ────────────────────────────────────────

def test_alembic_mot_head_va_migration_pha4_NAM_TRONG_CHUOI():
    """Hai bat bien, va ca hai phai la TINH CHAT chu khong phai mot GIA TRI.

    ⚠️ Ban dau bai nay khang dinh `"pha 4" in rev.doc` cua HEAD — tuc no khang
    dinh *"pha 4 la migration MOI NHAT"*, mot su that chi dung vao dung luc viet.
    Pha 5 them mot migration va bai DO ngay, du ⛔ khong co gi sai.

    ⭐ Cung lop loi voi `test_5152` (khang dinh tran anh `== 4`, do khi tran len 9):
    **mot phep kiem khang dinh mot GIA TRI cua mot quyet dinh se do khi quyet dinh
    doi.** Dieu dang bao ve o day la *migration pha 4 duoc NOI vao chuoi*, ⛔ khong
    phai *no dung cuoi chuoi*.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = scripts.get_heads()
    assert len(heads) == 1, f"mong DUNG MOT head, thay {heads}"

    # Bat bien 2: migration pha 4 la TO TIEN cua head (tuc no nam trong chuoi,
    # ⛔ khong treo lo lung), bat ke bao nhieu pha duoc them sau no.
    to_tien = {r.revision for r in scripts.iterate_revisions(heads[0], "base")}
    pha4 = [r.revision for r in scripts.walk_revisions()
            if "pha 4" in (r.doc or "").lower()]
    assert len(pha4) == 1, f"mong DUNG MOT migration pha 4, thay {pha4}"
    assert pha4[0] in to_tien, (
        f"migration pha 4 ({pha4[0]}) KHONG nam trong chuoi tu head "
        f"{heads[0]} ve base — no dang treo lo lung")


# ── Cot share_level: DA CO tu Pha 3 tren 3 bang, THEM MOI tren 3 bang ───────
# (doi chung: neu vo tinh ALTER lai ba bang da co cot, tao bang se loi
#  "duplicate column" — day la thu chinh migration nay phai KHONG lam).

def test_character_background_pose_da_co_share_level_tu_pha3(db):
    """Khong phai viec cua Task 3/4 — pha 3 da lam. Xac nhan lai de Task 4
    cua Lan M khong vo tinh ALTER trung."""
    from apps.prompt_ai_ommi.tables import (
        OmmiCharacter, OmmiBackground, OmmiPose)

    char = OmmiCharacter(owner_id="u1", name="Nhan vat")
    bg = OmmiBackground(owner_id="u1", name="Boi canh")
    pose = OmmiPose(owner_id="u1", name="Dang")
    db.add_all([char, bg, pose])
    db.commit()
    assert char.share_level == "private"
    assert bg.share_level == "private"
    assert pose.share_level == "private"


def test_meta_prompt_co_du_cot_pha4(db):
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt

    row = OmmiMetaPrompt(owner_id="u1", name="X", body="Y")
    db.add(row)
    db.commit()
    assert row.target_format == "gemini_style"
    assert row.is_default is False
    assert row.placeholders == []
    assert row.share_level == "private"


def test_style_co_du_cot_pha4(db):
    from apps.prompt_ai_ommi.tables import OmmiStyle

    row = OmmiStyle(owner_id="u1", name="X")
    db.add(row)
    db.commit()
    assert row.parent_id is None
    assert row.provider_overrides == {}
    assert row.share_level == "private"


def test_snippet_co_share_level(db):
    from apps.prompt_ai_ommi.tables import OmmiPromptSnippet

    row = OmmiPromptSnippet(owner_id="u1", name="X")
    db.add(row)
    db.commit()
    assert row.share_level == "private"


# ── 4 bang moi ───────────────────────────────────────────────────────────────

def test_image_template_mac_dinh_va_co_placeholders(db):
    """placeholders la cot bo sung 26/09 (spec Sec 7.2) — thieu no thi khong
    kiem duoc mau nao can bien gi. Ban nhap Task 3/10 ban dau CHUA co cot
    nay; da vieng vao ca migration lan model o day."""
    from apps.prompt_ai_ommi.tables import OmmiImageTemplate

    row = OmmiImageTemplate(owner_id="u1", name="Mau", prompt_text="{SUBJECT}",
                            asset_type="character")
    db.add(row)
    db.commit()
    assert row.aspect == "1:1"
    assert row.output_mode == "grid"
    assert row.is_builtin is False
    assert row.share_level == "private"
    assert row.placeholders == []


def test_storyboard_framework_mac_dinh(db):
    from apps.prompt_ai_ommi.tables import OmmiStoryboardFramework

    row = OmmiStoryboardFramework(owner_id="u1", name="Khung")
    db.add(row)
    db.commit()
    assert row.default_aspect == "16:9"
    assert row.default_n_scenes == 3
    assert row.share_level == "private"


def test_sample_va_profile_ton_tai(db):
    from apps.prompt_ai_ommi.tables import OmmiSample, OmmiProfile

    sample = OmmiSample(owner_id="u1", title="Mau ket qua")
    profile = OmmiProfile(owner_id="u1", name="Ho so")
    db.add_all([sample, profile])
    db.commit()
    assert sample.actual_credit == 0
    assert sample.share_level == "private"
    assert profile.asset_tag_filter == []
    assert profile.share_level == "private"


# ── Doi chung so 0: mot ten sai / thieu import phai gay loi that ───────────

def test_import_ten_khong_ton_tai_phai_bao_loi(db):
    """Doi chung cho cac test 'co du cot' o tren: neu ai do go sai ten thuoc
    tinh, AttributeError phai xuat hien — chung minh cac assert phia tren
    thuc su dang do duoc mot dieu gi do, khong phai luon xanh."""
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt

    row = OmmiMetaPrompt(owner_id="u1", name="X", body="Y")
    with pytest.raises(AttributeError):
        _ = row.ten_cot_khong_ton_tai_kiem_tra_doi_chung


# ── owner_id: bat bien so huu (H19 P0, xem test_135) ───────────────────────

def test_bon_bang_moi_deu_bat_buoc_owner_id(db):
    """4 bang schema cua Lan M (khong phai ommi_share_code — Lan F, khong
    phai ommi_budget — schema-only, chua co model o pha nay) deu la
    owner_id NOT NULL, khong phai bang noi thuan (khong nam trong
    tests/test_135_ommi_ownership.py::_JOIN_TABLES)."""
    from platform_core.db import Base
    from platform_core.registry import load_app_tables
    load_app_tables()

    for table_name in ("ommi_image_template", "ommi_storyboard_framework",
                       "ommi_sample", "ommi_profile"):
        table = Base.metadata.tables[table_name]
        assert "owner_id" in table.c, table_name
        assert not table.c["owner_id"].nullable, table_name
