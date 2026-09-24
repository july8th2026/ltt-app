"""QC bang AI: nghe lai, doc lai nghia, va nhin lai cho noi.

## Ba cau hoi ma QC ky thuat khong tra loi duoc

Pha 18 do duoc: tep hop le, dung thoi luong, dung am luong, khong toan den. Moi
thu do co the **dat het** trong khi ban ra van hong theo ba cach:

  1. may doc **sai** cau da viet (nuot tu, doc nham so)
  2. cau tieng Viet **lech nghia** so voi nguon
  3. cho noi hai canh lam **dut mach hinh**

⛔ Ba cau nay khong do duoc bang mot nguong. Chung can mot ben doc/nghe/nhin, va
   do la ly do pha 19 ton tai.

## Do TIN la mot truong, khong phai mot phep lam tron

Model tra ve mot phan doan **kem do tin**, va do tin duoi nguong thi ket luan
duoc **ghi lai nhung khong sinh viec sua**. Mot model khong chac chan khong phai
mot ly do de tra tien lam lai — nhung cung khong phai mot ly do de giau di.

## ⛔ Khong provider moi, khong nang luc moi

Ca ba deu di qua `ai.goi_tinh_tien` — cua duy nhat cua pha 08. Pha 19 cam them
provider, va cua do la cho duy nhat chuyen do co the xay ra ma khong ai thay.
"""
from __future__ import annotations

import json

from platform_core.i18n import _ as _t

#: Doi khi doi loi nhac hoac luoc do. Vao van tay bao cao.
PHIEN_BAN_QC_AI = 2

#: So doan moi lan hoi model ve ngu nghia.
#:
#: ⛔ `moi_lo=None` o cac ham chia lo, khong phai `moi_lo=DOAN_MOI_LO`: mot mac
#:    dinh gan LUC DINH NGHIA HAM thi doi hang so sau do khong doi duoc gi.
DOAN_MOI_LO = 10

#: So khung lay quanh MOI cho noi de hoi VLM.
#:
#: ⭐ Hai khung: mot ngay truoc cho noi, mot ngay sau. Cau hoi la "hai canh nay
#:    noi vao nhau co dut mach khong", va no can dung hai dau — mot khung khong
#:    tra loi duoc cau hoi ve mot chuyen tiep.
KHUNG_MOI_CHO_NOI = 2

#: Cach cho noi bao nhieu giay thi lay khung.
LECH_KHUNG_GIAY = 0.4

#: Nhiet do GHIM cho lop ngu nghia. `None` = de mac dinh cua cong.
#:
#: 🔴 **Ghim vi mot phep do, khong vi mot so thich.** Do 24/09 tren dai giu
#:    rieng, ti le **lo tra JSON hong** (`LuocDoSai`, mat tron 10 muc mot lan):
#:
#:        loi nhac NHI PHAN (V1)          1/30 lo = 3,3 %
#:        loi nhac PHAN MUC MQM (V3)      2/9  lo =  22 %
#:
#:    Dau ra MQM dai hon han dau ra nhi phan (mot danh sach loi kem ly do, thay
#:    cho mot co `true/false`), nen no lam **lo** dung diem yeu bam luoc do ma
#:    `--temp 1.0` cua cong von che di.
#:
#: ⚠️ Mat theo **LO**, khong theo **MUC** ⇒ mat ca mot cum chu khong phai mot
#:    mau ngau nhien. Mot phep do tren kenh do khong phai phep do kem — no
#:    **khong ton tai**. Nen day la buoc phai lam TRUOC khi so hai loi nhac.
#:
#: ⭐ Cung don thuoc voi Task 11b (`docs/superpowers/plans/…-thang-cong-asv.md`):
#:    *ghim nhiet do TRUOC, do lai ti le qua luoc do, ROI moi sua loi nhac* —
#:    neu khong ta se di sua loi nhac cho mot van de do nhiet do gay ra.
#:
#: ⛔ Ghim nhiet do **khong** lam lan chay tat dinh: do 24/09 cho thay `seed`
#:    khong co hieu luc tren cong nay va `temperature=0.0` van cho ket qua khac
#:    nhau giua cac luot. No chi thu hep dai lay mau, tuc lam luoc do de dung
#:    vung hon — ⛔ dung doc no thanh "gio moi luot giong nhau".
NHIET_DO_NGU_NGHIA: float | None = 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  Lop ngu nghia co duoc KHAI CHO KHACH khong — va cau tra loi la mot PHEP DO
# ══════════════════════════════════════════════════════════════════════════════

