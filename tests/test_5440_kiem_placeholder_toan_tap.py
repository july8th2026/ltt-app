"""T-2 (spec S10.2): kiem_placeholder tren CA 12 meta prompt va CA 21 image
template da nhap - khong phai mau dai dien.

PHAN QUYET dieu phoi 27/09 (docs/superpowers/plans/2026-09-26-prompt-ai-pha4-
kho-chung.md, muc "PHAN QUYET bon diem tren", diem 2): {SUBJECT}/{STYLE}/
{EXTRA}/{EQUIPMENT} la o NGUOI DUNG GO TAY luc sinh anh (Pha 5,
services/composite.py chua co) - khong co "nguon gia tri he thong" nao de
doi chieu. Nen voi 21 image template, T-2 chi kiem CU PHAP (ten nam trong
tap da khai, dang {TEN} dung, khong ten la) - KHONG kiem nguon gia tri
nghiep vu. Voi 12 meta prompt, kiem DAY DU (ca ba phep cua kiem_placeholder)
vi Pha 3 da co day du nguon gia tri that trong services/placeholders.py.

Dai so: 5420-5449 (Lan G).
"""
from __future__ import annotations

import re

import pytest

#: Bang quy doi S7 mo rong 15 -> 19 ten (PHAN QUYET diem 2): 15 ten "gia tri
#: he thong" cua bang S7 (doc tu ommi_brief/ommi_style/ommi_binding...) + 4
#: ten "tu do" cua mau "Ong Ngoai" (FACTION_A/FACTION_B/MIN_COMBAT_DISTANCE/
#: NEUTRAL_LIST, S7 doan van ban duoi bang) - ca 19 deu la ten HOP LE cho
#: MOI meta prompt dung toi, chi khac o AI cap gia tri (he thong tu suy, hay
#: khach go/khai trong ommi_meta_prompt.placeholders).
_TEN_GIA_TRI_HE_THONG = {
    "TITLE", "PROJECT_NAME", "BRIEF_VI", "DURATION", "SCENES", "ASPECT_RATIO",
    "ASPECT", "STYLE_FULL", "STYLE_POSITIVE", "STYLE_NEGATIVE", "ASSET_LIST",
    "VIDEO_LIST", "PROMPT", "REF_NOTE", "CHARACTER_DESCRIPTION",
}
_TEN_O_NGUOI_DUNG_GO_META = {
    "FACTION_A", "FACTION_B", "MIN_COMBAT_DISTANCE", "NEUTRAL_LIST",
}
_TEN_HE_THONG = _TEN_GIA_TRI_HE_THONG | _TEN_O_NGUOI_DUNG_GO_META
assert len(_TEN_HE_THONG) == 19, "bang quy doi S7 phai la 19 ten (15 + 4)"

#: Placeholder cua IMAGE TEMPLATE (S7.2) — o NGUOI DUNG GO TAY, khong doi
#: chieu duoc nguon gia tri o pha 4.
_TEN_O_NGUOI_DUNG_GO_ANH = {"SUBJECT", "STYLE", "EXTRA", "EQUIPMENT"}

_TOKEN_RE = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'kp.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    nsvc.nhap(session, admin_owner_id="admin-t2")
    session.commit()
    yield session
    session.close()
    dbmod.reset_engine()


def test_all_12_meta_prompts_declare_every_placeholder_they_use(db):
    from apps.prompt_ai_ommi.services.placeholders import kiem_placeholder
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    rows = db.query(OmmiMetaPrompt).filter(
        OmmiMetaPrompt.owner_id.is_(None)).all()
    assert len(rows) == 12, "T-2 doi hoi CA 12 meta, khong phai mau dai dien"
    co_gia_tri = {ten: f"<gia tri thu {ten}>" for ten in _TEN_HE_THONG}
    for row in rows:
        missing = kiem_placeholder(row.body, list(row.placeholders), co_gia_tri)
        assert missing == [], f"{row.name!r} ({row.target_format}): thieu {missing}"


def test_all_21_image_templates_have_well_formed_placeholders(db):
    """Chi kiem CU PHAP (PHAN QUYET diem 2): ten dung trong prompt_text nam
    trong khai_bao, khai_bao khong co ten la ngoai 4 ten da biet cua S7.2.
    KHONG doi chieu nguon gia tri nghiep vu — viec do thuoc Pha 5."""
    from apps.prompt_ai_ommi.services.placeholders import kiem_placeholder
    from apps.prompt_ai_ommi.tables import OmmiImageTemplate
    rows = db.query(OmmiImageTemplate).filter(
        OmmiImageTemplate.is_builtin.is_(True)).all()
    assert len(rows) == 21, "T-2 doi hoi CA 21 template, khong phai mau dai dien"
    for row in rows:
        khai_bao = sorted(set(_TOKEN_RE.findall(row.prompt_text)))
        ten_la = [ten for ten in khai_bao if ten not in _TEN_O_NGUOI_DUNG_GO_ANH]
        assert ten_la == [], f"{row.name!r}: ten la ngoai bo S7.2: {ten_la}"
        co_gia_tri = {ten: f"<{ten.lower()}>" for ten in khai_bao}
        missing = kiem_placeholder(row.prompt_text, khai_bao, co_gia_tri)
        assert missing == [], f"{row.name!r}: thieu {missing}"


def test_missing_declaration_is_caught_not_silently_green(db):
    """Doi chung (bay do luong #2 cua brief Lan G): '0 placeholder thieu' tren
    mot tap RONG cung xanh. Tiem mot ten KHONG CO THAT vao body ma khong khai
    -> kiem_placeholder phai bao THIEU, khong duoc im lang."""
    from apps.prompt_ai_ommi.services.placeholders import kiem_placeholder
    body_co_bien_la = "Xin chao {TEN_KHONG_CO_THAT}, day la {TITLE}."
    missing = kiem_placeholder(body_co_bien_la, ["TITLE"], {"TITLE": "X"})
    assert missing == ["TEN_KHONG_CO_THAT"], (
        "phep kiem phai bat duoc bien dung ma khong khai — neu tra ve [] o "
        "day thi bo kiem vo dung, se khong bao gio do duoc gi")


def test_image_template_stray_placeholder_outside_s72_set_is_flagged(db):
    """Doi chung rieng cho nhanh image template: mot ten la (khong thuoc 4
    ten S7.2) trong prompt_text phai bi bat, khong duoc lot qua vi phep kiem
    o day chi so sanh VOI CHINH khai_bao tu suy (ma khong doi chieu tap co
    dinh thi 'ten la' luon rong tren du lieu tu suy)."""
    prompt_la = "{SUBJECT} dung {MOT_TEN_LA_KHONG_THUOC_S72} lam nen."
    khai_bao = sorted(set(_TOKEN_RE.findall(prompt_la)))
    ten_la = [ten for ten in khai_bao if ten not in _TEN_O_NGUOI_DUNG_GO_ANH]
    assert ten_la == ["MOT_TEN_LA_KHONG_THUOC_S72"]
