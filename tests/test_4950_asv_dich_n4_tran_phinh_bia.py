"""B14/V3 N4 — tran PHAT HIEN dich PHINH/BIA, muon `D:\\Viral\\...\\ai_dich.py:1062-1077
_parse_lo` (chi doc). Chot 28/09 cua chu du an: dung NGUYEN cong thuc, khong
hieu chinh.

Cua nay la PHAT HIEN thuan tuy: `cau_dich_phinh_bia` chi tra ve True/False,
khong sua, khong cat gi ca — xem `apps/auto_scan_video/dich_thuat.py`.
"""
from __future__ import annotations

from apps.auto_scan_video import dich_thuat


def test_cau_PHINH_that_su_bi_gan_co():
    """Ca DUONG: nguon rat ngan, dich rat dai — dung hinh ca "AI ke/bia"."""
    nguon = "他来了。"  # 4 ky tu Han
    # 41 tu tieng Viet — vuot 4*10=40 va vuot tran tuyet doi 90 ky tu.
    dich = " ".join(["mot"] * 41) + " " + "x" * 60
    assert dich_thuat.cau_dich_phinh_bia(nguon, dich) is True


def test_cau_DAI_TUONG_XUNG_KHONG_bi_gan_co():
    """⭐ DOI CHUNG AM (bat buoc) — nguon DAI dich ra DAI TUONG XUNG (ti le
    duoi 10x) khong duoc gan co, du ban dich dai hon 90 ky tu.
    """
    nguon = "这" * 30                      # 30 ky tu Han
    dich = " ".join(["tu"] * 100)          # 100 tu — ti le 100/30 ≈ 3,3x < 10x
    assert len(dich) > 90, "mau thu qua ngan — chua vuot tran tuyet doi"
    assert dich_thuat.cau_dich_phinh_bia(nguon, dich) is False


def test_ngan_thi_khong_gan_co_du_ti_le_cao():
    """Mot minh TI LE khong du — con phai vuot tran TUYET DOI 90 ky tu."""
    nguon = "他"                            # 1 ky tu
    dich = " ".join(["a"] * 15)             # 15 tu, ti le 15x nhung < 90 ky tu
    assert len(dich) <= 90
    assert dich_thuat.cau_dich_phinh_bia(nguon, dich) is False


def test_dich_rong_khong_gan_co():
    assert dich_thuat.cau_dich_phinh_bia("有内容", "") is False
    assert dich_thuat.cau_dich_phinh_bia("有内容", "   ") is False


def test_dich_luon_co_dau_cach_nen_dung_tran_90_khong_bao_gio_60():
    """🔴 Dich cua ta CHI co vi/en (La Tinh, CO dau cach) — nhanh `>60` (CJK
    dinh lien) cua Viral khong bao gio duoc chon. Kiem bang mot cau vua qua
    60 ky tu (se PHINH neu dung sai nhanh `>60`) nhung chua toi 90.
    """
    nguon = "字"  # 1 ky tu -> n_nguon=1, moi nguong ti le deu de vuot
    dich = " ".join(["abcde"] * 13)  # 13 tu (>10) x 5 ky tu = 77 ky tu: >60, <=90
    assert 60 < len(dich) <= 90, "mau thu phai nam giua hai nhanh de phan biet"
    # Neu ham dung SAI nhanh `>60` thi ket qua se la True — phai la False.
    assert dich_thuat.cau_dich_phinh_bia(nguon, dich) is False
