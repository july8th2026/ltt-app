"""QC — cong chat luong cuoi cung. Thi hanh `MVP_CONTRACT.md` §7, muoi hai dung sai.

## Vi sao QC la ma MOI, khong phai ma muon

RISK-00-14 ghi tu pha 00: *"Chinh sach QC khong co nguon o dau ca. Ca ba cay di
san deu sinh ra ket qua; khong cay nao GAT no."* Do la mot cau dang nho: mot bo
render khong co cong chat luong van chay duoc hang nam, vi cai thieu chi lo ra
khi ai do nhin ky mot ket qua — va khong ai nhin ky moi ket qua.

⇒ Tep nay khong boc mot engine nao. No do, roi so voi mot con so da dong bang.

## Con so o day KHONG duoc phat minh trong pha nay

Moi nguong den tu `MVP_CONTRACT.md` §7, dong bang o pha 02, va moi dong ghi ro
nguon. Doi mot nguong o day ma khong doi hop dong la lam hai tai lieu noi hai
dieu khac nhau — va tai lieu se thua, vi ma chay con tai lieu thi khong.

⚠️ **T8/T9/T10 khong ap dung cho MVP nay, va do la mot phat hien chu khong phai
   mot thieu sot.** Ba dung sai do do viec **CHEN khoang lang** (nguon:
   `Bot_PausePipeline/engine/insertion_planner.py`). Chung duoc viet o pha 02.
   Den pha 13, ADR-003 doi mo hinh thoi gian: ta **khong chen** khoang lang nao
   ca, ta **muon** khoang lang san co lam ngan sach. Nen ba dung sai do khong
   con chu the de do.

   ⛔ Cach xu ly SAI la lang le bo chung khoi bao cao: mot cong chat luong it
      muc hon ma khong noi gi trong y het mot cong day du. Chung duoc bao cao la
      `khong_ap_dung` **kem ly do**, va `test_420` chot rang chung khong bao gio
      duoc bao la `dat`.
"""
from __future__ import annotations

import json
import re
import subprocess

from platform_core import media
from platform_core.i18n import _ as _t

from . import tach_tieng, thoi_gian

#: Doi khi doi bat ky nguong nao. Vao van tay (O13).
#:
#: ⭐ 1 → 2 o pha 18: QC tro thanh **biet che do render**. Neu khong nang so nay
#:    thi mot lan chay lai se dung lai bao cao QC cu tu cache — bao cao duoc lam
#:    boi mot bo luat khong biet preset cat ton tai.
#: ⭐ 2 → 3 o pha 27: bo kiem co them T14/T15/T16. Khong nang so nay thi mot
#:    lan chay lai se dung lai bao cao cu tu cache — bao cao do mot bo luat
#:    **chua biet ba phep kiem nay ton tai** lam ra, va no se bao "dat".
#: ⭐ 3 → 4 (asv-final) — HAI thay doi cung mot ban:
#:    · lan `phu-de`/`bien-tap`: T15 doi moc phu de sang truc BAN RA theo `toc_do`;
#:    · lan `ky-thuat`: T13 bo YAVG tu dat, thay bang `blackdetect` +
#:      `freezedetect` cua ffmpeg; them T17 (giai ma ca tep) va T18 (VMAF
#:      cua lan ma hoa lai). Bang do: `docs/auto_scan_video_final/L_KY_THUAT.md`.
PHIEN_BAN_QC = 4

# ── T13 — khung den / hinh dong bang: bo loc CHUAN cua ffmpeg ─────────────────
#
# 🔴 Ban truoc do YAVG trung binh cua 12 khung lay mau voi nguong 2/255 TU DAT.
#    No khong bat duoc mot ban ra den 40% hay dong bang mot khung suot 30 giay,
#    va con so 2/255 khong co nguon. Da xoa.
#
# ⭐ Tham so = MAC DINH tai lieu ffmpeg (ffmpeg-filters, muc blackdetect /
#    freezedetect), khong chinh:
#      blackdetect  d=2.0      do dai toi thieu mot khoang den (giay)
#                   pic_th=0.98 ti le diem anh "den" de goi ca khung la den
#                   pix_th=0.10 nguong do sang mot diem anh (0-1)
#      freezedetect n=-60dB    dung sai nhieu (MAFD) giua hai khung
#                   d=2        do dai toi thieu mot khoang dong bang (giay)
#
# 🔑 **So voi NGUON, khong so voi mot ti le tuyet doi.** Mot nguon hop le co the
#    dong bang ca video (podcast mot anh tinh, slide) hay co man den mo dau;
#    ban ra la mot TAP CON thoi gian cua nguon (hai preset), nen render dung thi
#    so giay den/dong bang cua ban ra KHONG vuot cua nguon. HONG khi phan vuot
#    > `DEN_DONG_DU_S` — tuc render da TAO RA hinh den / dong bang.
#    Do tren 4 video that (576p, 107-275 s): nguon 0 s den, 0 s dong bang; ban
#    ma hoa lai libx264 crf23: 0 s / 0 s ⇒ lan ma hoa khong sinh khoang nao.
BLACKDETECT = "blackdetect=d=2.0:pic_th=0.98:pix_th=0.10"
FREEZEDETECT = "freezedetect=n=-60dB:d=2"
#: Phan vuot cho phep (giay): chi de hap thu rung moc thoi gian o bien khoang.
#: Moi khoang ffmpeg bao ra da dai >= 2 s (`d`), nen mot khoang MOI bat ky
#: deu vuot con so nay.
DEN_DONG_DU_S = 0.5

