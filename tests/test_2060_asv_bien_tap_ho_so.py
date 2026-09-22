"""asv-final lan `bien-tap` — HO SO + HINH HOC cua cat khung / phong / ti le / toc do.

Ba tang, day la tang THUAN (khong HTTP, khong ffmpeg):

  · `bien_tap.chuan_hoa`/`tu_form` — duyet o cua, THUA, tu choi chu khong kep;
  · `cai_dat` — khoa `bien_tap` la mot `KHOA_THUA`;
  · `hinh_hoc.khung_bien_tap` — so pixel nguyen, chan, tinh MOT lan.

Tang render: `test_2061`. Tang engine that (ffmpeg, do tren tep ra): `test_2062`.
Tang HTTP: `test_2063`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import bien_tap as bt, cai_dat, hinh_hoc, hop_dong_v4 as hd

CAT = hd.PRESET_CAT_THONG_MINH
GIU = hd.PRESET_GIU_HINH


# ══ 1. Hop dong: da MO qua ADR, va nhung thu con lai VAN bi cam ═══════════════

def test_bon_nang_luc_da_mo_nam_dung_MOT_bang():
    for ma in ("crop", "zoom", "reframe", "speed"):
        assert ma in hd.NANG_LUC_DOI_DIEM_ANH
        assert ma not in hd.CAM_TRONG_MVP and ma not in hd.HAU_MVP


@pytest.mark.parametrize("ma", ["reorder", "broll", "upscale", "music_replace",
                                "transition"])
def test_nam_thu_chua_co_ADR_van_bi_CAM(ma):
    assert ma in hd.CAM_TRONG_MVP


def test_adr_ton_tai_va_ghi_quyet_dinh():
    adr = (Path(__file__).resolve().parents[1]
           / "docs/auto_scan_video_final/ADR_BIEN_TAP.md")
    van = adr.read_text(encoding="utf-8")
    for tu in ("crop", "zoom", "reframe", "speed", "reorder", "mirror"):
        assert tu in van, tu


# ══ 2. Duyet: THUA, luy dang, tu choi chu khong kep ══════════════════════════

def test_mac_dinh_la_RONG_va_tu_form_tra_None():
    assert bt.chuan_hoa({}) == {}
    assert bt.chuan_hoa({"toc_do": 1.0, "zoom": {"he_so": 1.0},
                         "cat_khung": {"x0": 0, "y0": 0, "x1": 1, "y1": 1}}) == {}
    assert bt.tu_form("", preset=CAT) is None
    assert bt.tu_form('{"toc_do": 1}', preset=CAT) is None
    # ⭐ Mac dinh o preset GIU HINH cung khong phai loi — khong co gi de tu choi.
    assert bt.tu_form('{"toc_do": 1}', preset=GIU) is None


def test_ho_so_day_du_luy_dang():
    tho = {"toc_do": 1.25, "cat_khung": {"x0": 0.1, "y0": 0, "x1": 0.9, "y1": 1},
           "zoom": {"he_so": 1.5, "tam_x": 0.3},
           "khung": {"ti_le": "9:16", "cach": "cat", "tam_x": 0.7}}
    ra = bt.chuan_hoa(tho)
    assert ra["toc_do"] == 1.25 and ra["zoom"] == {"he_so": 1.5, "tam_x": 0.3}
    assert ra["khung"] == {"ti_le": "9:16", "cach": "cat", "tam_x": 0.7}
    assert bt.chuan_hoa(ra) == ra


def test_nen_mo_KHONG_mang_tam():
    """Tam chi co nghia khi CAT theo ti le; nen mo giu tron hinh."""
    ra = bt.chuan_hoa({"khung": {"ti_le": "1:1", "cach": "nen_mo", "tam_x": 0.2}})
    assert ra["khung"] == {"ti_le": "1:1", "cach": "nen_mo"}


@pytest.mark.parametrize("tho,mau", [
    ({"toc_do": 0.8}, "Tốc độ"),                 # cham lai = video DAI ra
    ({"toc_do": 1.6}, "Tốc độ"),
    ({"toc_do": float("nan")}, "không hợp lệ"),
    ({"toc_do": True}, "không hợp lệ"),
    ({"zoom": {"he_so": 3.5}}, "phóng to"),
    ({"cat_khung": {"x0": 0.5, "x1": 0.6}}, "quá nhỏ"),
    ({"cat_khung": {"x0": 0.6, "x1": 0.4}}, "cạnh đầu"),
    ({"cat_khung": {"x0": -0.1}}, "cạnh đầu"),
    ({"khung": {"ti_le": "21:9"}}, "Tỉ lệ"),
    ({"khung": {"ti_le": "1:1", "cach": "lat"}}, "Cách đổi"),
    ({"khung": {"ti_le": "1:1", "tam_x": 1.2}}, "Tâm"),
    ({"mirror": True}, "trường lạ"),              # KHONG co lat guong
    ({"zoom": {"he_so": 2, "xoay": 5}}, "trường lạ"),
])
def test_sai_thi_TU_CHOI_khong_kep(tho, mau):
    with pytest.raises(bt.BienTapLoi, match=mau):
        bt.chuan_hoa(tho)


def test_preset_giu_hinh_TU_CHOI_voi_cau_cung_khuon():
    with pytest.raises(bt.BienTapLoi, match="Giữ nguyên hình ảnh.*tăng tốc"):
        bt.tu_form(json.dumps({"toc_do": 1.25}), preset=GIU)
    with pytest.raises(bt.BienTapLoi, match="sao chép nguyên vẹn từng điểm ảnh"):
        bt.tu_form(json.dumps({"khung": {"ti_le": "1:1"}}), preset=GIU)


def test_json_hong_bi_tu_choi():
    with pytest.raises(bt.BienTapLoi):
        bt.tu_form("{khong", preset=CAT)
    with pytest.raises(bt.BienTapLoi):
        bt.tu_form("[1]", preset=CAT)


# ══ 3. cai_dat: MOT khoa THUA ════════════════════════════════════════════════

def test_bien_tap_la_KHOA_THUA_va_doc_toan_phan():
    assert "bien_tap" in cai_dat.KHOA_THUA
    assert "bien_tap" not in cai_dat.chuan_hoa({})
    ho = {"toc_do": 1.25}
    assert cai_dat.chuan_hoa({"bien_tap": ho})["bien_tap"] == ho
    c = cai_dat.tu_ho_so({"bien_tap": ho})
    assert c.bien_tap == ho and c.co_sua_diem_anh is True
    assert cai_dat.tu_ho_so({}).bien_tap is None


# ══ 4. Hinh hoc — so nguyen, chan, mot ham ══════════════════════════════════

def _chan(*xs):
    return all(int(x) % 2 == 0 for x in xs)


def test_khong_bien_tap_khung_thi_ban_ra_bang_nguon():
    hh = hinh_hoc.khung_bien_tap(1280, 720, {"toc_do": 1.25})
    assert hh == {"cat": None, "phong": None, "khung": None, "ra": (1280, 720)}


def test_ti_le_9_16_cat_quanh_tam():
    hh = hinh_hoc.khung_bien_tap(1280, 720, {"khung": {"ti_le": "9:16", "cach": "cat"}})
    w, h, x, y = hh["khung"]["cat"]
    assert (w, h) == (404, 720) and hh["ra"] == (404, 720)
    assert x == 438 and y == 0                       # giua: (1280-404)/2
    assert _chan(w, h, x, y)


def test_tam_bi_KEP_trong_khung_khong_ra_ngoai_anh():
    hh = hinh_hoc.khung_bien_tap(1280, 720, {"khung": {
        "ti_le": "9:16", "cach": "cat", "tam_x": 1.0}})
    w, _h, x, _y = hh["khung"]["cat"]
    assert x + w <= 1280 and x == 1280 - 404


def test_nen_mo_giu_canh_ngan_va_dat_hinh_giua():
    hh = hinh_hoc.khung_bien_tap(1280, 720, {"khung": {"ti_le": "9:16",
                                                        "cach": "nen_mo"}})
    kh = hh["khung"]
    assert kh["nen"] == (720, 1280) and hh["ra"] == (720, 1280)
    fw, fh = kh["hinh"]
    assert fw == 720 and fh == 404 and _chan(*kh["vi_tri"])
    assert kh["vi_tri"] == (0, (1280 - 404) // 2 // 2 * 2)


def test_zoom_la_cua_so_nho_roi_phong_ve():
    hh = hinh_hoc.khung_bien_tap(640, 360, {"zoom": {"he_so": 2.0}})
    assert hh["cat"] == (320, 180, 160, 90) and hh["phong"] == (640, 360)
    assert hh["ra"] == (640, 360)


def test_cat_khung_roi_zoom_roi_ti_le_noi_tiep():
    hh = hinh_hoc.khung_bien_tap(1920, 1080, {
        "cat_khung": {"x0": 0.25, "y0": 0.0, "x1": 0.75, "y1": 1.0},
        "zoom": {"he_so": 1.5},
        "khung": {"ti_le": "1:1", "cach": "cat"}})
    assert hh["cat"][2] >= 480 and hh["phong"] == (960, 1080)
    assert hh["ra"] == (960, 960)


def test_khung_da_dung_ti_le_thi_khong_them_buoc():
    hh = hinh_hoc.khung_bien_tap(1280, 720, {"khung": {"ti_le": "16:9"}})
    assert hh["khung"] is None and hh["ra"] == (1280, 720)


def test_khong_biet_khung_nguon_thi_NEM():
    with pytest.raises(ValueError):
        hinh_hoc.khung_bien_tap(0, 0, {"khung": {"ti_le": "1:1"}})


# ══ 5. Anh xa thoi gian: truc bien tap -> ban ra la MOT phep chia ═══════════

def test_moc_ban_ra_chia_cho_toc_do():
    assert bt.moc_ban_ra(4.0, {"toc_do": 1.25}) == pytest.approx(3.2)
    assert bt.moc_ban_ra(4.0, None) == 4.0
