"""Pha V5 — bon luat hinh hoc cua vung che.

Ca bon luat deu do mot he thong khac tra gia de hoc; xuat xu o
`docs/auto_scan_video_v5/VIRAL_RENDER_FEATURE_MAP.md` §3. Tep nay bien chung tu
mot doan van trong tai lieu thanh mot rang buoc co rang.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import vung_che as vc


def _hop(**them):
    ra = {"loai": vc.LOAI_LAM_MO, "y0": 0.80, "y1": 0.95, "x0": 0.1, "x1": 0.9}
    ra.update(them)
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  L1 — toa do la PHAN SO, khong pixel
# ══════════════════════════════════════════════════════════════════════════════

def test_toa_do_ngoai_khoang_0_1_bi_TU_CHOI():
    """Mot hop tinh bang pixel (vd `y0=540`) phai chet o cua.

    ⭐ Day chinh la cach mot loi "quen chuan hoa" o giao dien lo ra: no khong
       hien thanh mot o che lech, no hien thanh mot loi ro rang.
    """
    for xau in ({"y1": 540}, {"y0": -0.1}, {"x1": 1.4}):
        with pytest.raises(vc.VungLoi):
            vc.chuan_hoa_mot(_hop(**xau))


def test_khong_so_thi_TU_CHOI():
    for xau in ({"y0": "gan day"}, {"x1": None}, {"y1": [0.9]}):
        with pytest.raises(vc.VungLoi):
            vc.chuan_hoa_mot(_hop(**xau))


def test_NaN_va_vo_cuc_bi_chan_RIENG():
    """⚠️ `float("nan")` doc duoc, va MOI phep so sanh voi no deu False — nen no
    lot qua `0 <= x <= 1` neu khong chan rieng.

    🔴 Mot NaN lot qua se di toi ffmpeg va thanh mot bo loc khong hop le **o giua
       chuoi** — sau khi khach da doi qua may giai doan va da bi giu credit.
    """
    for xau in ({"y0": float("nan")}, {"y1": float("inf")}):
        with pytest.raises(vc.VungLoi):
            vc.chuan_hoa_mot(_hop(**xau))


# ══════════════════════════════════════════════════════════════════════════════
#  L2 — sai thi TU CHOI, khong DOAN
# ══════════════════════════════════════════════════════════════════════════════

def test_hop_NGUOC_bi_tu_choi_chu_KHONG_bi_doi_cho():
    """⛔ Cach "de dai" la hoan doi `y0`/`y1` cho khach. Dung the la thi hanh mot
    hop khach **khong ve**, va khach khong co cach nao biet."""
    with pytest.raises(vc.VungLoi):
        vc.chuan_hoa_mot(_hop(y0=0.9, y1=0.2))


def test_hop_qua_NHO_bi_tu_choi():
    """Mot lan click nham khong phai mot y dinh, nhung no van ton mot bo loc."""
    with pytest.raises(vc.VungLoi):
        vc.chuan_hoa_mot(_hop(y0=0.50, y1=0.502))


def test_loai_vung_ngoai_danh_sach_bi_tu_choi():
    """⛔ `xoa_nen`, `logo`, `chu` deu dang `DEFER`. Nhan mot ma la la mo mot
    duong chua ai do VRAM."""
    with pytest.raises(vc.VungLoi):
        vc.chuan_hoa_mot(_hop(loai="xoa_nen"))
    with pytest.raises(vc.VungLoi):
        vc.chuan_hoa_mot(_hop(loai=""))


def test_qua_nhieu_vung_bi_tu_choi():
    with pytest.raises(vc.VungLoi):
        vc.chuan_hoa([_hop() for _ in range(vc.SO_VUNG_TOI_DA + 1)])


def test_thong_bao_loi_la_cau_TIENG_VIET_cho_khach():
    """Khach doc thong bao nay. No khong duoc chua ten truong hay ten ham."""
    try:
        vc.chuan_hoa_mot(_hop(y1=540))
    except vc.VungLoi as exc:
        van = str(exc)
    assert van and van[0].isupper()
    for cam in ("y0", "y1", "float", "None", "dict", "ValueError"):
        assert cam not in van, f"thong bao lo `{cam}`"


def test_danh_sach_RONG_la_hop_le():
    """Phan lon lan chay khong co vung nao — do la duong BINH THUONG."""
    assert vc.chuan_hoa([]) == []
    assert vc.chuan_hoa(None) == []


# ══════════════════════════════════════════════════════════════════════════════
#  L3 — bien doi hinh: LOAI hop, khong KEP ve bien
# ══════════════════════════════════════════════════════════════════════════════
#
# ⚠️ KHONG co phep kiem nao o day, va do la mot quyet dinh chu khong phai mot
#    thieu sot.
#
#    Ban dau toi viet `vung_che.anh_xa_zoom` + ba phep kiem cho no, voi ly do
#    "luat co truoc tinh nang". `test_453` chan lai: mot ham khong nguoi goi
#    trong ma san pham la mot nang luc **viet xong roi quen noi vao mach**, va
#    docstring cua chinh no noi ro cach sua la NOI VAO MACH chu khong phai them
#    ten vao danh sach mien tru.
#
# ⭐ `zoom` nam trong `CAM_TRONG_MVP` nen khong co mach de noi vao. Luat vi the
#    song o `V5_UI_INFORMATION_ARCHITECTURE.md` §11 luat 3 — kem cong thuc va
#    kem bang chung (loi zoom 2026-07 cua he tham chieu: kep ve bien **che nham
#    mot vung trong**). Ngay ADR-V5 mo `zoom`, phep kiem dau tien phai la hop bi
#    cat mat khoi khung tra ve "khong con nghia", khong phai mot hop kep o bien.


# ══════════════════════════════════════════════════════════════════════════════
#  Khoang thoi gian
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_dat_thoi_gian_thi_ap_CA_video():
    assert "tu_giay" not in vc.chuan_hoa_mot(_hop())


def test_khoang_thoi_gian_nguoc_bi_tu_choi():
    with pytest.raises(vc.VungLoi):
        vc.chuan_hoa_mot(_hop(tu_giay=10.0, den_giay=4.0))
    with pytest.raises(vc.VungLoi):
        vc.chuan_hoa_mot(_hop(tu_giay=-1.0))


def test_khoang_thoi_gian_hop_le_duoc_giu():
    ra = vc.chuan_hoa_mot(_hop(tu_giay=2.5, den_giay=9.0))
    assert (ra["tu_giay"], ra["den_giay"]) == (2.5, 9.0)