# ── T18 — VMAF cua lan MA HOA LAI (chi preset cat) ─────────────────────────────
#
# 🔑 Ban ra khac nguon CO CHU DICH (cat, che, logo, chu, phu de), nen VMAF
#    nguon-vs-ra la sai. Tham chieu = CHINH chuoi loc render (`loc_tham_chieu`)
#    chay lai tren nguon, KHONG ma hoa, so tung khung voi ban da ma hoa trong
#    CUNG mot lenh ffmpeg (khong ghi tep tham chieu) ⇒ do DUNG thiet hai cua bo
#    ma hoa, khong gi khac.
#
# ⭐ Mo hinh theo khung (Netflix/vmaf `resource/doc/faq.md`, `models.md`):
#    `vmaf_v0.6.1` du doan TV 1080p xem o 3H; tinh o 576p goc tuong duong xem o
#    ~5,6H va che giau loi ⇒ ca hai phia duoc CO GIAN vao khung 1920x1080 (giu ti
#    le, bicubic) nhu FAQ huong dan. Canh ngan >= 2160 ⇒ `vmaf_4k_v0.6.1` o do
#    phan giai goc. KHONG bat `phone_model`: san pham chua khai muc tieu dien
#    thoai, va mo hinh TV la phia NGHIEM hon.
MO_HINH_VMAF = "vmaf_v0.6.1"
MO_HINH_VMAF_4K = "vmaf_4k_v0.6.1"
#: Lay 1 khung / N de tinh (libvmaf `n_subsample`).
#:
#: ⭐ Do tren 4 video that: sub5 lech sub1 **0,01-0,10 diem** o diem trung binh,
#:    ma re hon 3 lan (v1: 318,9 s -> 97,2 s tren 2 luong). Bang do:
#:    `docs/auto_scan_video_final/L_KY_THUAT.md` §2.
VMAF_N_SUBSAMPLE = 5

#: Nguong HONG tren diem VMAF TRUNG BINH (khong phai khung te nhat).
#:
#: 🔑 **Khong phai mot con so cam giac — no nam giua hai dam may DA DO** (4 video
#:    that, chuoi loc render that, mo hinh 1080p):
#:
#:        bo ma hoa san pham (libx264 veryfast crf23)   86,3 · 87,1 · 88,6 · 90,1
#:        crf30 (hong nhe)                              62,6 · 67,7 · 68,2 · 68,9
#:        crf36 / crf45 (hong nang)                     36,7-47,8 / 11,7-17,6
#:        tham chieu khong mat mat (FFV1) — chieu am     98,2-100,0
#:
#: ⇒ 75 cach ban te nhat cua duong SAN XUAT 11,3 diem ve phia duoi va cach ban
#:   tot nhat cua duong HONG 6,1 diem ve phia tren. Sai so day ve phia KHONG
#:   hanh dong: mot muc HONG o day chan mot video da render xong.
#:
#: ⚠️ Khung te nhat cua mot ban crf23 binh thuong xuong toi 70,2 — nen chot o
#:    `nho_nhat` se danh hong nhung lan chay hoan toan binh thuong. Bao cao van
#:    GHI `nho_nhat`/`p5` de nguoi doc thay phan duoi cua phan bo.
VMAF_TOI_THIEU = 75.0

#: T14 — chinh sach render. Khong co nguong: hoac khop, hoac khong.
#:
#: 🔑 T3 da hoi *"luong hinh co giong nguon tung bit khong"* — nhung no roi ve
#:    `KHONG_AP_DUNG` khi khong bam duoc, va do la mot lo that: khi ay **khong
#:    ai** kiem loi hua cua preset giu hinh. T14 la luoi thu hai, va no mien
#:    phi: bon truong duoi da nam san trong ket qua ffprobe da chay.

#: T15 — bien phu de. Dung sai cho phep mot dong ket dung o cuoi ban ra.
#:
#: ⭐ Bang `ket_xuat.LECH_THOI_LUONG_GIAY` co chu dich: `kiem_tep_ra` da cuong
#:    che tep ra khong lech qua nguong do so voi ban dung, nen mot dong phu de
#:    nam trong ban dung cung khong the vuot ban ra qua nguong do. Dat chat hon
#:    la bao hong nhung lan chay hoan toan binh thuong.
BIEN_PHU_DE_DUNG_SAI_S = 0.50

#: T16 — lech giua do dai luong HINH va luong TIENG.
#:
#: 🔴 **Do tren chuoi lenh THAT, khong muon.** Do 11/09/2026 bang chinh
#:    `ket_xuat.dung_lenh`, ca hai duong render, gom ca nhip le 30000/1001:
#:
#:        giu hinh   30 fps        lech 0,0000 s
#:        cat        30 fps        lech 0,0000 s
#:        cat        29,97 fps     lech 0,0206 s
#:
#: ⭐ 0,50 s cho du dia **24 lan** muc te nhat da do. Rong the la co y: mot muc
#:    HONG o day CHAN mot video da render xong, nen sai so phai day ve phia
#:    KHONG hanh dong. Va 0,5 giay lech tieng-hinh thi tai nguoi nghe duoc.
#:
#: ⚠️ Ban do dau tien cua toi dung mot lenh ffmpeg TU VIET (0,0234 s) — no do
#:    mot thu khac: chuoi that con `trim`+`concat`, `amix`+`loudnorm` va
#:    `-shortest`, moi mat xich deu doi duoc do dai mot luong.
LECH_TIENG_HINH_S = 0.50

DAT = "dat"
HONG = "hong"
KHONG_AP_DUNG = "khong_ap_dung"

# ── Nguong, tu MVP_CONTRACT §7 ────────────────────────────────────────────────
#: T2 — thoi luong ban ra so voi nguon.
LECH_THOI_LUONG_S = 0.50

