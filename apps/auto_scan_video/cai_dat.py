"""ProductSettings chuan tac cua Auto Scan Video — pha 07 (V6).

`AsvRun.settings` da la ProductSettings tren thuc te tu V4. Thu no thieu, va
thieu ba thu cung mot luc:

  · **khong co phien ban schema** — mot run tao truoc pha 11 va mot run sau do
    khong phan biet duoc ve cau truc, nen khong ai doc duoc mot ho so cu ma biet
    truong nao co the vang mat mot cach hop le;
  · **khong co van tay tong** — moi giai doan tu bam dau vao cua rieng no, con
    "toan bo cau hinh khach chon" thi khong co dai dien nao;
  · **muoi cho doc rai rac**, moi cho chep lai mac dinh cua rieng no.

## 🔴 Va cai thu ba da tro thanh mot lan troi THAT, khong phai mot rui ro

Cung mot khoa `timing_mode`, hai mac dinh khac nhau:

```
giai_doan_thoi_gian.py:95   str(... .get("timing_mode") or "fit_original")
giai_doan_qc.py:154         str(... .get("timing_mode") or "")
```

Nen mot run thieu khoa do se **chay** o che do `fit_original` trong khi **bang
chung QC ghi rong**. Khong cho nao bao loi; hai ben deu tim thay mot gia tri hop
le cua rieng minh. Va `"fit_original"` o dong tren la mot ban CHEP CUNG cua
`gia.CHE_DO_MAC_DINH` — tuc ban thu ba cua cung mot hang so.

⭐ Do la dung hinh dang ma `su-that-doc-lap-chan-suy-luan-sai` mo ta: mot cau
   hoi phai co MOT cho tra loi.

## Hai che do doc, va vi sao chung phai khac nhau

| | LUU (`chuan_hoa`) | DOC (`doc`) |
|---|---|---|
| khoa khong dung toi | **vang mat** | co, mang mac dinh |
| muc dich | de ho so cua mot lan chay khong mang truong no khong dung | de khong ai phai chep mac dinh |

⛔ Luu THUA la mot thay doi co that: `cat_dau_cuoi` L4 va cac ghi chu o
   `routes.tao` noi ro rang "khong thu hep gi thi KHONG ghi khoa nao", vi mot
   mang rong ghi vao moi lan chay lam ho so cua nhung lan **khong** dung tinh
   nang do khac di ma khong vi ly do gi. Nen `chuan_hoa` giu nguyen tinh THUA
   ay, va chi `doc` moi lam day.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from . import gia, hop_dong_v4, ngon_ngu, rang_giong

#: Ten schema. Doi ten nay khi hinh dang doi den muc mot ban doc cu doc sai —
#: khong phai moi lan them mot truong.
SCHEMA = "asv.cai_dat.v3"

#: 🔑 `v3` khong phai "lan sua thu ba". No la thu tu cua **hop dong**: V4 luu
#:    settings phang khong khai gi (v1), V5/V6 them vung/cat/lop phu/logo van
#:    khong khai gi (v2), va day la ban dau tien TU KHAI (v3).
#:
#: ⚠️ Mot ho so KHONG co khoa `schema` la ho so **truoc v3**, khong phai ho so
#:    hong. `doc()` phai nhan no — co that hang nghin ho so nhu the trong CSDL,
#:    va mot lan chay lai tren ho so cu phai cho ra dung ket qua cu.
PHIEN_BAN = 3

#: Khoa mang phien ban trong chinh ho so.
KHOA_SCHEMA = "schema"

#: Nhung khoa CHI ghi khi khach thuc su dung tinh nang. Xem bang o docstring.
#: ⭐ `ho_so_noi_dung` la ho so ma `AUTO_MATCH` dung ra (bang chung + nguon cua
#:    tung mat). No nam o day chu khong o `dich_vu_tao.KHOA_NHAN`: cua tao
#:    **khong** nhan no tu khach — chi `giai_doan_noi_dung` ghi no, mot lan.
#: ⭐ `toc_doc_giong` (B17 §4.1, lan P0-a) cung mot ho: he thong tinh MOT LAN
#:    (`ho_so_dich.voi_toc_doc_giong`), khong phai khach nhap — xem `toc_doc_giong()`
#:    va `KHOA_DAN_XUAT` duoi day.
KHOA_THUA = ("cat", "vung", "lop_phu", "logo", "phu_de", "am_thanh",
             "bien_tap", "lop", "ho_so_noi_dung", "toc_doc_giong")

#: 🔴 **Khoa do CHINH HE THONG ghi vao GIUA mot lan chay, khong phai khach nhap.**
#:
#:    `thi_hanh.van_tay` gom **ca** `run.settings` vao van tay giai doan, va
#:    `jobs._vo_hieu_giai_doan_da_lech` dat lai moi giai doan co van tay lech.
#:    Nen mot dong ghi vao `settings` o giua chuoi se **dat lai media_prepare,
#:    audio_prepare, transcribe va edit_plan** — do duoc: log
#:    *"dat lai 5 giai doan do lech van tay"* xuat hien ngay o ban nhap dau cua
#:    duong `AUTO_MATCH`, tuc demucs + ASR chay lai tu dau. Dung 133 giay ma
#:    `NEN_V3` luot A da dot, lan nay dot theo mot cach khac.
#:
#: ⭐ Nen hai khoa nay bi **loai khoi van tay giai doan**. Dieu do khong lam mat
#:    mot phep vo hieu nao: giong da chot di vao van tay CUA BAN LONG TIENG
#:    (`long_tieng.van_tay_long_tieng` co `ma_giong`), va moi giai doan phia sau
#:    doc giong tu chinh ban long tieng do chu khong doc `settings`.
#:
#: ⛔ Chi them khoa vao day khi no do HE THONG sinh ra. Mot khoa KHACH nhap ma
#:    nam o day se lam mot lan doi cai dat khong vo hieu cache — tuc khach doi
#:    thong so roi nhan lai y nguyen ban cu.
#:
#: 🔑 `toc_doc_giong` (B17 §4.1): ghi tu `ho_so_dich.dung()`, GIUA chuoi
#:    `content_process` — dung hinh dang nguy hiem ma doc o tren canh bao (mot
#:    dong ghi settings giua chuoi lam `jobs._vo_hieu_giai_doan_da_lech` dat
#:    lai media_prepare/audio_prepare/transcribe). Loai no khoi van tay giai
#:    doan KHONG lam mat phep vo hieu nao: gia tri la HAM THUAN cua `giong_id`
#:    + `ngon_ngu_dich` (xem `toc_doc_giong()`), va CA HAI truong ay DA nam
#:    trong `long_tieng.van_tay_long_tieng` (tham so `ma_giong`, `ngon_ngu_dich`)
#:    — doi giong hay doi dich da tu dong lam van tay do khac di roi.
KHOA_DAN_XUAT: frozenset = frozenset(
    {"dac_diem_giong", "ho_so_noi_dung", "toc_doc_giong"})


def cho_van_tay(tho: Mapping | None) -> dict:
    """Ho so DA BO cac khoa dan xuat — ban di vao van tay giai doan.

    Xem `KHOA_DAN_XUAT` ve ly do. ⚠️ Khong chuan hoa o day: `thi_hanh.van_tay`
    bam **dung** thu dang nam trong `run.settings`, va chuan hoa o duong doc lam
    mot ho so cu bong nhien bam ra khac di.
    """
    return {k: v for k, v in dict(tho or {}).items() if k not in KHOA_DAN_XUAT}


# ══════════════════════════════════════════════════════════════════════════════
#  Toc doc CUA GIONG — settings dan xuat, giai chu trinh DAG (B17 §4.1)
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 **Vi sao ham nay ton tai.** `content_process` (giai doan 4/9, B17 §6) can
#    neo do dai cau dich theo toc doc CUA GIONG se doc no — nhung giong that
#    chi duoc CHOT o `voice_synthesis` (giai doan 6), chay SAU dich. Trong DAG:
#    `4 -> 6` theo `sau=`, ma `4` can mot dai luong cua `6` — MOT CHU TRINH.
#
# ⭐ **Cach giai DUY NHAT dung, muon nguyen tu Viral** (`localize.py:1946`
#    `_wps_giong_that`, neo o `docs/auto_scan_video_final/B17_PLAN_TRIEN_KHAI_
#    THEO_VIRAL.md` §4.1): KHONG do giong luc chay. Tra mot BANG DA DO TRUOC —
#    ham THUAN cua `giong_id` + hang so trong ma — nen tinh duoc TU DAU, khong
#    doi giai doan nao khac chay xong. ⛔ KHONG cai kieu "giai doan giong do
#    roi bao lai giai doan dich": ca ay KHONG no — no chi neo SAI, va khong
#    phep kiem nao do.
#
# ⚠️ **`min()` MOT CHIEU** (copy nguyen tinh chat cua Viral `localize.py:
#    15112-15117`, nguyen van *"CHI SIET, KHONG NOI"*): xem `toc_doc_giong()`.

#: Bang toc doc DA DO theo TUNG GIONG cu the — don vi la `ngon_ngu.DON_VI_DO_DAI`
#: cua ngon ngu DICH, moi giay. Khoa la MA GIONG (gia tri `giong_id`/`ma_giong`
#: LTT Voice tra ve), KHONG phai ten hien thi.
#:
#: 🔴 Neo Viral `:15109` do theo NGON NGU CUA GIONG (7 dong `id/en/es/vi/pt/
#:    ko/fr`) — MOT bang khac, dung o MOT cho khac (`dich_gemini_web._TU_MOI_
#:    GIAY`, hang so theo dich). Bang o DAY dong vai `capcut_tts.toc_doc` cua
#:    ho (`:15136`): do theo TUNG GIONG rieng le, ⛔ khong theo ngon ngu — cai
#:    do o ta la `ngon_ngu.NHIP`.
#:
#: ⛔ **RONG hom nay, va do la mot su that trung thuc chu khong phai mot cho
#:    dang do.** LTT Voice co nhieu giong cung mot dich, nhung ta moi do TOC
#:    DO THAT cho DUNG MOT giong tham chieu moi dich (`vi`: "Minh Duc"; `en`:
#:    giong khao chuan — xem docstring `ngon_ngu.NHIP`), va so do do da nam
#:    trong `ngon_ngu.NHIP` roi. Bang rong ⇒ `toc_doc_giong()` luon roi vao
#:    duong lui (hang so ngon ngu) cho MOI giong — DUNG hanh vi hom nay
#:    (`ngon_ngu.ngan_sach_do_dai` cung dang dung chung mot hang so cho moi
#:    giong), khong phai mot hoi quy. Do THAT them mot giong thi them DUNG
#:    mot dong o day, khoa la ma giong do — khong doi gi khac.
TOC_DOC_GIONG_DA_DO: dict[str, float] = {}


def toc_doc_giong(giong_id: str, ngon_ngu_dich,
                  *, bang: Mapping[str, float] | None = None) -> float:
    """Toc doc CUA GIONG `giong_id` khi doc tieng `ngon_ngu_dich` — ham THUAN.

    Dung `bang` (mac dinh `TOC_DOC_GIONG_DA_DO`) tra so do RIENG cho giong nay;
    khong co thi tra thang **hang so ca-ngon-ngu** `ngon_ngu.NHIP[dich]` — day
    la **duong lui TUONG MINH** cho ca "chua do giong nay", tach bach voi ca
    "da do ra giong CHAM/NHANH hon". ⛔ Khong bao gio tra `0`: `0` gop hai
    trang thai "chua do" va "do ra bang khong" thanh mot, xem
    [[hai-trang-thai-gop-thanh-mot-gia-tri]].

    Dich ngoai hop dong (`ngon_ngu.DICH_HOP_LE`) ⇒ nem `NgonNguError` cua
    chinh `ngon_ngu` — CUNG mot cua loi voi `ngan_sach_do_dai`, khong phai mot
    cua rieng cho ham nay.

    ⚠️ **`min()` MOT CHIEU — CHI SIET, KHONG NOI.** Copy nguyen tinh chat cua
       Viral (`localize.py:15112-15117`, nguyen van *"CHI SIET, KHONG NOI"*):

           giong do CHAM hon hang so  ⇒ neo bi SIET theo giong cham do (khach
                                         doc kip khe da cho)
           giong do NHANH hon hang so ⇒ neo GIU NGUYEN hang so, ⛔ KHONG noi
                                         len theo giong nhanh

       Ly do KHONG noi: noi neo cho giong nhanh se cho mot ban dich DAI hon,
       roi TTS phai nen (atempo) NANG hon de doc kip khe cu — dung NGUOC voi
       muc dich cua viec neo do dai. Ha neo cho giong cham thi chi co loi,
       nen `min()` la phep an toan MOT CHIEU — khong ca nao te di.
    """
    d = ngon_ngu.chuan_dich(ngon_ngu_dich)
    hang_so_ngon_ngu = ngon_ngu.NHIP.get(d)
    if hang_so_ngon_ngu is None:
        raise ngon_ngu.NgonNguError(f"dich {d!r} khong nam trong hop dong")
    bang_do = TOC_DOC_GIONG_DA_DO if bang is None else bang
    do_rieng = bang_do.get(str(giong_id or "").strip())
    if not do_rieng or do_rieng <= 0:
        return hang_so_ngon_ngu
    return min(hang_so_ngon_ngu, float(do_rieng))


def voi_toc_doc_giong(tho: Mapping | None,
                      *, bang: Mapping[str, float] | None = None) -> dict:
    """Ho so nguyen ven, kem THEM khoa `toc_doc_giong` da tinh.

    Ham THUAN tren dict — khong cham DB/`run`.

    🔴 **KHONG goi `chuan_hoa()` o day — bai hoc do duoc khi viet lan nay.**
       Ban dau ham nay tra `chuan_hoa(tho)` (cung khuon `ho_so_noi_dung.bao_dam`),
       va do LAM VO mot phep kiem dau-cuoi that (`test_408::TestAnToanCuocGoiTraTien
       ::test_giai_doan_hong_MO_HO_thi_job_KHONG_quay_lai_hang_doi`): `tao_run`
       luu `settings` THO, ⛔ CHUA chuan hoa (`features.tao_run`), va cac giai
       doan TRUOC (`media_prepare`/`audio_prepare`/`transcribe`) da tinh van
       tay tren ban THO do. Goi lai `chuan_hoa()` giua chuoi doi HINH DANG ca
       nhung khoa KHONG lien quan (them `preset`/`timing_mode`/`che_do_giong`/
       `voice_id`/`ngon_ngu_nguon`/`tu_dien` mac dinh) — `cho_van_tay` doi theo,
       va `jobs._vo_hieu_giai_doan_da_lech` **dat lai ca bon giai doan truoc
       do**, dung hinh dang canh bao o docstring `KHOA_DAN_XUAT`. `KHOA_DAN_XUAT`
       chi loai tru mot KHOA, no ⛔ khong bao ve duoc truoc viec dinh dang LAI
       toan bo cac khoa con lai.

    ⇒ Chi THEM dung mot khoa, giu MOI thu khac y nguyen tung bit — an toan du
       `tho` dang o hinh dang nao (tho hay da chuan hoa).

    🔑 **Ghi VO DIEU KIEN, khong canh gac "da co chua".** `toc_doc_giong()` la
       ham THUAN cua `giong_id`/`ngon_ngu_dich` — hai truong nay khong doi
       giua cac lan goi TRONG CUNG mot lan chay, nen goi lai nhieu lan (mot
       VONG SUA cua `content_process`) tren cung dau vao cho ra CUNG mot ket
       qua. Khac voi `ho_so_noi_dung.bao_dam` (goi MODEL, ton tien nen phai
       canh "da co chua"), o day khong co gi de tiet kiem ca.

    🔴 **Vi sao goi tu `ho_so_dich.py`, khong phai tu giai doan MEDIA_PREPARE
       that su (GD1 that):** lan nay (B17, P0-a) chi so huu `cai_dat.py` +
       `ho_so_dich.py`. Nhung ket qua GIONG HET du goi o GD1 hay o day, vi
       `toc_doc_giong()` khong doc gi ngoai hai truong da co san trong
       `settings` TU TRUOC `content_process`. "Tinh o giai doan 1" (B17 §4.1)
       la mot dac tinh cua HAM (thuan, khong doi giong khac chay xong), khong
       phai mot rang buoc ve NOI GOI — goi som hay muon deu ra dung mot so.
    """
    ra = dict(tho or {})
    tam = tu_ho_so(ra)
    ra["toc_doc_giong"] = toc_doc_giong(tam.giong_id, tam.ngon_ngu_dich, bang=bang)
    return ra


#: ⛔ `voice_id` la mot BI DANH cu cua `giong_id`, khong phai mot truong thu hai.
#:    Xem `rang_giong.tu_thiet_lap`: hai khoa nay da song song mot thoi gian va
#:    mot lan chay co the viet loi thoai CHO mot giong roi doc len bang giong
#:    KHAC. Ta giu no khi GHI (cho ban doc cu), va hop nhat khi DOC.
KHOA_BI_DANH_GIONG = "voice_id"


@dataclass(frozen=True)
class DacDiem:
    """Dac diem giong khach mong muon. Rong = khong kem."""

    gioi: str = ""
    vung: str = ""
    phong_cach: str = ""


@dataclass(frozen=True)
class CaiDat:
    """Ban doc TOAN PHAN cua mot ho so. Moi truong luon co mat."""

    preset: str
    timing_mode: str
    che_do_giong: str
    giong_id: str
    ngon_ngu_nguon: str
    dac_diem: DacDiem
    #: Ngon ngu DICH (22/09). Ho so cu khong co khoa nay la ho so `vi` — V4-V6
    #: chi sinh tieng Viet, nen do la mot SU THAT ve chung, khong phai doan.
    ngon_ngu_dich: str = ngon_ngu.DICH_MAC_DINH
    tu_dien: dict = field(default_factory=dict)
    cat: tuple[float, float] | None = None
    vung: tuple = ()
    lop_phu: tuple = ()
    logo: tuple = ()
    #: Ho so phu de (V6 pha 14), hoac `None`. Xem `phu_de.chuan_hoa`.
    #:
    #: ⚠️ `dict` chu khong `tuple` nhu ba truong tren, va do la khac biet CO
    #:    THAT chu khong phai thieu nhat quan: `vung`/`lop_phu`/`logo` la N mon
    #:    khach them tung cai mot, con phu de la MOT quyet dinh cho ca video.
    phu_de: dict | None = None
    #: Ho so am thanh (V6 pha 23), hoac `None` = mac dinh. Xem `am_thanh.py`.
    am_thanh: dict | None = None
    #: Ho so bien tap khung + toc do (asv-final), hoac `None`. Xem `bien_tap.py`.
    bien_tap: dict | None = None
    #: Ho so BA LOP nen (B2/B5, `giong_bat/gain`, `nhac_bat/gain`, `vfx_bat/gain`),
    #: hoac `None` = mac dinh (giong TAT, nhac+vfx BAT o gain 1,0). Xem
    #: `tach_tieng.LOP_STEM`/`chuan_hoa_lop`.
    lop: dict | None = None
    #: Toc doc CUA GIONG da chot (B17 §4.1, `toc_doc_giong()`), hoac `None` =
    #: **chua tinh** — mot lan chay chua qua `content_process` (ho_so_dich.dung)
    #: thi khoa nay CHUA CO trong `settings`. `None` o day KHONG phai loi doc:
    #: cung mot cau chuyen voi `phu_de`/`am_thanh` — "chua co" la mot trang
    #: thai hop le, phan biet voi "da tinh ra 0" (khong bao gio xay ra, xem
    #: `toc_doc_giong()`).
    toc_doc_giong: float | None = None

    @property
    def co_sua_diem_anh(self) -> bool:
        """Co bat ky dieu khien nao doi DIEM ANH khong.

        ⭐ Cau hoi nay tung phai tra loi bang cach hoi rieng bon danh sach o bon
           cho. Mot cho hoi la mot cho phai cap nhat khi co dieu khien thu nam.
        """
        # ⭐ `co_dot_vao_hinh`, khong phai `bool(self.phu_de)`: mot ho so chi
        #    `xuat_srt` KHONG cham mot diem anh nao. Hoi sai o day se lam mot
        #    lan chay chi-xuat-SRT bi doi xu nhu mot lan ma hoa lai — tuc cam
        #    no o preset giu hinh, dung noi ma no la lua chon DUY NHAT con lai.
        from . import phu_de as _pd
        return bool(self.vung or self.lop_phu or self.logo or self.bien_tap
                    or _pd.co_dot_vao_hinh(self.phu_de))


def _chuoi(tho: Mapping, khoa: str, mac_dinh: str = "") -> str:
    return str(tho.get(khoa) or mac_dinh)


def chuan_hoa(tho: Mapping | None) -> dict:
    """Ho so THUA, da khai phien ban. Dung khi GHI.

    ⛔ Ham nay KHONG dien mac dinh vao nhung khoa vang mat co chu dich
       (`KHOA_THUA`). Xem bang o docstring dau tep: lam day chung se doi ho so
       cua moi lan chay **khong** dung cac tinh nang do.

    ⭐ Bat bien: `chuan_hoa(chuan_hoa(x)) == chuan_hoa(x)`. Mot ham chuan hoa ma
       khong luy dang thi moi lan luu lai se cho mot ho so khac, tuc van tay doi
       ma cau hinh thi khong — dung kieu hong ma `sap-xep-list-trong-van-tay`
       ghi lai.
    """
    tho = dict(tho or {})
    ra: dict = {KHOA_SCHEMA: SCHEMA}

    ra["preset"] = _chuoi(tho, "preset", hop_dong_v4.PRESET_MAC_DINH)
    ra["timing_mode"] = _chuoi(tho, "timing_mode", gia.CHE_DO_MAC_DINH)
    ra["che_do_giong"] = _chuoi(tho, "che_do_giong",
                                rang_giong.CHE_DO_GIONG_MAC_DINH)

    giong = _chuoi(tho, "giong_id") or _chuoi(tho, KHOA_BI_DANH_GIONG)
    ra["giong_id"] = giong
    # Giu bi danh cho ban doc cu; xem `KHOA_BI_DANH_GIONG`.
    ra[KHOA_BI_DANH_GIONG] = giong

    ra["ngon_ngu_nguon"] = _chuoi(tho, "ngon_ngu_nguon")
    ra["ngon_ngu_dich"] = ngon_ngu.chuan_dich(tho.get("ngon_ngu_dich"))
    ra["tu_dien"] = dict(tho.get("tu_dien") or {})
    # ⛔ `nguon_loi` KHONG con la mot khoa ho so (Task 21, 26/09): mot duong
    #    duy nhat voice->voice ⇒ khong co gi de chon, nen khong co gi de luu.
    #    Mot ho so cu mang khoa nay di qua day se KHONG duoc ghi lai — dung y,
    #    va `dich_vu_tao` da ghi mot dong log truoc do (`nguon_loi.chuan_che_do`).
    dd = tho.get("dac_diem_giong") or {}
    if dd:
        ra["dac_diem_giong"] = {
            "gioi": str(dd.get("gioi") or ""),
            "vung": str(dd.get("vung") or ""),
            "phong_cach": str(dd.get("phong_cach") or "")}

    for k in KHOA_THUA:
        v = tho.get(k)
        if v:
            ra[k] = v

    return ra


def tu_ho_so(tho: Mapping | None) -> CaiDat:
    """Ban doc TOAN PHAN. Nhan ca ho so truoc v3 (khong co khoa `schema`).

    🔑 Day la cho DUY NHAT dat mac dinh. Truoc pha 07 chung nam o muoi cho, va
       hai trong so do da lech nhau ve `timing_mode`.
    """
    tho = dict(tho or {})
    dd = tho.get("dac_diem_giong") or {}
    cat = tho.get("cat")
    return CaiDat(
        preset=_chuoi(tho, "preset", hop_dong_v4.PRESET_MAC_DINH),
        timing_mode=_chuoi(tho, "timing_mode", gia.CHE_DO_MAC_DINH),
        che_do_giong=_chuoi(tho, "che_do_giong",
                            rang_giong.CHE_DO_GIONG_MAC_DINH),
        giong_id=_chuoi(tho, "giong_id") or _chuoi(tho, KHOA_BI_DANH_GIONG),
        ngon_ngu_nguon=_chuoi(tho, "ngon_ngu_nguon"),
        ngon_ngu_dich=ngon_ngu.chuan_dich(tho.get("ngon_ngu_dich")),
        dac_diem=DacDiem(gioi=str(dd.get("gioi") or ""),
                         vung=str(dd.get("vung") or ""),
                         phong_cach=str(dd.get("phong_cach") or "")),
        tu_dien=dict(tho.get("tu_dien") or {}),
        cat=(float(cat[0]), float(cat[1])) if cat else None,
        vung=tuple(tho.get("vung") or ()),
        lop_phu=tuple(tho.get("lop_phu") or ()),
        logo=tuple(tho.get("logo") or ()),
        # ⛔ KHONG goi `phu_de.chuan_hoa` o day. Duong GHI da chuan hoa (routes),
        #    va chuan hoa lan hai o duong DOC lam mot ho so cu bong nhien doc ra
        #    khac di — tuc doi van tay cua nhung lan chay da xong. Cung luat ma
        #    `vung` dang theo: *"ban da luu moi la ban that"*.
        phu_de=(dict(tho.get("phu_de")) if tho.get("phu_de") else None),
        am_thanh=(dict(am) if (am := tho.get("am_thanh")) else None),
        bien_tap=(dict(bt) if (bt := tho.get("bien_tap")) else None),
        lop=(dict(lp) if (lp := tho.get("lop")) else None),
        # `None` = chua tinh (xem docstring truong `toc_doc_giong` tren
        # `CaiDat`) — kiem `is not None`, KHONG kiem truthy: `0.0` se khong
        # bao gio xay ra tren duong ghi that (`toc_doc_giong()`), nhung mot
        # ho so bi go tay/hong khong duoc lang le doi no thanh "chua tinh".
        toc_doc_giong=(float(tdg) if (tdg := tho.get("toc_doc_giong")) is not None
                      else None))


def doc(run) -> CaiDat:
    """Ban doc toan phan cua mot lan chay. Mot cho, cho moi giai doan."""
    return tu_ho_so(getattr(run, "settings", None))


def van_tay(tho: Mapping | None) -> str:
    """Van tay cua TOAN BO cau hinh khach chon.

    ⛔ **Khong luu gia tri nay xuong.** Mot van tay duoc luu la mot van tay se
       cu di trong khi thu no dai dien thi doi — va no cu **im lang**, vi mot
       chuoi bam trong khong khac gi mot chuoi bam dung. Tinh khi can.

    ⚠️ `sort_keys=True` sap KHOA, khong sap PHAN TU CUA LIST — va o day dung la
       ta muon vay: thu tu cac lop phu, cac vung, cac logo **co y nghia** (thu
       tu ve chong len nhau, va thu tu cac `<input type=file>` trong multipart).
       Them mot `sorted()` cho chung se lam hai cau hinh khac nhau dung chung
       mot van tay. Xem `sap-xep-list-trong-van-tay-hai-chieu-hong`.
    """
    goi = json.dumps(chuan_hoa(tho), sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"))
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()[:16]


def phien_ban_ho_so(tho: Mapping | None) -> int:
    """`3` neu ho so tu khai, `0` neu la ho so truoc v3.

    ⭐ `0` chu khong phai `None`: mot ho so cu la mot ho so **co that va doc
       duoc**, khong phai mot ho so thieu du lieu. Tra `None` se moi nguoi doc
       viet mot nhanh `if ... is None` cho mot truong hop hoan toan binh thuong.
    """
    return PHIEN_BAN if str((tho or {}).get(KHOA_SCHEMA) or "") == SCHEMA else 0
