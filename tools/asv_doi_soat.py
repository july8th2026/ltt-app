r"""asv_doi_soat.py — Sau phep DEM tren mot luot chay ASV — ⛔ khong can ban
tham chieu, ⛔ khong can ai cham.

    python tools\asv_doi_soat.py <run_id>

🔑 **Vi sao dem chu khong cham.** `B2_DO_DICH_THAM_CHIEU.md` tu khai bo do dich
   dang bi khoa boi mot vong tron: chan ly nen la hai nguoi soi ma **ca hai deu
   la LLM**, kappa 0,714 voi KTC95 `[0,00 ; 1,00]`. Sau phep duoi day ⛔ khong
   hoi *"ban dich co hay khong"* — chung hoi *"luot chay nay co TU MAU THUAN
   khong"*, va mau thuan thi dem duoc. Mot bo cham sai gu van dem mau thuan
   dung.

⛔ `None` nghia la **chua do duoc**; `0` nghia la **do duoc va bang khong**. Gop
   hai thu do vao mot gia tri la mat dung kha nang phan biet ma bang nay ton
   tai de giu.

═══════════════════════════════════════════════════════════════════════════════
🔴 **DINH CHINH 26/09 (Task 5b) — ban truoc cua tep nay ⛔ KHONG DO GI.**

   Ban truoc doc `gd["tom_tat"]` cua mot muc trong `quan_sat.dong_thoi_gian`.
   ⛔ Muc `giai_doan` cua dong thoi gian **khong he co khoa `tom_tat`** (no co
   `bat_dau · giai_doan · giai_doan_hong · giay · ket_thuc · loi_co_ma ·
   so_ket_qua · trang_thai`). `thi_hanh.py:589` do `tom_tat` cua giai doan
   **PHANG** vao `asv_stage.outputs`:

       ket_qua = {"stage": ten, "khoa_asset": khoa_ra, **(ra.get("tom_tat") or {})}

   ⇒ moi phep do tra `None`, tuc *"chua do duoc"*, **mai mai** — mot dung cu do
   im lang khong do gi ma van xanh.

   ⭐ Va vi sao bo test cu XANH: fixture BIA ra mot `dong` co dung khoa ma ma
   nguon **muon nhan**. Chinh kho nay da ghi cai bay do o
   `giai_doan_noi_dung.py` (tim `cua_ai_gia`): *"Mot ban gia tra ve dung thu ma
   ma nguon muon nhan, thay vi thu cua that tra ve, se lam ca bo test xanh
   quanh mot loi khong the khong xay ra."*

   ⇒ Tu ban nay: lop TINH nhan `{ten_giai_doan: outputs}` (thuan, kiem duoc,
   ⛔ khong can CSDL), lop `main` dung map do TU CSDL.

🔴 **Đ4 (`so_doan_nan_oan`) NAY DO DUOC — va lo hong cua no la mot bai hoc rieng.**

   Ban truoc cua tep nay ghi rang bo dem `so_doan_nan_oan` ⛔ khong bao gio roi
   khoi `giai_doan_giong.chay`, nen Đ4 *"chua do duoc"*. `giai_doan_giong` **nay
   XUAT** no vao `tom_tat` tai cho `return`, nen cau ay ⛔ da sai — va cong cu
   nay van ⛔ khong doc no, tuc Đ4 **van vo hinh voi nguoi van hanh** du con so
   da nam san trong `asv_stage.outputs`.

   ⭐ **Vi sao lo hong ton tai: banh coc chi kiem MOT CHIEU.**
      `test_408::test_doi_soat_moi_khoa_doc_deu_CO_AI_GHI_vao_outputs` hoi *"khoa
      cong cu DOC -> co ai GHI khong"*. Chieu ay bat duoc N-5b (doc mot khoa
      khong ton tai). Nhung no ⛔ mu tuyet doi voi chieu con lai: *"khoa da duoc
      GHI -> cong cu co DOC khong"* — va dung o chieu ay mot phep do moi sinh ra
      roi nam khong ai dung tren dia. Tu ban nay `KHOA_BO_QUA_CO_Y` khai tuong
      minh tung khoa **co y khong doc**, va `test_408` chot CA HAI chieu: mot
      khoa moi trong `tom_tat` phai vao `KHOA_CAN` hoac vao danh sach bo qua —
      ⛔ khong co duong thu ba de no im lang.

🔴 **MOT khoa dac ta cu doi ma ⛔ KHONG MOT AI GHI RA** — da bo khoi bang:

   - `pause_kha_dung_s`: ⛔ khong ton tai o bat ky dau trong `apps/`. Khai niem
     that la `thoi_gian.ngan_sach_nan_s(khe_s, ngan_sach_s) - khe_s`, va no
     ⛔ khong duoc ghi vao `outputs` cua giai doan nao.

⚠️ **Mau so.** `sai_so_*` doc thang `lech` cua chinh ban ghi luot doc, tuc
   `(giay - khe) / khe` (`nan_cho_vua.lech`) — **cung mau so** ma `can_nan` /
   `dung_sai_giay` dung de phan quyet. Ban truoc chia cho `giay` (so THAT), tuc
   mot mau so khac, nen con so cua no ⛔ khong so sanh duoc voi nguong nao ca.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Khoa `outputs` ma cong cu nay doc, theo TEN GIAI DOAN.
#:
#: ⭐ Khai ra thanh DU LIEU chu khong an trong than ham, de mot phep kiem CO HOC
#:    doi chieu duoc tung khoa voi cho THAT SU ghi no (`test_408`). Mot loi dan
#:    do ⛔ khong chan duoc lan sau; mot phep do thi co.
KHOA_CAN: dict[str, tuple[str, ...]] = {
    # `giai_doan_giong.chay` -> `tom_tat` (phang vao outputs boi `thi_hanh`)
    "voice_synthesis": ("tung_luot_doc", "giay_tts", "giay_llm_nan",
                        # Đ4 — `giai_doan_giong.py` XUAT no o cho `return`
                        "so_doan_nan_oan",
                        # ⭐ Đ7 — CAI GIA cua quyet dinh "doan khong chu thi BO
                        #    QUA" (Task 25, 27/09). Quyet dinh do la DUNG cho san
                        #    pham — phim khach that SE co khe chi nhac — nhung no
                        #    lam khach MAT mot doan thoai, nen no phai DEM DUOC.
                        #    ⛔ Mot con so duoc GHI ma ⛔ khong ai DOC thi no chi la
                        #    mot bao cao; cho nay la cho no duoc doc.
                        "so_doan_im_lang", "doan_im_lang"),
    # `giai_doan_thoi_gian.chay` -> `tom_tat["master"] = do_duoc`
    "timing_align": ("master",),
    # `giai_doan_qc.tom_tat_kem_khong_do` -> `tom_tat` (giai_doan_qc.py:326)
    #
    # 🔴 **Ba khoa nay duoc GHI tu truoc ma ⛔ KHONG AI DOC** (do 27/09: khong mot
    #    cho nao trong `apps/`, `server/`, `platform_core/`, `tools/` doc chung).
    #    Chung ton tai de tra dung cau hoi *"cong PHAT HANH bao DAT sau khi do
    #    duoc bao nhieu phep?"* — mot luot thieu `libvmaf`, ffmpeg bam khong noi
    #    luong hinh, va giai ma het thoi gian se ha T3/T13/T17/T18 xuong
    #    `KHONG_AP_DUNG` roi in `dat: True, so_muc_hong: 0`. Mot chu DAT dung mot
    #    minh tren nhung phep do chua he chay.
    #
    # ⭐ Va day cung la lan mo rong banh coc hai chieu: truoc hom nay `KHOA_CAN`
    #    chi phu **2 trong 13** giai doan (`voice_synthesis`, `timing_align`), nen
    #    `test_408` chi canh duoc hai cho. `qc` la giai doan thu ba, va no la giai
    #    doan duy nhat co the noi "DAT" ma ⛔ khong do gi.
    #
    # ⚠️ Ba khoa nay duoc ghi **vo dieu kien** (ke ca khi rong) nen dat chung o
    #    day ⛔ khong lam luot binh thuong bao thieu — chung chi thieu khi giai
    #    doan `qc` chay bang mot duong ⛔ khong di qua `tom_tat_kem_khong_do`.
    "qc": ("qc_so_muc_khong_do", "qc_muc_khong_do", "qc_ly_do_khong_do",
           # ⭐ Đ8 doc CA loi tuyen bo LAN pham vi cua no. `qc_ky_thuat_dat` mot
           #    minh ⛔ khong tra loi duoc *"DAT tren bao nhieu phep do that?"*.
           "qc_ky_thuat_dat"),
}

#: 🔴 **Khoa `tom_tat` ma cong cu nay CO Y ⛔ khong doc** — chieu NGUOC cua banh
#: coc (xem khoi Đ4 o dau tep).
#:
#: ⭐ Mot khoa moi trong `tom_tat` phai vao `KHOA_CAN` **hoac** vao day; ⛔ khong
#:    co duong thu ba. Do la toan bo cong dung cua bang nay: no ⛔ khong lam gi
#:    luc chay, no bat mot NGUOI quyet dinh — *"con so moi nay co phai mot phep
#:    do doi soat khong?"* — dung luc nguoi ay con dang nho vi sao minh them no.
#:
#: ⚠️ Ghi vao day ⛔ khong co nghia *"con so nay vo dung"*: `tung_doan`,
#:    `so_vua`, `so_can_sua`... la bao cao van hanh cua chinh giai doan, va cong
#:    cu nay chi tra loi SAU cau hoi doi soat (Đ1-Đ6). Nghia dung la: *"da co
#:    nguoi nhin, va no ⛔ khong thuoc sau cau ay."*
KHOA_BO_QUA_CO_Y: dict[str, tuple[str, ...]] = {
    "voice_synthesis": (
        # Bao cao khoi luong / chi phi cua chinh giai doan
        "so_ma_noi_dung", "so_khe_da_gop", "so_doan_moi_sinh", "so_luot_doc",
        "so_doan_dung_lai", "tong_giay", "so_doan", "so_luot_do",
        # Cau hinh cua luot chay — sieu du lieu, ⛔ khong phai phep do
        "preset", "ma_giong",
        # Bao cao cua `nan_cho_vua.tom_tat`: dem theo trang thai + so gop.
        # ⭐ `tung_doan` la giay CUOI CUNG sau nan; Đ1/Đ2 doc `tung_luot_doc` vi
        #    no tra loi *"bo uoc luong co dung khong"* (xem `doi_soat`).
        "so_vua", "so_can_sua", "so_co_gian", "so_ngan", "so_vong_tong",
        "lech_lon_nhat", "tung_doan",
    ),
    "timing_align": (
        # ⭐ Đ5/Đ6 doc `master` (`he_so_toc_da_ap`, `so_doan_lech_cuoi`,
        #    `giay_lech_cuoi`) — thu DA AP. Cac khoa duoi la bao cao phang cua
        #    giai doan, va `he_so_toc_lon_nhat` la MOT cuc dai chu ⛔ khong phai
        #    phan vi 90 ma Đ5 hoi.
        "che_do", "so_doan", "so_doan_bi_cat", "so_doan_tang_toc",
        "he_so_toc_lon_nhat", "ket_cuoi_ms", "troi_toi_da_ms",
    ),
    "qc": (
        # Bao cao phang cua chinh cong QC — Đ8 doc `qc_ky_thuat_dat` cong
        # `qc_so_muc_khong_do`, la cap tra loi duoc cau hoi ve PHAM VI. Hai khoa
        # duoi dem MUC HONG, mot cau hoi khac va da co nguoi tra loi (bao cao QC
        # di thang ra man khach), nen o day chung la sieu du lieu.
        "qc_muc_hong", "qc_so_muc_hong",
        # Phien ban bo phep kiem — sieu du lieu cua luot chay.
        "qc_phien_ban",
    ),
}

#: Khoa nam TRONG `outputs["master"]` cua `timing_align` — mot cau truc LONG,
#: ⛔ khong phang: `giai_doan_thoi_gian.py:159` dat ca `do_duoc` duoi mot khoa.
KHOA_TRONG_MASTER: tuple[str, ...] = (
    "he_so_toc_da_ap", "so_doan_lech_cuoi", "giay_lech_cuoi")

#: Khoa cua MOT ban ghi trong `tung_luot_doc` (`nan_cho_vua.ban_ghi_luot_doc`).
KHOA_TRONG_LUOT_DOC: tuple[str, ...] = ("giay", "khe", "lech")


def _phan_vi(cac: list[float], p: float) -> float | None:
    if not cac:
        return None
    xs = sorted(cac)
    if len(xs) == 1:
        return xs[0]
    vt = p * (len(xs) - 1)
    lo = int(vt)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (vt - lo)


def doi_soat(outputs_theo_giai_doan: dict[str, dict]) -> dict:
    """Sau con so tu `outputs` cua CAC GIAI DOAN — ⛔ khong can CSDL.

    `outputs_theo_giai_doan` = `{ten_giai_doan: dict(asv_stage.outputs)}`. Giai
    doan chua chay thi vang mat (hoac map toi `{}`), va moi phep do cua no tra
    `None` = *"chua do duoc"*.
    """
    giong = dict(outputs_theo_giai_doan.get("voice_synthesis") or {})
    thoi = dict(outputs_theo_giai_doan.get("timing_align") or {})
    qc_o = dict(outputs_theo_giai_doan.get("qc") or {})
    master = dict(thoi.get("master") or {})

    # ── Đ1/Đ2: sai so thoi luong doc, tren TUNG LUOT DOC ────────────────────
    #
    # ⚠️ `tung_luot_doc` (mot dong moi LUOT) chu ⛔ khong `tung_doan` (mot dong
    #    moi DOAN, giay CUOI CUNG sau nan): luot doc DAU la thu tra loi *"bo uoc
    #    luong co dung khong"*, con giay sau nan da bi chinh phep nan keo ve.
    luot = [d for d in (giong.get("tung_luot_doc") or []) if isinstance(d, dict)]

    sai_so: list[float] = []
    ngan = 0
    for e in luot:
        khe = float(e.get("khe") or 0.0)
        if khe <= 0:
            continue
        # ⭐ Doc `lech` co san cua chinh ban ghi ay — cung mau so voi
        #    `nan_cho_vua.can_nan`. ⛔ Khong tu chia lai: hai ban sao cua mot
        #    phep tinh la thu kho nay da tra gia.
        lc = e.get("lech")
        if lc is None:
            continue
        sai_so.append(abs(float(lc)))
        if float(lc) < 0:
            ngan += 1

    he_so = [float(x) for x in (master.get("he_so_toc_da_ap") or [])]

    return {
        # Đ1 — sai so tuong doi so voi KHE (mau so = khe, nhu chinh sach nan)
        "sai_so_p50": _phan_vi(sai_so, 0.50),
        "sai_so_p90": _phan_vi(sai_so, 0.90),
        "sai_so_max": max(sai_so) if sai_so else None,
        # ⭐ `0` o day nghia la "co du lieu va khong luot nao ngan"; `None`
        #    nghia la "khong mot luot doc nao do duoc".
        "so_luot_do_duoc": len(sai_so) if luot else None,
        # Đ2 — ti le luot doc NGAN hon khe (`ngon_ngu.py:99` tro vao ten nay)
        "ti_le_doan_ngan": (ngan / len(sai_so)) if sai_so else None,
        # Đ3 — giai doan giong cham vi cai gi
        "giay_tts": giong.get("giay_tts"),
        "giay_llm_nan": giong.get("giay_llm_nan"),
        # ⭐ Đ7 — bao nhieu doan bi BO QUA (khoang lang) va la nhung doan nao.
        #    ⚠️ `0` nghia la "do duoc va ⛔ khong doan nao bi bo"; `None` nghia la
        #    "giai doan ⛔ khong ghi con so nay" — hai trang thai KHAC nhau, va
        #    `chan_doan` o duoi noi ro cai nao.
        "so_doan_im_lang": giong.get("so_doan_im_lang"),
        "doan_im_lang": giong.get("doan_im_lang"),
        # ⭐ Đ4 — so doan `giay > khe` NHUNG `giay <= ngan_sach`, tuc tung bi
        #    TINH TIEN OAN mot luot LLM nan truoc ban sua thu tu. `0` = do duoc
        #    va khong doan nao; `None` = giai doan chua chay.
        "so_doan_nan_oan": giong.get("so_doan_nan_oan"),
        # Đ5 — he so tang toc THAT SU da ap (⛔ khong phai thu khach chon)
        "he_so_toc_p90": _phan_vi(he_so, 0.90),
        # Đ6 — nac (c): chap nhan lech nhung ⛔ khong im
        "so_doan_lech_cuoi": master.get("so_doan_lech_cuoi"),
        "giay_lech_cuoi": master.get("giay_lech_cuoi"),
        # ── Đ8: cong PHAT HANH noi DAT sau khi do duoc bao nhieu phep? ───────
        #
        # 🔴 `giai_doan_qc` GHI ba khoa nay tu truoc (`tom_tat_kem_khong_do`), va
        #    do 27/09: ⛔ KHONG mot cho nao trong `apps/`, `server/`,
        #    `platform_core/`, `tools/` doc chung. Mot con so duoc ghi ma ⛔ khong
        #    ai doc thi no la mot bao cao, ⛔ khong phai mot phep kiem.
        #
        # ⚠️ Vi sao no dang gia: `dat = not hong`, va `KHONG_AP_DUNG` ⛔ khong
        #    phai `hong`. Mot luot thieu `libvmaf` + ffmpeg bam khong noi luong
        #    hinh + giai ma het thoi gian ⇒ T3/T13/T17/T18 deu ha xuong
        #    `KHONG_AP_DUNG`, va bao cao in `dat: True, so_muc_hong: 0`. Tuc
        #    **DAT sau khi ⛔ khong do gi** — dung ho loi cua gate o `f4c4f064`.
        #
        # ⭐ Doc CA HAI: `qc_ky_thuat_dat` (loi tuyen bo) va `qc_so_muc_khong_do`
        #    (pham vi cua no). Mot minh cai dau ⛔ khong tra loi duoc cau hoi;
        #    mot minh cai sau thi ⛔ khong ai biet no co dang lo hay khong.
        "qc_ky_thuat_dat": qc_o.get("qc_ky_thuat_dat"),
        "qc_so_muc_khong_do": qc_o.get("qc_so_muc_khong_do"),
        "qc_muc_khong_do": qc_o.get("qc_muc_khong_do"),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  G1/G2 — nhat quan dai tu va ten rieng (Task 13)
# ══════════════════════════════════════════════════════════════════════════════

#: Tu xung ho tieng Viet, CHIA THEO VAI — **du lieu ngon ngu**, ⛔ khong phai
#: phan quyet chat luong. Nen no duoc phep go ra, va no kiem duoc bang cach soi
#: lai tren ban ghi that.
#:
#: 🔴 **Vi sao phai chia vai (do duoc 26/09).** Ban dac ta dau lay mot **TAP
#:    theo CAU**: `frozenset` moi tu xung ho xuat hien trong cau ay, roi dem so
#:    tap phan biet. Tren mot tai lieu HOAN TOAN NHAT QUAN:
#:
#:      "Chao cac ban"           -> {ban, cac ban}
#:      "Hom nay minh di cam"    -> {minh}
#:
#:    ⇒ hai tap, tuc `so_bo_dai_tu == 2`, tuc **bao dong gia**. Hai loi rieng
#:    biet gop lai: (i) mot cau chi noi ngoi THU NHAT va mot cau chi noi ngoi
#:    THU HAI thi ⛔ khong he mau thuan — tap theo cau tron hai VAI lam mot;
#:    (ii) `ban` la con cua `cac ban`, nen mot lan xung ho dung dem thanh hai.
#:
#: ⚠️ `THAN_TOC` la mot vai RIENG vi tieng Viet dung cung mot tu cho ca nguoi
#:    noi va nguoi nghe (`em` tu goi minh / goi nguoi khac). Nhap chung vao ngoi
#:    thu nhat hay thu hai deu sinh bao dong gia, va **bao dong gia lam nguoi ta
#:    TAT cong**.
NGOI_MOT = ("toi", "to", "minh", "tao")
NGOI_HAI = ("ban", "cau", "may", "quy vi", "cac ban")
THAN_TOC = ("ong", "ba", "anh", "chi", "em", "chau", "con", "co", "chu", "bac")

#: Hop cua ba vai — giu ten cu de mot phep kiem/tai lieu tro vao no khong chet.
TU_XUNG_HO = NGOI_MOT + NGOI_HAI + THAN_TOC

#: Chu cai ⛔ KHONG co trong bang chu cai tieng Viet.
CHU_NGOAI = "fjwz"

_NGUYEN_AM = set("aeiouy")


def _bo_dau(v: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", v.lower())
                   if unicodedata.category(c) != "Mn")


def _la_am_tiet_viet(t: str) -> bool:
    """`t` (da bo dau, chu thuong) co the la MOT am tiet tieng Viet khong.

    ⭐ Hai dau hieu CO HOC, ⛔ khong can tu dien:
       - chua `f`/`j`/`w`/`z` ⇒ ⛔ khong phai chu tieng Viet;
       - co HAI nhom nguyen am cach nhau boi phu am ⇒ ⛔ khong phai mot am tiet
         (`photon` = `o` + `t` + `o`). Tieng Viet viet roi tung am tiet, nen moi
         **token** cua mot cau tieng Viet phai la mot am tiet.
    """
    if not t or any(c in CHU_NGOAI for c in t):
        return False
    nhom = 0
    truoc_la_nguyen_am = False
    for c in t:
        la = c in _NGUYEN_AM
        if la and not truoc_la_nguyen_am:
            nhom += 1
        truoc_la_nguyen_am = la
    return nhom <= 1


def _cum_hoa(cau: str) -> list[str]:
    """Cac cum token LIEN TIEP bat dau bang chu HOA trong `cau`.

    ⭐ Ten rieng la thu duy nhat viet hoa giua cau trong tieng Viet, va mot ten
       Viet gom nhieu am tiet deu viet hoa (`Quang Tu`).
    """
    tok = [t for t in re.split(r"[^0-9A-Za-zÀ-ỹ]+", cau) if t]
    cum: list[str] = []
    dang: list[str] = []
    for t in tok:
        if t[:1].isupper():
            dang.append(t)
        elif dang:
            cum.append(" ".join(dang))
            dang = []
    if dang:
        cum.append(" ".join(dang))
    return cum


def nhat_quan(cac_cau: list[str], *,
              ten_goc: dict[str, str] | None = None) -> dict:
    """G1 + G2 — dem MAU THUAN, ⛔ khong cham chat luong.

    🔑 ⛔ Khong can ban tham chieu va ⛔ khong can ai cham: hai con so nay dem
       mau thuan BEN TRONG mot tai lieu, nen chung di vong qua vong tron LLM
       dang khoa bo do dich (`B2_DO_DICH_THAM_CHIEU.md`).

    `so_bo_dai_tu` — dat = `1`: ca video dung MOT bo xung ho. Con so la so cach
    goi PHAN BIET nhieu nhat ma mot VAI phai ganh; ⛔ khong phai so tap theo cau
    (xem `NGOI_MOT`).

    `vi_pham_ten_rieng` — dat = `0`. Hai the, va the (b) la the ma ban dac ta
    dau thieu:
      (a) mot ten da chot ⛔ khong xuat hien lan nao ⇒ mot dang KHAC da duoc dung;
      (b) tai lieu co mot cum viet hoa ⛔ khong khop ten nao da chot VA ⛔ khong
          doc duoc nhu tieng Viet (`Photon`) ⇒ mot ten goc da ra HAI dang. Chi
          the (a) thi `["Quang Tu den roi", "Photon da di"]` **dat**, du no la
          dung ca mau thuan G2 ton tai de bat.
    """
    # ── G1: moi VAI duoc phep co dung MOT cach goi ───────────────────────────
    theo_vai: dict[str, set[str]] = {"mot": set(), "hai": set(), "than_toc": set()}
    for cau in cac_cau:
        v = f" {_bo_dau(cau)} "
        thay = {t for t in TU_XUNG_HO if f" {t} " in v}
        # ⭐ Khop DAI NHAT: `ban` la con cua `cac ban`, va mot lan xung ho ⛔
        #    khong duoc dem thanh hai cach goi.
        thay = {t for t in thay
                if not any(u != t and f" {t} " in f" {u} " for u in thay)}
        for t in thay:
            if t in NGOI_MOT:
                theo_vai["mot"].add(t)
            elif t in NGOI_HAI:
                theo_vai["hai"].add(t)
            else:
                theo_vai["than_toc"].add(t)
    so_bo = max((len(s) for s in theo_vai.values()), default=0)

    # ── G2: mot ten goc ⇒ dung MOT dang Viet ────────────────────────────────
    vi_pham = 0
    da_chot = {_bo_dau(d) for d in (ten_goc or {}).values() if d}
    for _goc, dang in (ten_goc or {}).items():
        d = _bo_dau(dang)
        co = sum(1 for cau in cac_cau if d in _bo_dau(cau))
        if co == 0 and cac_cau:
            vi_pham += 1
    if da_chot:
        for cau in cac_cau:
            for cum in _cum_hoa(cau):
                c = _bo_dau(cum)
                if any(c in d or d in c for d in da_chot):
                    continue  # khop mot ten da chot ⇒ khong phai mau thuan
                if not all(_la_am_tiet_viet(t) for t in c.split()):
                    vi_pham += 1
    return {"so_bo_dai_tu": so_bo or 1, "vi_pham_ten_rieng": vi_pham}


# ══════════════════════════════════════════════════════════════════════════════
#  Lop CSDL — dung map `{ten_giai_doan: outputs}` roi giao cho lop TINH
# ══════════════════════════════════════════════════════════════════════════════

#: Ba ly do KHAC LOAI mà một giá trị `None` có thể mang — và chỉ ly do thứ ba là LỖI.
THIEU_GIAI_DOAN = "thieu_giai_doan"
CHUA_XONG = "chua_xong"
THIEU_KHOA = "thieu_khoa"


def chan_doan(outputs_theo_giai_doan: dict[str, dict],
              trang_thai_theo_giai_doan: dict[str, str | None]) -> dict[str, str]:
    """`{ten_giai_doan: ly_do}` — vi sao giai doan nay CHUA cap duoc so. `""` = du.

    🔴 **`None` gop BA trang thai khac loai, va dung cai gop ay tung lam mot dung cu
       do im lang khong do gi ma van xanh** (`tools/asv_doi_soat.py` ban 26/09 doc
       `gd["tom_tat"]` — mot khoa ⛔ khong ton tai — nen tra `None` cho MOI phep do):

      1. `thieu_giai_doan` — ⛔ khong co dong `AsvStage` nao: luot chay chua tới đó.
         **Binh thuong**, ⛔ khong phai loi.
      2. `chua_xong:<trang_thai>` — co dong nhung chua `succeeded`: **cung binh thuong**.
      3. `thieu_khoa:<a,b>` — giai doan **DA XONG** ma khoa can ⛔ **khong co trong
         `outputs`**. ⭐ Chi ca nay la LOI, va no la loi o **phia GHI** hoac o **bang
         `KHOA_CAN`** — ⛔ khong bao gio la "chua tới lúc".

    ⇒ In ly do ra ben canh con so, de mot bang toan `None` tu khai bao no la
      *"chua chay tới"* hay *"dung cu hong"*. Mot lan chay that rat dat; doc sai
      ket qua cua no dat hon.
    """
    ra: dict[str, str] = {}
    for ten, can in KHOA_CAN.items():
        tt = trang_thai_theo_giai_doan.get(ten)
        if tt is None:
            ra[ten] = THIEU_GIAI_DOAN
            continue
        if str(tt) != "succeeded":
            ra[ten] = f"{CHUA_XONG}:{tt}"
            continue
        out = outputs_theo_giai_doan.get(ten) or {}
        thieu = [k for k in can if k not in out]
        ra[ten] = f"{THIEU_KHOA}:{','.join(thieu)}" if thieu else ""
    return ra


def trang_thai_tung_giai_doan(db, run_id: str) -> dict[str, str | None]:
    """`{ten_giai_doan: trang_thai}` — `None` khi ⛔ khong co dong nao.

    ⚠️ Tach khoi `outputs_tung_giai_doan` vi ham do **lam phang `None` thanh `{}`**:
       sau no thi *"chua co giai doan"* va *"giai doan xong voi outputs rong"* la
       cung mot thu — dung cai mat mat ma `chan_doan` ton tai de vá.
    """
    from apps.auto_scan_video import features

    ra: dict[str, str | None] = {}
    for ten in KHOA_CAN:
        s = features.giai_doan_theo_ten(db, run_id, ten)
        ra[ten] = None if s is None else str(s.status)
    return ra


def outputs_tung_giai_doan(db, run_id: str) -> dict[str, dict]:
    """`{ten_giai_doan: dict(outputs)}` cho dung cac giai doan `KHOA_CAN` can.

    ⭐ Cung khuon voi `quan_sat._outputs` va `giai_doan_noi_dung._doc_ban_bien_tap`:
       doc `asv_stage.outputs`, ⛔ khong doc `dong_thoi_gian`.
    """
    from apps.auto_scan_video import features

    ra: dict[str, dict] = {}
    for ten in KHOA_CAN:
        s = features.giai_doan_theo_ten(db, run_id, ten)
        ra[ten] = dict((s.outputs if s is not None else None) or {})
    return ra


def main(argv: list[str]) -> int:
    # ⭐ Boc lai stdout CHI o day (khi chay nhu CLI that), khong o muc module:
    #    boc o muc module lam pytest hong capture luc import ("I/O operation
    #    on closed file") vi TextIOWrapper giu mot tham chieu rieng toi buffer.
    if hasattr(sys.stdout, "buffer"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True)

    if len(argv) != 2:
        print(__doc__)
        return 2
    run_id = argv[1]

    from tools.asv_chay_worker_that import nap_env
    nap_env()

    from platform_core.db import get_session

    from apps.auto_scan_video.tables import AsvRun

    gen = get_session()
    db = next(gen)
    try:
        run = db.get(AsvRun, run_id)
        if run is None:
            print(f"KHONG THAY run {run_id!r} trong CSDL nay.")
            return 1

        outs = outputs_tung_giai_doan(db, run.id)
        ra = doi_soat(outs)
        for khoa, gt in ra.items():
            print(f"{khoa}={gt}")

        # ⭐ Vi sao mot phep do la `None` — xem docstring `chan_doan`.
        ly_do = chan_doan(outs, trang_thai_tung_giai_doan(db, run.id))
        print("\n-- NGUON: vi sao mot phep do co the la None --")
        loi = False
        for ten, vi_sao in ly_do.items():
            if not vi_sao:
                print(f"   {ten}: du khoa")
            else:
                print(f"   {ten}: {vi_sao}")
                loi = loi or vi_sao.startswith(THIEU_KHOA)
        if loi:
            print("\n🔴 Co giai doan DA XONG ma THIEU khoa can => loi o phia GHI"
                  " hoac o bang KHOA_CAN, ⛔ khong phai 'chua chay tới'.")
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