#: Ti le bao dong gia DA DO cua lop ngu nghia, tren ban dich CUA NGUOI.
#:
#: 🔴 Do 24/09 tren 100 cap FLORES-200 zh->vi (ban dich chuyen nghiep), 3 luot
#:    moi cap: **45,0 %** (dai tung luot 40,0-44,4 %).
#:    `docs/auto_scan_video_final/B2_XAC_THUC_BO_CHAM.md`.
#:
#: ⛔ Doi so nay bang cach DO LAI, khong bang cach go mot so de p hon:
#:    `python tools\bench_b2_xac_thuc_bo_cham.py ...` (muc §6 cua tai lieu tren).
TI_LE_BAO_DONG_GIA_DA_DO = 0.45

#: Duoi muc nay thi con so ngu nghia moi duoc khai cho khach.
NGUONG_KHAI_CHO_KHACH = 0.15


def khai_cho_khach() -> bool:
    """Con so "N/M cau dich chua sat" co duoc hien cho khach khong.

    🔴 **Chu du an chot 24/09: KHONG, cho toi khi bao dong gia ve duoi 15 %.**
       Luot that cham 44/95 (46 %) la dich chua sat; chinh bo cham do gan
       **45 %** cho ban dich cua NGUOI DICH CHUYEN NGHIEP. Tuc no khong phan
       biet duoc ban dich cua ta voi mot ban hoan hao — va khai mot con so ma
       mot nua la bao dong gia la lam khach hieu sai ve san pham ho vua mua.

    ⭐ **Cong nay la mot PHEP TINH tu con so da do, khong phai mot co bat tay.**
       Ai ha duoc bao dong gia xuong thi sua `TI_LE_BAO_DONG_GIA_DA_DO` — va man
       hinh tu bat lai. Khong ai bat duoc no ma khong khai mot phep do, va khong
       ai phai nho di bat lai mot co.

    ⚠️ Chi che o BE MAT CUA KHACH. Phan quyet van vao artifact, van vao
       `stage.outputs`, van hien o bao cao van hanh — cung ranh gioi voi
       `sua_chua.QC_HINH_LA_TU_VAN`. "Khong khoe" khac "khong ai duoc biet".

    ⛔ Hai con so KIA cua `bang_chung_chat_luong` (`so_giong_khong_dat`,
       `so_canh_bao_tieng`) **van giu** — chung den tu thuoc khac (ASR + WER/CER,
       SQUIM), chua bi nghi ngo, va go chung di la lay mot loi khai qua tay doi
       lay mot loi khai thieu.
    """
    return TI_LE_BAO_DONG_GIA_DA_DO <= NGUONG_KHAI_CHO_KHACH


class QcAiError(ValueError):
    """Phan hoi QC bang AI khong dung hop dong."""


# ══════════════════════════════════════════════════════════════════════════════
#  1. QC ngu nghia
# ══════════════════════════════════════════════════════════════════════════════

#: Ba muc nghiem trong cua MQM, nang dan. ⛔ Thu tu la mot phan hop dong:
#: `_muc_nang_nhat` doc no de tra ve muc nang nhat trong mot danh sach loi.
MUC = ("nhe", "nang", "nghiem_trong")

#: Muc nao SINH VIEC SUA. Bang anh xa nay viet TRUOC khi do
#: (`B2_XAC_THUC_BO_CHAM.md` §8.2), ⛔ khong chinh sau khi thay so.
MUC_KHONG_DAT = frozenset(("nang", "nghiem_trong"))

#: Gia tri tho model tra ve -> muc chuan hoa. Nhan ca tieng Anh cua MQM.
_MUC_THO = {
    "nhe": "nhe", "minor": "nhe", "nho": "nhe",
    "nang": "nang", "major": "nang", "lon": "nang",
    "nghiem_trong": "nghiem_trong", "critical": "nghiem_trong",
    "nghiem trong": "nghiem_trong",
}

#: Phan loai MQM ta hoi. ⛔ Khong bia them loai: mot loai khong co trong bang
#: nay se bi ghi thanh `khac`, va mot loai `khac` tran ngap la tin hieu rang
#: loi nhac dang hoi mot cau model khong tra loi duoc.
LOAI_LOI = ("lat_nghia", "sai_thuc_the", "bo_sot", "them", "khong_dich",
            "dien_dat", "khac")