#: T2 — bao nhieu GIAY dai hon MONG DOI van con la "khong dai hon".
#:
#: 🔴 **Khong phai mot noi long chinh sach — la DO PHAN GIAI cua phep so sanh.**
#:
#:    `mong_doi` khong do duoc tu tep ra: no di qua `BanDoThoiGian.sang_dict`,
#:    ham nay lam tron TUNG moc giu ve 4 chu so thap phan
#:    (`ban_do_thoi_gian.py:190`). Moi khoang giu vi the mang toi ±1e-4 s sai so
#:    lam tron, va container MP4 con lam tron lan nua theo timebase cua no.
#:
#: ⛔ Da do that, 23/09, nghiem thu cuoi luot A (v3, 30 fps, 106,833333 s):
#:    ban do luu 106,8333 · tep ra 106,833333 · `lech = +3,3e-5` ⇒ `lech <= 0`
#:    SAI ⇒ T2 **hong** tren mot ban giao khong sai mot khung hinh nao. Truoc
#:    ban sua R-02 loi nay bi che: `-shortest` cat bot hai goi hinh cuoi nen ban
#:    ra luon NGAN hon — T2 xanh vi mot khiem khuyet khac (T3 do).
#:
#: ⭐ 0,01 s = 100 lan do phan giai lam tron cua mot moc, va van nho hon
#:    `LECH_THOI_LUONG_S` hai bac: loi hua "khong bao gio dai hon" giu nguyen
#:    nghia (`test_444` chot mot ban ra dai hon 0,3 s van HONG).
DAI_HON_CHO_PHEP_S = 0.01
#: T4 — am luong tich hop. Cung so `tach_tieng` dung de CHUAN HOA, va do la co y:
#: chuan hoa toi mot dich roi do bang mot dich khac la tu bay minh.
#:
#: 🔴 **A26-04 (P3, pha 26) — va no duoc GIU nguyen mot cach co y, khong phai bo
#:    qua.** Chia se hang so voi ben SAN XUAT co nghia la T4/T5 chi hoi duoc
#:    *"co trung dich da nham khong"*. No bat duoc mot loi thi hanh va **khong
#:    the** bat duoc mot dich SAI.
#:
#: ⭐ Bang chung rang hinh dang nay co that chu khong ly thuyet: pha 24 nham dung
#:    tran (-1,5 dBTP) va giao -1,45 dBTP. Khoang lech do tim ra duoc chi vi
#:    duong DO khac duong SAN XUAT (AAC dau ra so voi PCM master) — khong phai
#:    vi phep kiem chat van cai dich.
#:
#: ⇒ Voi MVP, chia se hang so la DUNG: cau hoi dang hoi la "duong ong co lam
#:   dung thu no duoc bao khong". Mot **quy cach ban giao** la mot tai lieu
#:   khac, va no chua ton tai.
#:
#: ⛔ DIEU KIEN DE DOI: ngay co mot quy cach ban giao (mot muc am luong hua voi
#:    khach, mot chuan nen tang phat, mot yeu cau cua doi tac), T4/T5 phai doc
#:    **tai lieu do** chu khong doc `tach_tieng`. Khong duoc dan xep bang cach
#:    chep so sang day — hai ban sao cua mot dich la hai dich se lech nhau.
LUFS_DICH = tach_tieng.LUFS_DICH
LUFS_DUNG_SAI = 1.0
#: T5 — dinh that.
DINH_THAT_TOI_DA_DB = tach_tieng.DINH_THAT_DB
#: T7 — troi cua mot doan so voi vi tri DA HOACH DINH cua no.
#: ⚠️ So voi vi tri hoach dinh, KHONG so voi vi tri goc: ADR-003 lam viec doan
#:    tran qua vi tri goc thanh **thiet ke**, va T11 moi la thu do phan do.
TROI_MOI_DOAN_S = 0.30
#: T11 — troi tich luy, tinh bang so doan. `thoi_gian` cuong che no khi lap ke
#: hoach; o day ta do lai ban ra, vi mot chot chi dung khi no duoc kiem hai dau.
TRAN_TROI_SO_DOAN = thoi_gian.TRAN_TROI_SO_DOAN


class QcError(RuntimeError):
    """QC khong chay duoc. KHAC voi "QC chay xong va ket qua hong"."""


def _muc(ma: str, trang_thai: str, mo_ta: str, **so) -> dict:
    return {"ma": ma, "trang_thai": trang_thai, "mo_ta": mo_ta, **so}


