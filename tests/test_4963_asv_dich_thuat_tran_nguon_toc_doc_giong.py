"""B17 §4.1, lan P0-a3 — TRA NO cuoi cua chuoi `toc_doc_giong` (tiep P0-a2).

`ngon_ngu.ngan_sach_do_dai` nhan `toc_doc_giong` tu P0-a2. P0-a2 da noi CHO GOI
THU NHAT (`long_tieng.loi_nhac`, tran ghi vao loi nhac gui model). Lan nay
(P0-a3) noi CHO GOI THU HAI: `dich_thuat.tran_do_dai_theo_nguon` — tran cua cua
PHAT HIEN N5 (`vuot_tran_theo_nguon`) — truoc lan nay LUON dung hang so
ca-ngon-ngu `ngon_ngu.NHIP[dich]`, bat ke giong nao dang doc.

Dai so 4963-4966 (P0-a2 da dem rong den 4966 o `test_4962`).

## Pham vi so huu — CHI `dich_thuat.py`

⛔ Khong sua `ngon_ngu.py`/`long_tieng.py`/`cai_dat.py`/`ho_so_dich.py`. Cac bai
o day GOI THANG `dich_thuat.tran_do_dai_theo_nguon`/`vuot_tran_theo_nguon` —
ham THAT tren duong chay san xuat (`giai_doan_noi_dung.chay:435` goi
`vuot_tran_theo_nguon`) — ⛔ khong tu tinh lai cong thuc trong test (bay
[[phep-kiem-xanh-da-tai-hien-san-loi]] / test_2018: bai do ham CU thi xanh vo
nghia).

## Hai phep tiem nghich (xac minh thu cong, ghi lai bang chung o day)

1. Bo `toc_doc_giong=toc_doc_giong` o `dich_thuat.tran_do_dai_theo_nguon` (khi
   goi `ngon_ngu.ngan_sach_do_dai`) ⇒ `test_giong_CHAM_lam_tran_NHO_hon` DO
   (tran khong con siet theo giong cham).
2. Doi `nhip = min(nhip, do)` trong `ngon_ngu.ngan_sach_do_dai` thanh gan hai
   chieu (`nhip = do`) ⇒ `test_TIEM_NGHICH_giong_NHANH_KHONG_lam_tran_LON_hon`
   DO (tran noi ra khi giong nhanh).

Ca hai da chay thu cong (sua tam thoi + `pytest` + doi lai nguyen ban) trong
phien P0-a3 — xem bao cao lan.
"""
from __future__ import annotations

from apps.auto_scan_video import dich_thuat, ngon_ngu

#: Nguon dai, khe rong — de tran VAT LY (theo NHIP) la canh SIET THAT (thap
#: hon tran-theo-nguon), tranh lo min(tran_vat_ly, tran_theo_nguon) bi tran
#: theo nguon che mat hieu ung cua toc_doc_giong.
_NGUON_DAI = "这" * 400
_GIAY = 20.0


def _tran(dich: str = "vi", toc_doc_giong=None) -> int:
    return dich_thuat.tran_do_dai_theo_nguon(
        _GIAY, _NGUON_DAI, dich=dich, toc_doc_giong=toc_doc_giong)


# ══════════════════════════════════════════════════════════════════════════
#  1) Chieu SIET — giong CHAM lam tran NHO hon
# ══════════════════════════════════════════════════════════════════════════

def test_giong_CHAM_lam_tran_NHO_hon():
    nen = _tran()
    cham = _tran(toc_doc_giong=ngon_ngu.NHIP["vi"] * 0.5)
    assert cham < nen, (
        f"giong CHAM ma tran KHONG siet ({cham} vs {nen}) — toc_doc_giong "
        "khong toi phep tinh cua tran_do_dai_theo_nguon")


def test_giong_cang_CHAM_tran_cang_NHO__don_dieu():
    truoc = None
    for he_so in (1.0, 0.8, 0.6, 0.4):
        n = _tran(toc_doc_giong=ngon_ngu.NHIP["vi"] * he_so)
        if truoc is not None:
            assert n <= truoc, f"he so {he_so}: tran TANG khi giong cham di"
        truoc = n


# ══════════════════════════════════════════════════════════════════════════
#  2) ⭐ TIEM NGHICH — giong NHANH ⛔ KHONG duoc lam tran LON hon
# ══════════════════════════════════════════════════════════════════════════

def test_TIEM_NGHICH_giong_NHANH_KHONG_lam_tran_LON_hon():
    """🔴 Phep tiem nghich chinh cua lan nay, o TANG `dich_thuat` (khac tang
    `ngon_ngu` ma `test_4962`/`test_4951` da giu). Bai nay DO neu wiring moi
    (P0-a3) vo tinh cong them mot nhanh NOI o day, hoac neu ham `ngan_sach_
    do_dai` phia duoi mat tinh mot chieu.
    """
    nen = _tran()
    nhanh = _tran(toc_doc_giong=ngon_ngu.NHIP["vi"] * 2)
    assert nhanh == nen, (
        f"giong NHANH da NOI tran ({nhanh} > {nen}) — phep siet mot chieu bi vo")


# ══════════════════════════════════════════════════════════════════════════
#  3) Bang do RONG hom nay ⇒ hanh vi ⛔ KHONG doi mot don vi (so tuyet doi)
# ══════════════════════════════════════════════════════════════════════════

def test_HANH_VI_HOM_NAY_khong_doi__so_tuyet_doi():
    """`cai_dat.TOC_DOC_GIONG_DA_DO` rong ⇒ moi giong roi ve `ngon_ngu.NHIP` ⇒
    `toc_doc_giong=None` (mac dinh) phai ra CHINH XAC con so truoc lan nay.

    So tuyet doi, ⛔ khong so ham voi chinh no: `tran_vat_ly` mong doi la
    `int(round(20.0 * 3.35 * 0.92)) = 62`; `n_nguon` = 400 ky tu CJK;
    `tran_theo_nguon` = `int(400 * 0.75)` = 300; `min(62, 300) = 62`.
    """
    assert ngon_ngu.NHIP["vi"] == 3.35
    assert ngon_ngu.HE_SO_MUC_TIEU == 0.92
    tran_vat_ly_ky_vong = int(round(_GIAY * 3.35 * 0.92))
    assert tran_vat_ly_ky_vong == 62
    assert _tran() == 62
    assert _tran(toc_doc_giong=None) == 62


def test_vuot_tran_theo_nguon_HANH_VI_HOM_NAY_khong_doi():
    """Cung phep do nhung qua ham PHAT HIEN N5 — ham that giai_doan_noi_dung
    dung (xem `test_4965`)."""
    dich_vua = " ".join(["tu"] * 62)
    vuot, do_dai, tran = dich_thuat.vuot_tran_theo_nguon(
        giay=_GIAY, nguon=_NGUON_DAI, dich_ra=dich_vua, dich="vi")
    assert tran == 62
    assert do_dai == 62
    assert vuot is False
