"""HO SO NOI DUNG — nguoi SINH RA `HoSoNoiDung`, thu ca `AUTO_MATCH` dung de doi.

## 🔴 Lo hong tep nay dong

Truoc 23/09/2026, `AUTO_MATCH` la mot duong CHET tu dau den cuoi:

    rang_giong.py:219   `dac_diem` rong  -> `CHUA_RANG`
    giai_doan_noi_dung  `ma_giong()`     -> `ChuaRangError`

va **khong giai doan nao sinh ra mot `HoSoNoiDung`**, nen `dac_diem` khong bao
gio het rong. Luot nghiem thu that `NEN_V3` luot A chet o `content_process` sau
133 giay demucs + ASR DA TRA TIEN (`docs/auto_scan_video_final/bang_chung/NEN_V3.md`).
`hieu_canh.loi_nhac_ho_so`/`doc_ho_so` da co san — chung chi khong co nguoi goi.

⚠️ Va duong "cho VLM doc canh roi gop ho so" khong sua duoc ca hai preset:
   `localize_preserve_picture` **khong chay** mot lan `edit_plan` nao co nghia
   (0,0 giay trong luot that, xem `giai_doan_ban_bien_tap`: khong canh nao bi
   cat thi khong co gi de hoi VLM). Bat preset giu hinh tra tien mot luot VLM
   chi de biet chon giong nao la lam hong chinh cho re cua no.

## ⭐ Nen ho so nay dung tren BANG CHUNG DA TRA TIEN RUI

Hai nguon, va ca hai deu co mat o CA HAI preset vi chung nam TRUOC `edit_plan`:

    `audio_prepare`   F0 trung vi cua stem `vocals`  -> `gioi`   (DO DUOC)
    `transcribe`      van ban + moc thoi gian        -> mat con lai (MOT lan goi
                                                       model VAN BAN, re)

🔑 `gioi` — mat co gia nhat va la mat DUY NHAT kho giong chung khai
   (`rang_giong._rang_kho_chung`) — duoc **do**, khong duoc doan. Xem
   `cao_do.py` ve nguong va vung xam. Model chi dien nhung mat khong do duoc.

⛔ Va ho so **khong** duoc suy ra tu mot giong mac dinh nao ca. Khong do duoc,
   model khong tra loi duoc, thi ket qua van la `CHUA_RANG` — `ADR-V4-001`
   D-V4-04 cam dung cai "roi ve giong mac dinh", va tep nay khong mo cua do.

## Vi sao ho so duoc GHI vao `run.settings`

`dich_vu_tao.KHOA_NHAN` da chua san mot cho trong (`dac_diem_giong` — *"chua cua
nao sinh ra no"*), va `cai_dat.chuan_hoa` da doc/giu no. Ghi vao do co mot ly do
manh hon su gon gang:

🔴 **Van tay cua `content_process` co `ma_giong` trong do.** Mot lan chay lai ma
   chon ra mot giong KHAC se doi van tay, va doi van tay nghia la moi diem chot
   cua nhung lo da tra tien deu **khong con tinh**. Mot ho so sinh lai moi luot
   la mot hoa don nhan doi moi lan worker sap.

⇒ Sinh MOT lan, ghi xuong, commit. Luot sau doc lai va rang ra dung giong cu.
"""
from __future__ import annotations

import json
import logging

from . import ai, cao_do
from .hieu_canh import HieuCanhError, HoSoNoiDung, doc_ho_so, loi_nhac_ho_so

log = logging.getLogger(__name__)

#: Ma dispatch cua lan goi model o giai doan `content_process`. Mot lan / run.
ITEM_KEY = "ho_so_noi_dung"

#: Khoa ho so day du trong `run.settings` (bang chung + nguon cua tung mat).
KHOA_HO_SO = "ho_so_noi_dung"

