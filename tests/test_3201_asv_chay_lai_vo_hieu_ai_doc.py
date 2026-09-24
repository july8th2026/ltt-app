"""I1 tren duong CHAY LAI: ai DOC mot buoc thi phai bi VO HIEU khi buoc do chay lai.

`test_3004` chot chieu XUOI: `doc thuong nguon cua S` ⊆ `bao_dong(S.sau)`.
Tep nay chot chieu NGUOC — chieu ma `ha_nguon_cua` chiu luc:

    moi buoc DOC `g` (va dung SAU `g` trong `CHUOI`) phai nam trong `ha_nguon_cua(g)`

⛔ Va no **khong go lai** `MODULE` / `_doc_cua` / `bao_dong` / `vi_pham`: chung
   duoc nhap tu `test_3004`. Hai ban cua cung mot phep quet AST se lech, va kho
   nay dinh dung bay do ba lan trong hai ngay.

## 🔴 N-08 tren duong chay lai DA CAN mot lan

`features.py:263` ghi mot su co THAT: chay lai `media_prepare` → job
`audio_prepare` CU cua luot truoc van chay → `transcribe` doc ban tieng thuoc
luot chay TRUOC. Va no ghi them: *"mot loi chi hong doi khi thi truoc do no van
hong, chi la chua ai thay"*.

⇒ Chieu nguoc con dat hon chieu xuoi: vo hieu **thieu** mot buoc ha nguon nghia
  la giao mot ban long tieng tron lan ket qua cua hai lan chay khac nhau — hong
  theo kieu khong loi nao bao.

## ⚠️ GIOI HAN CUA BAI NAY — noi ra thay vi de nguoi doc tu suy

Tren CUNG mot do thi, bat bien chieu nguoc la **phan dao** cua bat bien chieu xuoi:

    S doc g, g truoc S   ⟹  g ∈ bao_dong(S.sau)     (I1 xuoi — `test_3004`)
    S ∈ ha_nguon_cua(g)  ⟺  g ∈ bao_dong(S.sau)     (dinh nghia ha nguon)

⇒ Nen `test_3004` xanh thi bai nay **xanh theo**, va no **khong the do doc lap**
  tren `CHUOI` hom nay. Noi *"toi da do duong chay lai va no dat"* ma khong noi
  cho nay la bao cao mot pham vi rong hon thu that su duoc do
  (`pham-vi-phep-do-hep-hon-loi-tuyen-bo`).

⭐ Cai no THAT SU do, va la cai dang mot bai kiem:

  1. `ha_nguon_cua` la mot **cai dat KHAC** (vong lap theo thu tu `CHUOI`,
     `pipeline.py`) voi `bao_dong` (de quy, `test_3004`). Bai nay bat hai cai dat
     do khop nhau **tren do thi that** — tuc ban khai (`sau=`) va co che vo hieu
     hoa khong lech nhau. Chinh docstring cua `ha_nguon_cua` canh bao rang hom
     nay no TRUNG voi `CHUOI[i+1:]` "*do hoan canh, khong do dinh nghia*".
  2. Phan phan xu la mot ham THUAN nhan **ca do thi lan tap vo hieu** lam du
     lieu, nen khoanh khac ai xen mot buoc co nhanh re vao giua thi no bat duoc.
     `test_phan_xu_chay_lai_BAT_DUOC_vi_pham_that` chung minh dieu do NGAY HOM
     NAY, tren mot do thi tong hop — khong phai mot loi hua.

⛔ Vi sao khong tiem vao `pipeline.py` that: `_kiem_tra_chuoi()` chan phu thuoc
   tien o cap **nap module**, nen phep tiem chet truoc khi toi phan phan xu. Mot
   doi chung that bai vi ly do KHAC thi khong phai mot doi chung (N-08b).
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import pipeline as P
from tests.test_3004_asv_khai_sau_phai_phu_thu_that_su_doc import (
    GOC, MODULE, SAU_CUA, THU_TU, _doc_cua, bao_dong)

#: `{ten_buoc: {ten_giai_doan_duoc_doc: dong_dau_tien}}` — quet MOT lan.
DOC_MOI_BUOC: dict[str, dict[str, int]] = {
    ten: _doc_cua(GOC / m) for ten, m in MODULE.items()}


def ai_doc(ten: str, doc_moi_buoc: dict, thu_tu: dict) -> dict[str, int]:
    """Buoc nao DOC `ten` va dung SAU `ten`. `{ten_buoc: dong}`. Thuan.

    ⚠️ Chi xet buoc dung SAU: doc NGUOC (`edit_plan` doc `qc`) la duong VONG SUA,
       co that va dung thiet ke — xem `test_3004`.
    """
    return {s: d[ten] for s, d in doc_moi_buoc.items()
            if ten in d and thu_tu[s] > thu_tu[ten]}


def vi_pham_chay_lai(ten: str, doc_moi_buoc: dict, ha_nguon, thu_tu: dict
                     ) -> dict[str, int]:
    """Buoc DOC `ten` ma KHONG bi vo hieu khi `ten` chay lai. Thuan, kiem duoc.

    🔑 `ha_nguon` la mot **tham so**, khong phai `P.ha_nguon_cua(ten)` goi ben
       trong: nho vay doi chung truyen vao duoc mot tap vo hieu THIEU va chung
       minh phan phan xu bat duoc, ma khong phai cham vao `pipeline.py`.
    """
    bi_vo_hieu = set(ha_nguon)
    return {s: d for s, d in ai_doc(ten, doc_moi_buoc, thu_tu).items()
            if s not in bi_vo_hieu}


@pytest.mark.parametrize("ten", list(MODULE))
def test_chay_lai_mot_buoc_VO_HIEU_dung_nhung_buoc_DOC_no(ten):
    """Bat bien chieu nguoc. ⚠️ Doc muc "GIOI HAN" o docstring dau tep truoc khi
    trich con so nay ra bao cao."""
    ngoai = vi_pham_chay_lai(ten, DOC_MOI_BUOC, P.ha_nguon_cua(ten), THU_TU)
    assert not ngoai, (
        f"chay lai `{ten}` KHONG vo hieu cac buoc sau, ma chung DOC no:\n  "
        + "\n  ".join(f"{MODULE[s]}:{d}  doc `{ten}`"
                      for s, d in sorted(ngoai.items(), key=lambda kv: kv[1]))
        + f"\n\n`ha_nguon_cua({ten!r})` = {P.ha_nguon_cua(ten)}\n"
          "⇒ Them phu thuoc vao `sau=` cua cac buoc tren, hoac bo lan doc do.")


def test_ha_nguon_cua_KHOP_bao_dong__hai_cai_dat_DOC_LAP_cua_cung_mot_quan_he():
    """⭐ Day la phan CO NOI DUNG cua tep nay (xem muc ⭐ o docstring dau tep).

    `ha_nguon_cua` (vong lap, `pipeline.py`) va `bao_dong` (de quy, `test_3004`)
    la hai cai dat cua **cung mot quan he**, va co che vo hieu hoa dung cai dau
    con ban khai dung cai sau. Chung lech nhau thi mot lan chay lai vo hieu sai
    tap buoc — va khong loi nao bao.
    """
    for g in P.CHUOI:
        theo_bao_dong = {s.ten for s in P.CHUOI
                         if g.ten in bao_dong(s.ten, SAU_CUA)}
        assert set(P.ha_nguon_cua(g.ten)) == theo_bao_dong, (
            f"{g.ten}: ha_nguon_cua={sorted(P.ha_nguon_cua(g.ten))} "
            f"!= qua bao_dong={sorted(theo_bao_dong)}")


def test_phep_kiem_nay_KHONG_RONG():
    """⛔ Mot phep quet AST rong thi xanh, va xanh mai mai (bai hoc `test_3004`).

    Nen phai co mot bai chot rang `ai_doc` **that su thay** thu no di tim: bon
    buoc duoi day doc `content_process` trong ma nguon that.
    """
    doc_cp = ai_doc(P.CONTENT_PROCESS, DOC_MOI_BUOC, THU_TU)
    assert {P.VOICE_SYNTHESIS, P.TIMING_ALIGN, P.QC_AI} <= set(doc_cp), sorted(doc_cp)


def test_phan_xu_chay_lai_BAT_DUOC_vi_pham_that():
    """⛔ DOI CHUNG, tren mot do thi TONG HOP + mot tap vo hieu TRUYEN VAO.

    Dung canh chu du an nham toi: **xen mot buoc moi vao giua**. `buoc_moi` DOC
    `media_prepare`, nen chay lai `media_prepare` phai vo hieu `buoc_moi`. Neu
    co che vo hieu bo sot no (tap `ha_nguon` thieu) thi luot chay lai giao mot
    ban tron lan ket qua hai luot — dung kieu hong `features.py:263` da ghi.
    """
    thu_tu = {"media_prepare": 0, "transcribe": 1, "content_process": 2,
              "buoc_moi": 3}
    doc = {"media_prepare": {},
           "transcribe": {"media_prepare": 10},
           "content_process": {"transcribe": 20},
           "buoc_moi": {"media_prepare": 42}}

    # Vo hieu DU -> khong vi pham.
    du = ["transcribe", "content_process", "buoc_moi"]
    assert vi_pham_chay_lai("media_prepare", doc, du, thu_tu) == {}

    # Vo hieu BO SOT `buoc_moi` -> phai bat, va phai mang SO DONG.
    sot = ["transcribe", "content_process"]
    assert vi_pham_chay_lai("media_prepare", doc, sot, thu_tu) == {"buoc_moi": 42}

    # Doc NGUOC (buoc truoc doc buoc sau) -> vong sua, KHONG phai vi pham.
    assert vi_pham_chay_lai("content_process", doc, [], thu_tu) == {}
