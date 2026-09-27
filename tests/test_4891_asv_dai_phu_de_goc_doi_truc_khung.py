"""ASV B8 — dai CHU GOC phai doi truc sang khung RA truoc khi dat phu de moi.

🔴 **Con bug do duoc 27/09, va chu du an chi ra cho de tim no.**

   Chu du an hoi: *"Tinh nang xoa/lam mo text trong video goc no van hanh nhu the
   nao? Ta dang lap no o buoc nao GD1 hay GD2? No phai xu ly TRUOC khi them text
   phu de moi, neu khong se xung dot vi lam sau thi se xoa phu de moi."*

   ⭐ Xung dot ay ⛔ KHONG the xay ra: lam mo o **GD1** (nung vao pixel, toa do
      NGUON, truoc `concat`), phu de dot o **GD2** (cuoi lop nhin). Thu tu do
      **chinh duong ong** bao dam, ⛔ khong nho mot quy uoc trong cung mot chuoi.

   ⛔ **Nhung ngay canh do co mot con bug THAT, cung ho voi `B6`.**
      `phu_de.dai_phu_de_goc` la phan so khung **NGUON** (khach ve tren nguon),
      con `vi_tri_tu_dong` tinh `margin_v` bang chieu cao khung **RA**. Khi hinh
      hoc GD2 cat theo chieu DOC thi hai phan so ⛔ khong bang nhau.

      Do 27/09 (nguon 1920x1080, dai chu goc 0,85-0,95, `da_che=True`):

        hinh hoc GD2                  margin_v CU   dung phai   lech
        ⛔ khong hinh hoc                     54          54        0
        khung 9:16 / 4:5 (cat BE RONG)        54          54        0
        cat_khung nua TREN                    27           0      +27 px
        cat_khung nua DUOI                    27          54      -27 px
        khung 1:1 nen_mo                      54         268     -214 px

      🔑 HAI cua so cat **nguoc nhau** cho CUNG mot `margin_v` (27) — bang chung
         rang phep tinh ⛔ khong he biet co cua so cat. Va `nen_mo` lech **214
         px**, ca nang nhat, vi no **them vien** chu ⛔ khong chi cat.

   ⚠️ Mat mat khach THAY: chu goc van bi lam mo (lam mo nung o GD1), nen ⛔ khong
      chu cu nao doc lai duoc. Cai sai la **vi tri phu de moi** — o ca "nua duoi"
      no dat DUOI vet mo thay vi phu len, nen khach thay mot vet mo lo lung.

⭐ Va day la dung loai bug ma *"mot job mot tinh nang"* ⛔ khong bao gio tim thay:
   no chi no khi CUNG LUC co `danh_dau_phu_de` + hinh hoc cat doc + `tu_dong`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import hinh_hoc as hh, phu_de  # noqa: E402

#: Dai chu goc khach danh dau: 85 %..95 % chieu cao NGUON.
DAI = {"y0": 0.85, "y1": 0.95, "da_che": True}
RONG_NGUON, CAO_NGUON = 1920, 1080


def _margin(bien_tap_gd2) -> int | None:
    """`margin_v` ma duong ong THAT se dung — di qua dung hai buoc cua no."""
    ho = {"che_do": phu_de.CHE_DO_TU_DONG, "kieu": "default",
          "dai_phu_de_goc": dict(DAI)}
    moi = phu_de.doi_truc_dai_phu_de(
        ho, bien_tap_gd2=bien_tap_gd2, rong_nguon=RONG_NGUON,
        cao_nguon=CAO_NGUON)
    ra_cao = (hh.khung_bien_tap(RONG_NGUON, CAO_NGUON, bien_tap_gd2)["ra"][1]
              if bien_tap_gd2 else CAO_NGUON)
    vt = phu_de.vi_tri_tu_dong(moi, cao=ra_cao)
    return vt.get("margin_v") if vt else None


# ══════════════════════════════════════════════════════════════════════════════
#  1. Phep doi truc — `hinh_hoc` la MOT nguon cho phep tinh
# ══════════════════════════════════════════════════════════════════════════════

def test_4891_doi_phan_so_doc_dung_tren_CA_BA_buoc_hinh_hoc():
    """⭐ Hinh hoc GD2 la mot chuoi BA buoc (`cat_khung` -> `zoom` -> `khung`
    cat/nen_mo), va `doi_phan_so_doc` phai di qua ca ba.

    ⚠️ `phong` la mot `scale` nen no GIU phan so; `nen_mo` thi **them vien** nen
       no DOI phan so — do la ve de quen nhat, va no lech nang nhat (214 px).
    """
    def doi(bt, y=0.95):
        buoc = (hh.khung_bien_tap(RONG_NGUON, CAO_NGUON, bt) if bt
                else {"cat": None, "phong": None, "khung": None,
                      "ra": (RONG_NGUON, CAO_NGUON)})
        return hh.doi_phan_so_doc(buoc, CAO_NGUON, y)

    # ⛔ Khong hinh hoc, va cat BE RONG: phan so doc GIU NGUYEN.
    assert doi(None) == pytest.approx(0.95)
    assert doi({"khung": {"ti_le": "9:16", "cach": "cat"}}) == pytest.approx(0.95)
    assert doi({"khung": {"ti_le": "4:5", "cach": "cat"}}) == pytest.approx(0.95)

    # Cat CHIEU CAO: phan so DOI, va mot diem ngoai cua so thi MAT.
    assert doi({"cat_khung": {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 0.5}}) is None
    assert doi({"cat_khung": {"x0": 0.0, "y0": 0.5, "x1": 1.0, "y1": 1.0}}) == (
        pytest.approx(0.90))

    # `nen_mo` THEM VIEN ⇒ noi dung bi day vao giua: 0,95 -> ~0,75.
    n = doi({"khung": {"ti_le": "1:1", "cach": "nen_mo"}})
    assert n is not None and n == pytest.approx(0.7516, abs=0.002), n
    # ⛔ Ve DOI CHUNG: neu `nen_mo` bi doc nhu mot phep cat thi so nay se la 0,95.
    assert n < 0.9, ("`nen_mo` them vien ma phan so ⛔ khong doi ⇒ phep doi truc "
                     "dang bo qua vien")


# ══════════════════════════════════════════════════════════════════════════════
#  2. `margin_v` cua duong ong — con so khach thuc su nhan
# ══════════════════════════════════════════════════════════════════════════════

def test_4891_margin_v_HAI_cua_so_cat_NGUOC_NHAU_phai_cho_HAI_so():
    """🔴 **Bat bien that su dang chot.**

    Ban cu cho CUNG `margin_v = 27` cho `cat_khung` nua TREN va nua DUOI — hai
    cua so **loai tru nhau**. Mot phep tinh cho cung mot dap an tren hai dau vao
    nguoc nhau la mot phep tinh ⛔ khong doc dau vao ay.

    ⭐ Chot bang TINH CHAT (*hai ca phai KHAC nhau*) chu ⛔ khong chi bang hai
       hang so: mot bai chot `0` va `54` se xanh ca khi ai do doi ca hai theo
       cung mot huong sai.
    """
    tren = _margin({"cat_khung": {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 0.5}})
    duoi = _margin({"cat_khung": {"x0": 0.0, "y0": 0.5, "x1": 1.0, "y1": 1.0}})
    assert tren != duoi, (
        "hai cua so cat NGUOC NHAU cho cung mot margin_v (%r) ⇒ phep tinh ⛔ "
        "khong doc cua so cat" % (tren,))

    # Nua TREN: dai chu goc (85-95 % nguon) bi cat MAT HAN ⇒ ⛔ khong con gi de
    # tranh ⇒ GIU vi tri cua preset (⛔ khong dat `margin_v`).
    assert tren is None, tren
    # Nua DUOI: dai o 70-90 % khung ra (cao 540) ⇒ margin_v = (1-0,9)*540 = 54.
    assert duoi == 54, duoi


def test_4891_margin_v_dung_tren_moi_hinh_hoc():
    """So do 27/09, tung ca mot. Cot "CU" la gia tri ban truoc B8 sinh ra."""
    assert _margin(None) == 54                                   # CU: 54 ✓
    assert _margin({"khung": {"ti_le": "9:16", "cach": "cat"}}) == 54   # CU: 54 ✓
    assert _margin({"khung": {"ti_le": "4:5", "cach": "cat"}}) == 54    # CU: 54 ✓
    # `nen_mo`: dai bi day vao giua ⇒ margin_v phai LON hon han. CU: 54 (lech 214).
    nm = _margin({"khung": {"ti_le": "1:1", "cach": "nen_mo"}})
    assert nm is not None and nm == 268, nm


def test_4891_KHONG_hinh_hoc_thi_tra_CHINH_doi_tuong_cu():
    """⭐ Duong ma phan lon lan chay di qua ⛔ khong duoc doi mot byte.

    Mot phep bien doi vo dieu kien la mot cho de lam tron va de sai them. Chot
    bang `is` — no phan biet "⛔ khong doi" voi "doi ra mot ban giong het".
    """
    ho = {"che_do": phu_de.CHE_DO_TU_DONG, "dai_phu_de_goc": dict(DAI)}
    assert phu_de.doi_truc_dai_phu_de(
        ho, bien_tap_gd2=None, rong_nguon=RONG_NGUON, cao_nguon=CAO_NGUON) is ho
    # ⛔ Bien tap CO nhung ⛔ khong truong hinh hoc nao (vd chi `toc_do`): cung
    #    ⛔ khong doi khung, nen cung phai tra chinh no.
    assert phu_de.doi_truc_dai_phu_de(
        ho, bien_tap_gd2={"toc_do": 1.25}, rong_nguon=RONG_NGUON,
        cao_nguon=CAO_NGUON) is ho
    # ⛔ Va ⛔ khong co dai thi cung tra chinh no.
    ho2 = {"che_do": phu_de.CHE_DO_TU_DONG}
    assert phu_de.doi_truc_dai_phu_de(
        ho2, bien_tap_gd2={"cat_khung": {"x0": 0.0, "y0": 0.5, "x1": 1.0,
                                         "y1": 1.0}},
        rong_nguon=RONG_NGUON, cao_nguon=CAO_NGUON) is ho2


def test_4891_KHONG_sua_TAI_CHO_ho_so_phu_de():
    """⛔ Cung mot `ho_so_pd` con di vao `van_tay` va vao bao cao. Mot dai da doi
    truc lot vao do se lam hai lan chay giong nhau co HAI van tay — hay te hon:
    mot bao cao noi mot con so ma ⛔ khong ai biet no o truc nao."""
    ho = {"che_do": phu_de.CHE_DO_TU_DONG, "kieu": "default",
          "dai_phu_de_goc": dict(DAI)}
    phu_de.doi_truc_dai_phu_de(
        ho, bien_tap_gd2={"cat_khung": {"x0": 0.0, "y0": 0.5, "x1": 1.0,
                                        "y1": 1.0}},
        rong_nguon=RONG_NGUON, cao_nguon=CAO_NGUON)
    assert ho["dai_phu_de_goc"] == DAI, "da sua ho so TAI CHO"


# ══════════════════════════════════════════════════════════════════════════════
#  3. Thu tu hai giai doan — xung dot chu du an lo la KHONG THE
# ══════════════════════════════════════════════════════════════════════════════

def test_4891_lam_mo_o_GD1_va_phu_de_o_GD2__moi_vung_deu_bi_lam_mo():
    """⭐ Hai khang dinh, va chung tra loi dung cau hoi cua chu du an.

    1. **`danh_dau_phu_de` CUNG bi lam mo.** `che_do_render._loc_vung` lap MOI
       vung va chi re nhanh theo `dien_nen` vs con-lai; no ⛔ khong loc theo
       `loai`. Nen `dai_phu_de_goc(...)["da_che"]` = `True` la mot loi khai DUNG,
       va phu de moi dat DE LEN vet mo.

       ⛔ Neu ai do lam `_loc_vung` bo qua vung danh dau, `da_che=True` thanh mot
          loi noi doi va phu de moi se dat len chu cu CHUA mo — bai nay do.

    2. **Lam mo thuoc GD1, phu de dot thuoc GD2**, nen thu tu do CHINH duong ong
       bao dam. `loc_cat_noi` (GD1) nhan `vung`; `loc_cat_hai_dong` (GD2) ⛔ khong.
    """
    import inspect

    from apps.auto_scan_video import che_do_render as cdr, vung_che

    # (1) MOI vung deu sinh ve loc — ke ca vung danh dau.
    vung = vung_che.chuan_hoa([
        {"x0": 0.1, "y0": 0.85, "x1": 0.9, "y1": 0.95,
         "loai": vung_che.LOAI_DANH_DAU_PHU_DE},
    ])
    ve = cdr._loc_vung(vung, "vao", "ra", None)
    assert ve, "vung `danh_dau_phu_de` ⛔ khong sinh ve loc nao ⇒ no ⛔ KHONG bi "
    assert any("boxblur" in d for d in ve), (
        "vung `danh_dau_phu_de` ⛔ khong duoc lam mo ⇒ `da_che=True` la loi noi "
        "doi, va phu de moi se dat len chu cu CHUA mo: %r" % (ve,))

    # (2) `vung` thuoc GD1; GD2 ⛔ khong nhan no.
    assert "vung" in inspect.signature(cdr.loc_cat_noi).parameters
    assert "vung" not in inspect.signature(cdr.loc_cat_hai_dong).parameters, (
        "GD2 nhan `vung` ⇒ lam mo co the chay SAU khi dot phu de, va luc do no "
        "se lam mo CHINH phu de moi — dung xung dot ma chu du an lo")
