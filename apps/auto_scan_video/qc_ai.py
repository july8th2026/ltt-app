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
PHIEN_BAN_QC_AI = 1

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
    """Cac moc (tren truc BAN RA) noi hai canh khong lien nhau.

    🔑 Chi hoi VLM o **cho noi**, khong hoi khap phim. Mot canh khong bi dong toi
       thi khong co gi de hoi ve no; hoi khap phim la tra tien de nghe model xac
       nhan rang phan khong bi cham van nguyen ven.
    """
    ra, truoc = [], 0.0
    for b, k in getattr(ban_do, "giu", ()):
        if truoc > 0:
            ra.append(round(truoc, 3))
        truoc += float(k) - float(b)
    return ra


def loi_nhac_hinh(khung_b64: list[str], *, moc_giay: float) -> list[dict]:
    """Hoi VLM: hai khung nay noi vao nhau co dut mach khong."""
    if not khung_b64:
        raise QcAiError(_t('Không có khung hình nào để hỏi.'))
    he_thong = (
        "Ban dang soat mot cho NOI giua hai canh trong mot ban dung. Cac anh la "
        "khung hinh ngay TRUOC va ngay SAU cho noi.\n"
        "Cau hoi: cho noi nay co lam **dut mach nhin** mot cach ro rang khong?\n"
        "Quy tac:\n"
        "- Doi canh la binh thuong trong dung phim; `dat=false` CHI khi cho noi "
        "gay kho hieu ro rang (cat giua mot dong tac, mot nguoi bien mat giua cau).\n"
        "- `do_tin` la do chac chan cua CHINH BAN, tu 0 den 1.\n"
        'Tra ve DUY NHAT: {"dat": true, "do_tin": 0.9, "ly_do": ""}')
    noi_dung = [{"type": "text",
                 "text": f"cho noi o giay {float(moc_giay):.2f} cua ban ra"}]
    for b64 in khung_b64:
        noi_dung.append({"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    return [{"role": "system", "content": he_thong},
            {"role": "user", "content": noi_dung}]


def doc_hinh(goi: dict, *, ma_canh: str, moc_giay: float) -> dict:
    if not isinstance(goi, dict):
        raise QcAiError(_t('Model không trả về phán đoán hình.'))
    return {
        "ma_canh": str(ma_canh),
        "moc_giay": round(float(moc_giay), 3),
        "dat": bool(goi.get("dat", True)),
        "ly_do": str(goi.get("ly_do") or "")[:300],
        "do_tin": _do_tin(goi.get("do_tin")),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  3. QC giong noi — DO, khong phai phan doan
# ══════════════════════════════════════════════════════════════════════════════

def so_khop_doc(muc: list[dict], ban_ghi_doc: dict) -> list[dict]:
    """`[{ma, chu, doc_ra}]` — ghep van ban da viet voi thu ASR nghe duoc.

    ⭐ Day la mot phep **DO**, khong phai mot phan doan cua model: hai chuoi, mot
       ty le khop. Nen ket qua cua no co `do_tin = 1.0` — ta khong doan gi ca.

    ⛔ ASR o day chay tren chinh tieng ta vua sinh ra, nen no khong the "sai" theo
       kieu nghe nham mot giong la. Neu no van lech thi hoac may doc sai that,
       hoac van ban co thu ASR khong doc duoc (so, ten rieng) — va nguong
       `NGUONG_KHOP_DOC` duoc chon de chiu duoc truong hop thu hai.
    """
    doc = {str(d.get("ma") or ""): str(d.get("chu") or "")
           for d in (ban_ghi_doc.get("doan") or [])}
    return [{"ma": str(m.get("ma") or ""),
             "chu": str(m.get("chu") or ""),
             "doc_ra": doc.get(str(m.get("ma") or ""), "")}
            for m in (muc or [])]


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