#: Nguon cua mat `gioi`, ghi vao ho so de man ho tro va hoa don doc duoc.
NGUON_GIOI_DO = "do_f0"          # do tren stem `vocals` (`cao_do.py`)
NGUON_GIOI_MODEL = "model"       # model van ban doan tu ban chep loi
NGUON_GIOI_KHONG = ""            # khong ai noi duoc

#: Tran ky tu ban chep loi gui kem loi nhac. Mot phim 120 phut khong can gui het
#: de tra loi "the loai gi, nhip nao"; cat o day giu lan goi nay o hang re.
TOM_TAT_TOI_DA = 4000


#: ⛔ **Khong co lop ngoai le rieng o day, va do la co y.** Tep nay khong bao gio
#:    that bai: model hong thi ho so ngheo di, do F0 hong thi mat `gioi` rong.
#:    Cai NEM la `rang_giong.ChuaRangError`, o cho biet du de noi thieu gi
#:    (`vi_sao_chua_rang`). Mot lop `HoSoError` them vao day se la mot nhanh loi
#:    khong ai nem — va `test_418` doi moi lop ngoai le phai duoc phan loai.


# ══════════════════════════════════════════════════════════════════════════════
#  Tu vung — LAY TU CATALOG, khong go tay
# ══════════════════════════════════════════════════════════════════════════════

def tu_vung() -> dict[str, frozenset[str]]:
    """Gia tri HOP LE cua ba mat, doc thang tu `ltt_voice.giong_mau`.

    🔴 **Day la cho mot ban sua truoc do suyt chet lan hai.** Model rat hay tra
       ve `phong_cach: "thuyet minh"` — mot chu dung tieng Viet, hop ly voi con
       nguoi, va **khong co trong catalog**. `giong_mau.loc` se tra ve rong, va
       `AUTO_MATCH` roi tro lai dung `CHUA_RANG` ma ca tep nay sinh ra de dong —
       lan nay voi mot ho so trong tay, tuc kho lan ra hon.

    ⛔ Nen moi gia tri model tra ve deu di qua day, va gia tri la thi bi **bo**
       (chu khong phai bi doi sang mot gia tri gan giong). Bo di = khong rang
       buoc mat do; doi = bia ra mot rang buoc khach khong he co.
    """
    from apps.ltt_voice.giong_mau import (NHAN_GIOI, NHAN_PHONG_CACH, NHAN_VUNG)

    return {"gioi": frozenset(NHAN_GIOI),
            "vung": frozenset(NHAN_VUNG),
            "phong_cach": frozenset(NHAN_PHONG_CACH)}


def loc_dac_diem(dac_diem: dict) -> dict:
    """Giu lai dung nhung mat/gia tri catalog that su co. Xem `tu_vung`."""
    hop_le = tu_vung()
    ra = {}
    for mat, gia_tri in hop_le.items():
        v = str((dac_diem or {}).get(mat) or "").strip().lower()
        if v in gia_tri:
            ra[mat] = v
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Bang chung TAT DINH — khong goi ai, khong ton gi
# ══════════════════════════════════════════════════════════════════════════════

def bang_chung(ban_ghi: dict, *, f0: float = 0.0) -> dict:
    """So lieu doc duoc tu ban chep loi + phep do F0. Khong goi model.

    ⭐ Tat ca deu la thu `transcribe` va `audio_prepare` DA sinh ra roi: mot lan
       chay `AUTO_MATCH` khong tra them mot giay may nao cho khoi nay.
    """
    doan = list((ban_ghi or {}).get("doan") or [])
    tong_chu = 0
    tong_giay = 0.0
    for d in doan:
        tong_chu += len(str(d.get("chu") or "").strip())
        try:
            tong_giay += max(0.0, float(d.get("ket", 0)) - float(d.get("bat", 0)))
        except (TypeError, ValueError):
            continue
    return {
        "ngon_ngu_goc": str((ban_ghi or {}).get("ngon_ngu") or ""),
        "so_doan": len(doan),
        "giay_co_thoai": round(tong_giay, 2),
        "ky_tu_moi_giay": round(tong_chu / tong_giay, 2) if tong_giay > 0 else 0.0,
        "f0_trung_vi": round(float(f0 or 0.0), 2),
    }


