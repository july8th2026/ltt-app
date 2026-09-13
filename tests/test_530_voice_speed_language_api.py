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

    def test_speed_min(self):
        # ⛔ `min`/`max` (quy uoc ngan cua nen tang), KHONG `minimum`/`maximum`:
        #    project_tool chi dich `min`->`minimum` vao input_schema cong khai.
        assert _tool().params_schema["speed"]["min"] == 0.5

    def test_speed_max(self):
        assert _tool().params_schema["speed"]["max"] == 2.0

    def test_speed_khong_bat_buoc(self):
        assert _tool().params_schema["speed"].get("required") is not True

    def test_language_trong_schema(self):
        assert "language" in _tool().params_schema

    def test_language_type_enum(self):
        # `type:"enum"` + `values`: chi kind=="enum" moi duoc project_tool phat
        # `enum` cong khai (string thuong thi khong).
        assert _tool().params_schema["language"]["type"] == "enum"

    def test_language_values(self):
        assert set(_tool().params_schema["language"]["values"]) == {"auto", "vi", "en"}

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


# ── D03: FAIL-CLOSED o BIEN CONG KHAI (test that su chot D03) ─────────────────
#
# ⛔ Class nay ton tai vi cac test tren CHUA DU. Chung kiem `params_schema`
#    (khai NOI BO); nhung `validate_public_input` chay tren `input_schema` da
#    duoc `project_tool` CHIEU RA. Neu phep chieu lam roi rang buoc (nhu no
#    tung lam khi params_schema dung sai quy uoc `minimum` thay vi `min`), thi
#    khai bao dung ma bien CONG KHAI van chap nhan `speed=2.5`. Chi test qua
#    chinh phep chieu moi bat duoc khoang trong "khai noi bo != cuong che bien".


def _public_tool():
    from platform_core.public_api.catalog import project_tool
    from platform_core.registry import discover
    mf = next(i.manifest for i in discover() if i.manifest.slug == "ltt_voice")
    tool = next(t for t in mf.tools if t.name == "speech.ltt")
    return project_tool(mf, tool)


class TestD03_FailClosedBienCongKhai:

    def _validate(self, payload):
        from platform_core.public_api.invocation import validate_public_input
        return validate_public_input(_public_tool(), payload)

    @staticmethod
    def _ApiError():
        from platform_core.public_api.errors import ApiError
        return ApiError

    def test_input_schema_speed_co_minimum(self):
        pt = _public_tool()
        assert pt.input_schema["properties"]["speed"]["minimum"] == 0.5

    def test_input_schema_speed_co_maximum(self):
        pt = _public_tool()
        assert pt.input_schema["properties"]["speed"]["maximum"] == 2.0

    def test_input_schema_language_co_enum(self):
        pt = _public_tool()
        assert set(pt.input_schema["properties"]["language"]["enum"]) == {
            "auto", "vi", "en"}

    def test_speed_tren_tran_bi_reject(self):
        import pytest
        with pytest.raises(self._ApiError()):
            self._validate({"text": "x", "speed": 2.5})

    def test_speed_duoi_san_bi_reject(self):
        import pytest
        with pytest.raises(self._ApiError()):
            self._validate({"text": "x", "speed": 0.1})

    def test_speed_bien_tren_chap_nhan(self):
        assert self._validate({"text": "x", "speed": 2.0})["speed"] == 2.0

    def test_speed_bien_duoi_chap_nhan(self):
        assert self._validate({"text": "x", "speed": 0.5})["speed"] == 0.5

    def test_language_ngoai_enum_bi_reject(self):
        import pytest
        with pytest.raises(self._ApiError()):
            self._validate({"text": "x", "language": "fr"})

    def test_language_vi_chap_nhan(self):
        assert self._validate({"text": "x", "language": "vi"})["language"] == "vi"

    def test_language_auto_chap_nhan(self):
        assert self._validate({"text": "x", "language": "auto"})["language"] == "auto"

    def test_hop_le_ca_hai(self):
        clean = self._validate({"text": "x", "speed": 1.25, "language": "en"})
        assert clean["speed"] == 1.25 and clean["language"] == "en"


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
