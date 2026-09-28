"""B17 §4.1, lan P0-a2 — `toc_doc_giong` NEO `do_dai_toi_da` cua TUNG cau.

Lan P0-a tinh gia tri (`cai_dat.toc_doc_giong`, xem `test_4960`) va ghi no vao
`run.settings` + dict tra ve cua `ho_so_dich.dung()` (xem `test_4961`), nhung
⛔ **khong ai doc no**: `long_tieng.loi_nhac` van tinh tran do dai bang mot hang
so CA-NGON-NGU (`ngon_ngu.NHIP[dich]`) cho MOI giong. Lan P0-a2 noi day.

Tep nay do **hanh vi** (con so ra khac di theo dung mot chieu). Neo CHO DOC
(AST: doc o dau, dung mot lan moi cau) o `test_4961` muc 3.

Dai 4960-4966 (da dem, dai trong).

## ⭐ Phep TIEM NGHICH, va vi sao no la bai quan trong nhat o day

Mot bai *"da noi day"* de xanh mot cach vo nghia: neu nhanh `min()` trong
`ngan_sach_do_dai` bi bo, con so **van dung** cho moi giong da do hom nay (bang
`TOC_DOC_GIONG_DA_DO` dang RONG, moi giong roi ve dung hang so). Nen tep nay
tiem **hai** gia tri co y:

    0,5 x NHIP  (giong CHAM gia)  ⇒ ngan sach PHAI nho di  — chung minh nhanh
                                    ay CO CHAY, ⛔ khong phai ma chet
    2   x NHIP  (giong NHANH gia) ⇒ ngan sach PHAI GIU NGUYEN — chung minh phep
                                    siet la MOT CHIEU (Viral `localize.py:
                                    15112-15117`, *"CHI SIET, KHONG NOI"*)

⛔ Thieu ve thu nhat: bo ca tham so di bai van xanh. Thieu ve thu hai: doi
`min()` thanh phep gan hai chieu bai van xanh. Hai ve phai di cung nhau — cung
bai hoc [[banh-coc-do-cach-go-thay-vi-do-tinh-chat]].
"""
from __future__ import annotations

import json

import pytest

from apps.auto_scan_video import cai_dat, long_tieng, ngon_ngu

#: Mot lo hai doan co thoi luong KHAC nhau — de bat ca "tinh mot lan roi dung
#: lai cho ca lo" (mot tran dung chung thi hai doan se ra cung mot so).
LO = [{"ma": "a", "chu": "x", "bat": 0.0, "ket": 19.879},
      {"ma": "b", "chu": "y", "bat": 19.879, "ket": 24.432}]


def _tran_moi_cau(ho_so: dict | None = None, *, dich: str = "vi") -> dict:
    """`{ma: do_dai_toi_da}` doc tu chinh loi nhac gui model."""
    msg = long_tieng.loi_nhac(LO, tat_ca=LO, ngon_ngu_goc="zh",
                              dac_diem_giong={}, ngon_ngu_dich=dich,
                              ho_so=ho_so)
    goi = json.loads(msg[1]["content"])
    return {m["ma"]: m["do_dai_toi_da"] for m in goi["doan"]}


# ══════════════════════════════════════════════════════════════════════════════
#  1) Chieu SIET — giong cham lam MOI cau ngan hon
# ══════════════════════════════════════════════════════════════════════════════

def test_giong_CHAM_lam_do_dai_toi_da_MOI_CAU_nho_hon():
    """⭐ *"MOI cau"*, ⛔ khong phai *"lo"*: mot tran tinh mot lan cho ca lo van
    nho hon ban nen nhung **sai dai luong** — hai doan cua `LO` dai khac nhau."""
    nen = _tran_moi_cau()
    cham = _tran_moi_cau({"toc_doc_giong": ngon_ngu.NHIP["vi"] * 0.5})

    assert set(cham) == set(nen) == {"a", "b"}
    for ma in ("a", "b"):
        assert cham[ma] < nen[ma], (
            f"doan {ma}: giong CHAM ma tran do dai KHONG siet "
            f"({cham[ma]} vs {nen[ma]}) — toc_doc_giong khong vao phep tinh")
    # ⛔ Va tran VAN phai khac nhau giua hai doan: mot con so dung cho ca lo la
    #    dau hieu loi goi bi keo ra ngoai vong `for`.
    assert cham["a"] != cham["b"]


