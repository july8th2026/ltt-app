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
#: 3/2 (22/09): bo "video tieng Viet" khoi loi nhac — nguon la zh/en/vi, va
#: ngon ngu thoai da hien ngay trong loi thoai dua kem.
#: 4/2 (23/09): loi nhac dua KHUNG JSON (thay vi ke ten khoa) va noi ro `de_xuat`
#: la MA chep y nguyen. Do 18 canh phim nghiem thu voi loi nhac cu: 8/18 hong —
#: 5 vi `"giữ"` co dau, 2 vi tra ve MANG, 1 vi boc `{"objects": [...]}`.
#: 5/2 (23/09, M-02): loi nhac nhan them BANG CHUNG cua vong sua (`phan_hoi_qc`)
#: — QC hinh da nhin cho noi tren BAN RA va bao no dut mach. Khong co no thi
#: vong sua hoi lai y nguyen cau cu va nhan lai y nguyen cau tra loi cu (M-07).
PHIEN_BAN_HIEU_CANH = 5
PHIEN_BAN_HO_SO = 2

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
                  tin_hieu: dict | None = None,
                  khung: tuple[bytes, ...] = (),
                  *, phan_hoi_qc: str = "") -> list:
    """Loi nhac cho MOT canh. ASV so huu prompt nay (pha 08 §ranh gioi).

    🔴 **`khung` la thu bien ham nay tu mot cau hoi VAN BAN thanh mot cau hoi
       THI GIAC.** Truoc pha 27 no chi noi *"co N khung hinh dai dien"* va khong
       gui khung nao — tuc `DOC_CANH.can_thi_giac = True` chon model thi giac,
       roi ta hoi no mot cau ma mot model van ban tra loi duoc y het. Mot cau
       tra loi "trong nhu that ve mot buc anh model chua bao gio nhin thay" la
       dung thu docstring cua `ai.model_cho` viet ra de ngan.

    ⭐ Dang `image_url` + `data:` la hop dong OpenAI ma `CongVlm.chat` chuyen
       **nguyen xi** xuong may B. Khong co ban ma hoa thu hai o day: ASV so huu
       noi dung cau hoi, nen tang so huu van chuyen.

    ⚠️ Khong khung nao thi van gui phan van ban — de mot lan tach khung hong
       khong lam chet ca giai doan. Nhung luc do cau tra loi la mot phong doan
       tu loi thoai, va nguoi doc bao cao phai thay duoc dieu do: `so_khung` di
       kem trong chinh cau hoi, va no la 0.
    """
    tin = json.dumps(tin_hieu or {}, ensure_ascii=False, sort_keys=True)
    # 🔑 **Vong sua phai hoi mot cau KHAC, khong hoi lai cau cu.**
    #
    #    QC hinh (`qc_ai`) nhin cho noi tren BAN RA da dung va noi no dut mach;
    #    canh nay la mot trong nhung canh bi bo tai cho do. Neu vong sua gui lai
    #    y nguyen loi nhac cu thi model tra loi y nhu cu — va `van_tay_canh`
    #    con cache no lai. Do la M-07 cua duong GIONG, do tren duong that.
    #
    # ⛔ Dua no vao nhu BANG CHUNG, khong nhu mot lenh: dong duoi noi "mot nguoi
    #    soat da xem" va yeu cau can nhac LAI, chu khong noi "hay giu canh nay".
    #    Mot loi nhac ra lenh se bien vong sua thanh mot cong tac giu-het, va
    #    khi do phan doan cua model khong con la bang chung cua ai.
    nhac_qc = (
        f"\nLUU Y - BANG CHUNG TU VONG SUA: mot nguoi soat da xem BAN DUNG "
        f"co canh nay bi BO, va bao rang "
        f"cho noi tai do lam dut mach nhin: \"{str(phan_hoi_qc)[:300]}\". "
        f"Hay can nhac LAI canh nay voi bang chung do. Neu canh nay la cau noi "
        f"can thiet cho mach nhin thi de xuat giu; neu khong thi giu nguyen "
        f"de xuat cu va noi ro vi sao o `ly_do`.\n"
        if str(phan_hoi_qc or "").strip() else "")
    van = (
        f"Doc canh {ma_canh} cua mot video. "
        f"Co {so_khung} khung hinh dai dien. "
        f"Tin hieu do duoc: {tin}. "
        f"Loi thoai trong canh: {ngu_canh or '(khong co loi thoai)'}\n"
        f"{nhac_qc}\n"
        # 🔴 **KHUNG JSON, khong phai mot cau ke ten khoa (do 23/09).**
        #
        #    Ban cu ke ten khoa bang van xuoi ("Tra ve DUNG mot doi tuong JSON
        #    voi cac khoa: loai, chu_the (mang), ..."). Do 18 canh cua phim
        #    nghiem thu, model that: 2/18 tra ve mot **MANG** doi tuong, 1/18
        #    boc trong `{"objects": [...]}`. Moi loi nhac khac cua ASV deu dua
        #    mot khung — chi loi nhac nay ke ten, va chi no bi tra ve sai hinh.
        "Tra ve DUY NHAT mot doi tuong JSON, DUNG khung nay "
        "(mot doi tuong, KHONG phai mang, KHONG boc them lop nao):\n"
        '{"loai": "...", "chu_the": ["..."], "hanh_dong": "...", '
        '"cam_xuc": "...", "quan_trong": 0.0, '
        f'"de_xuat": "{GIU}", "do_tin": 0.0, '
        '"ly_do": "...", "canh_bao": ["..."]}\n'
        "`quan_trong` va `do_tin` la so trong [0,1].\n"
        # 🔴 **`de_xuat` la mot MA, khong phai mot tu tieng Viet (do 23/09).**
        #
        #    5/18 luot tra ve `"giữ"` (co dau) — cau tra loi DUNG ve nghia, bi
        #    `doc_hieu_canh` tu choi vi bang ma la ASCII khong dau. Loi nhac
        #    phai noi ro day la ma chu khong phai chu, va `doc_hieu_canh` con
        #    bo dau truoc khi doi chieu.
        f"`de_xuat` phai la DUNG mot trong ba MA sau, chep y nguyen, "
        f"khong dich, khong them dau tieng Viet: "
        f'"{GIU}" | "{BO}" | "{KHONG_CHAC}".\n'
        "Khong them van ban nao ngoai JSON.")
    if not khung:
        return [{"role": "user", "content": van}]

    import base64

    phan: list = [{"type": "text", "text": van}]
    for b in khung:
        if not b:
            continue
        b64 = base64.b64encode(b).decode("ascii")
        phan.append({"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    return [{"role": "user", "content": phan}]


# ══════════════════════════════════════════════════════════════════════════════
#  Doc phan hoi — KIEM NGHIEM NGAT
# ══════════════════════════════════════════════════════════════════════════════

def chuan_ma(gt) -> str:
    """Mot gia tri tho cua model -> mot MA ASCII khong dau, hoac `""`.

    🔑 **Phan CHUAN HOA cua `chuan_de_xuat`, tach ra vi no co nguoi dung thu
       hai** (`qc_ai.chuan_dat`, 23/09). Bo dau (NFD + `đ`→`d`), ha chu thuong,
       gop dau ngan cach ve `_`. Khong doi chieu bang nao — nguoi goi lam viec
       do, va vi vay ham nay khong bao gio "doan" ho.

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


def chuan_de_xuat(gt) -> str:
    """Mot gia tri `de_xuat` tho -> mot ma trong `DE_XUAT`, hoac `""`.

    🔴 **Bo DAU TIENG VIET truoc khi doi chieu, va do khong phai su chiu dung.**

       `DE_XUAT` la ASCII khong dau (`giu`/`bo`/`khong_chac`) vi moi loi nhac
       cua ASV viet ASCII. Model thi tra loi bang tieng Viet THAT: do 23/09 tren
       18 canh cua phim nghiem thu, **5 luot** tra ve `"giữ"` — dung nghia, dung
       khoa, dung kieu, va bi tu choi vi mot dau ngã.

    ⭐ Day KHONG phai "chiu hai hinh dang" (thu ma `doc_hieu_canh` da go bo mot
       lan): `giữ` va `giu` la CUNG mot gia tri viet hai cach, con `{"canh":
       {...}}` va `{...}` la hai luoc do khac nhau. Bo dau la mot phep chuan hoa
       **mat mat mot chieu va tat dinh**, khong phai mot nhanh thu hai cua hop
       dong.

    ⛔ Va no khong nuot rac: mot gia tri la (`"bu"` — do duoc 1/18 luot) van ra
       `""`, tuc van la `HieuCanhError`. Chuan hoa nhan dien, khong doan.
    """
    s = chuan_ma(gt)
    return s if s in DE_XUAT else ""


def _so_trong_khoang(gt, ten: str) -> float:
    try:
        x = float(gt)
    except (TypeError, ValueError) as exc:
        raise HieuCanhError(f"{ten} khong phai so: {gt!r}") from exc
    if not (0.0 <= x <= 1.0):
        raise HieuCanhError(f"{ten} phai trong [0,1], nhan {x}")
    return x


def doc_hieu_canh(kq: dict, ma_canh: str) -> HieuCanh:
    """KET QUA cua `ai.goi` -> `HieuCanh`. Nem `HieuCanhError` neu sai luoc do.

    ⛔ **Mot phan hoi sai luoc do khong phai mot artifact thanh cong** (yeu cau 5).
       Mot truong thieu thanh `None` di tiep se lo ra o pha 12 duoi dang "khong
       canh nao duoc giu" — mot thong bao khong lien quan gi den nguyen nhan.

    🔴 **Tham so la CA KET QUA, khong phai `noi_dung`, va do la ban sua 09/09.**

       Ban cu nhan `noi_dung: str`, nen nguoi goi phai viet
       `hc.doc_hieu_canh(kq.get("noi_dung") or "", c.ma)` — va dung cho ay vut
       mat `finish_reason`. Hau qua o duong CHI EM (`chuyen_loi_thoai`) do duoc:
       lan chay `giu_hinh` 09/09 chet ba lan voi *"model tra ve rong"*, trong
       khi su that la `finish_reason=length` — het tran token ra 4.096 giua
       khoi suy nghi. Bon phien lien tiep di do may B vi cau ay.

    ⚠️ `doc_canh` chua bao gio cham tran (do duoc: 1.258 token/luot trung binh
       tren tran 4.096), nen day la ban va PHONG chu khong phai ban va mot loi
       dang chay. Ly do van la du: no goi CUNG mot model qua CUNG mot tran, va
       mot thong diep khong noi duoc `finish_reason` se gui nguoi doc di nham
       cho y het lan truoc.
    """
    # 🔴 **Cho nay tung co MOT lop boc tuy chon, va lop boc do la nguon cua
    #    khiem khuyet B22-01 o tang luoc do.**
    #
    #    Dong cu la `goc = ra.get("canh") if isinstance(...) else ra`: no chiu
    #    duoc CA hai hinh dang, `{"canh": {...}}` lan `{...}`. Nhung
    #    `loi_nhac_canh` chi bao model tra ve hinh dang PHANG, va
    #    `DOC_CANH.truong_bat_buoc` lai khai `("canh",)` — tuc ba cho mo ta ba
    #    thu khac nhau, va cai duy nhat khach nhan duoc la mot loi "thieu truong
    #    bat buoc" cho mot phan hoi hoan toan dung.
    #
    # ⇒ MOT hinh dang, khai mot lan: loi dan hoi phang, `DOC_CANH` khai phang,
    #   `doc_json` kiem phang. Su chiu dung kia khong bao ve ai — no chi lam ba
    #   ban mo ta duoc phep lech nhau ma khong ai thay.
    goc = ai.doc_ket_qua(kq, ai.DOC_CANH)

    de_xuat = chuan_de_xuat(goc.get("de_xuat"))
    if not de_xuat:
        raise HieuCanhError(
            f"{ma_canh}: de_xuat phai la mot trong {DE_XUAT}, nhan "
            f"{str(goc.get('de_xuat') or '')!r}")

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


def doc_ho_so(kq: dict) -> HoSoNoiDung:
    """KET QUA cua `ai.goi` -> `HoSoNoiDung`. Nem neu thieu truong bat buoc.

    🔴 **Tham so la CA KET QUA, khong phai `noi_dung`** — cung ban sua 09/09 ma
       `doc_hieu_canh` da chiu: boc `noi_dung` ra bang tay vut mat
       `finish_reason`/`suy_nghi`, tuc vut mat thu duy nhat phan biet "model tra
       sai luoc do" voi "model het tran token giua khoi suy nghi". Ham nay chua
       tung co nguoi goi nen no giu chu ky cu toi 23/09.
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
#  Van tay
# ══════════════════════════════════════════════════════════════════════════════

def van_tay_canh(ma_canh: str, ngu_canh: str, so_khung: int,
                 nguong_canh: float, *, bat: float = 0.0, ket: float = 0.0,
                 muoi: str = "") -> str:
    """Van tay cua MOT canh. Gom prompt/luoc do, nen doi prompt = mat cache.

    🔴 **`bat`/`ket` la ban va F-10 (23/09), va no la mot cache CU KHONG BAO GIO
       TRUOT chu khong phai mot truong trang tri.**

       Ban truoc khoa theo `ma_canh` + `ngu_canh` + `so_khung` + `nguong`. Ma
       canh la mot so thu tu (`canh_0003`), khong phai mot danh tinh: doi bo
       tach canh — dung viec lane `ky-thuat` vua lam, `select=gt(scene,0.4)` →
       `ContentDetector(35)` — sinh ra mot `canh_0003` o **mot khoang thoi gian
       khac han**, va ba truong con lai deu co the trung:

         * `ngu_canh` trung khi ca hai canh deu khong co thoai (chuoi rong);
         * `so_khung` trung vi `canh.khung` lay mot so khung CO DINH moi canh;
         * `nguong` la mot hang so chinh sach, khong doi theo bo tach.

       ⇒ Diem chot cu khop, `_doc_cac_canh` doc lai `outputs` cu, va lan chay
         dung mot phan doan VLM ve **mot doan phim khac**. Khong loi nao bao:
         bang chung ve canh A duoc dan vao quyet dinh cat canh B.

    ⚠️ `canh.PHIEN_BAN_CANH` da vao van tay GIAI DOAN (`thi_hanh`), nen doi bo
       tach lam ca giai doan chay lai. Nhung diem chot theo DON VI thi khong ai
       vo hieu — `su_dung.don_vi_theo_khoa` doc dung `fingerprint` nay. Hai tang
       khac nhau, va chi tang duoi tra loi duoc cau *"canh_0003 nay co phai
       canh_0003 kia khong"*.

    ⭐ `muoi` = so vong sua da day canh nay ve `edit_plan` (`qc_hinh`). Cung bai
       hoc M-07 cua duong GIONG: khong muoi thi mot "vong sua" doc lai dung tep
       cu tu cache va tra ve **dung phan doan vua bi bao la sai** — mot vong sua
       khong the sua duoc gi la mot hoa don khong co san pham.
    """
    import hashlib

    kh = json.dumps({
        "v_prompt": PHIEN_BAN_HIEU_CANH,
        "v_cua_goi": ai.PHIEN_BAN_PROMPT,
        "v_luoc_do": ai.PHIEN_BAN_LUOC_DO,
        "ma": ma_canh, "so_khung": so_khung,
        "nguong": nguong_canh,
        "ngu_canh": ngu_canh,
        # ⛔ Lam tron 3 chu so (mili giay): moc canh la so thuc tu ffmpeg/PSD,
        #    va hai lan tinh cung mot canh co the lech o chu so thu 15. Mot van
        #    tay nhay theo nhieu dau cham dong la mot cache khong bao gio khop —
        #    tuc hoi (va tra tien) lai moi luot lat cat.
        "bat": round(float(bat), 3), "ket": round(float(ket), 3),
        "muoi": str(muoi or ""),
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(kh.encode("utf-8")).hexdigest()[:32]


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