def loi_nhac_ngu_nghia(lo: list[dict], ngon_ngu_dich: str = "vi") -> list[dict]:
    """Hoi model LIET KE LOI kem MUC NGHIEM TRONG — ⛔ khong hoi dung/sai.

    🔴 **Ban V1 hoi mot cau NHI PHAN (`dat: true/false`), va do la sai thiet ke.**

       Do 24/09 tren 100 cap FLORES-200 zh->vi **do NGUOI dich**: bo cham gan
       **45 %** la "dich sai" cho ban dich chuyen nghiep, trong khi luot that
       cua ta bi gan 46 % — tuc no khong phan biet duoc ban dich cua ta voi mot
       ban hoan hao (`B2_XAC_THUC_BO_CHAM.md`).

       Doc `ly_do` cua 122 luot bao dong gia: gan het la loi **nhe** theo MQM —
       mat sac thai, thieu mot bo ngu, them mot chu, thay ten rieng bang dai tu.
       ⛔ Loi nhac V1 **khong co o de noi "nhe"**: no chi co `false`. Nen moi
       nhan xet tinh te deu roi xuong cung mot o voi "lat nghia".

    ⭐ **Giao thuc: GEMBA-MQM** (Kocmi & Federmann, WMT 2023, arXiv 2310.13988),
       ho voi AutoMQM (arXiv 2308.07286) va xCOMET (arXiv 2310.10482). Ca ba deu
       doi model **liet ke tung loi** kem **phan loai** + **muc nghiem trong** +
       **doan trich**, roi tinh diem tu do (GEMBA: critical 25 / major 5 /
       minor 1, chan 5 loi) — nen nam loi `minor` van cham 5/25, tuc **van tot**.

    ⛔ **Lay DAC TA, khong lay loi van.** `MicrosoftTranslator/GEMBA` la
       **CC BY-SA 4.0** — ShareAlike phu ca ma (`README.md` §License: *"GEMBA
       code and data"*; khong co tep `LICENSE` tran, chi `LICENSE.md`). Thang
       muc MQM thi la **chuan cong khai**, muon duoc. Nen ba dinh nghia muc duoi
       day viet bang loi cua ta, neo vao **hau qua cho nguoi xem**.

    ⛔ **Khong hoi `do_tin` nua.** arXiv 2603.25052 do duoc rang khi model **vua
       lap luan vua tu khai do tin**, chinh viec lap luan **pha** tin hieu do tin
       va lam lech hieu chinh **nang them** — ma V1 doi dung hai thu do trong
       mot phan hoi. Cong 2605.12446 (*"high certainty even when incorrect"*) va
       so cua chinh ta: **98,4 %** bao dong gia co `do_tin >= 0,70`. Truong do
       khong chi vo dung ma **gay hai**. ⛔ Dung them lai "cho chac".

    ⛔ Hoi theo LO nhung tra ve theo MA — cung ly do nhu pha 14: mot lo 10 cau
       tra ve 9 ma ghep theo vi tri se lam moi cau sau do lech mot bac, va tai
       lieu van hop le.
    """
    from . import ngon_ngu
    t = ngon_ngu.cum(ngon_ngu_dich)["tieng"]
    he_thong = (
        f"Ban soat ban long tieng {t}. Voi moi cap (cau goc, cau {t}), hay "
        "LIET KE cac loi dich, moi loi mot muc nghiem trong.\n"
        "Ba muc, theo HAU QUA cho nguoi xem clip:\n"
        "- `nghiem_trong`: nguoi xem hieu SAI su viec.\n"
        "- `nang`: pha mach, nhung van hieu duoc dieu cau muon noi.\n"
        "- `nhe`: la loi that, nhung KHONG can tro hieu (sac thai, mot bo ngu "
        "phu, cach dien dat).\n"
        # 🔴 **San muc cho SAI THUC THE — do 24/09, va no la mot phep do chu
        #    khong phai mot linh cam.** Ban V2 (phan muc, chua co ba dong nay)
        #    tut do nhay `sai_thuc_the` tu 100 % xuong **40 %** tren 15 cap da
        #    lam hong co chu y. Soi ra: **9/9** ca bi bo sot deu la model **CO
        #    THAY** loi va **CO** goi dung ten `sai_thuc_the` — roi cham `nhe`.
        #    ⇒ Khong phai loi phat hien, la loi XEP MUC.
        #
        # ⭐ Neo vao hau qua, dung khuon ba muc o tren: mot con so hay mot cai
        #    ten sai khong lam cau kho hieu — no lam nguoi xem **tin chac mot
        #    su viec khong co that**, tuc nang hon han mot cho vung ve.
        "Rieng SO, TEN RIENG, DON VI, NGAY THANG bi doi: nguoi xem se tin mot "
        "su viec KHONG co that, nen it nhat la `nang` — ⛔ khong bao gio `nhe`.\n"
        f"Loai loi: {', '.join(LOAI_LOI)}.\n"
        "Quy tac:\n"
        "- `doan` BAT BUOC: trich NGUYEN VAN doan bi loi, lay tu cau goc hoac "
        f"cau {t}. Loi khong trich duoc doan se bi bo.\n"
        "- Cach dien dat khac, dao trat tu, rut gon ma giu y: KHONG phai loi.\n"
        "- Khong tim thay loi nao thi tra danh sach rong.\n"
        'Tra ve DUY NHAT: {"doan": {"<ma>": {"loi": [{"loai": "lat_nghia", '
        '"muc": "nang", "doan": "...", "ly_do": "..."}]}}}')
    nguoi_dung = json.dumps({"doan": [
        {"ma": str(d.get("ma") or ""),
         "goc": str(d.get("goc") or "")[:600],
         "tieng_viet": str(d.get("chu") or "")[:600]}
        for d in lo]}, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": he_thong},
            {"role": "user", "content": nguoi_dung}]


