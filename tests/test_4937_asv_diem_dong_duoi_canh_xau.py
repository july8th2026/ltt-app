"""B13 E2 — `diem_dong.duoi_xau_cua_canh`/`ung_vien_duoi_xau`: "duoi canh xau"
la mot phep so TUONG DOI (duoi so voi GIUA cua CHINH no), ⛔ khong phai mot
nguong TUYET DOI ap chung cho moi canh.

Ham `.THUAN` — khong ffmpeg, khong file — nen bai nay ⛔ khong can khoa CPU.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.auto_scan_video import diem_dong as dd


def _diem_deu(bat: float, ket: float, *, nen: float, duoi_tu: float,
             duoi_gia: float) -> tuple:
    """Sinh diem dong 5 fps deu tren `[bat, ket)` — gia tri `nen` moi noi, tru
    vung `giay >= duoi_tu` mang gia tri `duoi_gia`."""
    ra = []
    i = 1
    while True:
        giay = round(bat + i * 0.2, 4)
        if giay >= ket:
            break
        gia = duoi_gia if giay >= duoi_tu else nen
        ra.append((giay, gia))
        i += 1
    return tuple(ra)


# ══════════════════════════════════════════════════════════════════════════════
#  TUONG DOI, ⛔ khong TUYET DOI — menh de trung tam
# ══════════════════════════════════════════════════════════════════════════════

def test_canh_DONG_nhung_ti_le_duoi_giua_BINH_THUONG__khong_bi_gan_xau():
    """Mot canh hanh dong (nen 50,0 tren thang 0..255) co duoi hoi cao hon
    (55,0) — ti le 1,1, duoi nguong 1,6. Mot nguong TUYET DOI se bat NHAM canh
    nay (ca giua LAN duoi deu cao); phep TUONG DOI thi khong."""
    diem = _diem_deu(0.0, 10.0, nen=50.0, duoi_tu=8.0, duoi_gia=55.0)
    assert dd.duoi_xau_cua_canh(diem, 0.0, 10.0) is None


def test_canh_TINH_nhung_duoi_BAT_THUONG_so_voi_giua__bi_gan_xau():
    """Cung hinh dang thoi gian voi bai tren, nhung muc dong THAP (nen 1,2,
    duoi 6,0 — ti le 5,0). Phep TUONG DOI bat duoc du muc dong tuyet doi rat
    nho — dung cai ma nguong tuyet doi se BO SOT."""
    diem = _diem_deu(100.0, 110.0, nen=1.2, duoi_tu=108.0, duoi_gia=6.0)
    ket_qua = dd.duoi_xau_cua_canh(diem, 100.0, 110.0)
    assert ket_qua is not None
    (duoi_bat, duoi_ket), he_so = ket_qua
    assert duoi_bat == pytest.approx(108.0)
    assert duoi_ket == pytest.approx(110.0)
    assert he_so == pytest.approx(5.0)


# ══════════════════════════════════════════════════════════════════════════════
#  Bien: canh qua ngan, thieu mau, giap ranh GIUA/DUOI, rao chong nhieu
# ══════════════════════════════════════════════════════════════════════════════

def test_canh_qua_ngan__khong_danh_gia():
    diem = _diem_deu(0.0, 0.5, nen=1.0, duoi_tu=0.4, duoi_gia=50.0)
    assert dd.duoi_xau_cua_canh(diem, 0.0, 0.5) is None


def test_thieu_mau_o_mot_trong_hai_vung__khong_danh_gia():
    """Canh du dai (5 s) nhung chi co MOT diem moi vung — duoi
    `SO_DIEM_TOI_THIEU = 2`."""
    diem = ((2.0, 10.0), (4.5, 20.0))
    assert dd.duoi_xau_cua_canh(diem, 0.0, 5.0) is None


def test_duoi_KHONG_BAO_GIO_cham_giua__ke_ca_canh_ngan_vua_du():
    """Canh 2 s: `TI_LE_DUOI` (0,2 x 2 = 0,4 s) < `TOI_THIEU_DUOI_S` (0,6 s),
    nhung `TRAN_TI_LE_DUOI` (0,25 x 2 = 0,5 s) khoa duoi lai dung diem giua
    cua canh (1,5 s) — duoi va giua GIAP RANH, ⛔ khong CHONG LAN."""
    diem = _diem_deu(0.0, 2.0, nen=1.0, duoi_tu=1.5, duoi_gia=5.0)
    ket_qua = dd.duoi_xau_cua_canh(diem, 0.0, 2.0)
    assert ket_qua is not None
    (duoi_bat, duoi_ket), he_so = ket_qua
    assert duoi_bat == pytest.approx(1.5)      # == giua_ket, ⛔ khong lech
    assert duoi_ket == pytest.approx(2.0)
    assert he_so == pytest.approx(5.0)


def test_rao_chong_nhieu_cam_bien__ti_le_lon_nhung_muc_tuyet_doi_qua_nho():
    """giua = 0,05, duoi = 0,15 -> ti le 3,0 (> nguong 1,6) NHUNG ca hai deu
    duoi `NGUONG_DIEM_TOI_THIEU` (1,0) — day la nhieu cam bien, ⛔ khong phai
    rung/chuyen canh loi, nen ⛔ khong duoc gan xau."""
    diem = _diem_deu(0.0, 10.0, nen=0.05, duoi_tu=8.0, duoi_gia=0.15)
    assert dd.duoi_xau_cua_canh(diem, 0.0, 10.0) is None


# ══════════════════════════════════════════════════════════════════════════════
#  `ung_vien_duoi_xau` — gop nhieu canh, ⛔ tu loc `co_thoai`/tran (viec cua
#  `ke_cat.chon`, ⛔ lam lai o day)
# ══════════════════════════════════════════════════════════════════════════════

def test_ung_vien_duoi_xau_gop_nhieu_canh__chi_canh_bat_thuong_moi_ra_ung_vien():
    canh_binh_thuong = SimpleNamespace(bat=0.0, ket=10.0)     # nhu bai 1
    canh_xau = SimpleNamespace(bat=100.0, ket=110.0)          # nhu bai 2
    diem = (_diem_deu(0.0, 10.0, nen=50.0, duoi_tu=8.0, duoi_gia=55.0)
           + _diem_deu(100.0, 110.0, nen=1.2, duoi_tu=108.0, duoi_gia=6.0))

    uv = dd.ung_vien_duoi_xau((canh_binh_thuong, canh_xau), diem)

    assert len(uv) == 1
    assert uv[0].bat == pytest.approx(108.0)
    assert uv[0].ket == pytest.approx(110.0)
    assert uv[0].diem_kem == pytest.approx(5.0)
    assert uv[0].ly_do_cat == dd.LY_DO_DUOI_CANH_XAU


def test_ung_vien_duoi_xau_danh_sach_rong_khi_khong_canh_nao_xau():
    canh = SimpleNamespace(bat=0.0, ket=10.0)
    diem = _diem_deu(0.0, 10.0, nen=50.0, duoi_tu=8.0, duoi_gia=55.0)
    assert dd.ung_vien_duoi_xau((canh,), diem) == []
    assert dd.ung_vien_duoi_xau((), diem) == []