def bam_luong_hinh(duong: str, *, timeout: int = 600) -> str:
    """MD5 cua RIENG luong hinh, khong ke container.

    🔑 T3 doi "luong hinh giong het nguon tung bit". Bam ca tep thi khong tra
       loi duoc: tep ra co container khac, co luong tieng khac, co moov atom o
       cho khac. Chi `-map 0:v -c copy -f md5` moi so dung thu can so.
    """
    cmd = [media.ffmpeg_bin(), "-v", "error", "-i", duong,
           "-map", "0:v:0", "-c", "copy", "-f", "md5", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise QcError(_t('Không băm được luồng hình.'))
    ra = (r.stdout or b"").decode("utf-8", "replace").strip()
    return ra.split("=", 1)[1] if "=" in ra else ra


_RE_DEN = re.compile(r"black_start:\s*([0-9.]+)\s+black_end:\s*([0-9.]+)")
_RE_DONG_BAT = re.compile(r"freeze_start:\s*([0-9.]+)")
_RE_DONG_KET = re.compile(r"freeze_end:\s*([0-9.]+)")


def lenh_do_hinh(duong: str) -> list[str]:
    """MOT luot giai ma ca tep: `blackdetect` + `freezedetect` + bat loi giai ma.

    ⭐ Khong `-map`: ffmpeg chon luong hinh VA luong tieng tot nhat, nen T17 giai
       ma ca hai. `level+info` gan nhan `[error]` cho tung dong — cach duy nhat
       tach loi giai ma khoi dong bao cua hai bo loc (cung muc info).
    """
    return [media.ffmpeg_bin(), "-hide_banner", "-nostdin",
            "-loglevel", "level+info", "-i", str(duong),
            "-vf", f"{BLACKDETECT},{FREEZEDETECT}", "-f", "null", "-"]


def doc_do_hinh(stderr: str, *, thoi_luong: float, ma_thoat: int = 0) -> dict:
    """Doc stderr cua `lenh_do_hinh`. Ham thuan — kiem duoc khong can ffmpeg.

    ⚠️ `freezedetect` khong in `freeze_end` cho mot khoang dong bang keo toi het
       tep; khi do khoang ket o `thoi_luong`.
    """
    van = stderr or ""
    den = [(float(a), float(b)) for a, b in _RE_DEN.findall(van)]
    bat = [float(x) for x in _RE_DONG_BAT.findall(van)]
    ket = [float(x) for x in _RE_DONG_KET.findall(van)]
    if len(ket) < len(bat):
        ket.append(max(float(thoi_luong or 0.0), bat[-1]))
    # ⚠️ Cat cho BANG nhau truoc khi ghep: mot `freeze_end` mo coi (ffmpeg doi
    #    cach in, tep hong) se lam `zip` cat IM LANG mot khoang dong bang that.
    ket = ket[:len(bat)]
    dong = list(zip(bat, ket, strict=True))
    loi = [dong_log.strip() for dong_log in van.splitlines()
           if "[error]" in dong_log or "[fatal]" in dong_log]
    return {
        "den_s": round(sum(b - a for a, b in den), 3),
        "dong_s": round(sum(b - a for a, b in dong), 3),
        "khoang_den": [[round(a, 3), round(b, 3)] for a, b in den][:20],
        "khoang_dong": [[round(a, 3), round(b, 3)] for a, b in dong][:20],
        "so_loi_giai_ma": len(loi),
        "loi_giai_ma": loi[:5],
        "ma_thoat": int(ma_thoat),
    }


def do_hinh(duong: str, *, thoi_luong: float, timeout: int = 3600) -> dict:
    """Chay `lenh_do_hinh`. Nem `QcError` khi KHONG CHAY duoc ffmpeg — khac voi
    ffmpeg chay va bao loi giai ma (do la ket qua do, T17 doc no)."""
    try:
        r = subprocess.run(lenh_do_hinh(duong), capture_output=True,
                           timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise QcError(_t('Không chạy được bộ đo hình.')) from exc
    return doc_do_hinh((r.stderr or b"").decode("utf-8", "replace"),
                       thoi_luong=thoi_luong, ma_thoat=r.returncode)


# ── T18 — VMAF ────────────────────────────────────────────────────────────────

#: Thu tu dau vao cua lenh VMAF. `2..` = logo, TRUNG voi `ket_xuat.dung_lenh`
#: (o do `1` la ban phoi am — chuoi loc hinh khong doc no), nen chuoi loc render
#: dung lai NGUYEN VAN duoc: `[0:v]` van la nguon, `[2+i:v]` van la logo.
CHI_SO_BAN_RA = 1
CHI_SO_LOGO_DAU = 2


def loc_tham_chieu(hinh: dict, *, duong_chu: list[str], duong_ass: str) -> str:
    """Chuoi loc hinh cua preset cat, dung DUNG tham so `ket_xuat.dung_lenh` dua
    cho `che_do_render.loc_cat_noi`. `test_2012` chot hai ben bang nhau."""
    from . import che_do_render as cdr

    khoang = [(float(b), float(k)) for b, k in (hinh.get("khoang_giu") or ())]
    return cdr.loc_cat_noi(
        khoang, vung=(hinh.get("vung") or ()),
        lop_phu=list(hinh.get("lop_phu") or ()), duong_chu=list(duong_chu),
        cao_khung=int(hinh.get("cao_khung") or 0),
        ds_logo=list(hinh.get("logo") or ()),
        rong_khung=int(hinh.get("rong_khung") or 0),
        chi_so_logo_dau=CHI_SO_LOGO_DAU, duong_ass=duong_ass)


def chon_mo_hinh_vmaf(rong: int, cao: int) -> tuple[str, str]:
    """(mo hinh, bo loc co gian) theo khung ban ra. Xem khoi T18 o dau tep."""
    if min(int(rong or 0), int(cao or 0)) >= 2160:
        return MO_HINH_VMAF_4K, ""
    return MO_HINH_VMAF, ("scale=w=1920:h=1080:force_original_aspect_ratio="
                          "decrease:flags=bicubic,")


def _thoat_duong_loc(duong: str) -> str:
    return str(duong).replace("\\", "/").replace(":", "\\:")


def lenh_vmaf(*, duong_nguon: str, duong_ra: str, loc_hinh: str,
              duong_logo: list[str], rong: int, cao: int, duong_log: str,
              n_subsample: int = 0) -> list[str]:
    """Mot lenh: nguon -> chuoi loc render -> [ref]; ban ra -> [dist]; libvmaf.

    ⚠️ libvmaf: dau vao THU NHAT la ban bi mo (distorted), thu hai la tham
       chieu. `setpts=PTS-STARTPTS` hai phia + `ts_sync_mode=nearest` ghep khung
       theo moc thoi gian; `shortest=1` dung khi mot phia het.
    """
    mo_hinh, co_gian = chon_mo_hinh_vmaf(rong, cao)
    n = int(n_subsample or VMAF_N_SUBSAMPLE)
    loc = (f"{loc_hinh};"
           f"[ra]setpts=PTS-STARTPTS,{co_gian}format=yuv420p[ref];"
           f"[{CHI_SO_BAN_RA}:v]setpts=PTS-STARTPTS,{co_gian}format=yuv420p[dist];"
           f"[dist][ref]libvmaf=model=version={mo_hinh}:n_subsample={n}"
           f":shortest=1:ts_sync_mode=nearest:log_fmt=json"
           f":log_path='{_thoat_duong_loc(duong_log)}'")
    cmd = [media.ffmpeg_bin(), "-hide_banner", "-nostdin", "-v", "error",
           "-i", str(duong_nguon), "-i", str(duong_ra)]
    for d in duong_logo:
        cmd += ["-i", str(d)]
    return cmd + ["-filter_complex", loc, "-f", "null", "-"]


def doc_vmaf(goi: dict, *, mo_hinh: str = MO_HINH_VMAF) -> dict:
    """Log JSON cua libvmaf -> so tong hop. Ham thuan."""
    khung = sorted(float(f["metrics"]["vmaf"]) for f in (goi.get("frames") or [])
                   if "vmaf" in (f.get("metrics") or {}))
    if not khung:
        raise QcError(_t('libvmaf không trả về khung nào.'))
    gop = ((goi.get("pooled_metrics") or {}).get("vmaf") or {})
    tb = float(gop.get("mean", sum(khung) / len(khung)))
    return {
        "mo_hinh": mo_hinh,
        "trung_binh": round(tb, 3),
        "trung_binh_dieu_hoa": round(float(gop.get("harmonic_mean", tb)), 3),
        "nho_nhat": round(khung[0], 3),
        "p5": round(khung[int(len(khung) * 0.05)], 3),
        "so_khung": len(khung),
    }


def do_vmaf(*, duong_nguon: str, duong_ra: str, loc_hinh: str,
            duong_logo: list[str], rong: int, cao: int, thu_muc: str,
            timeout: int = 7200) -> dict:
    """Chay `lenh_vmaf`. Nem `QcError` khi khong do duoc (thieu libvmaf, loi
    ffmpeg) — nguoi goi bien thanh `khong_kha_dung`, KHONG lui ve heuristic."""
    import os
    import time

    log = os.path.join(thu_muc, "vmaf.json")
    cmd = lenh_vmaf(duong_nguon=duong_nguon, duong_ra=duong_ra,
                    loc_hinh=loc_hinh, duong_logo=duong_logo, rong=rong,
                    cao=cao, duong_log=log)
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise QcError(_t('Không chạy được VMAF.')) from exc
    if r.returncode != 0 or not os.path.exists(log):
        raise QcError(_t('VMAF thất bại: {e}').format(
            e=(r.stderr or b"").decode("utf-8", "replace")[-300:]))
    with open(log, encoding="utf-8") as f:
        kq = doc_vmaf(json.load(f), mo_hinh=chon_mo_hinh_vmaf(rong, cao)[0])
    kq["giay"] = round(time.monotonic() - t0, 2)
    return kq


def kiem(*, tt_ra: dict, tt_nguon: dict, am_luong: dict, ke_hoach: dict,
         ban_ke_tieng: dict, ban_dung_lop: list | None = None,
         bam_ra: str = "", bam_nguon: str = "",
         che_do_thoi_gian: str = "fit_original",
         che_do_render: str = "", thoi_luong_mong_doi: float = 0.0,
         hinh_ra: dict | None = None, hinh_nguon: dict | None = None,
         vmaf: dict | None = None, ban_hinh: dict | None = None) -> dict:
    """Do het cac dung sai T1-T18.

    `hinh_ra`/`hinh_nguon` = `do_hinh(...)` cua ban ra / nguon (T13, T17).
    `vmaf` = `do_vmaf(...)`, hoac `{"loi": "..."}` khi khong do duoc (T18). Tra ve bao cao; KHONG nem khi co muc hong.

    ⭐ Khong nem la mot quyet dinh, khong phai mot thieu sot: mot bao cao QC liet
       ke **moi** muc hong co ich hon mot ngoai le noi ve muc dau tien. Nguoi
       goi (`giai_doan_qc`) doc `dat` roi quyet dinh so phan cua lan chay.
    """
    muc: list[dict] = []

    # ── T1 — tep ra hop le, mot luong hinh + mot luong tieng ────────────────
    t1 = bool(tt_ra.get("co_video")) and bool(tt_ra.get("co_tieng"))
    muc.append(_muc("T1", DAT if t1 else HONG,
                    "tep ra co du luong hinh va luong tieng",
                    co_video=bool(tt_ra.get("co_video")),
                    co_tieng=bool(tt_ra.get("co_tieng"))))

    # ── T2 — thoi luong ────────────────────────────────────────────────────
    #
    # 🔴 **So voi cai gi, moi la cau hoi that.**
    #
    #    Truoc pha 18 T2 luon so voi NGUON. Dung cho preset giu hinh, noi luong
    #    hinh duoc sao chep. Voi preset CAT thi sai han: ban ra ngan hon nguon
    #    dung bang phan da cat — va do la **muc dich cua san pham**, khong phai
    #    mot khiem khuyet. So voi nguon o do se lam T2 hong o MOI lan chay preset
    #    cat, tuc QC chan dung cai no phai cho qua.
    #
    # ⭐ `thoi_luong_mong_doi` do nguoi goi tinh tu ban do thoi gian. Khong co no
    #    thi lui ve thoi luong nguon — dung hanh vi cu, cho preset cu.
    d_ra = float(tt_ra.get("thoi_luong") or 0)
    d_nguon = float(tt_nguon.get("thoi_luong") or 0)
    mong_doi = float(thoi_luong_mong_doi or 0.0) or d_nguon
    lech = d_ra - mong_doi
    # "khong bao gio dai hon MONG DOI" la mot chot RIENG, khong phai he qua cua
    # `abs(lech) <= 0.5`: mot ban ra dai hon 0,3 giay van vi pham loi hua §3.
    t2 = abs(lech) <= LECH_THOI_LUONG_S and lech <= DAI_HON_CHO_PHEP_S
    muc.append(_muc("T2", DAT if t2 else HONG,
                    "thoi luong ban ra so voi MONG DOI cua che do",
                    thoi_luong_ra=round(d_ra, 3), thoi_luong_nguon=round(d_nguon, 3),
                    mong_doi=round(mong_doi, 3),
                    # ⚠️ 6 chu so, khong 3: o 3 chu so `lech` cua loi 23/09 in ra
                    # `0.0` trong khi phan quyet la HONG — bao cao tu mau thuan.
                    lech=round(lech, 6), nguong=LECH_THOI_LUONG_S,
                    dai_hon_cho_phep=DAI_HON_CHO_PHEP_S))

    # ── T3 — luong hinh giong het nguon tung bit ────────────────────────────
    #
    # 🔴 **Chi co nghia o preset GIU HINH.**
    #
    #    Preset cat **ma hoa lai** luong hinh (bat buoc — xem `che_do_render`:
    #    cat bang stream copy chi cat duoc tai keyframe, va GOP do duoc la 8,333
    #    giay). Nen bam KHONG BAO GIO khop, va so no o do la chot mot dieu ta vua
    #    co y khong lam.
    #
    # ⛔ Cong thoat pha 18 goi dich danh dieu nay: QC "khong duoc gia dinh bam
    #    luong hinh bang nguon o che do cat".
    #
    # ⭐ Chi phi bam **da duoc do** truoc khi giu lai: MD5 ca luong hinh cua mot
    #    tep 154 MB / 10 phut het **0,27 giay** (stream copy, khong giai ma). O
    #    tran 2 gio uoc ~3,5 giay — canh mot luot render tinh bang phut. Pha 18
    #    doi "profile roi thay bang cach re hon **neu bang chung ung ho**"; bang
    #    chung noi khong can thay, va moi cach re hon deu la bang chung YEU HON.
    from .che_do_render import CAT_MA_HOA_LAI, SAO_CHEP

    if str(che_do_render) == CAT_MA_HOA_LAI:
        muc.append(_muc("T3", KHONG_AP_DUNG,
                        "che do CAT ma hoa lai luong hinh — bam khong the bang "
                        "nguon, va so no la chot mot dieu ta co y khong lam",
                        che_do_render=str(che_do_render)))
    elif bam_ra and bam_nguon:
        t3 = bam_ra == bam_nguon
        muc.append(_muc("T3", DAT if t3 else HONG,
                        "luong hinh giong het nguon tung bit",
                        bam_ra=bam_ra, bam_nguon=bam_nguon))
    else:
        muc.append(_muc("T3", KHONG_AP_DUNG,
                        "chua bam duoc luong hinh de doi chieu"))

    # ── T4/T5 — am luong tich hop va dinh that ──────────────────────────────
    lufs = float(am_luong.get("lufs", 0) or 0)
    dinh = float(am_luong.get("dinh_that", 0) or 0)
    t4 = abs(lufs - LUFS_DICH) <= LUFS_DUNG_SAI
    muc.append(_muc("T4", DAT if t4 else HONG, "am luong tich hop",
                    lufs=round(lufs, 2), dich=LUFS_DICH, dung_sai=LUFS_DUNG_SAI))
    t5 = dinh <= DINH_THAT_TOI_DA_DB
    muc.append(_muc("T5", DAT if t5 else HONG, "dinh that",
                    dinh_that=round(dinh, 2), toi_da=DINH_THAT_TOI_DA_DB))

    # ── T6 — moi doan trong ke hoach co tep tieng ───────────────────────────
    doan = list(ke_hoach.get("doan") or [])
    co_tieng = {str(d.get("ma")) for d in (ban_ke_tieng.get("doan") or [])
                if d.get("khoa")}
    # Doan bi cat o TIMING (dai_ms <= 0) khong con la doan can tieng — chinh T12
    # dem chung, va dem chung hai lan la bao cao mot loi thanh hai.
    can = [str(d["ma"]) for d in doan if int(d.get("dai_ms") or 0) > 0]
    thieu = [m for m in can if m not in co_tieng]
    muc.append(_muc("T6", DAT if not thieu else HONG,
                    "moi doan con lai deu co tep tieng",
                    so_can=len(can), so_thieu=len(thieu), thieu=thieu[:10]))

    # ── T7 — moi doan nam DUNG cho ke hoach da dinh ────────────────────────
    #
    # 🔑 "So voi vi tri DA HOACH DINH", khong phai so voi vi tri goc: ADR-003 lam
    #    viec mot doan tran qua vi tri goc thanh **thiet ke**, va T11 moi do phan
    #    do. Vay do cai gi? Do **ke hoach so voi ban dung**: COMPOSE chep
    #    `dat_tai_ms` tu ke hoach sang ban dung, nen T7 chot rang no khong lam
    #    lech mot doan nao.
    #
    # ⚠️ Ban dau cho nay doc mot khoa `bat_hoach_dinh_ms` **khong ton tai** trong
    #    ke hoach, nen phep tru luon ra 0 va T7 luon DAT. Mot chot luon xanh la
    #    mot chot khong canh gi ca — te hon khong co, vi no trong nhu co.
    kh_theo_ma = {str(d["ma"]): int(d["dat_tai_ms"]) for d in doan
                  if int(d.get("dai_ms") or 0) > 0}
    troi_max, ma_troi = 0.0, ""
    for lop in (ban_dung_lop or []):
        ma = str(lop.get("ma"))
        if ma not in kh_theo_ma:
            continue
        t = abs(int(lop.get("dat_tai_ms", 0)) - kh_theo_ma[ma]) / 1000.0
        if t > troi_max:
            troi_max, ma_troi = t, ma
    if not ban_dung_lop:
        muc.append(_muc("T7", KHONG_AP_DUNG,
                        "chua co ban dung de doi chieu vi tri tung doan"))
    else:
        muc.append(_muc("T7", DAT if troi_max <= TROI_MOI_DOAN_S else HONG,
                        "moi doan nam dung cho ke hoach da dinh",
                        troi_lon_nhat_s=round(troi_max, 3), doan=ma_troi,
                        nguong=TROI_MOI_DOAN_S))

    # ── T8/T9/T10 — KHONG AP DUNG (xem docstring dau tep) ───────────────────
    ly_do = ("MVP khong CHEN khoang lang nao — ADR-003 doi mo hinh thoi gian "
             "sang MUON khoang lang san co lam ngan sach, nen ba dung sai nay "
             "khong con chu the de do")
    for ma in ("T8", "T9", "T10"):
        muc.append(_muc(ma, KHONG_AP_DUNG, ly_do))

    # ── T11 — troi tich luy khong vuot ngan sach cua 3 doan ke tiep ─────────
    #
    # `thoi_gian` da cuong che dieu nay khi LAP ke hoach. Do lai o day vi mot
    # chot chi dung khi no duoc kiem o ca hai dau: neu mot ngay nao do phep lap
    # ke hoach sai, khong gi khac trong chuoi phat hien duoc.
    #
    # Tran cua doan `i` = tong `ngan_sach_ms` cua ba doan `i..i+2`, dung cong
    # thuc cua `lap_ke_hoach` (ADR-003 D5).
    ns = [int(d.get("ngan_sach_ms") or 0) for d in doan]
    vuot: list[str] = []
    for i, d in enumerate(doan):
        tran = sum(ns[i:i + TRAN_TROI_SO_DOAN])
        if int(d.get("troi_sau_ms") or 0) > tran:
            vuot.append(str(d.get("ma")))
    muc.append(_muc("T11", DAT if not vuot else HONG,
                    "troi tich luy trong tran ngan sach cua 3 doan ke tiep",
                    tran_so_doan=TRAN_TROI_SO_DOAN, so_doan_vuot=len(vuot),
                    doan_vuot=vuot[:10],
                    troi_toi_da_ms=int(ke_hoach.get("troi_toi_da_ms") or 0)))

    # ── T12 — moi doan bi cat deu duoc BAO CAO ─────────────────────────────
    #
    # ⭐ T12 khong phai mot nguong: mat loi thoai **luon** la mot khiem khuyet
    #    chat luong. No `dat` khi so bi cat duoc bao cao ra, va con so do di kem
    #    de nguoi doc thay — mot lan chay cat 12 doan van "dat T12" nhung khong
    #    ai doc bao cao do ma nghi la on.
    bi_cat = int(ke_hoach.get("so_doan_bi_cat") or 0)
    muc.append(_muc("T12", DAT, "so doan bi cat da duoc bao cao",
                    so_doan_bi_cat=bi_cat))

    # ── T13 — render khong TAO RA hinh den / dong bang ─────────────────────
    #
    # 🔴 Mot tep hop le, dung thoi luong, dung am luong, va **toan mau den** (hay
    #    dong bang mot khung) van la mot lan giao hong — T1 chi hoi "co luong
    #    hinh khong". Do bang `blackdetect`/`freezedetect` (tham so mac dinh cua
    #    ffmpeg, xem dau tep), so PHAN VUOT cua ban ra so voi nguon.
    if hinh_ra is None or hinh_nguon is None:
        muc.append(_muc("T13", KHONG_AP_DUNG,
                        "chua do duoc khung den / dong bang cua ban ra va nguon"))
    else:
        vuot_den = float(hinh_ra["den_s"]) - float(hinh_nguon["den_s"])
        vuot_dong = float(hinh_ra["dong_s"]) - float(hinh_nguon["dong_s"])
        t13 = vuot_den <= DEN_DONG_DU_S and vuot_dong <= DEN_DONG_DU_S
        muc.append(_muc("T13", DAT if t13 else HONG,
                        "render khong tao ra khung den hay hinh dong bang",
                        den_ra_s=hinh_ra["den_s"], den_nguon_s=hinh_nguon["den_s"],
                        dong_ra_s=hinh_ra["dong_s"],
                        dong_nguon_s=hinh_nguon["dong_s"],
                        ti_le_den_ra=(round(hinh_ra["den_s"] / d_ra, 4)
                                      if d_ra > 0 else None),
                        ti_le_dong_ra=(round(hinh_ra["dong_s"] / d_ra, 4)
                                       if d_ra > 0 else None),
                        khoang_den=hinh_ra.get("khoang_den") or None,
                        khoang_dong=hinh_ra.get("khoang_dong") or None,
                        du_s=DEN_DONG_DU_S))

    # ── T17 — ban ra GIAI MA HET khong loi ──────────────────────────────────
    #
    # 🔑 ffprobe (T1) chi doc phan dau container. Mot tep cut cuoi, mot goi hong
    #    giua chung van qua T1/T2 — chi giai ma ca tep moi thay. Cung luot ffmpeg
    #    voi T13, nen khong ton them mot lan giai ma.
    if hinh_ra is None:
        muc.append(_muc("T17", KHONG_AP_DUNG, "chua giai ma duoc ban ra"))
    else:
        so_loi = int(hinh_ra.get("so_loi_giai_ma") or 0)
        ma_thoat = int(hinh_ra.get("ma_thoat") or 0)
        muc.append(_muc("T17", DAT if (so_loi == 0 and ma_thoat == 0) else HONG,
                        "ban ra giai ma het khong loi",
                        so_loi=so_loi, ma_thoat=ma_thoat,
                        loi=hinh_ra.get("loi_giai_ma") or None))

    # ── T18 — chat luong hinh sau MA HOA LAI (VMAF) ─────────────────────────
    if str(che_do_render) != CAT_MA_HOA_LAI:
        muc.append(_muc("T18", KHONG_AP_DUNG,
                        "preset giu hinh sao chep luong hinh — T3/T14 da chung "
                        "minh giong nguon tung bit, VMAF khong co gi de do",
                        che_do_render=str(che_do_render or SAO_CHEP)))
    elif vmaf is None:
        muc.append(_muc("T18", KHONG_AP_DUNG, "chua do VMAF"))
    elif vmaf.get("loi"):
        # ⛔ Khong do duoc (thieu libvmaf...) => `khong_kha_dung`, KHONG lui
        #    ve mot heuristic tu che (luat bo do, BRIEF_CHUNG).
        muc.append(_muc("T18", KHONG_AP_DUNG, "khong_kha_dung",
                        ly_do=str(vmaf.get("loi"))[:300]))
    else:
        tb = float(vmaf["trung_binh"])
        muc.append(_muc("T18", DAT if tb >= VMAF_TOI_THIEU else HONG,
                        "chat luong hinh sau ma hoa lai (VMAF, tham chieu = "
                        "chuoi loc render khong ma hoa)",
                        **dict(vmaf), toi_thieu=VMAF_TOI_THIEU))

    hinh = dict(ban_hinh or {})

    # ── T14 — chinh sach render: preset giu hinh KHONG duoc ma hoa lai ──────
    #
    # 🔴 **Loi hua cua preset giu hinh la mot loi hua VE DIEM ANH**, va truoc
    #    pha 27 no chi duoc kiem boi T3 — thu roi ve `KHONG_AP_DUNG` ngay khi
    #    khong bam duoc luong hinh. Tuc co mot duong ma **khong ai** kiem.
    #
    # ⭐ T14 mien phi va khong the sai: `-c:v copy` cho byte hinh di thang tu
    #    nguon sang tep ra, nen no **khong the** doi bo ma hoa, kich thuoc hay
    #    goc xoay. Bon truong nay da nam san trong ket qua ffprobe da chay.
    #
    # ⛔ Chi so nhung truong CA HAI ben deu khai. Mot truong vang mat la mot
    #    truong ffprobe khong doc duoc — khong phai mot truong da doi.
    if str(che_do_render) != SAO_CHEP:
        muc.append(_muc("T14", KHONG_AP_DUNG,
                        "che do CAT co quyen ma hoa lai — khong co loi hua nao "
                        "ve bo ma hoa hay kich thuoc de doi chieu",
                        che_do_render=str(che_do_render)))
    else:
        # 🔴 **"Thieu du lieu" khac nhau theo TUNG TRUONG, va gop chung lam
        #    mot da giet mot truc.**
        #
        #    Ban dau toi coi `0` la thieu cho ca bon truong. Voi `rong`/`cao`
        #    dieu do dung — mot luong hinh khong the rong 0. Voi `xoay` thi
        #    **sai**: `0` la gia tri HOP LE va la gia tri pho bien nhat, nen
        #    truc xoay khong bao gio duoc so. Mot phep kiem chet lang le.
        #
        # ⭐ `test_473[doi2]` bat duoc no ngay lan chay dau — do la ly do bai
        #    kiem liet ke ca ba truc thay vi tin mot ca dai dien.
        def _co(truong: str, gia_tri) -> bool:
            if gia_tri is None:
                return False
            if truong == "codec_video":
                return gia_tri != ""
            if truong in ("rong", "cao"):
                return int(gia_tri) > 0
            return True          # `xoay`: 0 la mot goc that

        lech_t14 = {}
        so_sanh, thuc_chat = 0, 0
        for truong in ("codec_video", "rong", "cao", "xoay"):
            a, b = tt_ra.get(truong), tt_nguon.get(truong)
            if not _co(truong, a) or not _co(truong, b):
                continue
            so_sanh += 1
            # ⭐ `xoay` mot minh KHONG du de tuyen bo "khong ma hoa lai": mot
            #    lan ma hoa lai giu nguyen goc xoay la chuyen binh thuong. Doi
            #    it nhat mot truc THUC CHAT (bo ma hoa hoac kich thuoc), neu
            #    khong thi pham vi phep do hep hon loi tuyen bo — dung hang
            #    `pham-vi-phep-do-hep-hon-loi-tuyen-bo`.
            if truong != "xoay":
                thuc_chat += 1
            if a != b:
                lech_t14[truong] = {"ra": a, "nguon": b}
        if not thuc_chat:
            muc.append(_muc("T14", KHONG_AP_DUNG,
                            "ffprobe khong doc duoc bo ma hoa hay kich thuoc "
                            "de doi chieu — goc xoay mot minh khong du",
                            so_truong_da_so_sanh=so_sanh))
        else:
            muc.append(_muc("T14", DAT if not lech_t14 else HONG,
                            "preset giu hinh khong ma hoa lai luong hinh",
                            so_truong_da_so_sanh=so_sanh,
                            lech=lech_t14 or None))

    # ── T15 — bien phu de: moi dong phai NAM TRONG ban ra ───────────────────
    #
    # 🔴 **Mot dong phu de dat qua cuoi ban ra la mot dong khong ai thay.**
    #    Khach tra tien cho phu de, tep `.ass` hop le, ffmpeg khong bao gi, va
    #    dong chu do khong bao gio hien ra. Dung hinh dang *tinh nang khong ton
    #    tai* ma chuong trinh nay lien tuc gap.
    #
    # ⭐ Doc su kien DA CHOT trong ban dung, khong tinh lai tu ke hoach: cho
    #    nay hoi *"thu da giao co dung khong"*, va thu da giao la ban dung.
    ho_pd = hinh.get("phu_de") or {}
    su_kien = list(ho_pd.get("su_kien") or [])
    if not su_kien:
        muc.append(_muc("T15", KHONG_AP_DUNG,
                        "ban dung khong mang su kien phu de nao"))
    elif d_ra <= 0:
        muc.append(_muc("T15", KHONG_AP_DUNG,
                        "chua biet thoi luong ban ra de doi chieu"))
    else:
        # ⚠️ Ten RIENG: `tran` da duoc T11 dung cho ngan sach troi (mot
        #    `int`). Dung lai no cho mot `float` la dung lai mot ten cho hai
        #    kieu — thu lam moi cong cu kiem kieu mu voi ca doan phia sau.
        tran_phu_de = d_ra + BIEN_PHU_DE_DUNG_SAI_S
        # 🔑 asv-final: su kien dat tren truc BIEN TAP; `setpts` o cuoi chuoi loc
        #    nen chung cung he so voi hinh. So voi ban ra thi phai chia — mot cho:
        #    `bien_tap.moc_ban_ra`.
        from .bien_tap import moc_ban_ra, toc_do
        bt = hinh.get("bien_tap")
        ngoai, xuoi_nguoc = [], []
        for i, e in enumerate(su_kien):
            bat = moc_ban_ra(float(e.get("start") or 0.0), bt)
            ket = moc_ban_ra(float(e.get("end") or 0.0), bt)
            if ket <= bat:
                xuoi_nguoc.append(i)
            if bat < -BIEN_PHU_DE_DUNG_SAI_S or ket > tran_phu_de:
                ngoai.append({"i": i, "bat": round(bat, 3),
                              "ket": round(ket, 3)})
        # ⚠️ Chong lan KHONG phai loi: `ass_builder` xep chong duoc, va mot ban
        #    phu de karaoke co the co hai dong cung luc. Chi dem, khong danh
        #    truot — dem de nguoi doc bao cao thay, khong de chan lan chay.
        truoc, sau = su_kien[:-1], su_kien[1:]
        chong = sum(1 for a, b in zip(truoc, sau, strict=True)
                    if float(b.get("start") or 0) < float(a.get("end") or 0))
        t15 = not ngoai and not xuoi_nguoc
        muc.append(_muc("T15", DAT if t15 else HONG,
                        "moi dong phu de nam trong ban ra",
                        so_dong=len(su_kien), thoi_luong_ra=round(d_ra, 3),
                        toc_do=toc_do(bt),
                        dung_sai=BIEN_PHU_DE_DUNG_SAI_S,
                        ngoai_bien=ngoai or None,
                        xuoi_nguoc=xuoi_nguoc or None, so_chong_lan=chong))

    # ── T16 — luong hinh va luong tieng phai dai bang nhau ──────────────────
    #
    # 🔴 **Day la hong dung thu san pham nay ban.** Mot ban long tieng ma tieng
    #    va hinh lech nhau thi moi thu khac deu vo nghia — va truoc pha 27
    #    khong chot nao hoi: T2 do do dai CONTAINER, mot con so van dung khi hai
    #    luong ben trong lech nhau.
    #
    # ⚠️ `None` = luong khong tu khai `duration` (MP4 duoc phep). Do KHONG phai
    #    `0`, va doan bang `0` se bien mot tep binh thuong thanh bao cao hong.
    dv = tt_ra.get("thoi_luong_video")
    da = tt_ra.get("thoi_luong_tieng")
    if dv is None or da is None:
        muc.append(_muc("T16", KHONG_AP_DUNG,
                        "tep ra khong khai do dai tung luong",
                        co_do_dai_video=dv is not None,
                        co_do_dai_tieng=da is not None))
    else:
        lech_av = abs(float(dv) - float(da))
        muc.append(_muc("T16", DAT if lech_av <= LECH_TIENG_HINH_S else HONG,
                        "luong hinh va luong tieng dai bang nhau",
                        thoi_luong_video=round(float(dv), 3),
                        thoi_luong_tieng=round(float(da), 3),
                        lech=round(lech_av, 4), toi_da=LECH_TIENG_HINH_S))

    hong = [m["ma"] for m in muc if m["trang_thai"] == HONG]
    return {
        "phien_ban": PHIEN_BAN_QC,
        "che_do_thoi_gian": che_do_thoi_gian,
        # 🔑 Bao cao QC phai noi no da do theo LUAT NAO. Mot bao cao khong ghi
        #    che do la mot bao cao khong doc lai duoc: "T3 khong ap dung" co
        #    nghia hoan toan khac giua hai preset.
        "che_do_render": str(che_do_render or ""),
        "thoi_luong_mong_doi": round(float(thoi_luong_mong_doi or 0.0), 3),
        "dat": not hong,
        "so_muc_hong": len(hong),
        "muc_hong": hong,
        "muc": muc,
    }


def tom_tat(bao_cao: dict) -> dict:
    """Con so cho tien do va giao dien. Khong duong dan, khong bi mat."""
    return {
        "qc_dat": bool(bao_cao.get("dat")),
        "qc_so_muc_hong": int(bao_cao.get("so_muc_hong") or 0),
        "qc_muc_hong": list(bao_cao.get("muc_hong") or []),
        "qc_phien_ban": int(bao_cao.get("phien_ban") or 0),
    }