def _chuan(s) -> str:
    """Gop khoang trang + thuong hoa, de so khop doan trich.

    ⚠️ Nhan gia tri THO tu model (co the `None`, so, dict) — nen khong ghim kieu
       `str`: mot phan hoi lech kieu phai ra chuoi rong roi bi loc, ⛔ khong duoc
       nem giua mot vong lap dang doc phan quyet cua ca lo.
    """
    return " ".join(str(s if s is not None else "").split()).casefold()


def _muc(x) -> str:
    """Gia tri tho -> mot muc trong `MUC`. Khong nhan dien duoc -> `nhe`.

    ⭐ Mac dinh `nhe`, ⛔ khong phai `nang`: mot muc khong doc duoc la mot dieu
       ta KHONG biet, va mac dinh phai la cai **khong tieu tien**. Mac dinh
       `nang` se bien moi lan model go sai mot chu thanh mot lan dich lai co
       tra tien — dung hinh dang loi ma ban V1 mac phai.
    """
    return _MUC_THO.get(_chuan(x).replace(" ", "_"), "nhe")


def _loc_loi(tho, goc: str, dich: str) -> list[dict]:
    """Cac loi CO TRICH DOAN that. ⛔ Loi khong trich duoc doan bi LOAI.

    🔴 **Loc bang MAY, khong nho loi nhac "hay chinh xac".** GEMBA-MQM va
       GEMBA-ESA deu bat model chi ra doan loi; do la thu ghim loi bia.

    ⚠️ **Nhan doan o CA HAI phia.** Loi *them/dich sai* trich doan o **ban
       dich**, con loi *bo sot* trich doan o **cau nguon** — dung nhu vi du cua
       GEMBA (`accuracy/omission - "the account holder"` la doan NGUON). Chi so
       voi ban dich se loai sach loi bo sot, tuc doi mot thuoc qua tay lay mot
       thuoc mu o dung loai MetricX von manh (`L_DICH.md` §3).
    """
    hai_phia = _chuan(goc) + "\n" + _chuan(dich)
    ra = []
    for e in (tho if isinstance(tho, list) else []):
        if not isinstance(e, dict):
            continue
        doan = str(e.get("doan") or "")[:200]
        if not doan.strip() or _chuan(doan) not in hai_phia:
            continue
        loai = _chuan(e.get("loai")).replace(" ", "_")
        ra.append({
            "loai": loai if loai in LOAI_LOI else "khac",
            "muc": _muc(e.get("muc")),
            "doan": doan,
            "ly_do": str(e.get("ly_do") or "")[:300],
        })
    return ra


def _muc_nang_nhat(loi: list[dict]) -> str:
    """Muc nang nhat trong danh sach, hoac `""` khi khong co loi nao."""
    co = [e["muc"] for e in loi if e.get("muc") in MUC]
    return max(co, key=MUC.index) if co else ""