def test_giong_cang_CHAM_tran_cang_NHO__don_dieu():
    """Mot chieu don dieu, ⛔ khong chi mot diem. Hai diem roi co the khop tinh co."""
    truoc = None
    for he_so in (1.0, 0.8, 0.6, 0.4):
        n = _tran_moi_cau({"toc_doc_giong": ngon_ngu.NHIP["vi"] * he_so})["a"]
        if truoc is not None:
            assert n <= truoc, f"he so {he_so}: tran TANG khi giong cham di"
        truoc = n


# ══════════════════════════════════════════════════════════════════════════════
#  2) ⭐ TIEM NGHICH — giong NHANH ⛔ KHONG duoc NOI tran
# ══════════════════════════════════════════════════════════════════════════════

def test_TIEM_NGHICH_giong_NHANH_gap_doi_KHONG_lam_tran_lon_hon():
    """🔴 **Phep tiem nghich cua lan nay.**

    Tiem `2 x NHIP` — mot *"giong doc nhanh gap doi"* — vao dung kenh san pham
    (`ho_so["toc_doc_giong"]`). Ban dich ⛔ **khong duoc** dai ra.

    Ly do nguyen van cua Viral (`localize.py:15112-15117`, *"CHI SIET, KHONG
    NOI"*): noi neo cho giong nhanh cho mot ban dich DAI hon, roi TTS phai nen
    (atempo) NANG hon de doc kip khe cu — dung NGUOC muc dich cua viec neo.

    ⇒ Bai nay DO ngay khi ai do doi `min(nhip, do)` thanh mot phep gan hai
    chieu, va do la hong duy nhat ma bai *"giong cham thi ngan hon"* o tren
    ⛔ khong bat duoc.
    """
    nen = _tran_moi_cau()
    nhanh = _tran_moi_cau({"toc_doc_giong": ngon_ngu.NHIP["vi"] * 2})

    for ma in ("a", "b"):
        assert nhanh[ma] == nen[ma], (
            f"doan {ma}: giong NHANH da NOI tran ({nhanh[ma]} > {nen[ma]}) — "
            "phep siet KHONG con mot chieu")


def test_TIEM_NGHICH_o_tang_HAM__ca_hai_chieu_tren_mot_phep_do():
    """Cung phep tiem, do thang o `ngan_sach_do_dai` — de khi bai tren do ta
    biet ngay tang nao vo: tang NOI DAY (`long_tieng`) hay tang TINH."""
    nhip = ngon_ngu.NHIP["vi"]
    nen = ngon_ngu.ngan_sach_do_dai(20.0, "vi")

    assert ngon_ngu.ngan_sach_do_dai(20.0, "vi", toc_doc_giong=nhip * 2) == nen
    assert ngon_ngu.ngan_sach_do_dai(20.0, "vi", toc_doc_giong=nhip * 0.5) < nen
    # `None` = ben goi khong biet giong ⇒ y nguyen hanh vi truoc P0-a2.
    assert ngon_ngu.ngan_sach_do_dai(20.0, "vi", toc_doc_giong=None) == nen


@pytest.mark.parametrize("hong", [0, 0.0, -1.0, "", None])
def test_so_do_HONG_roi_ve_hang_so_KHONG_ra_mot_am_tiet(hong):
    """⛔ Mot so do hong ⛔ khong duoc keo tran ve `max(1, ...)`: mot cau MOT am
    tiet la mot ban dich bi cat, ⛔ khong phai mot ngan sach.

    ⚠️ Day la ve thu hai cua [[hai-trang-thai-gop-thanh-mot-gia-tri]]: `0` va
    `None` roi ve CUNG mot con so nhung vi hai ly do khac nhau, va ca hai deu
    phai ra hang so ca-ngon-ngu.
    """
    nen = ngon_ngu.ngan_sach_do_dai(20.0, "vi")
    assert ngon_ngu.ngan_sach_do_dai(20.0, "vi", toc_doc_giong=hong) == nen
    assert _tran_moi_cau({"toc_doc_giong": hong}) == _tran_moi_cau()


