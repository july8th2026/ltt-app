"""B14/V3 N6 — phat hien GOP CAU qua do dai bat thuong TRONG CUNG LO, muon
`D:\\Viral\\...\\dich_gemini_web.py:1366-1416 _bo_key_gop/_nguong_gop` (chi
doc). Chot 28/09 cua chu du an: nguong dung NGUYEN — tran tuyet doi 200 ky tu +
tran tuong doi trung_vi*4, do that **27.139 cue / 90 video** (p50=29, p90=48,
p99=63).

Cua nay dung o CAP LO (khong phai ca video) — mot cau dai bat thuong trong mot
lo thoai it khac han mot lo thoai nhieu. Xem `apps/auto_scan_video/dich_thuat.py`
va `giai_doan_noi_dung.chay` (goi trong vong lap MOI LO).
"""
from __future__ import annotations

from apps.auto_scan_video import dich_thuat


def test_nguong_dung_NGUYEN_ban_cua_Viral():
    assert dich_thuat.TRAN_GOP_CAU_TUYET_DOI == 200
    assert dich_thuat.HE_SO_GOP_CAU_TUONG_DOI == 4


def test_mot_ma_GOP_CAU_bi_gan_co():
    """Ca DUONG: mot ma dai vot han cac ma con lai TRONG CUNG LO."""
    lo = {"seg_01": 30, "seg_02": 28, "seg_03": 32, "seg_04": 25,
          "seg_05": 220}   # gop 2-3 doan vao 1 khoa
    ra = dich_thuat.danh_dau_gop_cau(lo)
    assert ra == {"seg_05"}


def test_lo_THOAI_NHIEU_deu_nhau_KHONG_bi_gan_co():
    """⭐ DOI CHUNG AM (bat buoc) — lo ma MOI cau deu dai DEU NHAU (phim nhieu
    loi thoai) khong duoc gan co, du tung gia tri co the cao hon mot lo thoai
    it.
    """
    lo = {f"seg_{i:02d}": 150 for i in range(8)}   # deu 150 ky tu, deu < 200
    assert dich_thuat.danh_dau_gop_cau(lo) == set()


def test_can_CA_HAI_dieu_kien__vuot_tuyet_doi_khong_du():
    """Mot ma dai (>200) nhung o mot lo ma trung vi CUNG cao (vd phim day
    thoai) thi KHONG vuot nguong TUONG DOI — khong duoc gan co mot minh boi
    tran tuyet doi.
    """
    lo = {"a": 210, "b": 205, "c": 208, "d": 60}
    # trung vi ~ (205+208)/2 = 206.5 -> *4 = 826; khong ma nao vuot 826.
    assert dich_thuat.danh_dau_gop_cau(lo) == set()


def test_can_CA_HAI_dieu_kien__vuot_tuong_doi_khong_du():
    """Mot ma vuot median*4 nhung CHUA toi tran tuyet doi 200 thi cung khong
    bi gan co (cue ngan tu nhien co the dao dong).
    """
    lo = {"a": 10, "b": 12, "c": 11, "d": 80}   # trung vi ~11, *4=44; 80>44
    # nhung 80 <= 200 nen KHONG vuot tran tuyet doi -> khong gan co.
    assert dich_thuat.danh_dau_gop_cau(lo) == set()


def test_lo_rong_tra_ve_rong():
    assert dich_thuat.danh_dau_gop_cau({}) == set()


def test_nhieu_ma_cung_vuot_deu_bi_gan_co():
    # Nam ma "lanh" giu trung vi thap (~22) de hai ma "gop" (300/310) vuot ro
    # ca hai dieu kien; chi hai ma to (300, 310) mot minh se khong du DU LIEU
    # de tinh mot trung vi thap nhu vay.
    lo = {"a": 20, "b": 22, "c": 21, "d": 19, "e": 23, "f": 300, "g": 310}
    assert dich_thuat.danh_dau_gop_cau(lo) == {"f", "g"}