def doc_ngu_nghia(goi: dict, ma_da_gui: set[str],
                  van_ban: dict[str, tuple[str, str]]) -> list[dict]:
    """`[{ma, dat, muc, loi, ly_do}]` — chi cho nhung ma DA GUI.

    🔑 **`dat` duoc TINH RA tu muc, khong phai do model phan.** Bang anh xa
       (`B2_XAC_THUC_BO_CHAM.md` §8.2, viet TRUOC khi do):

           nghiem_trong -> dat=false     can tro hieu
           nang         -> dat=false     pha mach, van hieu duoc
           nhe          -> dat=TRUE      la loi that, nhung khong can tro hieu

    ⭐ **Loi `nhe` van duoc GHI LAI trong `loi`, ⛔ khong vut di.** Vut chung la
       dung lai dung bay *"hai trang thai gop thanh mot gia tri"*: *"khong co
       loi nao"* va *"chi co loi nhe"* lai roi chung mot o, va ta mat dung kha
       nang phan biet ma ban sua nay sinh ra de co. Doc `muc == ""` de biet
       "sach", ⛔ dung doc `dat == True`.

    ⚠️ `van_ban` la `{ma: (cau_goc, cau_dich)}` — BAT BUOC, vi khong co no thi
       phep loc doan trich khong chay duoc, va mot phep loc khong chay am tham
       se tra ve y NGUYEN so bao dong gia cu trong khi bao cao noi da loc.

    ⭐ Thieu mot ma thi doan do duoc coi la **DAT**, khong phai hong: mot cau hoi
       khong duoc tra loi la mot cau hoi khong duoc tra loi. Coi im lang la "co
       loi" se bien moi lan model tra thieu thanh mot lan sua tra tien.
    """
    tho = (goi or {}).get("doan")
    if not isinstance(tho, dict):
        raise QcAiError(_t('Model không trả về bảng phán đoán.'))
    ra = []
    for ma in sorted(ma_da_gui):
        v = tho.get(ma)
        if not isinstance(v, dict):
            continue
        goc, dich = (van_ban or {}).get(ma, ("", ""))
        loi = _loc_loi(v.get("loi"), goc, dich)
        muc = _muc_nang_nhat(loi)
        nang = [e for e in loi if e["muc"] in MUC_KHONG_DAT]
        ra.append({
            "ma": ma,
            "dat": not nang,
            "muc": muc,
            "loi": loi,
            # `ly_do` giu lai cho bao cao van hanh va cho `sua_chua`: gop ly do
            # cua CAC LOI da sinh ra phan quyet, khong gop ca loi `nhe`.
            "ly_do": " · ".join(
                f"[{e['loai']}] {e['doan']}: {e['ly_do']}".strip(": ")
                for e in nang)[:300],
        })
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  2. QC hinh — chi hoi o CHO NOI
# ══════════════════════════════════════════════════════════════════════════════

def moc_cho_noi(ban_do) -> list[float]:
    """Cac moc (tren truc BIEN TAP) noi hai canh khong lien nhau.

    🔑 Chi hoi VLM o **cho noi**, khong hoi khap phim. Mot canh khong bi dong toi
       thi khong co gi de hoi ve no; hoi khap phim la tra tien de nghe model xac
       nhan rang phan khong bi cham van nguyen ven.

    ⚠️ Truc BIEN TAP, khong phai truc BAN RA. Hai truc chi trung khi `toc_do`
       bang 1; `cac_cho_noi` lam not phep chia. Xem `bien_tap.moc_ban_ra`.
    """
    ra, truoc = [], 0.0
    for b, k in getattr(ban_do, "giu", ()):
        if truoc > 0:
            ra.append(round(truoc, 3))
        truoc += float(k) - float(b)
    return ra


