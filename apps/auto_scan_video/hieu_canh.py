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

#: 🔑 Phien ban PROMPT + LUOC DO cua loi nhac HO SO (`loi_nhac_ho_so`).
#:
#: 🔴 **26/09/2026 — `PHIEN_BAN_HIEU_CANH` DA BI XOA cung `van_tay_canh`.**
#:    Task 10 (`defba7b2`) thay VLM bang phep do TAT DINH o `edit_plan`, nen
#:    khong con diem chot theo CANH nao, tuc khong con van tay nao doc con so
#:    ay. Lich su cua no (3/2 bo "video tieng Viet"; 4/2 dua KHUNG JSON sau khi
#:    8/18 canh phim nghiem thu hong; 5/2 M-02 them `phan_hoi_qc`) nam o
#:    `docs/auto_scan_video_final/L_FIX_TOC_DO.md` va `L_QC_HINH.md`.
#:
#: ⚠️ `PHIEN_BAN_HO_SO` **chua co ai bam** — `ho_so_noi_dung` khong dua no vao
#:    van tay nao (do 26/09 bang `grep`). Ghi lai chu ⛔ khong xoa: no la hang
#:    "duong co, chua co xe" cua chinh loi nhac dang song, va cai gia cua viec
#:    thieu no da duoc mo ta ngay tren.
PHIEN_BAN_HO_SO = 2

#: Quyet dinh giu/bo ma VLM de xuat. ⚠️ **De xuat**, khong phai lenh: pha 12 moi
#: la noi quyet dinh, va no can biet do tin cay.
#:
#: 🔑 **VAN SONG sau 26/09**: `giai_doan_ban_bien_tap.BangChungCanh` dat
#:    `de_xuat` bang chinh hai ma nay (`hc.GIU`/`hc.BO`) tu phep do tat dinh, va
#:    `ban_bien_tap._quyet_dinh_mot_canh` doc chung. ⛔ Chi NGUON cua `de_xuat`
#:    doi tu model sang phep do — tap gia tri thi khong.
GIU = "giu"
BO = "bo"
KHONG_CHAC = "khong_chac"
DE_XUAT = (GIU, BO, KHONG_CHAC)


class HieuCanhError(ValueError):
    """Khong doc duoc canh, hoac ket qua sai hinh dang."""


@dataclass(frozen=True)
class HieuCanh:
    """Ket qua doc MOT canh. Moi truong deu la thu VLM tra ve, da kiem."""


    #: Xuất xứ của `do_tin` — xem `BangChungCanh.NGUON_BANG_CHUNG`.
    #: ⚠️ Lớp này hiện ⛔ KHÔNG có người dựng nào trong `apps/` (Task 22 xoá
    #:    `doc_hieu_canh`); trường này để bản khai đúng nếu đường VLM sống lại.
    NGUON_BANG_CHUNG = "do tin VLM (chu quan)"
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


def tu_dict(goi: dict) -> HieuCanh:
    """Doc lai mot `HieuCanh` da luu trong `AsvWorkItem.outputs`.

    🔑 Doi ngau cua `sang_dict`, va no ton tai vi checkpoint theo canh chi co
       nghia khi doc lai duoc: mot lan chay lai phai **dung lai** ket qua da tra
       tien, khong hoi model lan hai ve cung mot khung hinh.
    """
    g = dict(goi or {})
    return HieuCanh(
        ma_canh=str(g.get("ma_canh") or ""),
        loai=str(g.get("loai") or ""),
        chu_the=tuple(str(x) for x in (g.get("chu_the") or [])),
        hanh_dong=str(g.get("hanh_dong") or ""),
        cam_xuc=str(g.get("cam_xuc") or ""),
        quan_trong=float(g.get("quan_trong") or 0.0),
        de_xuat=str(g.get("de_xuat") or KHONG_CHAC),
        do_tin=float(g.get("do_tin") or 0.0),
        ly_do=str(g.get("ly_do") or ""),
        canh_bao=tuple(str(x) for x in (g.get("canh_bao") or [])))


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
#  Doc phan hoi — KIEM NGHIEM NGAT
# ══════════════════════════════════════════════════════════════════════════════

