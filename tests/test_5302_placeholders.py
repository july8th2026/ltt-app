"""Pha 3 -- placeholder: ba phep cua spec Sec 7.1, khong thieu phep nao."""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services.placeholders import (
    kiem_placeholder, render, tim_placeholder)


def test_chi_bat_chu_hoa_khong_bat_vi_du_json():
    """Mau chua vi du JSON `{"scenes": []}` -- do khong phai placeholder."""
    body = 'Tra ve {"summary": "", "scenes": []} cho {TITLE}'
    assert tim_placeholder(body) == ["TITLE"]


def test_bat_ten_co_gach_duoi_va_so():
    body = "{BRIEF_VI} {STYLE_NEGATIVE} {FACTION_A} {MIN_COMBAT_DISTANCE}"
    assert set(tim_placeholder(body)) == {
        "BRIEF_VI", "STYLE_NEGATIVE", "FACTION_A", "MIN_COMBAT_DISTANCE"}


def test_phep_1_bien_dung_ma_khong_khai_thi_thieu():
    """Mau co bien ma khong ai biet de HOI khach -- phai bao thieu."""
    thieu = kiem_placeholder("{TITLE} {BI_AN}", ["TITLE"], {"TITLE": "x"})
    assert "BI_AN" in thieu


def test_phep_2_bien_khai_ma_khong_ai_cap_gia_tri_thi_thieu():
    """Khong co phep nay thi mau render ra `{BRIEF_VI}` nguyen van gui LLM."""
    thieu = kiem_placeholder("{TITLE} {BRIEF_VI}", ["TITLE", "BRIEF_VI"],
                             {"TITLE": "x"})
    assert "BRIEF_VI" in thieu


def test_phep_3_chuoi_da_render_khong_con_cap_chu_hoa_nao():
    """Luoi cuoi -- bat ca hai ca tren."""
    ra = render("{TITLE}: {BRIEF_VI}", {"TITLE": "A", "BRIEF_VI": "B"})
    assert tim_placeholder(ra) == []
    assert ra == "A: B"


def test_du_gia_tri_thi_khong_thieu_gi():
    assert kiem_placeholder("{TITLE}", ["TITLE"], {"TITLE": "x"}) == []


def test_gia_tri_rong_VAN_la_thieu():
    """Khach de trong o nhap la mot ca THAT (mau `Ong Ngoai` co 4 bien tu do).

    Coi rong la "co gia tri" thi mau render ra cau cut dau roi gui LLM.
    """
    assert kiem_placeholder("{FACTION_A}", ["FACTION_A"],
                            {"FACTION_A": "  "}) == ["FACTION_A"]


def test_bang_nguon_gia_tri_co_du_15_ten_spec_doi():
    from apps.prompt_ai_ommi.services.placeholders import NGUON_GIA_TRI
    can = {"TITLE", "PROJECT_NAME", "BRIEF_VI", "DURATION", "SCENES",
           "ASPECT_RATIO", "ASPECT", "STYLE_FULL", "STYLE_POSITIVE",
           "STYLE_NEGATIVE", "ASSET_LIST", "VIDEO_LIST", "PROMPT", "REF_NOTE",
           "CHARACTER_DESCRIPTION"}
    assert can <= set(NGUON_GIA_TRI)