# ══════════════════════════════════════════════════════════════════════════════
#  3) Ngon ngu ⛔ KHONG co so do rieng — van ra mot ngan sach HOP LE
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("dich", ["vi", "en"])
def test_dich_khong_co_so_do_RIENG_van_ra_ngan_sach_hop_le(dich):
    """`TOC_DOC_GIONG_DA_DO` RONG hom nay ⇒ moi giong roi ve `ngon_ngu.NHIP`.

    ⛔ Khong ra `0`, ⛔ khong nem — va tran phai TRUNG dung ban khong-biet-giong,
    tuc noi day ⛔ khong lam **doi hanh vi hom nay** mot don vi nao.
    """
    assert cai_dat.TOC_DOC_GIONG_DA_DO == {}, (
        "bang da co dong moi — them dong thi phai tang long_tieng."
        "PHIEN_BAN_LONG_TIENG (xem chu thich tai hang do)")

    ho_so = cai_dat.voi_toc_doc_giong(
        {"giong_id": "mot_giong_chua_ai_do", "ngon_ngu_dich": dich})
    assert ho_so["toc_doc_giong"] == ngon_ngu.NHIP[dich] > 0

    tran = _tran_moi_cau({"toc_doc_giong": ho_so["toc_doc_giong"]}, dich=dich)
    assert tran == _tran_moi_cau(dich=dich)
    assert all(v >= 1 for v in tran.values())


def test_dich_NGOAI_hop_dong_nem_NgonNguError_khong_ra_mot_con_so():
    """Mot cua loi, ⛔ khong mot con so im lang. Cung cua voi ban khong co giong."""
    with pytest.raises(ngon_ngu.NgonNguError):
        ngon_ngu.ngan_sach_do_dai(10.0, "ja", toc_doc_giong=3.0)


# ══════════════════════════════════════════════════════════════════════════════
#  4) CA CHUOI — nguoi GHI va nguoi DOC gap nhau tren mot kenh that
# ══════════════════════════════════════════════════════════════════════════════

def test_CHUOI_THAT_ho_so_dich_dung_roi_loi_nhac_doc__giong_cham_siet_tran(monkeypatch):
    """🔑 **Bai chung minh day da NOI, ⛔ khong chi hai dau day cung ton tai.**

    Di dung duong san pham: `TOC_DOC_GIONG_DA_DO` co mot giong CHAM do that ->
    `ho_so_dich.dung()` ghi + tra `toc_doc_giong` -> chinh dict do di vao
    `long_tieng.loi_nhac(ho_so=...)` (dung cach `giai_doan_noi_dung:357`/`:514`
    truyen) -> tran do dai moi cau SIET lai.

    ⚠️ ⛔ Khong tu dung mot dict `{"toc_doc_giong": ...}` o bai nay: mot dict tu
    go chi chung minh ben DOC hoat dong. Cai can chung minh la ben GHI va ben
    DOC dung **cung mot ten khoa** — dung hinh dang
    [[cho-noi-hai-module-vut-truong-im-lang]].
    """
    from apps.auto_scan_video import ai, ho_so_dich

    cham = ngon_ngu.NHIP["vi"] * 0.5
    monkeypatch.setitem(cai_dat.TOC_DOC_GIONG_DA_DO, "giong_cham_do_that", cham)

    def _ban_gia(db, run, thao_tac, tin, **kw):
        return {"noi_dung": json.dumps({
            "the_loai": "x", "so_nguoi_noi": 1, "bang_dai_tu": {},
            "bang_ten_rieng": {}, "giong_van": "", "bang_sua_dong_am": {},
        }, ensure_ascii=False), "su_dung": None}

    monkeypatch.setattr(ai, "goi_tinh_tien", _ban_gia)

    class _Run:
        def __init__(self):
            self.id = 1
            self.owner_id = 1
            self.credit_held = 0
            self.settings = {"giong_id": "giong_cham_do_that",
                             "ngon_ngu_dich": "vi"}

    run = _Run()
    ho_so = ho_so_dich.dung(None, run, {"doan": [{"ma": "a", "chu": "x"}]})
    assert ho_so["toc_doc_giong"] == cham

    nen = _tran_moi_cau()
    tran = _tran_moi_cau(ho_so)
    for ma in ("a", "b"):
        assert tran[ma] < nen[ma], (
            f"doan {ma}: ca chuoi da chay ma tran KHONG siet — ben GHI va ben "
            f"DOC dang khong gap nhau ({tran[ma]} vs {nen[ma]})")


def test_HO_SO_RONG_nhanh_model_tra_RAC_KHONG_lam_tran_hong():
    """Nhanh *"model tra rac"* tra ho so RONG ⛔ khong mang khoa nay (hop dong
    `ho_so_dich.KHOA`, chot boi `test_408`) ⇒ tran roi ve hang so, y nhu truoc
    P0-a2. ⛔ Mot ho so rong lam ban dich NGHEO hon, no ⛔ khong duoc lam ban
    dich HONG."""
    from apps.auto_scan_video import ho_so_dich

    rong = {k: ({} if k.startswith("bang_") else "") for k in ho_so_dich.KHOA}
    assert "toc_doc_giong" not in rong
    assert _tran_moi_cau(rong) == _tran_moi_cau()
