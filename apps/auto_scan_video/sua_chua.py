"""Ke hoach SUA: tu mot khiem khuyet, tim giai doan SOM NHAT co the sua no.

## Vi sao "som nhat CO THE" chu khong phai "som nhat"

Mot lan chay lai ca chuoi sua duoc moi thu — va tra tien cho moi thu. Pha 19 cam
dieu do bang chu ("No full-run automatic rerun"), va ly do khong chi la tien:

⛔ Chay lai mot giai doan da dung se cho ra mot ket qua **khac** (model la ngau
   nhien). Nen mot lan chay lai rong khong phai "sua mot loi" — no la "danh doi
   mot loi da biet lay mot tap ket qua chua biet".

⭐ Nen moi loai khiem khuyet duoc anh xa toi **dung** giai doan sua duoc no:

    doc sai      -> VOICE_SYNTHESIS   (doc lai DUNG doan do)
    dich sai     -> CONTENT_PROCESS   (viet lai DUNG cau do)
    khong vua    -> VOICE_SYNTHESIS   (nan lai — pha 15 da co bac thang)
    cat sai      -> EDIT_PLAN         (xem lai DUNG canh do)
    hinh hong    -> RENDER            (dung lai — khong phai loi noi dung)

🔴 **Va chieu nguoc lai moi la cho de sai.** Mot cau bi may doc sai (TTS nuot mot
   tu) **khong duoc** day nguoc ve `CONTENT_PROCESS`: cau van ban do dang DUNG,
   va viet lai no la tra tien de doi mot cau dung lay mot cau khac cung dung —
   roi van co the bi doc sai lan nua.

   Mot ban dich sai thi nguoc lai: doc lai bao nhieu lan cung ra cung mot y sai.

⇒ "Som nhat co the" = giai doan som nhat ma **noi dung cua no la nguyen nhan**.
  Di som hon la lam lai viec dung; di muon hon la khong sua duoc gi.

## Vong sua co TRAN, va tran do la mot con so nho

Mot vong "sua roi kiem lai" tren nhung dich vu tra tien la mot hoa don khong co
day. Va khac vong nan cua pha 15 (vong do sua mot dai luong DO DUOC — do dai —
nen no hoi tu), vong nay sua mot phan doan CHU QUAN cua model. Hai lan lien tiep
model cho hai phan doan khac nhau ve cung mot cau la binh thuong; lap ba lan la
tra tien de xem model doi y.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from platform_core.i18n import _ as _t

#: Doi khi doi bat cu thu gi o duoi. Vao van tay cua ke hoach.
PHIEN_BAN_SUA = 1

# ── Loai khiem khuyet ────────────────────────────────────────────────────────
DOC_SAI = "doc_sai"          #: tieng doc ra khong khop van ban dich
DICH_SAI = "dich_sai"        #: nghia tieng Viet lech so voi nguon
KHONG_VUA = "khong_vua"      #: doan khong vua khe (pha 15 danh dau `CAN_SUA`)
CAT_SAI = "cat_sai"          #: canh bi cat lam dut mach hinh
HINH_HONG = "hinh_hong"      #: ban ra hong ve ky thuat, khong phai noi dung
LOAI = (DOC_SAI, DICH_SAI, KHONG_VUA, CAT_SAI, HINH_HONG)

#: 🔑 Bang nay LA chinh sach. Mot chuoi `if` rai rac cho cung viec se lech nhau
#:    o mot nhanh nao do, va nhanh lech se la nhanh it duoc chay nhat.
GIAI_DOAN_SUA = {
    DOC_SAI: "voice_synthesis",
    DICH_SAI: "content_process",
    KHONG_VUA: "voice_synthesis",
    CAT_SAI: "edit_plan",
    HINH_HONG: "render",
}

#: So vong sua tu dong toi da cho MOT lan chay.
#:
#: ⛔ Khac vong nan cua pha 15: vong do sua mot dai luong DO DUOC (do dai tieng)
#:    nen no hoi tu. Vong nay sua mot phan doan CHU QUAN cua model — hai lan chay
#:    co the cho hai phan doan khac nhau ve cung mot cau, va lap ba lan la tra
#:    tien de xem model doi y.
VONG_SUA_TOI_DA = 1

#: Nguong DOC SAI theo ngon ngu dich: `{ngon_ngu: {"wer": x, "cer": y}}`.
#:
#: Phep do: tieng da long cua MOT doan -> ASR (faster-whisper, cung model
#: TRANSCRIBE) -> WER (+ CER voi tieng Viet) so voi cau may doc da nhan, hai ve
#: chuan hoa bang CUNG mot ham (`apps/asv_gpu/do_luong/chuan_hoa_loi.py`).
#: Mot doan la DOC SAI khi vuot MOI nguong khai cho ngon ngu do.
#:
#: 🔑 Con so HIEU CHINH tu tieng that cua LTT Voice (:8120), khong tu nghi — so
#:    lieu, phan bo va doi chung o `docs/auto_scan_video_final/L_GIONG.md`.
#: ⛔ Ngon ngu KHONG co trong bang = chua hieu chinh ⇒ ket qua do van ghi vao
#:    bao cao, nhung KHONG sinh viec sua. Mot nguong doan mo sinh viec doc lai
#:    (co tra tien) tren mot bang chung khong ai do.
NGUONG_DOC_SAI: dict[str, dict[str, float]] = {
    # vi: 36 doan THAT (LTT Voice :8120, 4 giong, 4 video zh->vi) — WER am tiet
    #     cao nhat 0,407 nhung CER cao nhat chi 0,213; doi chung "nuot 1/3
    #     cuoi" (35 doan) co WER >= 0,308 VA CER >= 0,248. Hai nguong cung
    #     phai vuot: 0/36 bao dong gia, 35/35 doan thieu chu bi bat.
    "vi": {"wer": 0.30, "cer": 0.23},
    # en: 14 doan THAT (giong nhan ban en, muc engine) — WER cao nhat 0,074;
    #     doi chung nuot chu thap nhat 0,273. 0,15 nam giua, khong sat ben nao.
    #     ⛔ CER khong khai: chuan hoa en la `EnglishTextNormalizer` (so ->
    #     chu so), nen CER tren chuoi do khong cung nghia voi CER tieng Viet.
    "en": {"wer": 0.15},
}

#: Do tin toi thieu de tin mot phan doan cua model.
#:
#: ⭐ Duoi muc nay, ket luan duoc ghi lai nhung **khong** sinh viec sua: mot model
#:    khong chac chan khong phai mot ly do de tra tien lam lai.
DO_TIN_TOI_THIEU = 0.70


class SuaChuaError(ValueError):
    """Ke hoach sua khong dung hop dong."""


@dataclass(frozen=True)
class KhiemKhuyet:
    """MOT khiem khuyet, gan voi MOT don vi cu the."""

    loai: str
    #: Ma doan (loi noi) hoac ma canh (hinh). Rong = ca ban ra.
    ma: str = ""
    ly_do: str = ""
    do_tin: float = 1.0
    bang_chung: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.loai not in LOAI:
            raise SuaChuaError(
                _t('Loại khiếm khuyết không hợp lệ: {l}').format(l=self.loai))

    @property
    def giai_doan(self) -> str:
        return GIAI_DOAN_SUA[self.loai]

    @property
    def dang_tin(self) -> bool:
        return float(self.do_tin) >= DO_TIN_TOI_THIEU


def _vuot_nguong(d: dict) -> dict | None:
    """Nguong da vuot cua MOT ket qua do, hoac None (dat / chua hieu chinh)."""
    ng = NGUONG_DOC_SAI.get(str(d.get("ngon_ngu") or "").lower())
    if not ng or "wer" not in d:
        return None
    for chi_so, gioi_han in ng.items():
        gt = d.get(chi_so)
        if gt is None or float(gt) <= float(gioi_han):
            return None
    return dict(ng)


def giong_khong_dat(do_duoc: list[dict]) -> list[dict]:
    """Loc ket qua do giong: chi giu doan VUOT nguong, kem nguong da ap.

    Dau vao `[{ma, ngon_ngu, wer, cer?, doc_ra, tham_chieu_chuan, ...}]` —
    dung dang `giai_doan_qc_do_luong` ghi. Dau ra la thu vong sua doc.
    """
    ra = []
    for d in do_duoc or []:
        ng = _vuot_nguong(d)
        if ng is None:
            continue
        ra.append({"ma": str(d.get("ma") or ""),
                   "ngon_ngu": str(d.get("ngon_ngu") or ""),
                   "wer": d.get("wer"), "cer": d.get("cer"), "nguong": ng,
                   "doc_ra": str(d.get("doc_ra") or "")[:200],
                   "tham_chieu": str(d.get("tham_chieu_chuan") or "")[:200]})
    return ra


def tu_qc_giong(doan: list[dict]) -> list[KhiemKhuyet]:
    """Khiem khuyet DOC SAI tu ket qua do giong (ASR + WER/CER).

    ⭐ `do_tin=1.0`: day la mot phep DO (WER tren hai chuoi da chuan hoa), khong
       phai phan doan cua model. Phan chu quan duy nhat — nguong — la con so
       hieu chinh o `NGUONG_DOC_SAI`, va no duoc ap LAI o day chu khong tin co
       `khong_dat` cua nguoi goi: mot chinh sach, mot cho.
    """
    ra = []
    for d in doan or []:
        ng = _vuot_nguong(d)
        if ng is None:
            continue
        ra.append(KhiemKhuyet(
            DOC_SAI, ma=str(d.get("ma") or ""),
            ly_do=_t('Tiếng đọc ra không khớp lời đã viết.'),
            do_tin=1.0,
            bang_chung={"wer": d.get("wer"), "cer": d.get("cer"), "nguong": ng,
                        "doc_ra": str(d.get("doc_ra") or "")[:200]}))
    return ra


def lan_lam_lai(cac_ke_hoach: list[dict], giai_doan: str) -> dict[str, int]:
    """`{ma: n}` — so ke hoach sua (`KeHoachSua.sang_dict()`) da dua don vi `ma`
    ve `giai_doan`.

    🔑 **Mot ham cho MOI giai doan co vong sua, khong mot ham moi giai doan.**
       `voice_synthesis` muoi van tay tieng bang `n` (M-07); `edit_plan` muoi
       van tay canh bang `n` (M-02). Hai ban sao cua phep dem nay se lech nhau
       o mot nhanh nao do, va nhanh lech la nhanh it duoc chay nhat.

    ⭐ Vi sao phai muoi: cung van tay = cung khoa = cung ket qua cache. Mot
       "vong sua" khong muoi tra ve **dung phan doan vua bi bao la sai** — tuc
       mot hoa don khong co san pham. Do la M-07, do duoc tren duong that.
    """
    ra: dict[str, int] = {}
    for ke in cac_ke_hoach or []:
        for ma in (ke.get("giai_doan_sua") or {}).get(str(giai_doan)) or []:
            ra[str(ma)] = ra.get(str(ma), 0) + 1
    return ra


def lan_doc_lai(cac_ke_hoach: list[dict]) -> dict[str, int]:
    """`lan_lam_lai` cho `voice_synthesis` — ten cu, giu cho nguoi goi hien co."""
    return lan_lam_lai(cac_ke_hoach, "voice_synthesis")


def tu_qc_ngu_nghia(phan_doan: list[dict]) -> list[KhiemKhuyet]:
    """Khiem khuyet tu QC NGU NGHIA: `[{ma, dat, ly_do, do_tin}]`."""
    ra = []
    for d in phan_doan or []:
        if bool(d.get("dat", True)):
            continue
        ra.append(KhiemKhuyet(
            DICH_SAI, ma=str(d.get("ma") or ""),
            ly_do=str(d.get("ly_do") or ""),
            do_tin=float(d.get("do_tin") or 0.0),
            bang_chung={"nguon": str(d.get("nguon") or "")[:200],
                        "dich": str(d.get("dich") or "")[:200]}))
    return ra


#: 🔴 **QC HINH chi TU VAN — phan quyet duoc GHI nhung KHONG sinh viec sua.**
#:
#: ⛔ **Va ly do la CHUA DO, chu khong phai "do thay kem".** Tinh den 23/09 chua
#:    ai do do chinh xac cua phan quyet `dat=false` tren phim that: luot do dau
#:    tien (`tools/do_qc_hinh.py`, 4 phim tieng Trung) bi dung giua chung vi no
#:    giu khoa toan may de CHO MANG, va moi phan quyet nam trong bo nho nen mat
#:    sach. `L_QC_HINH.md` §4 ghi dung nhung gi con lai va dung mot cau "chua
#:    do" o cho con so.
#:
#: 🔑 Mot con so KHONG CO khong duoc doc thanh mot con so TOT. Cua mac dinh cua
#:    mot phan quyet CHU QUAN chua ai do phai la "ghi lai", khong phai "tieu
#:    tien" — do la chinh nguyen tac ma `DO_TIN_TOI_THIEU` ngay duoi viet ra.
#:
#: 🔴 **Va rieng `cat_sai` con mot ly do doc lap voi do chinh xac: no la vong
#:    sua DAT NHAT trong he.** `edit_plan` la giai doan SOM NHAT, nen dat lai no
#:    keo theo `content_process` + `voice_synthesis` + `timing_align` +
#:    `compose` + `render` + ca ba lop QC. Lane `fix-toc-do` do duoc
#:    `voice_synthesis` = ~190 giay cho mot phim 107 giay SAU khi toi uu (943
#:    giay truoc do). Tuc mot bao dong gia o day khong phai mot lan hoi lai —
#:    no la gan mot lan chay lai ca chuoi.
#:
#: ⇒ Tin hieu KEM TIN CAY NHAT cua he dang noi vao vong sua DAT NHAT cua he.
#:   Hai dieu do cong lai thi mac dinh chi co the la tu van.
#:
#: ⭐ Va cai gia hai chieu khong bang nhau. Bo sot mot cho noi hong: khach nhan
#:    mot ban dung co mot cho giat, thay duoc, khieu nai duoc. Bao dong gia: mot
#:    hoa don khong ai thay, tren mot lan chay khong ai bao la sai.
#:
#: ⛔ Va vong sua KHONG phai duong duy nhat: phan quyet van vao `qc_ai` report,
#:    van vao `stage.outputs`, van hien o bao cao van hanh. "Tu van" o day nghia
#:    la *khong tu dong tieu tien*, khong phai *khong ai duoc biet*.
#:
#: 🔑 Doi co nay thanh `False` la mot quyet dinh ve GIA. Doi kem mot bo do moi
#:    o cung tep tren, khong doi mot minh.
QC_HINH_LA_TU_VAN = True


def tu_qc_hinh(phan_doan: list[dict], *, tu_van: bool | None = None
               ) -> list[KhiemKhuyet]:
    """Khiem khuyet CAT SAI tu QC HINH: `[{ma_canh, ma_cat, dat, ly_do, do_tin}]`.

    🔑 **MOT khiem khuyet cho MOI canh bi bo tai cho noi do, khong mot cho ca
       cho noi.** Cai `edit_plan` nhan lam don vi viec la mot MA CANH; mot "cho
       noi o giay 74" khong dat lai duoc gi. `qc_ai.cac_cho_noi` doi nguoc tu
       khoang bi cat ra `ma_cat`, va day la noi no tro thanh viec.

    ⚠️ `ma_cat` rong (khong truyen chi muc canh, hoac khoang bi cat khong trung
       canh nao) ⇒ phan quyet duoc ghi lai nhung khong sinh viec sua duoc. Ta
       KHONG bia mot ma canh de co viec lam.

    ⛔ Mac dinh TU VAN — xem `QC_HINH_LA_TU_VAN`. `tu_van` chi de phep kiem
       (va mot nguoi van hanh) doi chieu ca hai chieu ma khong phai va hang so.
    """
    if bool(QC_HINH_LA_TU_VAN if tu_van is None else tu_van):
        return []
    ra = []
    for d in phan_doan or []:
        if bool(d.get("dat", True)):
            continue
        ds = [str(m) for m in (d.get("ma_cat") or ()) if str(m)]
        if not ds and d.get("ma_canh"):
            ds = [str(d["ma_canh"])]
        for ma in ds:
            ra.append(KhiemKhuyet(
                CAT_SAI, ma=ma,
                ly_do=str(d.get("ly_do") or ""),
                do_tin=float(d.get("do_tin") or 0.0),
                bang_chung={"moc_giay": d.get("moc_giay"),
                            "ma_cat": ds}))
    return ra


def tu_nan(cac_nan: list[dict]) -> list[KhiemKhuyet]:
    """Khiem khuyet tu bac thang nan cua pha 15: trang thai `can_sua`."""
    from .nan_cho_vua import CAN_SUA

    return [KhiemKhuyet(KHONG_VUA, ma=str(d.get("ma") or ""),
                        ly_do=_t('Đoạn không vừa khe kể cả sau khi co giãn.'),
                        do_tin=1.0,
                        bang_chung={"giay": d.get("giay"), "khe": d.get("khe")})
            for d in cac_nan or []
            if str(d.get("trang_thai_nan") or "") == CAN_SUA]


@dataclass(frozen=True)
class KeHoachSua:
    """Nhung gi phai lam lai, va o dau."""

    khiem_khuyet: tuple[KhiemKhuyet, ...]
    vong: int = 0

    @property
    def dang_tin(self) -> tuple[KhiemKhuyet, ...]:
        return tuple(k for k in self.khiem_khuyet if k.dang_tin)

    @property
    def can_sua(self) -> bool:
        return bool(self.dang_tin)

    def giai_doan_sua(self) -> dict[str, list[str]]:
        """`{giai_doan: [ma, ...]}` — dung nhung don vi phai lam lai.

        ⛔ Chi gom khiem khuyet **dang tin**: mot model khong chac chan khong phai
           mot ly do de tra tien lam lai.
        """
        ra: dict[str, list[str]] = {}
        for k in self.dang_tin:
            ra.setdefault(k.giai_doan, [])
            if k.ma and k.ma not in ra[k.giai_doan]:
                ra[k.giai_doan].append(k.ma)
        return {g: sorted(m) for g, m in ra.items()}

    def con_vong(self) -> bool:
        return int(self.vong) < VONG_SUA_TOI_DA

    def sang_dict(self) -> dict:
        return {
            "phien_ban": PHIEN_BAN_SUA,
            "vong": int(self.vong),
            "can_sua": self.can_sua,
            "con_vong": self.con_vong(),
            "giai_doan_sua": self.giai_doan_sua(),
            "khiem_khuyet": [
                {"loai": k.loai, "ma": k.ma, "ly_do": k.ly_do,
                 "do_tin": round(float(k.do_tin), 3),
                 "dang_tin": k.dang_tin,
                 "giai_doan": k.giai_doan,
                 "bang_chung": dict(k.bang_chung)}
                for k in self.khiem_khuyet],
        }

    def van_tay(self) -> str:
        goi = json.dumps(self.sang_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(goi.encode("utf-8")).hexdigest()[:32]


def lap_ke_hoach(*, qc_giong=None, qc_ngu_nghia=None, qc_hinh=None,
                 cac_nan=None, vong: int = 0) -> KeHoachSua:
    """Gom moi nguon khiem khuyet thanh MOT ke hoach.

    ⭐ Mot ke hoach chu khong phai bon danh sach: neu mot doan vua bi doc sai vua
       bi dich sai, ta phai sua o `content_process` (som hon) va lan doc lai se
       tu den sau — chu khong phai sua hai lan o hai cho.
    """
    kk = (list(tu_qc_giong(qc_giong or []))
          + list(tu_qc_ngu_nghia(qc_ngu_nghia or []))
          + list(tu_qc_hinh(qc_hinh or []))
          + list(tu_nan(cac_nan or [])))
    return KeHoachSua(tuple(kk), vong=int(vong))


def gon_theo_don_vi(ke: KeHoachSua) -> dict[str, str]:
    """`{ma: giai_doan}` — MOT giai doan cho MOI don vi, la giai doan SOM NHAT.

    🔴 Day la cho "pham vi nho nhat an toan" duoc cuong che.

       Neu doan `seg_0007` vua bi bao doc sai (sua o `voice_synthesis`) vua bi bao
       dich sai (sua o `content_process`), thi sua o `voice_synthesis` la vo ich:
       doc lai mot cau dich sai van ra mot cau dich sai. Phai sua o cho som hon,
       va lan doc lai se tu den sau no.

    ⛔ Nguoc lai KHONG dung: mot doan CHI bi doc sai khong duoc day nguoc ve
       `content_process`. Cau van ban do dang DUNG; viet lai no la tra tien de
       doi mot cau dung lay mot cau khac cung dung.
    """
    from .pipeline import CHUOI

    thu_tu = {g.ten: i for i, g in enumerate(CHUOI)}
    ra: dict[str, str] = {}
    for k in ke.dang_tin:
        if not k.ma:
            continue
        cu = ra.get(k.ma)
        if cu is None or thu_tu.get(k.giai_doan, 99) < thu_tu.get(cu, 99):
            ra[k.ma] = k.giai_doan
    return ra