def tom_tat_ban_ghi(ban_ghi: dict, *, toi_da: int = TOM_TAT_TOI_DA) -> str:
    """Van ban thoai noi lien, cat theo tran ky tu.

    ⚠️ Cat o ranh DOAN chu khong giua cau: mot cau cut moi model doan tiep phan
       thieu, va no doan bang token cua khach (cung ly do voi
       `hieu_canh.ngu_canh_cho_canh`).
    """
    ra: list[str] = []
    con = max(0, int(toi_da))
    for d in (ban_ghi or {}).get("doan") or []:
        chu = str(d.get("chu") or "").strip()
        if not chu:
            continue
        if len(chu) + 1 > con:
            break
        ra.append(chu)
        con -= len(chu) + 1
    return " ".join(ra)


def f0_tu_giai_doan(db, run) -> float:
    """F0 trung vi ma `audio_prepare` da ghi lai. `0.0` neu khong co.

    ⛔ Khong mo lai mot tep tieng nao o day: stem `vocals` **da bi xoa** khi tien
       trinh con ket thuc (`giai_doan_am_thanh`), co chu dinh — do la giong goc
       cua khach. Cai con lai la mot con so trong `outputs`.
    """
    from . import features, pipeline

    try:
        gd = features.giai_doan_theo_ten(db, run.id, pipeline.AUDIO_PREPARE)
    except Exception:                                      # noqa: BLE001
        return 0.0
    try:
        return float(((gd.outputs or {}) if gd else {}).get("f0_trung_vi") or 0.0)
    except (TypeError, ValueError):
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  Dung ho so
# ══════════════════════════════════════════════════════════════════════════════

def dung(db, run, *, ban_ghi: dict, f0: float = 0.0, ctx=None) -> HoSoNoiDung:
    """Bang chung tat dinh + MOT lan goi model van ban -> `HoSoNoiDung`.

    🔑 Thu tu la mot phan cua hop dong: `gioi` DO DUOC thang `gioi` model doan.
       Mot phep do tren chinh giong dang noi manh hon mot phan doan tu van ban
       da dich, va khi hai cai lech nhau thi cai lech la cai doan.

    ⚠️ Model hong (het ngan sach, `LuocDoSai`, may B chet) **khong** lam hong ca
       lan chay: ta tra ve ho so chi co phan do duoc. Neu phan do duoc cung
       rong thi ho so rong — va `rang_giong` se noi `CHUA_RANG` mot cach that
       tha, dung nhu D-V4-04 doi.
    """
    bc = bang_chung(ban_ghi, f0=f0)
    gioi_do = cao_do.gioi_tu_f0(bc["f0_trung_vi"])

    hs = _hoi_model(db, run, bc=bc, ban_ghi=ban_ghi, ctx=ctx)
    dd = loc_dac_diem(hs.dac_diem_giong if hs else {})
    if gioi_do:
        dd["gioi"] = gioi_do

    # ⭐ NGUON cua mat `gioi` khong nam trong `HoSoNoiDung` (dataclass do
    #    `hieu_canh` so huu, va no khong biet gi ve phep do F0). `bao_dam` ghi no
    #    canh ho so trong `run.settings[KHOA_HO_SO]["nguon_gioi"]` — MOT cho,
    #    de man ho tro va hoa don doc duoc "vi sao giong nay".
    return HoSoNoiDung(
        the_loai=(hs.the_loai if hs else ""),
        giong_dieu=(hs.giong_dieu if hs else ""),
        khan_gia=(hs.khan_gia if hs else ""),
        nhip=(hs.nhip if hs else ""),
        dac_diem_giong=dd,
        tom_tat=(hs.tom_tat if hs else ""))


