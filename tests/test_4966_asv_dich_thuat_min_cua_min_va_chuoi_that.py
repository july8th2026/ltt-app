"""B17 §4.1, lan P0-a3 — bai cuoi cua dai (4963-4966): `min` CUA `min` khong
bao gio NOI, va CA CHUOI qua kenh san xuat that (`cai_dat.voi_toc_doc_giong`
-> `vuot_tran_theo_nguon`).

⚠️ **Diem soat #2 trong brief**: `tran_do_dai_theo_nguon` da la
`min(tran_vat_ly, tran_theo_nguon)`; noi them `toc_doc_giong` vao ben trong
`tran_vat_ly` phai CHI SIET tran CUOI CUNG, ⛔ khong bao gio NOI no — bat ke
`tran_theo_nguon` co dang CHE (nho hon `tran_vat_ly`) hay khong (khi do doi
`toc_doc_giong` khong duoc lam gi ca, vi `min` da chon nhanh kia).
"""
from __future__ import annotations

import itertools

from apps.auto_scan_video import cai_dat, dich_thuat, ngon_ngu

#: Nguon THUA (n_nguon nho) -> tran_theo_nguon THAP, che tran_vat_ly. Dung de
#: chung minh toc_doc_giong ⛔ khong noi tran ngay ca khi bi nguon "khoa".
_NGUON_THUA = "这" * 5
#: Nguon DAY (n_nguon lon) -> tran_theo_nguon cao, tran_vat_ly la canh SIET
#: THAT — nhanh de thay hieu ung cua toc_doc_giong nhat.
_NGUON_DAY = "这" * 500


# ══════════════════════════════════════════════════════════════════════════
#  1) min-cua-min: MOI to hop (giay, dich, mat do nguon) deu KHONG NOI
# ══════════════════════════════════════════════════════════════════════════

def test_MIN_CUA_MIN_toc_doc_giong_khong_bao_gio_lam_tran_CUOI_CUNG_lon_hon():
    to_hop = itertools.product(
        (3.0, 8.0, 15.0, 40.0),                    # giay
        (ngon_ngu.VI, ngon_ngu.EN),                 # dich
        (_NGUON_THUA, _NGUON_DAY),                   # mat do nguon
        (0.3, 0.7, 1.0, 1.5, 3.0),                   # he so nhan NHIP[dich]
    )
    vi_pham = []
    for giay, dich, nguon, he_so in to_hop:
        nhip = ngon_ngu.NHIP[dich]
        nen = dich_thuat.tran_do_dai_theo_nguon(giay, nguon, dich=dich)
        co_giong = dich_thuat.tran_do_dai_theo_nguon(
            giay, nguon, dich=dich, toc_doc_giong=nhip * he_so)
        if co_giong > nen:
            vi_pham.append((giay, dich, len(nguon), he_so, nen, co_giong))
    assert not vi_pham, (
        f"{len(vi_pham)} to hop lam tran NOI ra khi them toc_doc_giong (giay, "
        f"dich, do_dai_nguon, he_so, tran_nen, tran_co_giong): {vi_pham[:5]}")


def test_khi_TRAN_THEO_NGUON_da_CHE__doi_toc_doc_giong_khong_lam_gi():
    """Nguon thua -> `tran_theo_nguon` << `tran_vat_ly` du toc_doc_giong the
    nao. `min` phai luon chon nhanh nguon, tran CUOI CUNG dung yen."""
    giay = 40.0  # khe rat rong -> tran_vat_ly rat cao
    nhip = ngon_ngu.NHIP[ngon_ngu.VI]
    tran_theo_nguon_ky_vong = max(1, int(len(_NGUON_THUA) * 0.75))  # 5*0.75->3

    cho_moi_he_so = {
        he_so: dich_thuat.tran_do_dai_theo_nguon(
            giay, _NGUON_THUA, dich=ngon_ngu.VI, toc_doc_giong=nhip * he_so)
        for he_so in (0.2, 1.0, 5.0)
    }
    assert len(set(cho_moi_he_so.values())) == 1, (
        f"tran doi theo toc_doc_giong du dang bi tran-theo-nguon khoa: "
        f"{cho_moi_he_so!r}")
    assert list(cho_moi_he_so.values())[0] == tran_theo_nguon_ky_vong


# ══════════════════════════════════════════════════════════════════════════
#  2) CA CHUOI qua kenh SAN XUAT that: cai_dat.voi_toc_doc_giong -> ham nay
# ══════════════════════════════════════════════════════════════════════════

def test_CHUOI_THAT_cai_dat_voi_toc_doc_giong_qua_vuot_tran_theo_nguon(monkeypatch):
    """⛔ Khong tu go `{"toc_doc_giong": ...}`: dung THANG ham san xuat
    `cai_dat.voi_toc_doc_giong` (ben GHI that cua P0-a) de dung ten khoa VA
    dang gia tri that no tra ve — cung hinh dang bai chuoi cua `test_4962`
    nhung dung cho cua PHAT HIEN N5 cua lan nay.
    """
    cham = ngon_ngu.NHIP["vi"] * 0.4
    monkeypatch.setitem(cai_dat.TOC_DOC_GIONG_DA_DO, "giong_cham_p0a3", cham)

    ho_so = cai_dat.voi_toc_doc_giong(
        {"giong_id": "giong_cham_p0a3", "ngon_ngu_dich": "vi"})
    assert ho_so["toc_doc_giong"] == cham

    giay, nguon = 20.0, _NGUON_DAY
    dich_dai = " ".join(["tu"] * 200)  # co y dai, de thay ro hieu ung siet

    vuot_nen, do_dai_nen, tran_nen = dich_thuat.vuot_tran_theo_nguon(
        giay=giay, nguon=nguon, dich_ra=dich_dai, dich="vi")
    vuot_cham, do_dai_cham, tran_cham = dich_thuat.vuot_tran_theo_nguon(
        giay=giay, nguon=nguon, dich_ra=dich_dai, dich="vi",
        toc_doc_giong=ho_so["toc_doc_giong"])

    assert tran_cham < tran_nen, (
        f"ca chuoi (cai_dat -> vuot_tran_theo_nguon) khong siet tran "
        f"({tran_cham} vs {tran_nen})")
    assert do_dai_cham == do_dai_nen == 200
    # Cung mot ban dich, tran SIET hon -> de "vuot" hon (hoac giu nguyen).
    assert vuot_cham or not vuot_nen or tran_cham <= tran_nen
