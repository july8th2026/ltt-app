"""R-01 §2 — `AUTO_MATCH` rang duoc giong, va van BIET DUNG LAI khi khong co can cu.

Hai nua cua cung mot hop dong, va nua thu hai de mat hon:

  * mot ho so ba mat KHONG khop het van phai chot duoc giong (`rang_noi_long`);
  * khong co can cu thi van la `CHUA_RANG` — `ADR-V4-001` D-V4-04 cam thoai hoa
    thanh "giong mac dinh", va mot ban sua vuot ra ngoai luat do se khong lo ra
    o bat cu phep kiem nao ve chuoi.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import rang_giong as rg
from apps.auto_scan_video.hop_dong_v4 import (CHE_DO_GIONG_TU_CHON,
                                              CHE_DO_GIONG_TU_KHOP)


def _yc(**dd):
    return rg.YeuCau(che_do=CHE_DO_GIONG_TU_KHOP,
                     dac_diem=rg.DacDiemMongMuon(**dd))


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Noi long — bo mat IT CU nhat truoc, khong bao gio bo `gioi`
# ══════════════════════════════════════════════════════════════════════════════

def test_to_hop_khong_co_trong_catalog_van_chot_duoc_giong():
    """⭐ 20 giong mau phu 13 to hop. Mot ho so dung tuyet doi — "nu, mien
    Trung, tin tuc" — van co the tra ve khong ung vien nao, va bo cuoc o do la
    vut di mot rang buoc CO GIA (`gioi`) chi vi mot rang buoc khong co gia."""
    kq = rg.rang_noi_long(None, owner_id="uA",
                          yeu_cau=_yc(gioi="nu", vung="trung",
                                      phong_cach="tin_tuc"))
    assert kq.da_chot
    assert kq.nguon == rg.NGUON_TU_KHOP
    assert kq.can_cu["mat_da_noi_long"] == ["phong_cach"]


def test_khop_duoc_ngay_thi_KHONG_noi_long_mat_nao():
    kq = rg.rang_noi_long(None, owner_id="uA",
                          yeu_cau=_yc(gioi="nu", vung="bac",
                                      phong_cach="tu_nhien"))
    assert kq.da_chot
    assert "mat_da_noi_long" not in kq.can_cu


def test_thu_tu_noi_long_la_phong_cach_ROI_MOI_vung():
    """🔑 `phong_cach` la **nhan mo ta giong, khong phai nut van** — mat model
    doan yeu nhat. `vung` la giong vung mien tieng Viet, thu mot phim tieng
    Trung khong mang thong tin nao ve no. Ca hai deu bo truoc `gioi`."""
    assert rg.THU_TU_NOI_LONG == ("phong_cach", "vung")


def test_GIOI_khong_bao_gio_bi_bo():
    """⛔ Bo not `gioi` thi phep loc tra ve ca catalog, va "lay cai dau tien cua
    ca catalog" chinh la giong mac dinh doi ten — dung dieu D-V4-04 cam."""
    assert "gioi" not in rg.THU_TU_NOI_LONG
    # Mot gioi khong ton tai: khong giong nao khop, va ket qua la CHUA_RANG
    # chu khong phai "giong dau bang".
    kq = rg.rang_noi_long(None, owner_id="uA", yeu_cau=_yc(gioi="phi gioi"))
    assert not kq.da_chot


def test_chot_duoc_bang_MOT_MAT_do_duoc():
    """Duong that pho bien nhat: model im lang, chi co F0 noi duoc gioi."""
    kq = rg.rang_noi_long(None, owner_id="uA", yeu_cau=_yc(gioi="nam"))
    assert kq.da_chot and kq.can_cu["dac_diem"] == {
        "gioi": "nam", "vung": "", "phong_cach": ""}


def test_hai_lan_chay_cung_dac_diem_ra_CUNG_mot_giong():
    """⭐ Van tay cua `content_process` co `ma_giong` trong do; mot ket qua nhay
    lam moi diem chot da tra tien khong con tinh."""
    a = rg.rang_noi_long(None, owner_id="uA", yeu_cau=_yc(gioi="nu"))
    b = rg.rang_noi_long(None, owner_id="uA", yeu_cau=_yc(gioi="nu"))
    assert a.giong_id == b.giong_id != ""


# ══════════════════════════════════════════════════════════════════════════════
#  §2  `CHUA_RANG` van la mot trang thai THAT
# ══════════════════════════════════════════════════════════════════════════════

def test_ho_so_rong_van_la_CHUA_RANG_chu_khong_phai_mot_giong():
    kq = rg.rang_noi_long(None, owner_id="uA", yeu_cau=_yc())
    assert kq.trang_thai == rg.CHUA_RANG and kq.giong_id == ""
    with pytest.raises(rg.ChuaRangError):
        kq.ma_giong()


def test_cau_loi_NOI_DUNG_thieu_gi():
    """🔴 Khach doc "khong giong nao khop" se lam mot viec khac han khi doc
    "chua co ho so noi dung". Hai trang thai, hai cau."""
    chua_co = rg.rang_noi_long(None, owner_id="uA", yeu_cau=_yc())
    khong_khop = rg.rang_noi_long(None, owner_id="uA",
                                  yeu_cau=_yc(gioi="phi gioi"))
    a, b = rg.vi_sao_chua_rang(chua_co), rg.vi_sao_chua_rang(khong_khop)
    assert a != b
    # Ca hai deu phai chi cho khach loi ra, khong phai mot ma loi.
    assert "tự chọn" in a and "tự chọn" in b


def test_USER_SELECTED_di_nguyen_duong_cu():
    """⛔ Noi long chi ap cho `AUTO_MATCH`. Mot ma giong khach GO VAO khong bao
    gio duoc "noi long" thanh mot giong khac — ket qua phai la DUNG giong do,
    voi nguon `khach_chon`, va khong mot mat nao bi dong vao ho."""
    kq = rg.rang_noi_long(None, owner_id="uA",
                          yeu_cau=rg.YeuCau(che_do=CHE_DO_GIONG_TU_CHON,
                                            giong_id="Minh Đức"))
    assert kq.giong_id == "Minh Đức"
    assert kq.nguon == rg.NGUON_KHACH_CHON
    assert "mat_da_noi_long" not in kq.can_cu


# ══════════════════════════════════════════════════════════════════════════════
#  §3  `can_cho_ho_so` — cau hoi cua dieu phoi, sau khi da co nguoi tra loi
# ══════════════════════════════════════════════════════════════════════════════

def test_can_cho_ho_so_dung_cho_AUTO_MATCH_chua_co_dac_diem():
    assert rg.can_cho_ho_so(_yc()) is True


def test_khong_can_nua_khi_ho_so_DA_GHI_xuong_thiet_lap():
    """⭐ Day la cai khien ca duong nay luy dang: luot chay lai doc `dac_diem`
    da ghi, khong goi model lan hai, va rang ra dung giong cu."""
    yc = rg.tu_thiet_lap({"che_do_giong": CHE_DO_GIONG_TU_KHOP,
                          "dac_diem_giong": {"gioi": "nam"}})
    assert rg.can_cho_ho_so(yc) is False


def test_USER_SELECTED_khong_bao_gio_cho_ho_so():
    yc = rg.YeuCau(che_do=CHE_DO_GIONG_TU_CHON, giong_id="Minh Đức")
    assert rg.can_cho_ho_so(yc) is False
