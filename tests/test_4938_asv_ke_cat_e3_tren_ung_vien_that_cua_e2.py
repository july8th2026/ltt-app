"""B13 E3 tren ung vien THAT do E2 sinh ra — khong chi ca dung tay (`test_4936`).

Nguoi dieu phoi (28/09): "Sau E2, chay lai phep kiem chong lap cua E3 tren
ung vien THAT do E2 sinh ra, khong chi tren ca dung tay."

Bai nay dung HAI nguon ung vien THAT — `giai_doan_hinh_anh.ung_vien_tu_ban_
bien_tap` (quyet dinh CAT CA canh, tu `BanBienTap`/`ChiMucCanh` that) va
`diem_dong.ung_vien_duoi_xau` (duoi canh xau, tu diem dong that) — tren CUNG
mot canh. Hai nguon nay CHONG LAN mot cach TU NHIEN: ban bien tap muon bo CA
canh, diem_dong chi muon bo DUOI cua no — dung ca ma §2.4 cua plan B13 mo ta,
⛔ khong phai mot cap khoang dung tay.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import ban_bien_tap as bbt
from apps.auto_scan_video import canh as canh_mod
from apps.auto_scan_video import diem_dong as dd
from apps.auto_scan_video import giai_doan_hinh_anh as gdha
from apps.auto_scan_video import ke_cat as kc
from apps.auto_scan_video.hop_dong_v4 import THAO_TAC_CAT


def _diem_deu(bat, ket, *, nen, duoi_tu, duoi_gia):
    ra, i = [], 1
    while True:
        giay = round(bat + i * 0.2, 4)
        if giay >= ket:
            break
        ra.append((giay, duoi_gia if giay >= duoi_tu else nen))
        i += 1
    return tuple(ra)


def test_ban_bien_tap_CA_canh_CHONG_LAN_duoi_canh_xau__hop_khong_dong_som():
    """Canh [0;20). Ban bien tap muon cat CA canh (do_tin 0,9). `diem_dong`
    thay duoi [17;20) bat thuong (he_so 5,0, > 0,9 nen duoc uu tien truoc —
    "KEM NHAT truoc"). Hai ung vien CHONG LAN HOAN TOAN (duoi la tap con cua
    ca canh).

    Ngan sach chon co y nam GIUA hop (20 s) va tong (23 s): `thoi_luong =
    430` -> `ngan_sach = 21,5 s`.
      - TONG (bay cu)  20 + 3 = 23 > 21,5  -> ung vien THU HAI (ca canh) se
        bi bao `vuot_tran` OAN, du no chi THEM 17 giay MOI vao hop.
      - HOP (dung)     hop({[17;20)}) = 3; hop({[17;20),[0;20)}) = 20 <= 21,5
        -> CA HAI duoc nhan.
    """
    chi_muc = canh_mod.ChiMucCanh(
        canh=(canh_mod.Canh(ma="c1", bat=0.0, ket=20.0),), thoi_luong=430.0)
    ban = bbt.BanBienTap(
        preset="smart_localize",
        quyet_dinh=(bbt.QuyetDinh("c1", THAO_TAC_CAT, "chat luong kem", 0.9),),
        thoi_luong_nguon=430.0)

    uv_ban_bien_tap = gdha.ung_vien_tu_ban_bien_tap(ban, chi_muc)
    assert len(uv_ban_bien_tap) == 1
    assert (uv_ban_bien_tap[0].bat, uv_ban_bien_tap[0].ket) == (0.0, 20.0)

    diem = _diem_deu(0.0, 20.0, nen=1.2, duoi_tu=17.0, duoi_gia=6.0)
    uv_duoi_xau = dd.ung_vien_duoi_xau(chi_muc.canh, diem)
    assert len(uv_duoi_xau) == 1
    assert uv_duoi_xau[0].bat == pytest.approx(17.0)
    assert uv_duoi_xau[0].ket == pytest.approx(20.0)
    assert uv_duoi_xau[0].diem_kem > uv_ban_bien_tap[0].diem_kem, (
        "canh dung: uv duoi_xau (he_so) phai duoc xep uu tien TRUOC "
        "(kem nhat truoc) de bai nay that su di qua nhanh HOP-truoc-roi-"
        "them, khong phai nhanh nguoc lai")

    ung_vien_that = list(uv_ban_bien_tap) + list(uv_duoi_xau)
    ke = kc.chon(ung_vien_that, thoi_luong=430.0)

    # ── Ca hai duoc nhan, gop thanh MOT khoang — ⛔ khong vuot_tran oan ──────
    assert ke.cat == ((0.0, 20.0),)
    assert ke.bo_qua == ()
    assert ke.giay_cat == pytest.approx(20.0)          # HOP, ⛔ khong 23,0 (TONG)
    assert ke.ti_le_cat == pytest.approx(20.0 / 430.0)


def test_ngan_sach_qua_hep_cho_HOP__chi_duoi_duoc_nhan_ca_canh_bi_loai_dung_HOP():
    """Ngan sach 15 s (thoi_luong = 300): du cho duoi rieng no (3 s) nhung
    khong du cho HOP ca hai (20 s, vi ca canh CHUA duoi trong no). Ung vien
    duoi_xau (uu tien cao hon) duoc nhan truoc; ca canh bi loai vi HOP (20 s)
    vuot 15 s — ⛔ khong phai vi mot phep cong lech nao."""
    chi_muc = canh_mod.ChiMucCanh(
        canh=(canh_mod.Canh(ma="c1", bat=0.0, ket=20.0),), thoi_luong=300.0)
    ban = bbt.BanBienTap(
        preset="smart_localize",
        quyet_dinh=(bbt.QuyetDinh("c1", THAO_TAC_CAT, "chat luong kem", 0.9),),
        thoi_luong_nguon=300.0)
    uv_ban_bien_tap = gdha.ung_vien_tu_ban_bien_tap(ban, chi_muc)
    diem = _diem_deu(0.0, 20.0, nen=1.2, duoi_tu=17.0, duoi_gia=6.0)
    uv_duoi_xau = dd.ung_vien_duoi_xau(chi_muc.canh, diem)

    ke = kc.chon(list(uv_ban_bien_tap) + list(uv_duoi_xau), thoi_luong=300.0)
    assert ke.cat == ((17.0, 20.0),)                  # chi duoi duoc nhan
    assert ke.giay_cat == pytest.approx(3.0)
    assert [(x["bat"], x["ly_do"]) for x in ke.bo_qua] == [
        (0.0, kc.LY_DO_VUOT_TRAN)]                     # ca canh bi loai
