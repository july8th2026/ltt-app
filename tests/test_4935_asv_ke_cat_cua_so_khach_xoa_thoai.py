"""B13 E1 — cua so khach (`cat_dau_cuoi`) xoa loi thoai phai duoc DEM, va CANH
BAO, ⛔ khong chan.

Bo moc THAT tu luot do `asvr_47327a869a8f4597960048f09064740`
(`docs/auto_scan_video_final/B13_PLAN_NAM_HANG_MUC.md` §2.2): video 275,008 s,
`ti_le_giu = 1.0` (may cat canh khong cat gi), cua so khach `[0.05, 0.95]` ->
`khoang_giu = [[13.7504, 261.2579]]`. Cai gia dung bang loi thoai: 6 doan mat
han (seg_0001..0003 dau, seg_0076..0078 cuoi) + 1 doan mat mot phan
(seg_0004, 11.28..15.46, bi cat ngan o dau).
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import cat_dau_cuoi
from apps.auto_scan_video import ke_cat as kc

THOI_LUONG = 275.008
CUA_SO_KHACH = (0.05, 0.95)

# Cac khe thoai (bat, ket) tren truc BAN RA — mot tap con dai dien cua 78 doan
# that, du de tai hien dung 6 mat han + 1 mat mot phan cua plan.
THOAI_THAT = (
    (0.11, 2.63),        # seg_0001 — truoc cua so -> mat han
    (2.63, 6.40),        # seg_0002 — truoc cua so -> mat han
    (6.40, 11.28),        # seg_0003 — truoc cua so -> mat han
    (11.28, 15.46),       # seg_0004 — cham mep dau cua so -> mat MOT PHAN
    (100.0, 105.0),       # doan giua, nam TRON trong cua so -> khong mat gi
    (262.24, 263.04),     # seg_0076 — sau cua so -> mat han
    (263.04, 273.84),     # seg_0077 — sau cua so -> mat han
    (273.84, 275.008),    # seg_0078 — sau cua so -> mat han (khop THOI_LUONG)
)


def _khoang_sau_cua_so(cua_so):
    """Mo phong dung `chay()`: khong canh nao bi may cat (`ti_le_giu = 1.0`) nen
    `ke.giu == [(0, thoi_luong)]`; cua so khach giao THEM vao do."""
    ke = kc.chon([], thoi_luong=THOI_LUONG)
    assert ke.giu == ((0.0, THOI_LUONG),)
    cua = cat_dau_cuoi.chuan_hoa(cua_so)
    return cat_dau_cuoi.giao(list(ke.giu), cua, THOI_LUONG), cua


# ══════════════════════════════════════════════════════════════════════════════
#  Bo moc that: cua so [0.05, 0.95] -> 6 mat han + 1 mat mot phan
# ══════════════════════════════════════════════════════════════════════════════

def test_cua_so_khach_that_xoa_DUNG_6_mat_han_1_mat_mot_phan():
    khoang, cua = _khoang_sau_cua_so(CUA_SO_KHACH)
    assert cua == pytest.approx(CUA_SO_KHACH)
    # ⭐ Ghim dung con so `khoang_giu` cua luot that o §2.2 truoc khi dem thoai.
    assert len(khoang) == 1
    # abs=1e-3: so lieu §2.2 la con so DA LAM TRON 4 chu so cua phep nhan
    # phan-so x thoi-luong, ⛔ khong phai gia tri float chua lam tron.
    assert khoang[0] == pytest.approx((13.7504, 261.2579), abs=1e-3)

    mat_han, mat_mot_phan = kc.thoai_bi_xoa(THOAI_THAT, khoang)
    assert (mat_han, mat_mot_phan) == (6, 1)


def test_tung_doan_mat_han_KHONG_con_mot_giay_nao_trong_cua_so():
    khoang, _ = _khoang_sau_cua_so(CUA_SO_KHACH)
    mat_han_mong_doi = ((0.11, 2.63), (2.63, 6.40), (6.40, 11.28),
                        (262.24, 263.04), (263.04, 273.84), (273.84, 275.04))
    for tb, tk in mat_han_mong_doi:
        h, p = kc.thoai_bi_xoa(((tb, tk),), khoang)
        assert (h, p) == (1, 0), (tb, tk)


def test_doan_seg_0004_MAT_MOT_PHAN__con_lai_dung_phan_trong_cua_so():
    khoang, _ = _khoang_sau_cua_so(CUA_SO_KHACH)
    h, p = kc.thoai_bi_xoa(((11.28, 15.46),), khoang)
    assert (h, p) == (0, 1)


def test_doan_nam_TRON_trong_cua_so_KHONG_bi_dem():
    khoang, _ = _khoang_sau_cua_so(CUA_SO_KHACH)
    h, p = kc.thoai_bi_xoa(((100.0, 105.0),), khoang)
    assert (h, p) == (0, 0)


# ══════════════════════════════════════════════════════════════════════════════
#  cat = None -> khong cua so nao -> 0 va 0
# ══════════════════════════════════════════════════════════════════════════════

def test_cat_None_khong_xoa_gi__0_va_0():
    khoang, cua = _khoang_sau_cua_so(None)
    assert cua is None
    assert len(khoang) == 1
    assert khoang[0] == pytest.approx((0.0, THOI_LUONG))

    mat_han, mat_mot_phan = kc.thoai_bi_xoa(THOAI_THAT, khoang)
    assert (mat_han, mat_mot_phan) == (0, 0)


def test_cua_so_toan_video_L4_tuong_duong_None__0_va_0():
    """`(0.0, 1.0)` chuan hoa ve `None` (L4 cua `cat_dau_cuoi`) — cung mot ket
    qua voi khong dat cua so nao."""
    khoang, cua = _khoang_sau_cua_so((0.0, 1.0))
    assert cua is None
    mat_han, mat_mot_phan = kc.thoai_bi_xoa(THOAI_THAT, khoang)
    assert (mat_han, mat_mot_phan) == (0, 0)


# ══════════════════════════════════════════════════════════════════════════════
#  Ham thuan `thoai_bi_xoa` — bien
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_co_khe_thoai_nao__khong_dem_gi():
    assert kc.thoai_bi_xoa((), [(10.0, 20.0)]) == (0, 0)


def test_khong_co_khoang_giu_nao__moi_khe_MAT_HAN():
    h, p = kc.thoai_bi_xoa(((0.0, 5.0), (10.0, 12.0)), [])
    assert (h, p) == (2, 0)