def _hoi_model(db, run, *, bc: dict, ban_ghi: dict, ctx=None):
    """MOT lan goi `ai.HO_SO_NOI_DUNG` tren VAN BAN. `None` neu khong hoi duoc.

    ⛔ Di qua `ai.goi_tinh_tien` — cua tra tien DUY NHAT cua app. Mot lan goi
       model khong qua cua do la mot but toan khong co nguoi lam chung
       (`test_434` chot dieu nay bang AST).
    """
    from . import pipeline

    if db is None or run is None:
        return None
    messages = loi_nhac_ho_so((), tom_tat_ban_ghi(ban_ghi), bang_chung=bc)
    try:
        kq = ai.goi_tinh_tien(db, run, ai.HO_SO_NOI_DUNG, messages,
                              stage=pipeline.CONTENT_PROCESS,
                              item_key=ITEM_KEY, ctx=ctx)
        # ⛔ Truyen CA `kq` — boc `noi_dung` ra o day vut mat `finish_reason`,
        #    tuc vut mat cau tra loi cho "model sai luoc do hay het tran token".
        return doc_ho_so(kq)
    except (ai.AiError, ai.AiMoHo, HieuCanhError, ValueError) as exc:
        # ⚠️ Nuot co chu dinh, va CHI o day: phan do duoc van con, nen mot lan
        #    goi hong lam ho so NGHEO di chu khong lam lan chay chet. Cai chet
        #    (neu ho so rong han) se den tu `rang_giong` voi mot cau loi noi
        #    dung chuyen gi thieu.
        log.warning("ho so noi dung: khong hoi duoc model (%s)", exc)
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  Ghi xuong `run.settings` — MOT lan cho ca lan chay
# ══════════════════════════════════════════════════════════════════════════════

def bao_dam(db, run, *, ban_ghi: dict, ctx=None) -> dict:
    """Bao dam `run.settings["dac_diem_giong"]` da co. Tra ve ho so (dict).

    🔑 Luy dang: da co `dac_diem_giong` thi KHONG goi model lan hai. Xem
       docstring dau tep ve van tay — sinh lai ho so moi luot chay lai la nhan
       doi hoa don cua `content_process`.
    """
    from . import cai_dat as cd

    cai = dict(run.settings or {})
    da_co = loc_dac_diem(cai.get("dac_diem_giong") or {})
    if da_co:
        return dict(cai.get(KHOA_HO_SO) or {"dac_diem_giong": da_co})

    f0 = f0_tu_giai_doan(db, run)
    hs = dung(db, run, ban_ghi=ban_ghi, f0=f0, ctx=ctx)
    goi = hs.sang_dict()
    goi["bang_chung"] = bang_chung(ban_ghi, f0=f0)
    goi["nguon_gioi"] = (NGUON_GIOI_DO if cao_do.gioi_tu_f0(f0)
                         else (NGUON_GIOI_MODEL if hs.dac_diem_giong.get("gioi")
                               else NGUON_GIOI_KHONG))

    cai[KHOA_HO_SO] = goi
    # ⭐ `dac_diem_giong` la be mat MA `rang_giong.tu_thiet_lap` doc. Ghi ca hai:
    #    mot cho de rang giong, mot cho de NOI DUOC vi sao (man ho tro, hoa don).
    cai["dac_diem_giong"] = dict(hs.dac_diem_giong)
    run.settings = cd.chuan_hoa(cai)
    # 🔴 `commit`, khong `flush` — cung ly do `giai_doan_noi_dung` commit sau moi
    #    lo: worker sap ngay sau day thi mot `flush` bi cuon lai, va luot sau se
    #    goi model lan hai cho cung mot cau hoi.
    db.commit()
    return goi


def mo_ta(goi: dict) -> str:
    """Mot dong doc duoc cho nhat ky/bao cao. Khong dung trong quyet dinh nao."""
    return json.dumps({k: v for k, v in (goi or {}).items()
                       if k in ("dac_diem_giong", "nguon_gioi", "bang_chung")},
                      ensure_ascii=False, sort_keys=True)