def cac_cho_noi(ban_do, *, chi_muc=None, cac_ma_cat=(), toc_do: float = 1.0,
                lech_s: float = LECH_KHUNG_GIAY) -> list[dict]:
    """Mo ta DAY DU tung cho noi: moc tren BAN RA, hai moc khung, va canh bi bo.

    ⭐ Ba thu nay phai di chung mot cho, khong phai ba phep tinh o ba noi:

        `moc_ra`    giay tren tep DA RENDER — cho de rut khung, va cho de
                    nguoi doc bao cao tua toi kiem lai bang mat
        `khung_s`   hai moc rut khung, mot ngay truoc mot ngay sau cho noi
        `ma_cat`    ma cac canh bi BO tai chinh cho noi do

    🔴 **`ma_cat` la thu bien mot phan quyet thanh mot viec SUA.** Mot cho noi
       hong o giay 74 cua ban ra khong sua duoc: khong giai doan nao nhan "giay
       74" lam don vi. Cai sua duoc la *"canh_0011 va canh_0012 bi bo o day —
       xem lai"*, va `edit_plan` nhan dung don vi do. Khong co phep doi nguoc
       nay thi vong sua chi con mot lua chon: chay lai ca chuoi.

    ⛔ Doi NGUOC tu khoang bi cat tren truc NGUON, khong doan tu ma canh. Cho
       noi thu `j` nam giua `giu[j-1]` va `giu[j]`, nen khoang bi bo la
       `(giu[j-1][1], giu[j][0])` — mot su that cua ban do, khong phai mot phep
       do so thu tu canh.

    ⚠️ `ma_cat` co the RONG, va do khong phai loi: `BanDoThoiGian.tu_khoang` gop
       cac khoang lien nhau, nhung mot chi muc canh khong duoc truyen vao
       (`chi_muc=None`) thi khong ai tra loi duoc canh nao nam trong khoang do.
       Khi do phan quyet van duoc GHI — chi khong sinh viec sua duoc. Bao cao
       noi ro bang `ma_cat: []`.
    """
    td = float(toc_do) if float(toc_do or 0.0) > 0 else 1.0
    giu = [(float(b), float(k)) for b, k in (getattr(ban_do, "giu", ()) or ())]
    canh = list(getattr(chi_muc, "canh", ()) or ()) if chi_muc is not None else []
    bo = set(str(m) for m in (cac_ma_cat or ()))

    ra: list[dict] = []
    truoc = 0.0
    for j in range(len(giu)):
        b, k = giu[j]
        if j > 0:
            ke_truoc = giu[j - 1][1]
            moc_bt = round(truoc, 3)
            moc_ra = round(moc_bt / td, 3)
            # ⚠️ Khung lay o `moc_ra ± lech`, KHONG duoi 0 va (nguoi goi chan)
            #    khong qua thoi luong ban ra. Hai moc trung nhau la mot cau hoi
            #    ve mot chuyen tiep hoi bang MOT buc anh — `KHUNG_MOI_CHO_NOI`
            #    ghi ro vi sao phai la hai.
            ra.append({
                "moc_ra": moc_ra,
                "moc_bien_tap": moc_bt,
                "khung_s": [round(max(0.0, moc_ra - float(lech_s)), 3),
                            round(moc_ra + float(lech_s), 3)],
                "cat_nguon": [round(ke_truoc, 3), round(b, 3)],
                "ma_cat": sorted(
                    str(c.ma) for c in canh
                    if str(c.ma) in bo
                    and float(c.ket) > ke_truoc + 1e-6
                    and float(c.bat) < b - 1e-6),
            })
        truoc += k - b
    return ra


#: Gia tri tho cua `dat` -> `True`. ⛔ Chi nhung gia tri NHAN DIEN duoc; moi thu
#: khac ra `None`, tuc `QcAiError`. Chuan hoa nhan dien, khong doan.
_DAT_DUNG = frozenset((
    "true", "dat", "co", "lien_mach", "dung", "ok", "yes", "y", "1"))
_DAT_SAI = frozenset((
    "false", "khong_dat", "khong", "dut_mach", "sai", "no", "n", "0"))


