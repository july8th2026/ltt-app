"""B4 hai giai doan — KE CAT cua GD2 va TRAN CUNG 5 %.

Nam nhom:

  A. Tran 5 %      — phim MUON cat 30 % ⇒ dung o 5 % **va KHAI RA**
  B. Bat bien bien — `kiem()` NEM; mot `KeCat` vuot tran khong the ton tai
  C. Loi thoai     — CHI cat vung khong thoai, va LOAI chu khong thu hep
  D. Uu tien       — KEM NHAT truoc, khai ra trong ma (khong phai he qua duyet)
  E. Ban do        — hinh va tieng bi cat CUNG NHAU, khong doan tieng nao cut
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import ke_cat as kc


def _uv(bat, ket, diem=0.9, ly_do="chat_luong_kem"):
    return kc.UngVien(bat=bat, ket=ket, diem_kem=diem, ly_do_cat=ly_do)


# ══════════════════════════════════════════════════════════════════════════════
#  A. Tran 5 % — phep kiem chu du an chot 25/09 doi
# ══════════════════════════════════════════════════════════════════════════════

def test_tieu_chi_MUON_cat_30_phan_tram__he_dung_o_5_va_KHAI_RA():
    """🔴 Menh de trung tam. ⛔ Khong im lang cat it di.

    Phim 1.000 giay. Tieu chi muon cat 30 doan x 10 giay = 300 giay = 30 %.
    Tran cho 50 giay = 5 %.
    """
    tl = 1000.0
    # 30 doan, moi doan 10 giay, dat cach nhau de khong chong lan.
    ung_vien = [_uv(i * 30.0, i * 30.0 + 10.0, diem=0.9) for i in range(30)]

    ke = kc.chon(ung_vien, thoai=(), thoi_luong=tl)

    # ── Dung o 5 %, khong hon mot phan nghin ────────────────────────────────
    assert ke.giay_cat == pytest.approx(50.0)
    assert ke.ti_le_cat == pytest.approx(0.05)
    assert ke.ti_le_cat <= kc.TRAN_CAT_TI_LE

    # ── Va KHAI RA phan khong cat duoc ──────────────────────────────────────
    vuot = [x for x in ke.bo_qua if x["ly_do"] == kc.LY_DO_VUOT_TRAN]
    assert len(vuot) == 25, [x["bat"] for x in vuot]
    assert sum(x["dai"] for x in vuot) == pytest.approx(250.0)

    tt = kc.tom_tat(ke)
    assert tt["dung_o_tran"] is True
    assert tt["ti_le_muon"] == pytest.approx(0.30)
    assert tt["giay_muon_cat"] == pytest.approx(300.0)
    assert tt["so_bo_qua"][kc.LY_DO_VUOT_TRAN] == 25


def test_dung_o_tran_PHAN_BIET_duoc_voi_tieu_chi_chi_muon_bay_nhieu():
    """⛔ "Hai trang thai gop thanh mot gia tri" — hai lan chay deu cat 5 %.

    Mot lan bi tran chan, mot lan tieu chi chi doi dung 5 %. `ti_le_cat` cua
    chung BANG NHAU; neu bao cao chi co con so do thi hai chuyen khac han nhau
    trong y het.
    """
    tl = 1000.0
    bi_chan = kc.chon([_uv(i * 30.0, i * 30.0 + 10.0) for i in range(30)],
                      thoi_luong=tl)
    vua_du = kc.chon([_uv(i * 30.0, i * 30.0 + 10.0) for i in range(5)],
                     thoi_luong=tl)

    assert bi_chan.ti_le_cat == pytest.approx(vua_du.ti_le_cat)   # ⚠️ trung nhau
    # ⭐ Nhung bao cao PHAN BIET duoc:
    assert kc.tom_tat(bi_chan)["dung_o_tran"] is True
    assert kc.tom_tat(vua_du)["dung_o_tran"] is False
    assert kc.tom_tat(vua_du)["ti_le_muon"] == pytest.approx(0.05)


# ══════════════════════════════════════════════════════════════════════════════
#  B. Bat bien O BIEN — `kiem()` NEM (khuon `hinh_hoc_dien_nen`)
# ══════════════════════════════════════════════════════════════════════════════

def test_kiem_NEM_khi_mot_KeCat_vuot_tran__doi_chung_that():
    """🔴 DOI CHUNG: ham that su bat duoc, khong phai mot phep kiem rong.

    Dung tay mot `KeCat` cat 20 % roi goi `kiem()`. Neu bat bien chi la mot `if`
    o cho goi thi dong nay se **xanh** — nen no phai do.
    """
    hong = kc.KeCat(cat=((0.0, 200.0),), thoi_luong=1000.0)
    assert hong.ti_le_cat == pytest.approx(0.20)
    with pytest.raises(kc.KeCatError) as e:
        kc.kiem(hong)
    # ⭐ Thong bao phai noi CA HAI con so — xem `kiem()`.
    assert "20" in str(e.value) and "5" in str(e.value)


def test_chon_KHONG_BAO_GIO_tra_ve_mot_ke_vuot_tran__du_tieu_chi_doi_gi():
    """⛔ `chon()` goi `kiem()` truoc khi tra ve: nguoi goi khong the quen."""
    for so_doan in (1, 5, 30, 200):
        ke = kc.chon([_uv(i * 5.0, i * 5.0 + 4.0) for i in range(so_doan)],
                     thoi_luong=2000.0)
        kc.kiem(ke)                       # khong nem
        assert ke.ti_le_cat <= kc.TRAN_CAT_TI_LE


def test_kiem_do_khoang_chong_lan_va_khoang_ngoai_thoi_luong():
    with pytest.raises(kc.KeCatError):
        kc.kiem(kc.KeCat(cat=((10.0, 20.0), (15.0, 30.0)), thoi_luong=1000.0))
    with pytest.raises(kc.KeCatError):
        kc.kiem(kc.KeCat(cat=((990.0, 1100.0),), thoi_luong=1000.0))
    with pytest.raises(kc.KeCatError):
        kc.kiem(kc.KeCat(cat=((10.0, 10.0),), thoi_luong=1000.0))


# ══════════════════════════════════════════════════════════════════════════════
#  C. Loi thoai — CHI cat vung khong thoai
# ══════════════════════════════════════════════════════════════════════════════

def test_doan_CHONG_LAN_khe_tieng_bi_LOAI__khong_bi_thu_hep():
    """⛔ Thu hep la tu bien tap ho khach; loai thi trung thuc va khai duoc."""
    ke = kc.chon([_uv(100.0, 110.0, diem=0.99)],
                 thoai=((105.0, 106.0),), thoi_luong=1000.0)
    assert ke.cat == ()
    assert [x["ly_do"] for x in ke.bo_qua] == [kc.LY_DO_CO_THOAI]


def test_doan_CHI_giap_ranh_khe_tieng_van_cat_duoc():
    """Giap ranh khong phai chong lan — nguoc lai thi khong doan nao cat duoc."""
    ke = kc.chon([_uv(100.0, 110.0)],
                 thoai=((90.0, 100.0), (110.0, 120.0)), thoi_luong=1000.0)
    assert ke.cat == ((100.0, 110.0),)


def test_khe_thoai_doc_tu_KE_HOACH_THOI_GIAN__khong_tu_ban_chep_loi_nguon():
    """🔑 Loi thu hai cua thu tu moi: "co thoai" doc thu SE PHAT RA.

    `dai_ms <= 0` la doan `lap_ke_hoach` DA bo — no khong chiem khe nao.
    """
    ke_hoach = {"doan": [
        {"ma": "a", "dat_tai_ms": 1000, "dai_ms": 2000},
        {"ma": "b", "dat_tai_ms": 9000, "dai_ms": 0},       # da bi bo
        {"ma": "c", "dat_tai_ms": 20000, "dai_ms": 500},
    ]}
    khe = kc.khe_thoai_tu_ke_hoach(ke_hoach)
    assert khe == ((1.0, 3.0), (20.0, 20.5))

    # Vung quanh doan DA BI BO thi cat duoc — khong gi phat ra o do.
    ke = kc.chon([_uv(8.0, 12.0)], thoai=khe, thoi_luong=1000.0)
    assert ke.cat == ((8.0, 12.0),)


def test_doan_ngan_hon_TOI_THIEU_bi_loai_kem_ly_do_RIENG():
    """⛔ "qua ngan" khac "co thoai" khac "vuot tran" — ba chuyen, ba ly do."""
    ke = kc.chon([_uv(10.0, 10.05)], thoi_luong=1000.0)
    assert ke.cat == ()
    assert [x["ly_do"] for x in ke.bo_qua] == [kc.LY_DO_QUA_NGAN]


# ══════════════════════════════════════════════════════════════════════════════
#  D. Thu tu uu tien — KEM NHAT truoc, va no duoc KHAI RA
# ══════════════════════════════════════════════════════════════════════════════

def test_dung_tran_thi_bo_doan_KEM_NHAT_truoc__KHONG_phai_doan_DAI_NHAT():
    """🔑 Chu du an doi quyet va khai ra. Day la phep kiem ghim quyet dinh do.

    Ngan sach 5 % cua 200 giay = 10 giay. Hai ung vien:
       A  9 giay, diem 0,40  (dai)
       B  4 giay, diem 0,95  (kem nhat)
    Bo "dai nhat truoc" se nhan A (9 giay) va het cho cho B.
    Bo "kem nhat truoc" nhan B roi khong con cho cho A.
    """
    ke = kc.chon([_uv(10.0, 19.0, diem=0.40), _uv(50.0, 54.0, diem=0.95)],
                 thoi_luong=200.0)
    assert ke.cat == ((50.0, 54.0),), "phai bo doan KEM NHAT truoc"
    assert [(x["bat"], x["ly_do"]) for x in ke.bo_qua] == [
        (10.0, kc.LY_DO_VUOT_TRAN)]


def test_cung_diem_kem_thi_DAI_HON_truoc__roi_moi_den_bat_som_hon():
    """Pha the: cung diem thi bo duoc nhieu hon; roi tat dinh theo `bat`."""
    ke = kc.chon([_uv(10.0, 13.0, diem=0.9), _uv(50.0, 59.0, diem=0.9)],
                 thoi_luong=200.0)
    assert ke.cat == ((50.0, 59.0),)

    # Cung diem, cung do dai -> `bat` som hon thang, va hai lan chay giong nhau.
    a = kc.chon([_uv(50.0, 54.0, diem=0.9), _uv(10.0, 14.0, diem=0.9)],
                thoi_luong=100.0)
    b = kc.chon([_uv(10.0, 14.0, diem=0.9), _uv(50.0, 54.0, diem=0.9)],
                thoi_luong=100.0)
    assert a.cat == b.cat == ((10.0, 14.0),)


def test_ke_cat_luon_theo_thu_tu_THOI_GIAN__khong_theo_thu_tu_uu_tien():
    """⛔ `concat` doc danh sach nay: sai thu tu la dung lai canh phim."""
    ke = kc.chon([_uv(500.0, 505.0, diem=0.99), _uv(100.0, 104.0, diem=0.50),
                  _uv(300.0, 303.0, diem=0.80)], thoi_luong=1000.0)
    assert ke.cat == ((100.0, 104.0), (300.0, 303.0), (500.0, 505.0))


def test_hai_khoang_cat_LIEN_NHAU_duoc_gop():
    ke = kc.chon([_uv(100.0, 110.0), _uv(110.0, 120.0)], thoi_luong=1000.0)
    assert ke.cat == ((100.0, 120.0),)


# ══════════════════════════════════════════════════════════════════════════════
#  E. Ban do — hinh va tieng bi cat CUNG NHAU
# ══════════════════════════════════════════════════════════════════════════════

def test_giu_la_PHAN_BU_cua_cat__tinh_o_MOT_cho():
    ke = kc.KeCat(cat=((10.0, 20.0), (50.0, 60.0)), thoi_luong=100.0)
    assert ke.giu == ((0.0, 10.0), (20.0, 50.0), (60.0, 100.0))
    assert ke.giay_cat == 20.0


def test_cat_o_dau_va_o_cuoi_khong_sinh_khoang_rong():
    assert kc.KeCat(cat=((0.0, 10.0),), thoi_luong=100.0).giu == ((10.0, 100.0),)
    assert kc.KeCat(cat=((90.0, 100.0),), thoi_luong=100.0).giu == ((0.0, 90.0),)


def test_ban_do_cua_ke_cat_doi_moc_dung__mot_tep_MOT_phep_doi():
    """🔑 O GD2, ban do doi moc tren MOT tep da xong.

    Cat [10;20). Giay 35 cua GD1 la giay 25 cua ban giao — hinh VA tieng cung
    lui 10 giay, vi ca hai di qua cung mot `concat`.
    """
    ke = kc.KeCat(cat=((10.0, 20.0),), thoi_luong=100.0)
    bd = ke.ban_do()
    assert bd.thoi_luong_ra == 90.0
    assert bd.ra(5.0) == 5.0
    assert bd.ra(35.0) == 25.0
    # Moc NAM TRONG phan da cat thi khong ton tai o ban giao.
    assert bd.ra(15.0) is None


def test_khong_cat_gi_thi_ban_do_la_DONG_NHAT():
    ke = kc.chon([], thoi_luong=100.0)
    assert ke.co_cat is False
    bd = ke.ban_do()
    assert bd.thoi_luong_ra == 100.0 and bd.so_cho_noi == 0


def test_sang_dict_roi_tu_dict_giu_nguyen_ke__ke_ca_phan_KHAI_RA():
    ke = kc.chon([_uv(i * 30.0, i * 30.0 + 10.0) for i in range(30)],
                 thoi_luong=1000.0)
    lai = kc.KeCat.tu_dict(ke.sang_dict())
    assert lai.cat == ke.cat
    assert lai.thoi_luong == ke.thoi_luong
    # ⛔ `bo_qua` KHONG duoc mat trong vong doi tuan tu hoa: no la nua "khai ra".
    assert len(lai.bo_qua) == len(ke.bo_qua)
    assert kc.tom_tat(lai)["dung_o_tran"] is True