def chuan_ma(gt) -> str:
    """Mot gia tri tho cua model -> mot MA ASCII khong dau, hoac `""`.

    🔑 **Phan CHUAN HOA tach khoi phep doi chieu bang, vi no co nguoi dung thu
       hai** (`qc_ai.chuan_dat`, 23/09). Bo dau (NFD + `đ`→`d`), ha chu thuong,
       gop dau ngan cach ve `_`. Khong doi chieu bang nao — nguoi goi lam viec
       do, va vi vay ham nay khong bao gio "doan" ho.

    ⚠️ **26/09/2026 — nguoi dung THU NHAT (`chuan_de_xuat`) da bi xoa** cung
       `doc_hieu_canh` (Task 10: `edit_plan` ⛔ khong con goi VLM). Nguoi dung
       CON LAI la `qc_ai.chuan_dat`, va no van la nguoi duy nhat duoc phep bo
       dau — luat "khong ban sao thu hai" duoi day khong doi.

    ⛔ Khong duoc viet ban sao thu hai cua phep bo dau nay o cho khac. Do 23/09
       (`L_FIX_TOC_DO.md` R-05) cho thay 5/18 luot hong chi vi mot dau nga; hai
       ban sao cua phep chua ay se lech nhau, va nhanh lech la nhanh it duoc
       chay nhat.
    """
    import unicodedata

    s = unicodedata.normalize("NFD", str(gt or "")).strip().lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    # `đ` khong tach duoc bang NFD — mot ky tu rieng trong Unicode.
    s = s.replace("đ", "d").replace("Đ", "d")
    return "_".join(s.replace("-", " ").replace("_", " ").split())


def doc_ho_so(kq: dict) -> HoSoNoiDung:
    """KET QUA cua `ai.goi` -> `HoSoNoiDung`. Nem neu thieu truong bat buoc.

    🔴 **Tham so la CA KET QUA, khong phai `noi_dung`** — ban sua 09/09, ap cho
       ca hai bo doc cua tep nay hoi ay: boc `noi_dung` ra bang tay vut mat
       `finish_reason`/`suy_nghi`, tuc vut mat thu duy nhat phan biet "model tra
       sai luoc do" voi "model het tran token giua khoi suy nghi". Ham nay chua
       tung co nguoi goi nen no giu chu ky cu toi 23/09. (Bo doc kia,
       `doc_hieu_canh`, da bi xoa 26/09 — Task 10.)
       (`test_434::test_KHONG_giai_doan_nao_con_boc_noi_dung_ra_khoi_kq_bang_tay`
       chot dieu nay bang AST, va no da bat dung luc nguoi goi dau tien xuat hien.)
    """
    ra = ai.doc_ket_qua(kq, ai.HO_SO_NOI_DUNG)
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
#  Gop ho so
# ══════════════════════════════════════════════════════════════════════════════

def loi_nhac_ho_so(cac_canh, tom_tat_ban_ghi: str,
                   *, bang_chung: dict | None = None) -> list:
    """Loi nhac dung ho so tu bang chung canh + ban chep loi.

    ⭐ Gui **tom tat** cua tung canh, khong gui lai khung hinh: khung da duoc doc
       roi, va gui lai chung la tra tien lan hai cho cung mot buc anh.

    🔑 **`cac_canh` duoc phep RONG, va do la mot duong chay that chu khong phai
       mot truong hop bien.** Preset `localize_preserve_picture` khong doc canh
       nao (khong canh nao bi cat ⇒ khong co gi de hoi VLM), nhung no van can
       mot ho so de `AUTO_MATCH` chot giong. Khi do bang chung la `bang_chung`
       — so lieu tat dinh cua ban chep loi — cong chinh loi thoai.

    ⛔ `phong_cach` phai nam trong tu vung CATALOG. Truoc day loi nhac de trong
       mat do, va mot chu dung tieng Viet nhung khong co trong catalog (vi du
       "thuyet minh") lam `giong_mau.loc` tra ve rong — tuc ho so co ma van khong
       rang duoc giong. `ho_so_noi_dung.loc_dac_diem` con chan lan thu hai.
    """
    from apps.ltt_voice.giong_mau import NHAN_PHONG_CACH

    bang = [{"ma": c.ma_canh, "loai": c.loai, "hanh_dong": c.hanh_dong,
             "cam_xuc": c.cam_xuc, "quan_trong": round(c.quan_trong, 2)}
            for c in cac_canh]
    phong_cach = "|".join(sorted(NHAN_PHONG_CACH))
    dong_canh = (f"Cac canh: {json.dumps(bang, ensure_ascii=False)}\n"
                 if bang else "")
    dong_do = (f"So lieu do duoc: {json.dumps(bang_chung, ensure_ascii=False, sort_keys=True)}\n"
               if bang_chung else "")
    return [{
        "role": "user",
        "content": (
            "Duoi day la bang chung doc tu mot video.\n"
            f"{dong_canh}{dong_do}"
            f"Loi thoai (tom tat): {tom_tat_ban_ghi}\n\n"
            "Tra ve DUNG mot doi tuong JSON voi cac khoa: the_loai, giong_dieu, "
            "khan_gia, nhip, tom_tat, va dac_diem_giong la mot doi tuong co "
            f"gioi (nam|nu), vung (bac|trung|nam), phong_cach ({phong_cach}). "
            "Mat nao khong du can cu thi de chuoi rong, KHONG doan. "
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