def chuan_dat(gt):
    """Gia tri `dat` tho -> `True` / `False` / `None` (khong nhan dien duoc).

    🔴 **Bai hoc do duoc cua lan `fix-toc-do` (R-05, 23/09), ap cho truong nay.**

       8/18 luot `doc_canh` hong deu la phan hoi HTTP THANH CONG co hinh dang
       sai, va nguyen nhan lon nhat la model tra loi bang **tieng Viet that**
       (`"giữ"`) trong khi bang ma cua ta la ASCII khong dau. Truong `dat` o
       day mang dung rui ro do o dang boolean: `"đạt"`, `"có"`, `"true"` (chuoi
       thay vi boolean), `1`.

    ⭐ Nen phep doc di qua **dung** ham chuan hoa cua duong kia
       (`hieu_canh.chuan_ma` — bo dau NFD + `đ`→`d`), khong phai mot ban sao
       thu hai. Mot ban sao se lech, va nhanh lech la nhanh it duoc chay nhat.

    ⛔ Va no khong nuot rac: mot gia tri la (`"co le"`, `"0.5"`) ra `None`, tuc
       nguoi goi nem `QcAiError`. Mot phan doan khong doc duoc phai lo ra la mot
       phan doan khong doc duoc — mac dinh no ve `True` la bien mot cau hoi
       khong duoc tra loi thanh mot loi khai rang ban ra lanh lan.
    """
    from . import hieu_canh

    if isinstance(gt, bool):
        return gt
    if isinstance(gt, (int, float)):
        return bool(gt) if float(gt) in (0.0, 1.0) else None
    s = hieu_canh.chuan_ma(gt)
    if s in _DAT_DUNG:
        return True
    if s in _DAT_SAI:
        return False
    return None


