"""HIEU CANH (VLM) va HO SO NOI DUNG (LLM) — bang chung cho moi quyet dinh sau.

## Vi sao hai buoc chu khong mot

Doc CANH la mot cau hoi **cuc bo**: canh nay co gi, ai dang noi, co quan trong
khong. Dung HO SO la mot cau hoi **toan cuc**: ca video nay thuoc the loai gi,
nhip the nao, giong nao hop.

⛔ Hoi ca hai trong mot luot goi thi mot canh hong lam hong ca ho so, va mot ho
   so muon sua phai doc lai toan bo canh. Tach ra thi mot canh hong chi lam hong
   chinh no — va do la dieu `checkpoint per scene` cua pha nay doi.

## 🔑 Checkpoint theo CANH, khong theo giai doan

Moi canh la mot `AsvWorkItem` voi `item_key = ma canh`. Mot lan VLM hong o canh
thu 47 khong duoc bat 46 canh truoc chay lai — chung da tra tien roi.

`ADR-V4-002` D-V4-10 dung cho viec nay, va pha 05 dung bang do cho no.

## ⛔ Phan hoi sai luoc do KHONG phai mot artifact thanh cong

Yeu cau 5 cua pha 11, va no la mot phan biet dat gia: mot canh **da doc va tra
ve rac** khac han mot canh **chua doc**. Cai dau da ton tien va phai duoc ghi so
cai; cai sau thi chua. Nen `LuocDoSai` van di kem mot but toan `da_giao`.

## Ranh gioi chu so huu

Van tay cua moi item gom `run_id`, va `AsvWorkItem` co cot `owner_id` rieng. Hai
khach co cung video se co hai `run_id`, nen khong lan chay nao doc duoc cache cua
lan chay kia — bat bien do da co tu pha 05, va pha nay chi khong pha no.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from . import ai
from .canh import ChiMucCanh

log = logging.getLogger(__name__)

#: 🔑 Phien ban PROMPT + LUOC DO cua rieng pha nay, di vao van tay.
#:
#: ⛔ Thieu no thi doi mot cau prompt xong, cache van khop, va lan chay dung lai
#:    ket qua sinh boi prompt CU. `ai.PHIEN_BAN_PROMPT` la phien ban cua CUA
#:    GOI; day la phien ban cua NOI DUNG cau hoi — hai thu doi doc lap voi nhau.
PHIEN_BAN_HIEU_CANH = 1
PHIEN_BAN_HO_SO = 1

#: Toi da bao nhieu ky tu ban chep loi gui kem MOT canh.
#:
#: 🔴 Cua so thi giac do duoc **65.536 token** — mot nua ban van ban. Gui ca ban
#:    chep loi kem moi canh la cach chac chan nhat de cham tran do, va no cham
#:    theo cach te nhat: thanh cong o canh 1, 413 o canh 40, sau khi da tra tien
#:    cho 39 canh.
NGU_CANH_MOI_CANH = 1200

#: Quyet dinh giu/bo ma VLM de xuat. ⚠️ **De xuat**, khong phai lenh: pha 12 moi
#: la noi quyet dinh, va no can biet do tin cay.
GIU = "giu"
BO = "bo"
KHONG_CHAC = "khong_chac"
DE_XUAT = (GIU, BO, KHONG_CHAC)


class HieuCanhError(ValueError):
    """Khong doc duoc canh, hoac ket qua sai hinh dang."""


@dataclass(frozen=True)
class HieuCanh:
    """Ket qua doc MOT canh. Moi truong deu la thu VLM tra ve, da kiem."""

    ma_canh: str
    loai: str = ""
    chu_the: tuple[str, ...] = ()
    hanh_dong: str = ""
    cam_xuc: str = ""
    #: 0..1 — canh nay quan trong the nao voi mach truyen.
    quan_trong: float = 0.0
    de_xuat: str = KHONG_CHAC
    #: 0..1 — VLM tin ket luan cua no den dau.
    do_tin: float = 0.0
    ly_do: str = ""
    canh_bao: tuple[str, ...] = ()

    def sang_dict(self) -> dict:
        return {
            "ma_canh": self.ma_canh, "loai": self.loai,
            "chu_the": list(self.chu_the), "hanh_dong": self.hanh_dong,
            "cam_xuc": self.cam_xuc, "quan_trong": round(self.quan_trong, 3),
            "de_xuat": self.de_xuat, "do_tin": round(self.do_tin, 3),
            "ly_do": self.ly_do, "canh_bao": list(self.canh_bao),
        }


@dataclass(frozen=True)
class HoSoNoiDung:
    """Ho so cua CA video. Pha 12 dung no de chon preset; pha 09 de rang giong."""

    the_loai: str = ""
    giong_dieu: str = ""
    khan_gia: str = ""
    nhip: str = ""
    #: Dac diem giong mong muon — dung ba mat cua `ltt_voice.giong_mau`.
    dac_diem_giong: dict = field(default_factory=dict)
    tom_tat: str = ""

    def sang_dict(self) -> dict:
        return {
            "the_loai": self.the_loai, "giong_dieu": self.giong_dieu,
            "khan_gia": self.khan_gia, "nhip": self.nhip,
            "dac_diem_giong": dict(self.dac_diem_giong),
            "tom_tat": self.tom_tat,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Ngu canh gui kem — CO CHAN
# ══════════════════════════════════════════════════════════════════════════════

def ngu_canh_cho_canh(ban_ghi: dict, bat: float, ket: float,
                      *, toi_da: int = NGU_CANH_MOI_CANH) -> str:
    """Loi thoai nam TRONG canh, cat theo tran ky tu.

    ⭐ Chi lay doan chong lan voi canh, khong gui ca ban chep loi. Mot canh 4
       giay khong can biet phut thu 30 noi gi — va gui no la tra tien token cho
       mot thu model se bo qua.
    """
    ra = []
    for d in (ban_ghi or {}).get("doan") or []:
        try:
            b, k = float(d.get("bat", 0)), float(d.get("ket", 0))
        except (TypeError, ValueError):
            continue
        if k <= bat or b >= ket:
            continue
        ra.append(str(d.get("chu") or "").strip())
    van = " ".join(x for x in ra if x)
    if len(van) <= toi_da:
        return van
    # ⚠️ Cat o dau CAU gan nhat, khong cat giua tu: mot cau cut lam model doan
    #    tiep phan thieu, va no doan bang token cua khach.
    cat = van[:toi_da]
    dau = max(cat.rfind(". "), cat.rfind("! "), cat.rfind("? "))
    return (cat[:dau + 1] if dau > toi_da // 2 else cat).strip()


def loi_nhac_canh(ma_canh: str, ngu_canh: str, so_khung: int,
                  tin_hieu: dict | None = None) -> list:
    """Loi nhac cho MOT canh. ASV so huu prompt nay (pha 08 §ranh gioi)."""
    tin = json.dumps(tin_hieu or {}, ensure_ascii=False, sort_keys=True)
    return [{
        "role": "user",
        "content": (
            f"Doc canh {ma_canh} cua mot video tieng Viet. "
            f"Co {so_khung} khung hinh dai dien. "
            f"Tin hieu do duoc: {tin}. "
            f"Loi thoai trong canh: {ngu_canh or '(khong co loi thoai)'}\n\n"
            "Tra ve DUNG mot doi tuong JSON voi cac khoa: "
            "loai, chu_the (mang), hanh_dong, cam_xuc, quan_trong (0..1), "
            "de_xuat (giu|bo|khong_chac), do_tin (0..1), ly_do, "
            "canh_bao (mang). Khong them van ban nao ngoai JSON."),
    }]


# ══════════════════════════════════════════════════════════════════════════════
#  Doc phan hoi — KIEM NGHIEM NGAT
# ══════════════════════════════════════════════════════════════════════════════

def _so_trong_khoang(gt, ten: str) -> float:
    try:
        x = float(gt)
    except (TypeError, ValueError) as exc:
        raise HieuCanhError(f"{ten} khong phai so: {gt!r}") from exc
    if not (0.0 <= x <= 1.0):
        raise HieuCanhError(f"{ten} phai trong [0,1], nhan {x}")
    return x


def doc_hieu_canh(noi_dung: str, ma_canh: str) -> HieuCanh:
    """Phan hoi VLM -> `HieuCanh`. Nem `HieuCanhError` neu sai luoc do.

    ⛔ **Mot phan hoi sai luoc do khong phai mot artifact thanh cong** (yeu cau 5).
       Mot truong thieu thanh `None` di tiep se lo ra o pha 12 duoi dang "khong
       canh nao duoc giu" — mot thong bao khong lien quan gi den nguyen nhan.
    """
    ra = ai.doc_json(noi_dung, ai.DOC_CANH)

    # `ai.doc_json` da chot `canh` la truong bat buoc cua `DOC_CANH`; o day ta
    # doc luoc do CHI TIET cua rieng pha 11.
    goc = ra.get("canh") if isinstance(ra.get("canh"), dict) else ra

    de_xuat = str(goc.get("de_xuat") or "").strip().lower()
    if de_xuat not in DE_XUAT:
        raise HieuCanhError(
            f"{ma_canh}: de_xuat phai la mot trong {DE_XUAT}, nhan {de_xuat!r}")

    chu_the = goc.get("chu_the") or []
    if not isinstance(chu_the, list):
        raise HieuCanhError(f"{ma_canh}: chu_the phai la mang")

    canh_bao = goc.get("canh_bao") or []
    if not isinstance(canh_bao, list):
        raise HieuCanhError(f"{ma_canh}: canh_bao phai la mang")

    return HieuCanh(
        ma_canh=ma_canh,
        loai=str(goc.get("loai") or "")[:64],
        chu_the=tuple(str(x)[:64] for x in chu_the[:12]),
        hanh_dong=str(goc.get("hanh_dong") or "")[:300],
        cam_xuc=str(goc.get("cam_xuc") or "")[:64],
        quan_trong=_so_trong_khoang(goc.get("quan_trong", 0), "quan_trong"),
        de_xuat=de_xuat,
        do_tin=_so_trong_khoang(goc.get("do_tin", 0), "do_tin"),
        ly_do=str(goc.get("ly_do") or "")[:500],
        canh_bao=tuple(str(x)[:120] for x in canh_bao[:8]))


def doc_ho_so(noi_dung: str) -> HoSoNoiDung:
    """Phan hoi LLM -> `HoSoNoiDung`. Nem neu thieu truong bat buoc."""
    ra = ai.doc_json(noi_dung, ai.HO_SO_NOI_DUNG)
    dd = ra.get("dac_diem_giong") or {}
    if not isinstance(dd, dict):
        raise HieuCanhError("dac_diem_giong phai la doi tuong")

    # ⚠️ Loc ve DUNG ba mat cua `ltt_voice.giong_mau`. Mot mat thu tu se cho ra
    #    mot bo loc khong bao gio khop — cung ly do voi `rang_giong` pha 09.
    return HoSoNoiDung(
        the_loai=str(ra.get("the_loai") or "")[:64],
        giong_dieu=str(ra.get("giong_dieu") or "")[:64],
        khan_gia=str(ra.get("khan_gia") or "")[:64],
        nhip=str(ra.get("nhip") or "")[:32],
        dac_diem_giong={k: str(dd.get(k) or "")[:32]
                        for k in ("gioi", "vung", "phong_cach")
                        if dd.get(k)},
        tom_tat=str(ra.get("tom_tat") or "")[:1000])


# ══════════════════════════════════════════════════════════════════════════════
#  Van tay
# ══════════════════════════════════════════════════════════════════════════════

def van_tay_canh(ma_canh: str, ngu_canh: str, so_khung: int,
                 nguong_canh: float) -> str:
    """Van tay cua MOT canh. Gom prompt/luoc do, nen doi prompt = mat cache."""
    import hashlib

    kh = json.dumps({
        "v_prompt": PHIEN_BAN_HIEU_CANH,
        "v_cua_goi": ai.PHIEN_BAN_PROMPT,
        "v_luoc_do": ai.PHIEN_BAN_LUOC_DO,
        "ma": ma_canh, "so_khung": so_khung,
        "nguong": nguong_canh,
        "ngu_canh": ngu_canh,
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(kh.encode("utf-8")).hexdigest()[:32]


# ══════════════════════════════════════════════════════════════════════════════
#  Gop ho so
# ══════════════════════════════════════════════════════════════════════════════

def loi_nhac_ho_so(cac_canh, tom_tat_ban_ghi: str) -> list:
    """Loi nhac dung ho so tu bang chung canh + ban chep loi.

    ⭐ Gui **tom tat** cua tung canh, khong gui lai khung hinh: khung da duoc doc
       roi, va gui lai chung la tra tien lan hai cho cung mot buc anh.
    """
    bang = [{"ma": c.ma_canh, "loai": c.loai, "hanh_dong": c.hanh_dong,
             "cam_xuc": c.cam_xuc, "quan_trong": round(c.quan_trong, 2)}
            for c in cac_canh]
    return [{
        "role": "user",
        "content": (
            "Duoi day la bang chung doc tu mot video tieng Viet.\n"
            f"Cac canh: {json.dumps(bang, ensure_ascii=False)}\n"
            f"Loi thoai (tom tat): {tom_tat_ban_ghi}\n\n"
            "Tra ve DUNG mot doi tuong JSON voi cac khoa: the_loai, giong_dieu, "
            "khan_gia, nhip, tom_tat, va dac_diem_giong la mot doi tuong co "
            "gioi (nam|nu), vung (bac|trung|nam), phong_cach. "
            "Khong them van ban nao ngoai JSON."),
    }]


def tom_tat_chi_muc(ci: ChiMucCanh, cac_canh) -> dict:
    """So lieu de nguoi doc bao cao hieu vi sao ho so lai la the nay."""
    theo_de_xuat: dict = {}
    for c in cac_canh:
        theo_de_xuat[c.de_xuat] = theo_de_xuat.get(c.de_xuat, 0) + 1
    return {
        "so_canh_chi_muc": len(ci.canh),
        "so_canh_da_doc": len(list(cac_canh)),
        "theo_de_xuat": theo_de_xuat,
        "do_tin_trung_binh": (
            round(sum(c.do_tin for c in cac_canh) / len(list(cac_canh)), 3)
            if cac_canh else 0.0),
    }
