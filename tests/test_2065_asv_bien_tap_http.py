"""asv-final lan `bien-tap` — tang HTTP (cua `routes.tao`) + khoi giao dien.

⭐ Tu choi o CUA, truoc khi giu credit; hop le thi LUU dung ho so THUA; va trang
   Studio phat khoi dieu khien + o an ma `asv/bien_tap.js` doc. Bang chung trinh
   duyet that: `L_BIEN_TAP.md` §5.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import hop_dong_v4
from tests import asv_js
from tests import test_423_asv_giao_dien as _gd
from tests import test_447_asv_v4_giao_dien_san_pham as _sp

moi_truong = _gd.moi_truong
_nop = _sp._nop
_settings = _sp._settings


def _run_id(r) -> str:
    assert "/run/" in str(r.url), r.text[:600]
    return str(r.url).rsplit("/run/", 1)[1].split("/")[0]


def test_preset_giu_hinh_TU_CHOI_toc_do_truoc_credit(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_GIU_HINH,
             bien_tap=json.dumps({"toc_do": 1.25}))
    assert r.status_code == 400 and "/run/" not in str(r.url)
    assert "không đổi tốc độ được" in r.text


def test_preset_giu_hinh_TU_CHOI_doi_ti_le(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_GIU_HINH,
             bien_tap=json.dumps({"khung": {"ti_le": "9:16"}}))
    assert r.status_code == 400 and "đổi tỉ lệ" in r.text


def test_ho_so_sai_bi_TU_CHOI_o_cua(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
             bien_tap=json.dumps({"toc_do": 0.5}))
    assert r.status_code == 400 and "Tốc độ" in r.text
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
             bien_tap=json.dumps({"mirror": True}))
    assert r.status_code == 400 and "trường lạ" in r.text


def test_preset_cat_LUU_ho_so_da_chuan_hoa(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
             bien_tap=json.dumps({"toc_do": 1.25, "khung": {"ti_le": "9:16",
                                                            "cach": "nen_mo"}}))
    ho = _settings(_run_id(r))["bien_tap"]
    assert ho == {"toc_do": 1.25, "khung": {"ti_le": "9:16", "cach": "nen_mo"}}


def test_khong_bien_tap_thi_settings_KHONG_mang_khoa(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
             bien_tap=json.dumps({"toc_do": 1}))
    assert "bien_tap" not in _settings(_run_id(r))


def test_trang_Studio_phat_khoi_va_moi_o_JS_doc_deu_CO(moi_truong):
    """Khong o chet: moi id `asv/bien_tap.js` doc phai ton tai tren trang, va o an
    mang dung ten truong ma `routes.tao` nhan."""
    import re

    _app, a, _csrf, _b, _cb = moi_truong
    van = a.get("/auto-scan-video/").text
    assert 'name="bien_tap"' in van and 'id="asv-nhom-bien-tap"' in van
    js = asv_js.doc("asv/bien_tap.js")
    for ma in re.findall(r'o\("([a-z-]+)"\)', js):
        assert f'id="asv-bt-{ma}"' in van, ma
    for cat in ("trai", "phai", "tren", "duoi"):
        assert f'id="asv-bt-cat-{cat}"' in van
    assert "asv/bien_tap.js" in asv_js.ds_module()