def loi_nhac_hinh(khung_b64: list[str], *, moc_giay: float) -> list[dict]:
    """Hoi VLM: hai khung nay noi vao nhau co dut mach khong.

    🔴 **Loi nhac nay dung KHUNG JSON, va do la mot phep sua co so do dung sau.**

       Lan `fix-toc-do` do 18 canh cua phim nghiem thu voi loi nhac `doc_canh`
       ban cu — loi nhac DUY NHAT cua ASV ke ten khoa bang van xuoi thay vi dua
       mot khung JSON — va no la loi nhac DUY NHAT bi tra ve sai hinh: 2/18 tra
       ve mot MANG doi tuong, 1/18 boc trong `{"objects": [...]}`, 5/18 tra ma
       co dau tieng Viet. **8/18 hong vi LOI NHAC, khong phai vi model.**

    ⇒ Ham nay ra doi SAU phep do do, nen no mang san ca ba ban va: khung JSON
      tuong minh · cam mang · cam boc them lop. Khong viet lai bai hoc do bang
      mot loi nhac moi de roi do lai tu dau.

    ⚠️ Anh phai duoc GIOI THIEU trong phan van ban ("anh thu nhat... anh thu
       hai..."), khong chi dinh kem: cau hoi la ve mot CHUYEN TIEP, va model
       khong tra loi dung neu no khong biet anh nao truoc anh nao sau.
    """
    if not khung_b64:
        raise QcAiError(_t('Không có khung hình nào để hỏi.'))
    he_thong = (
        "Ban dang soat mot cho NOI giua hai canh trong mot ban dung video.\n"
        "Anh THU NHAT la khung hinh ngay TRUOC cho noi; anh THU HAI la khung "
        "hinh ngay SAU cho noi.\n"
        "Cau hoi: cho noi nay co lam DUT MACH NHIN mot cach ro rang khong?\n"
        "Quy tac:\n"
        "- Doi canh la chuyen binh thuong trong dung phim. `dat=false` CHI khi "
        "cho noi gay kho hieu ro rang: cat giua mot dong tac dang dien ra, mot "
        "nguoi hoac vat bien mat giua chung, hoac hai khung ro rang la CUNG mot "
        "canh bi cat mat mot khuc (nhay hinh).\n"
        "- Hai khung khac han nhau (khac boi canh, khac goc may, khac chu the) "
        "la mot cat DUNG => `dat=true`.\n"
        "- `do_tin` la do chac chan cua CHINH BAN, so trong [0,1].\n"
        "- `ly_do` bat buoc khi `dat=false`, va phai ta thu BAN NHIN THAY o hai "
        "khung, khong phai mot nhan xet chung chung.\n"
        # 🔴 KHUNG JSON — xem docstring.
        "Tra ve DUY NHAT mot doi tuong JSON, DUNG khung nay "
        "(mot doi tuong, KHONG phai mang, KHONG boc them lop nao):\n"
        '{"dat": true, "do_tin": 0.0, "ly_do": "..."}\n'
        "`dat` la true hoac false kieu JSON (lien mach = true, dut mach = "
        "false) — khong viet thanh chu, khong them dau tieng Viet.\n"
        "Khong them van ban nao ngoai JSON.")
    noi_dung = [{"type": "text",
                 "text": f"cho noi o giay {float(moc_giay):.2f} cua ban ra"}]
    for b64 in khung_b64:
        noi_dung.append({"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    return [{"role": "system", "content": he_thong},
            {"role": "user", "content": noi_dung}]


def doc_hinh(kq: dict, *, ma_canh: str = "", moc_giay: float,
             ma_cat=(), so_khung: int = 0) -> dict:
    """KET QUA cua `ai.goi` -> mot phan quyet cho noi. Nem `QcAiError` neu sai.

    🔴 **Tham so la CA KET QUA, khong phai `kq["noi_dung"]`.** Boc `noi_dung` ra
       bang tay vut mat `finish_reason` va `suy_nghi` — tuc vut mat thu duy nhat
       phan biet *"model tra sai luoc do"* voi *"model het tran token giua khoi
       suy nghi"*. Ban truoc cua ham nay nhan `goi: dict` va bat nguoi goi tu
       boc; `test_434` chot bang AST rang khong giai doan nao con lam vay.

    ⛔ **`dat` thieu hoac khong nhan dien duoc thi NEM, khong mac dinh `True`.**
       Ban truoc viet `bool(goi.get("dat", True))`: mot phan hoi thieu truong
       doc ra thanh "cho noi nay DAT". Im lang cua model khong phai mot loi khai
       rang ban ra lanh lan. `ai.QC_HINH.truong_bat_buoc` da chan mot nua (thieu
       han khoa), ham nay chan not nua kia (khoa co, gia tri la).
    """
    from . import ai

    goc = ai.doc_ket_qua(kq, ai.QC_HINH)
    dat = chuan_dat(goc.get("dat"))
    if dat is None:
        raise QcAiError(
            f"qc_hinh giay {float(moc_giay):.2f}: `dat` khong nhan dien duoc "
            f"({str(goc.get('dat'))[:40]!r})")
    ds = sorted(str(m) for m in (ma_cat or ()) if str(m))
    return {
        "ma_canh": str(ma_canh or (ds[0] if ds else "")),
        "ma_cat": ds,
        "so_khung": int(so_khung),
        "moc_giay": round(float(moc_giay), 3),
        "dat": bool(dat),
        "ly_do": str(goc.get("ly_do") or "")[:300],
        "do_tin": _do_tin(goc.get("do_tin")),
    }


# 3. QC giong noi DA CHUYEN sang lan `gpu` (22/09): ASR + WER/CER that o
#    `giai_doan_qc_do_luong` + `apps/asv_gpu/do_luong/giong.py`. Cong thuc
#    Dice tu che (`sua_chua.khop_van_ban`) va bo ghep cua no da xoa.

# ══════════════════════════════════════════════════════════════════════════════

def _do_tin(x) -> float:
    """Do tin ve `[0; 1]`. Thieu hoac hong -> 0, tuc **khong dang tin**.

    ⛔ Mac dinh phai la 0, khong phai 1: mot model khong noi no chac chan bao
       nhieu thi ta khong duoc tu gan cho no su chac chan. Mac dinh 1 se bien mot
       phan hoi thieu truong thanh mot lenh sua co tra tien.
    """
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


def chia_lo(doan: list[dict], *, moi_lo: int | None = None) -> list[list[dict]]:
    n = max(1, int(moi_lo if moi_lo is not None else DOAN_MOI_LO))
    doan = list(doan or [])
    return [doan[i:i + n] for i in range(0, len(doan), n)]


# 🔴 **`tom_tat(qc_giong, qc_nghia, qc_hinh)` da XOA (23/09, M-02).**
#
#    No dem lai dung nhung con so ma `giai_doan_qc_ai.chay` tu dem, va no
#    **chua tung co nguoi goi** — khong o san pham, khong o phep kiem. Tuc mot
#    ban mo ta THU HAI cua cung mot bao cao, duoc phep lech khoi ban that ma
#    khong ai thay.
#
# ⛔ Va no mang `phien_ban_qc_ai` vao mot cho khong ai doc, trong khi cho DOC
#    no la van tay bao cao. Hai ban sao cua mot con so phien ban la cach chac
#    chan nhat de mot lan doi loi nhac khong toi duoc khach.
#
# ⇒ Giu MOT cho dem: `chay` dem, `bao_cao` mang, `tom_tat` cua giai doan di
#   thang vao `stage.outputs`. Day la lan thu nam kho nay go mot "nang luc
#   khong ai goi" (kiem toan pha 26); go luon thay vi de no doi nguoi goi dau
#   tien phat hien no lech.
