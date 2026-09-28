"""P0-c — **BAI PHAN SO**: cua so `cat_dau_cuoi` cua khach la mot PHAN SO, nen no
chi dung MOT lan, va chi tren MOT do dai.

## Cau hoi lan P0-c phai tra loi bang phep do, ⛔ khong bang loi

Brief P0-c de nghi doi viec **ap cua so `cat_dau_cuoi`** len `media_prepare` de
ASR ⛔ khong phai nghe phan khach da bo. Cua so ay ⛔ **khong** phai mot so GIAY —
`cat_dau_cuoi.chuan_hoa` (L1, `cat_dau_cuoi.py:11-14`) tra ve mot cap **PHAN SO
0..1 cua THOI LUONG**, va phep doi sang giay nam o `cat_dau_cuoi.giao`, noi nhan
`thoi_luong` tu **noi goi**.

⇒ 🔑 Cung mot khai `(tu, den)` ap tren do dai **GOC** va ap tren do dai **DA CAT**
   cho **HAI ket qua khac nhau**, va ti so giua chung la `(den - tu)` — tuc mot
   lan ap thu hai ⛔ khong phai "khong lam gi", no cat THEM.

## ⛔ Va hom nay cua so duoc ap o HAI cho, ca hai tren do dai GOC

    giai_doan_hinh_anh.py:364-369   cat THAT  — `giao(ke.giu, cua, thoi_luong)`
                                    voi `thoi_luong` = do dai MP4 cua GD1
    giai_doan_qc.py:271-275         DUNG LAI phep giao de biet do dai mong doi,
                                    voi `dai_vao` = `tong_ms` cua ke hoach

Hai cho ay **dong y voi nhau** vi chung nhan cung mot do dai vao. Dat mot lan ap
thu ba o `media_prepare` thi ca hai van dong y — voi nhau, tren mot ban giao
SAI. Do la ly do bai `test_qc_dong_thuan_voi_ban_giao_SAI` o duoi ton tai: no do
**su VANG MAT cua mot phep kiem**, thu ⛔ khong bang do phu nao bat duoc.

Bo moc that lay tu luot `asvr_47327a869a8f4597960048f09064740`
(`B13_PLAN_NAM_HANG_MUC.md` §2.2, cung bo moc voi `test_4935`).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import cat_dau_cuoi, ke_cat as kc  # noqa: E402
from apps.auto_scan_video.giai_doan_qc import _thoi_luong_mong_doi  # noqa: E402

#: Bo moc that — video 275,008 s, khach keo cua so `[0,05 ; 0,95]`.
THOI_LUONG_GOC = 275.008
CUA_SO = (0.05, 0.95)


def _giu_ca_video(thoi_luong: float):
    """`ke.giu` khi may cat canh ⛔ khong cat gi (`ti_le_giu = 1.0`)."""
    ke = kc.chon([], thoi_luong=thoi_luong)
    assert ke.giu == ((0.0, thoi_luong),)
    return list(ke.giu)


def _ap_mot_lan(thoi_luong: float):
    """Ap cua so DUNG mot lan tren `thoi_luong`. Tra `(khoang, do_dai)`."""
    cua = cat_dau_cuoi.chuan_hoa(CUA_SO)
    khoang = cat_dau_cuoi.giao(_giu_ca_video(thoi_luong), cua, thoi_luong)
    return khoang, sum(k - b for b, k in khoang)


# ══════════════════════════════════════════════════════════════════════════════
#  BAI PHAN SO — cung mot khai, hai do dai, hai ket qua
# ══════════════════════════════════════════════════════════════════════════════

def test_cua_so_la_PHAN_SO_chu_khong_phai_GIAY():
    """Chot ĐẠI LƯỢNG truoc khi chot con so: `chuan_hoa` tra 0..1, ⛔ khong giay.

    ⭐ Bai nay la cai chan bai duoi dung tren: neu mot ngay nao do cua so doi
       sang giay thi phep nhan `cua_so[i] * thoi_luong` o `giao` thanh vo nghia,
       va ca lap luan cua tep nay phai viet lai.
    """
    cua = cat_dau_cuoi.chuan_hoa(CUA_SO)
    assert cua == pytest.approx(CUA_SO)
    assert all(0.0 <= x <= 1.0 for x in cua)
    # `giao` la DUY NHAT cho doi phan so -> giay, va no nhan `thoi_luong` tu
    # NGUOI GOI. Hai nguoi goi khac nhau => hai truc khac nhau.
    assert "thoi_luong" in cat_dau_cuoi.giao.__code__.co_varnames


def test_bai_phan_so__ap_tren_do_dai_GOC_va_DA_CAT_cho_hai_ket_qua():
    """🔑 Cau hoi quan trong nhat cua lan P0-c, tra loi bang so.

    Ap tren do dai GOC       -> giu 247,507 s  (= 0,90 x 275,008)
    Ap tren do dai DA CAT    -> giu 222,757 s  (= 0,90 x 247,507 = 0,81 x goc)
    """
    khoang_goc, dai_goc = _ap_mot_lan(THOI_LUONG_GOC)
    assert khoang_goc[0] == pytest.approx((13.7504, 261.2579), abs=1e-3)
    assert dai_goc == pytest.approx(0.90 * THOI_LUONG_GOC, abs=1e-6)

    # Gia dinh cua brief: `media_prepare` da cat, nen do dai vao cua ha nguon la
    # `dai_goc`. Cung MOT khai `(0,05 ; 0,95)` ap len do dai ay:
    _, dai_lan_hai = _ap_mot_lan(dai_goc)
    assert dai_lan_hai == pytest.approx(0.81 * THOI_LUONG_GOC, abs=1e-6)

    # ⭐ Ti so giua hai ket qua LA `(den - tu)`, ⛔ khong phai 1.
    assert dai_lan_hai / dai_goc == pytest.approx(CUA_SO[1] - CUA_SO[0])
    assert dai_lan_hai != pytest.approx(dai_goc, abs=1e-3)


# ══════════════════════════════════════════════════════════════════════════════
#  PHEP TIEM NGHICH — co y ap cua so HAI lan
# ══════════════════════════════════════════════════════════════════════════════

def test_tiem_nghich__ap_HAI_lan_lam_khach_mat_them_24_75_giay():
    """⛔ Ap hai lan ⇒ ban giao HEP hon dung cai khach keo, 24,751 s.

    Doi chieu tren TRUC GOC:

        khach yeu cau   13,750 .. 261,258   (247,507 s)
        ap hai lan      26,126 .. 248,882   (222,757 s)  <- mat 12,375 s moi dau

    ⭐ Va mat mat ay la mat mat NHIN THAY duoc: khach keo hai tay cam roi tu xem
       ket qua (`giai_doan_hinh_anh._cua_so_khach`). Nen bai nay la mot bai ve
       **san pham**, ⛔ khong chi ve so hoc.
    """
    khoang_goc, dai_goc = _ap_mot_lan(THOI_LUONG_GOC)
    goc_moi = khoang_goc[0][0]                     # goc truc sau lan cat thu nhat

    khoang_hai, dai_hai = _ap_mot_lan(dai_goc)
    # Doi khoang cua lan hai tro ve TRUC GOC de doi chieu duoc.
    tren_truc_goc = [(goc_moi + b, goc_moi + k) for b, k in khoang_hai]
    assert tren_truc_goc[0] == pytest.approx((26.1254, 248.8826), abs=1e-3)

    assert dai_goc - dai_hai == pytest.approx(24.7507, abs=1e-3)
    # ⛔ Va phan bi mat nam TRONG cai khach yeu cau giu — tuc mot yeu cau ro rang
    #    cua khach bi thi hanh SAI, ⛔ khong phai mot tranh chap tran nao.
    assert tren_truc_goc[0][0] > khoang_goc[0][0]
    assert tren_truc_goc[0][1] < khoang_goc[0][1]


def test_qc_dong_thuan_voi_ban_giao_SAI__nen_khong_do_nao_do():
    """🔴 **Phep tiem nghich DAT nhat**: ap hai lan thi QC van XANH.

    `giai_doan_qc._thoi_luong_mong_doi` dung LAI phep giao tu hai ban khai doc
    lap (`giai_doan_qc.py:203-209`) — mot thiet ke dung. Nhung ca hai ban khai
    ay noi ve do dai VAO cua `image_finish`, nen neu `media_prepare` da cat thi
    **ca phep do va cai bi do deu lech y het mot luong**, va T2 ⛔ khong do nao
    do duoc.

    ⇒ Day la ly do ket luan cua lan P0-c ⛔ KHONG the la "doi roi kiem bang QC".
    """
    dai_goc = 0.90 * THOI_LUONG_GOC

    # (1) The gioi hom nay: ke hoach khai do dai NGUON (GD1 ⛔ khong cat gi).
    mong_doi_hom_nay = _thoi_luong_mong_doi(
        {"tong_ms": round(THOI_LUONG_GOC * 1000)}, {}, None, cua_so_khach=CUA_SO)
    assert mong_doi_hom_nay == pytest.approx(dai_goc, abs=1e-3)

    # (2) The gioi neu `media_prepare` cat: `tong_ms` la do dai DA CAT, vi
    #     `giai_doan_thoi_gian.py:314-318` lay `tong_giay` tu ho so soi cua
    #     MEDIA_PREPARE.
    mong_doi_sau_khi_doi = _thoi_luong_mong_doi(
        {"tong_ms": round(dai_goc * 1000)}, {}, None, cua_so_khach=CUA_SO)
    assert mong_doi_sau_khi_doi == pytest.approx(0.81 * THOI_LUONG_GOC, abs=1e-3)

    # 🔴 Va con so ay la CHINH do dai cua tep bi cat hai lan ⇒ `lech = 0`.
    _, dai_hai_lan = _ap_mot_lan(dai_goc)
    assert mong_doi_sau_khi_doi == pytest.approx(dai_hai_lan, abs=1e-3)
    assert abs(mong_doi_sau_khi_doi - dai_hai_lan) < 0.5   # T2 dung sai 0,50 s


# ══════════════════════════════════════════════════════════════════════════════
#  BAI TRUC — cat dau DICH TRUC, va phep dich ay ⛔ chua ai lam
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("moc_goc", [0.11, 15.46, 100.0, 274.9])
def test_bai_truc__moc_thoai_T_phai_thanh_T_tru_dau_cat(moc_goc):
    """Cat dau ⇒ moc ASR nam tren truc DA CAT: `T - dau_cat`, ⛔ khong `T`.

    ⭐ Bai nay ⛔ khong kiem mot ham nao — no ghim **DAI LUONG** de bai
       `test_4975` do duoc rang ⛔ khong mot cho ha nguon nao dang tru di
       `dau_cat`.
    """
    dau_cat = CUA_SO[0] * THOI_LUONG_GOC
    assert dau_cat == pytest.approx(13.7504, abs=1e-3)

    tren_truc_cat = moc_goc - dau_cat
    if moc_goc < dau_cat:
        # ⛔ Moc truoc cua so KHONG duoc "troi ve 0" — no phai BIEN MAT, cung
        #    luat `giai_doan_hinh_anh.doi_moc_su_kien` da viet ra.
        assert tren_truc_cat < 0
    else:
        assert tren_truc_cat == pytest.approx(moc_goc - 13.7504, abs=1e-3)
        assert tren_truc_cat != pytest.approx(moc_goc, abs=1e-3)
