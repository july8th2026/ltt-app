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


class QcAiError(ValueError):
    """Phan hoi QC bang AI khong dung hop dong."""


# ══════════════════════════════════════════════════════════════════════════════
#  1. QC ngu nghia
# ══════════════════════════════════════════════════════════════════════════════

def loi_nhac_ngu_nghia(lo: list[dict], ngon_ngu_dich: str = "vi") -> list[dict]:
    """Hoi model: ban tieng Viet co giu dung y cua nguon khong.

    ⛔ Hoi theo LO nhung tra ve theo MA — cung ly do nhu pha 14: mot lo 10 cau
       tra ve 9 ma ghep theo vi tri se lam moi cau sau do lech mot bac, va tai
       lieu van hop le.
    """
    from . import ngon_ngu
    t = ngon_ngu.cum(ngon_ngu_dich)["tieng"]
    he_thong = (
        f"Ban la nguoi soat ban long tieng {t}. Voi moi cap (cau goc, cau "
        f"{t}), hay noi ban {t} co **giu dung y va thai do** cua cau "
        "goc khong.\n"
        "Quy tac:\n"
        "- `dat=false` CHI khi y nghia bi doi, mat, hoac them.\n"
        "- Cach dien dat khac, dao trat tu, hay rut gon ma giu y => `dat=true`.\n"
        "- `do_tin` la do chac chan cua CHINH BAN, tu 0 den 1.\n"
        "- `ly_do` chi bat buoc khi `dat=false`, va phai noi ro y nao bi lech.\n"
        'Tra ve DUY NHAT: {"doan": {"<ma>": {"dat": true, "do_tin": 0.9, '
        '"ly_do": ""}}}')
    nguoi_dung = json.dumps({"doan": [
        {"ma": str(d.get("ma") or ""),
         "goc": str(d.get("goc") or "")[:600],
         "tieng_viet": str(d.get("chu") or "")[:600]}
        for d in lo]}, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": he_thong},
            {"role": "user", "content": nguoi_dung}]


def doc_ngu_nghia(goi: dict, ma_da_gui: set[str]) -> list[dict]:
    """`[{ma, dat, ly_do, do_tin}]` — chi cho nhung ma DA GUI.

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
        ra.append({
            "ma": ma,
            "dat": bool(v.get("dat", True)),
            "ly_do": str(v.get("ly_do") or "")[:300],
            "do_tin": _do_tin(v.get("do_tin")),
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


def tom_tat(qc_giong: list, qc_nghia: list, qc_hinh: list) -> dict:
    return {
        "so_doan_do_giong": len(qc_giong or []),
        "so_doan_do_nghia": len(qc_nghia or []),
        "so_cho_noi_do_hinh": len(qc_hinh or []),
        "so_nghia_khong_dat": sum(1 for d in (qc_nghia or []) if not d.get("dat", True)),
        "so_hinh_khong_dat": sum(1 for d in (qc_hinh or []) if not d.get("dat", True)),
        "phien_ban_qc_ai": PHIEN_BAN_QC_AI,
    }
