"""D01–D03: speed và language trên Public API `speech.ltt`.

Ba quyết định đã khoá (phiên 2026-09-13):

  D01  speed  [0.5, 2.0] continuous — nới từ [0.75, 1.50]
  D02  language  auto|vi|en — default auto
  D03  Public API reject ngoài range/enum, không silent clamp
"""
from __future__ import annotations

from apps.ltt_voice import features, toc_do
from apps.ltt_voice.manifest import MANIFEST


def _tool():
    return next(t for t in MANIFEST.tools if t.name == "speech.ltt")


# ── D01: khoảng tốc độ ──────────────────────────────────────────────────────


class TestD01_KhoangTocDo:

    def test_bien_duoi(self):
        assert toc_do.TOC_DO_MIN == 0.5

    def test_bien_tren(self):
        assert toc_do.TOC_DO_MAX == 2.0

    def test_hop_le_trong_khoang(self):
        assert toc_do.hop_le(0.5) == 0.5
        assert toc_do.hop_le(1.0) == 1.0
        assert toc_do.hop_le(2.0) == 2.0
        assert toc_do.hop_le(1.37) == 1.37

    def test_hop_le_clamp_duoi(self):
        assert toc_do.hop_le(0.3) == 0.5

    def test_hop_le_clamp_tren(self):
        assert toc_do.hop_le(2.5) == 2.0

    def test_hop_le_nan_ve_1(self):
        assert toc_do.hop_le(float("nan")) == 1.0

    def test_hop_le_inf_ve_1(self):
        assert toc_do.hop_le(float("inf")) == 1.0

    def test_cac_nac_web_khong_doi(self):
        assert toc_do.CAC_NAC == (0.75, 0.85, 1.0, 1.15, 1.25, 1.5)

    def test_cac_nac_nam_trong_khoang(self):
        for nac in toc_do.CAC_NAC:
            assert toc_do.TOC_DO_MIN <= nac <= toc_do.TOC_DO_MAX


# ── D01+D02: params_schema ───────────────────────────────────────────────────


class TestD01D02_ParamsSchema:

    def test_speed_trong_schema(self):
        assert "speed" in _tool().params_schema

    def test_speed_type_number(self):
        assert _tool().params_schema["speed"]["type"] == "number"

    def test_speed_minimum(self):
        assert _tool().params_schema["speed"]["minimum"] == 0.5

    def test_speed_maximum(self):
        assert _tool().params_schema["speed"]["maximum"] == 2.0

    def test_speed_khong_bat_buoc(self):
        assert _tool().params_schema["speed"].get("required") is not True

    def test_language_trong_schema(self):
        assert "language" in _tool().params_schema

    def test_language_type_string(self):
        assert _tool().params_schema["language"]["type"] == "string"

    def test_language_enum(self):
        assert set(_tool().params_schema["language"]["enum"]) == {"auto", "vi", "en"}

    def test_language_khong_bat_buoc(self):
        assert _tool().params_schema["language"].get("required") is not True

    def test_api_contract_co_speed(self):
        contract = _tool().api_contract
        assert "speed" in contract["params"]
        assert "description" in contract["params"]["speed"]

    def test_api_contract_co_language(self):
        contract = _tool().api_contract
        assert "language" in contract["params"]
        assert "description" in contract["params"]["language"]


# ── D03: chuan_hoa dual-name ─────────────────────────────────────────────────


class TestD03_ChuanHoaDualName:

    def test_toc_do_tu_ten_noi_bo(self):
        yc = features.chuan_hoa({"text": "xin chào", "toc_do": 1.5})
        assert yc.toc_do == 1.5

    def test_toc_do_tu_ten_cong_khai(self):
        yc = features.chuan_hoa({"text": "xin chào", "speed": 1.5})
        assert yc.toc_do == 1.5

    def test_toc_do_noi_bo_uu_tien(self):
        yc = features.chuan_hoa({"text": "xin chào", "toc_do": 0.8,
                                  "speed": 1.5})
        assert yc.toc_do == 0.8

    def test_toc_do_mac_dinh_1(self):
        yc = features.chuan_hoa({"text": "xin chào"})
        assert yc.toc_do == 1.0

    def test_ngon_ngu_tu_ten_noi_bo(self):
        yc = features.chuan_hoa({"text": "xin chào", "ngon_ngu": "vi"})
        assert yc.ngon_ngu == "vi"

    def test_ngon_ngu_tu_ten_cong_khai(self):
        yc = features.chuan_hoa({"text": "xin chào", "language": "en"})
        assert yc.ngon_ngu == "en"

    def test_ngon_ngu_noi_bo_uu_tien(self):
        yc = features.chuan_hoa({"text": "xin chào", "ngon_ngu": "vi",
                                  "language": "en"})
        assert yc.ngon_ngu == "vi"

    def test_ngon_ngu_mac_dinh_auto(self):
        yc = features.chuan_hoa({"text": "xin chào"})
        assert yc.ngon_ngu == "auto"

    def test_language_auto_la_hop_le(self):
        yc = features.chuan_hoa({"text": "xin chào", "language": "auto"})
        assert yc.ngon_ngu == "auto"

    def test_language_gia_tri_la_ve_auto(self):
        yc = features.chuan_hoa({"text": "xin chào", "language": "fr"})
        assert yc.ngon_ngu == "auto"

    def test_speed_ngoai_khoang_bi_clamp(self):
        yc = features.chuan_hoa({"text": "xin chào", "speed": 5.0})
        assert yc.toc_do == 2.0

    def test_speed_0_3_bi_clamp_len_0_5(self):
        yc = features.chuan_hoa({"text": "xin chào", "speed": 0.3})
        assert yc.toc_do == 0.5
