"""Tach nguon tieng va tron nen — chat nen cua giai doan AUDIO_PREPARE.

## Vi sao giai doan nay BAT BUOC, khong phai mot thu lam dep

`MVP_CONTRACT.md` §4 (D-ASV-04). San pham la **long tieng**: giong Viet phai
thay cho loi thoai goc. Neu khong go duoc giong goc ra thi giong Viet chong len
tieng nguoi noi that, va ban ra khong dung duoc. Do la ly do tach nguon nam
trong MVP du no la giai doan nang nhat.

⭐ Va thu ta go la **GIONG**, khong phai nhac nen. Goi no la "xoa nhac nen" la
   goi nguoc, va cai ten nguoc do dan toi mot chinh sach stem nguoc.

## Chinh sach stem (Prompt 09 muc 4) — kem gioi han, noi thang

htdemucs tach ra bon nguon: `drums`, `bass`, `other`, `vocals`.

    NEN GIU LAI = drums + bass + other
    BO DI       = vocals

⛔ **Day KHONG phai phep tach hoan hao, va dung hua nhu the.** Gioi han da biet:

  * Giong con vuong lai trong `other` khi no bi tron nang voi nhac (hop xuong,
    giong da qua xu ly, giong hat trong nhac nen).
  * Tieng dong phat ra tu mieng nguoi — cuoi, tho, ho — thuong bi xep vao
    `vocals` va se **bien mat** khoi ban nen. Ve mat ky thuat la dung; ve mat
    cam nhan la mot canh phim im di.
  * Nhac cu bi coi la giong (saxophone, dan day theo giai dieu) co the bi cat.

  ⇒ QC (pha 18) do "nen khong im" chu **khong** do "khong con giong goc". Cai
    thu hai khong do duoc bang mot nguong, va hua no la hua mot thu ta khong
    kiem duoc.

## Vi sao KHONG dung lai ban 16 kHz mono cua pha 08

`nhap_media.tach_tieng_cho_asr` sinh ra ban 16 kHz **mot kenh** — dung dang cho
Whisper. Dua chinh ban do vao demucs la sai theo hai huong cung mot luc:

  * mat toan bo dai tren 8 kHz (Nyquist), tuc mat phan lon thong tin ma phep
    tach dua vao;
  * mat anh stereo, ma htdemucs dung de phan biet nguon.

Nen giai doan nay **rut ban rieng**: 44,1 kHz, hai kenh. Hai ban tieng cho hai
muc dich khac nhau la dung, khong phai trung lap.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import subprocess
import sys
from pathlib import Path

from platform_core import media
from platform_core.i18n import _ as _t

from .demucs_runner import ThieuCard
from .nhap_media import DaHuy, MediaError, _chay

log = logging.getLogger(__name__)

#: Dang vao cua htdemucs. 44,1 kHz stereo la dang model duoc huan luyen tren.
TAN_SO_TACH = 44100
SO_KENH_TACH = 2

#: Stem giu lai lam nen. `vocals` bi bo — do la ca muc dich.
STEM_GIU = ("drums", "bass", "other")
STEM_BO = ("vocals",)


# ══════════════════════════════════════════════════════════════════════════
#  B2 (25/09) — BA LOP dieu khien duoc, tu BON stem demucs
# ══════════════════════════════════════════════════════════════════════════
#
# Chu du an chot: "o phan demucs, tach 3 lop: voice / vfx / background music
# ... cung co cac cai dat nhu giam 3 muc hay bat tat neu muon". htdemucs cho
# BON stem (`drums`, `bass`, `other`, `vocals`); anh xa xuong BA lop la MOT
# QUYET DINH, khong hien nhien — ghi lai o day de khong ai phai doan lai:
#
#   "nhac" (background music) = drums + bass, MOT gain chung.
#       Nghe that tren mot doan 12 giay co nhac nen + buoc chan + gio (dung
#       `sine`/`anoisesrc` tong hop, xem `tests/test_.../_dung_stem_gia`):
#       drums mang nhip trong, bass mang nen tram — ca hai la nhac cu THEO
#       GIAI DIEU/NHIP, khong phai tieng dong roi rac. Gop chung MOT gain la
#       dung voi cach nguoi nghe goi ten "nhac nen": ho khong tach rieng
#       "trong" voi "bass" bang tai, ho nghe MOT khoi nhac.
#   "vfx" (am truong / tieng dong) = other.
#       `other` la PHAN CON LAI sau khi demucs da lay het giong (vocals) va
#       nhac co nhip (drums/bass) — trong thuc hanh no mang tieng buoc chan,
#       gio, va am truong khong-nhip. Goi no "vfx" thay vi "nhac phu" vi no
#       KHONG co nhip/giai dieu — dung mo hinh cua nguoi nghe hon.
#   "giong" (voice) = vocals — CHINH la `STEM_BO` hom nay.
#       ⛔ Day KHONG phai dao nguoc chinh sach "bo giong goc" (dau tep noi ro
#       vi sao: giong Viet phai thay giong goc). Lop nay ton tai de CUU tieng
#       ĐỘNG phat ra tu mieng nguoi ma `vocals` "nuot" theo — cuoi, tho, ho
#       (canh bao da ghi o dau tep) — VOI CAI GIA la giong goc co the ri qua
#       cung. Do la mot danh doi khach tu chon, khong phai mac dinh: mac dinh
#       lop nay TAT, tai tao dung hanh vi truoc B2.
#
# ⛔ Gioi han: day la anh xa THEO STEM, khong phai mot phep tach am hoc moi.
#   Gioi han cua chinh sach stem cu (giong lan trong `other` khi tron nang,
#   nhac cu bi coi la giong) van nguyen — ba lop chi la CACH GOM lai bon stem
#   da co, khong sua duoc gioi han cua demucs.
LOP_STEM = {
    "giong": STEM_BO,           # ("vocals",)
    "nhac": ("drums", "bass"),
    "vfx": ("other",),
}
assert set(LOP_STEM["nhac"]) | set(LOP_STEM["vfx"]) == set(STEM_GIU), (
    "LOP_STEM lech STEM_GIU — hai cho khai cung mot chinh sach phai khop nhau")
assert set(LOP_STEM["giong"]) == set(STEM_BO), "LOP_STEM lech STEM_BO"

#: Bien do tuyen tinh (khong phai dB) — dong bo thang truot cua
#: `Cut_only ver2/bot_gui.py:909-913` (0,0-2,0, buoc 0,05): cung mot san pham
#: chu du an dang dung, cung mot mien gia tri se it bat ngo hon khi lam GUI (B5).
GAIN_NHO_NHAT = 0.0
GAIN_LON_NHAT = 2.0

#: Ho so BA LOP mac dinh. ⭐ Phai tai tao DUNG chinh sach STEM_GIU/STEM_BO hom
#: nay: "nhac" va "vfx" bat o gain 1,0 (== STEM_GIU khong nhan gi them),
#: "giong" TAT (== STEM_BO, bi bo hoan toan). Doi bo nay la doi ban ra cua moi
#: lan chay khong chon gi khac — phai di kem mot cache-bump (xem PHIEN_BAN_TACH).
#
# 🔑 **`giong_gain = 0.30` = −10,46 dB (chu du an chot 26/09/2026).**
#    Truoc do la `1.0` = **0 dB**: khach vua bat "giu giong noi goc" la loi
#    thoai goc tro lai **am luong DAY**, doi dau truc dien voi giong long
#    tieng Viet. Nhan CO canh bao se chong — nhung gia tri mac dinh lam no
#    te nhat co the.
#    ⚠️ Thang truot la **bien do tuyen tinh**, ⛔ khong phai dB, va `step="5"`
#    nen −10 dB (= 0,316) ⛔ khong nam tren luoi. `0.30` lech 0,46 dB.
LOP_MAC_DINH = {
    "giong_bat": False, "giong_gain": 0.30,
    "nhac_bat": True, "nhac_gain": 1.0,
    "vfx_bat": True, "vfx_gain": 1.0,
}


class LopNenLoi(ValueError):
    """Ho so ba lop nen khong hop le. Thong diep noi cho khach, tieng Viet."""


def _gain(gt, ten: str) -> float:
    if isinstance(gt, bool) or not isinstance(gt, (int, float)) or not math.isfinite(gt):
        raise LopNenLoi(_t('Giá trị âm lượng lớp không hợp lệ: {ten}.').format(ten=ten))
    v = round(float(gt), 2)
    if not GAIN_NHO_NHAT <= v <= GAIN_LON_NHAT:
        raise LopNenLoi(_t('Âm lượng lớp {ten} phải từ {a} đến {b}.').format(
            ten=ten, a=GAIN_NHO_NHAT, b=GAIN_LON_NHAT))
    return v


def chuan_hoa_lop(tho: dict) -> dict:
    """Ho so BA LOP, DAY DU, da duyet. Nem `LopNenLoi`. Luy dang (khuon
    `am_thanh.chuan_hoa` / `bien_tap.chuan_hoa`: tu choi truong la, dien mac
    dinh cho truong vang, tu choi to hop khong lam gi)."""
    if not isinstance(tho, dict):
        raise LopNenLoi(_t('Hồ sơ lớp nền không đọc được.'))
    la = set(tho) - set(LOP_MAC_DINH)
    if la:
        raise LopNenLoi(_t('Hồ sơ lớp nền có trường lạ: {ds}.').format(
            ds=", ".join(sorted(la))))
    ra: dict = dict(LOP_MAC_DINH)
    for k in ("giong_bat", "nhac_bat", "vfx_bat"):
        if k in tho:
            if not isinstance(tho[k], bool):
                raise LopNenLoi(_t('Giá trị âm lượng lớp không hợp lệ: {ten}.')
                                .format(ten=k))
            ra[k] = tho[k]
    for k in ("giong_gain", "nhac_gain", "vfx_gain"):
        if k in tho:
            ra[k] = _gain(tho[k], k)
    # ⛔ Ba lop deu tat (hoac bat nhung gain=0) la mot ho so KHONG LAM GI —
    #    tu choi TAI DAY, truoc khi cham ffmpeg, de loi noi dung nguyen nhan
    #    thay vi mot MediaError chung chung roi tu tang duoi ("khong tim thay
    #    phan nhac nen") — hai loi do noi CUNG mot trieu chung, khac NGUYEN
    #    NHAN (chinh sach vs. stem thieu that su, xem `tron_nen`).
    if not any(ra[f"{lp}_bat"] and ra[f"{lp}_gain"] > 0.0
              for lp in ("giong", "nhac", "vfx")):
        raise LopNenLoi(_t('Đã tắt hoặc hạ về 0 cả ba lớp — không còn gì để '
                           'làm nhạc nền.'))
    return ra


def tu_cai_dat_lop(ho_so: dict | None) -> dict:
    """Ban DOC day du tu ho so BA LOP da luu (hoac `None` = mac dinh)."""
    return dict(LOP_MAC_DINH) if not ho_so else chuan_hoa_lop(dict(ho_so))


def tu_form_lop(chuoi: str) -> dict | None:
    """JSON tu form -> ho so BA LOP de LUU, hoac `None` khi rong / bang mac dinh.

    ⭐ Khuon `am_thanh.tu_form` — luat B2 #2 (ho so THUA): `None` khi bang mac
       dinh, de mot lan chay khach KHONG cham gi ghi mot ho so VANG MAT, khong
       phai `{"nhac_gain": 1.0, ...}` day du. Noi thang: ham nay CHUA duoc noi
       vao kho luu that (do la `cai_dat.py`, ngoai pham vi B2 — xem `KHOA_THUA`
       trong `am_thanh.py` cho khuon da co san); no la HOP DONG THAM SO san
       sang cho B5/B6 noi day.
    """
    if not (chuoi or "").strip():
        return None
    try:
        tho = json.loads(chuoi)
    except (ValueError, TypeError) as exc:
        raise LopNenLoi(_t('Hồ sơ lớp nền không đọc được.')) from exc
    ra = chuan_hoa_lop(tho)
    return None if ra == LOP_MAC_DINH else ra


def cho_giao_dien_lop() -> dict:
    """Mien gia tri cho giao dien (B5) — MOT nguon voi phep duyet o tren."""
    return {"gain_min": GAIN_NHO_NHAT, "gain_max": GAIN_LON_NHAT, **LOP_MAC_DINH}

#: Chuan am luong cua ban nen. Ke thua tu
#: `Cut_only ver2/nerf_engine/stages/audio.py:54` — do la con so da chay that.
LUFS_DICH = -14.0
DINH_THAT_DB = -1.5

#: Doi khi doi bat cu thu gi o tren. Di vao van tay (O13).
#: ⬆️ 1 -> 2 (B2, 25/09): `tron_nen` nhan them ho so BA LOP (`lop`) va
#:    `van_tay_tach` nhan them tham so cung ten — ban nen CO THE doi byte du
#:    checksum nguon/model/ffmpeg khong doi gi (khach doi gain mot lop). Them
#:    khoa "lop" vao goi hash da tu doi van tay o MOI gia tri; bump o day la
#:    tai lieu tuong minh, theo dung quy uoc `am_master.PHIEN_BAN_MASTER`.
PHIEN_BAN_TACH = 2

#: Model tach. Ten nay di vao van tay: nang model = van tay doi = cache cu vo hieu.
MODEL_TACH = "htdemucs"


def rut_ban_day_du(nguon: str, dich: str, *, hoi_huy=None,
                   timeout: int = 1800) -> str:
    """Rut ban tieng DAY DU DAI, stereo — dau vao cua phep tach.

    Khac han ban 16 kHz mono cua pha 08. Xem ghi chu dau tep.
    """
    Path(dich).parent.mkdir(parents=True, exist_ok=True)
    cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
           "-i", nguon, "-vn",
           "-ac", str(SO_KENH_TACH), "-ar", str(TAN_SO_TACH),
           "-c:a", "pcm_s16le", dich]
    try:
        r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired as exc:
        raise MediaError(_t('Tách tiếng quá hạn.')) from exc
    if r.returncode != 0:
        raise MediaError(_t('Tách tiếng thất bại: {loi}').format(
            loi=(r.stderr or b"").decode("utf-8", "replace")[-300:]))
    return dich


#: Timeout mac dinh cua MOT lan demucs. ⚠️ LON HON tran job `asv_gpu.audio_prepare`
#: (3.600 s): nguoi goi trong job PHAI kep bang `lat_cat.han_tien_trinh_con`.
TIMEOUT_TACH_S = 5400


#: Python chay tien trinh con demucs. ⛔ Mac dinh la `sys.executable`, tuc
#: **khong doi gi o production**: worker chay bang `C:\LTTPlatform\venv` va do
#: chinh la venv co `torch 2.11.0+cu128`.
#:
#: 🔴 **Vi sao can mot cua ghi de, va vi sao no khong phai mot cua sau.**
#:
#:    Do that 24/09, lan `nghiem-thu-v2`, tren phim khach that: nen tang cap card
#:    dung (`JobContext.gpu_uuid` khac rong, `gpu_lease` da giu), nhung tien
#:    trinh con nem `ThieuCard` — vi bo nghiem thu chay bang **trinh thong dich
#:    test** (`…\\Programs\Python\Python313`) va torch o do la `2.11.0+cpu`,
#:    `cuda False`. Hai venv, hai cau tra loi khac nhau cho cung mot cau hoi.
#:
#: ⛔ Va `setup/nghiem_thu_asv.ps1` **khong the** chay pytest bang venv san pham:
#:    venv do co y khong cai pytest (no cai thu SAN PHAM chay). Nen khong co cach
#:    nao de ca hai dung MOT trinh thong dich — pytest can mot cai, demucs can
#:    cai kia.
#:
#: ⭐ Cung hinh dang voi `apps/asv_gpu/do_luong/venv.py:LTT_QC_PYTHON` (mot duong
#:    mac dinh + mot bien ghi de). Khong phat minh giao thuc moi cho cung mot
#:    van de.
BIEN_PYTHON_TACH = "LTT_ASV_PYTHON_TACH"


def python_tach() -> Path:
    """Trinh thong dich chay `demucs_runner`. `sys.executable` neu khong ghi de."""
    return Path(os.environ.get(BIEN_PYTHON_TACH) or sys.executable)


def tach_nguon(vao_wav: str, thu_muc_ra: str, *, gpu_env: dict | None = None,
               buoc_gpu: bool = False, hoi_huy=None,
               timeout: int = TIMEOUT_TACH_S) -> dict:
    """Chay demucs trong TIEN TRINH CON. Tra ve bang duong dan cac stem.

    🔑 `gpu_env` phai la ket qua cua `JobContext.gpu_env()` — card do **nen tang**
       cap qua `platform_core.gpu_lease`. Handler khong bao gio tu chon card
       (I11/O6); no chi chuyen tiep moi truong da duoc cap xuong tien trinh con.

    🔑 `buoc_gpu=True` nghia la nen tang DA giu cho mot card. Khi do tien trinh
       con **khong duoc** tut xuong CPU im lang: xem `demucs_runner.chon_thiet_bi`
       ve ly do mot lan tut xuong nhu the tac ca hang doi chu khong chi lam cham
       mot job.
    """
    Path(thu_muc_ra).mkdir(parents=True, exist_ok=True)
    cmd = [str(python_tach()), "-m", "apps.auto_scan_video.demucs_runner",
           vao_wav, thu_muc_ra]
    if buoc_gpu:
        cmd.append("--buoc-gpu")

    moi_truong = dict(gpu_env) if gpu_env else dict(os.environ)
    # `-m` can thu muc goc cua kho trong duong import.
    #
    # ⛔ KHONG dem cap bang `parents[2]`. Dem cap hong LANG LE khi file doi cho:
    #    khong loi nao no ra, chi la `PYTHONPATH` tro vao mot thu muc khong phai
    #    goc kho, roi `-m apps.auto_scan_video.demucs_runner` bao "no module"
    #    o mot cho hoan toan khac. Dung dung mot thuong quyen cua nen tang, no
    #    di nguoc len toi thu muc DAU TIEN co `server/static` — khong phu thuoc
    #    do sau cua file goi.
    from platform_core.frontend_bundle import REPO_ROOT
    goc = str(REPO_ROOT)
    moi_truong["PYTHONPATH"] = goc + os.pathsep + moi_truong.get("PYTHONPATH", "")

    try:
        r = _chay_kem_moi_truong(cmd, timeout=timeout, hoi_huy=hoi_huy,
                                 moi_truong=moi_truong)
    except subprocess.TimeoutExpired as exc:
        raise MediaError(_t('Tách nguồn tiếng quá hạn.')) from exc

    if r.returncode != 0:
        # ⭐ Doc stdout TRUOC khi dung ma thoat de dung mot loi chung: tien trinh
        #    con phan biet duoc "cap card hong" voi "tieng hong", va san hai thu
        #    do thanh mot `MediaError` la vut di chinh cai phan biet ay. Mot ben
        #    nen THU LAI (card khac co the chay); ben kia thu lai bao nhieu lan
        #    cung the.
        try:
            bao = json.loads((r.stdout or b"").decode("utf-8", "replace")
                             .strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            bao = {}
        if bao.get("thieu_card"):
            raise ThieuCard(_t('Nền tảng đã cấp card nhưng tiến trình tách '
                               'không thấy GPU.'))
        loi = (r.stderr or b"").decode("utf-8", "replace")[-400:]
        raise MediaError(_t('Tách nguồn tiếng thất bại: {loi}').format(loi=loi))
    try:
        return json.loads((r.stdout or b"").decode("utf-8", "replace").strip()
                          .splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise MediaError(_t('Tách nguồn tiếng không trả về kết quả đọc được.')) from exc


def _chay_kem_moi_truong(cmd, *, timeout, hoi_huy, moi_truong):
    """Nhu `nhap_media._chay` nhung truyen moi truong xuong tien trinh con.

    Tach ra thay vi them tham so vao `_chay`: `_chay` phuc vu ffmpeg/ffprobe,
    va chung khong bao gio can moi truong GPU. Mot tham so chi mot ben dung la
    mot tham so se bi truyen nham.
    """
    import time

    if hoi_huy is None:
        return subprocess.run(cmd, capture_output=True, timeout=timeout,
                              env=moi_truong)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=moi_truong)
    han = time.monotonic() + timeout
    while True:
        if hoi_huy():
            proc.kill(); proc.communicate()
            raise DaHuy(_t('Phiên chạy đã bị huỷ giữa chừng.'))
        con_lai = han - time.monotonic()
        if con_lai <= 0:
            proc.kill(); out, err = proc.communicate()
            raise subprocess.TimeoutExpired(cmd, timeout, output=out, stderr=err)
        try:
            out, err = proc.communicate(timeout=min(0.5, con_lai))
            return subprocess.CompletedProcess(cmd, proc.returncode, out, err)
        except subprocess.TimeoutExpired:
            continue


def bieu_thuc_nen(duong_stem: dict, lop: dict | None = None) -> tuple[list[str], str]:
    """`(danh sach "-i ...", chuoi loc)` cho `tron_nen`.

    Tach rieng de KIEM duoc ma khong chay ffmpeg (khuon
    `am_master.bieu_thuc_tron`, xem `test_479`). Xem `tron_nen` ve hop dong
    day du cua ho so `lop`.
    """
    a = tu_cai_dat_lop(lop)

    vao: list[str] = []
    dau_vao: list[tuple[int, float]] = []   # (chi so `-i`, gain tuyen tinh)
    idx = 0
    for ten_lop, stems in LOP_STEM.items():
        if not a[f"{ten_lop}_bat"]:
            continue
        gain = a[f"{ten_lop}_gain"]
        if gain <= 0.0:
            continue
        for ten_stem in stems:
            duong = duong_stem.get(ten_stem)
            if not duong:
                log.warning("tron_nen: thieu stem %s cho lop %s — bo qua "
                           "(khac voi khach tat lop)", ten_stem, ten_lop)
                continue
            vao += ["-i", duong]
            dau_vao.append((idx, gain))
            idx += 1

    if not dau_vao:
        raise MediaError(_t('Không tìm thấy phần nhạc nền sau khi tách.'))

    phan: list[str] = []
    nhan_amix: list[str] = []
    for i, gain in dau_vao:
        # ⭐ gain == 1,0 -> KHONG chen bo loc `volume`: giu dinh dang mac dinh
        #    dung tung ky tu chuoi loc cu (va tranh mot lan `volume` vo ich).
        if abs(gain - 1.0) < 1e-9:
            nhan_amix.append(f"[{i}:a]")
        else:
            phan.append(f"[{i}:a]volume={gain}[g{i}];")
            nhan_amix.append(f"[g{i}]")
    n = len(dau_vao)
    loc = ("".join(phan) + "".join(nhan_amix)
           + f"amix=inputs={n}:normalize=0[tron];"
           f"[tron]loudnorm=I={LUFS_DICH}:TP={DINH_THAT_DB}:LRA=11[ra]")
    return vao, loc


def tron_nen(duong_stem: dict, dich: str, *, hoi_huy=None,
             timeout: int = 900, lop: dict | None = None) -> str:
    """Tron CAC STEM theo ho so BA LOP (`lop`) thanh ban nen, roi chuan am luong.

    Khuon `amix` lay tu `Cut_only ver2/nerf_engine/stages/audio.py:95 mix_stems`
    (mot `volume=<gain>` rieng cho tung dau vao roi `amix normalize=0`).

    B2 (25/09) — truoc chi gom `STEM_GIU` o he so 1,0 co dinh; nay `lop` (xem
    `LOP_STEM`/`chuan_hoa_lop`) chon TUNG lop co vao amix hay khong va he so
    nhan cua no:

      * `lop=None` (hoac ho so RONG/MAC_DINH) phai tai tao DUNG hanh vi cu:
        cung ba stem (drums, bass, other), cung THU TU, khong mot bo loc
        `volume` nao chen them khi gain == 1,0 — chuoi loc RA Y HET chuoi
        truoc B2 (`test_lop_nen_MAC_DINH_giu_dung_chuoi_va_byte_cu`).
      * mot lop `_bat=False` HOAC `_gain<=0` bi LOAI KHOI danh sach `-i` —
        khong dua vao amix nhu mot nhanh cam: mot nhanh cam van doi so dau
        vao cua `amix` va co the doi `normalize`/do dai ket qua (⭐ luat B2 #6).
      * mot stem duoc yeu cau (`_bat=True`, gain>0) nhung KHONG co trong
        `duong_stem` (demucs thieu tep) chi bi BO QUA co canh bao log — day la
        NGUYEN NHAN KHAC voi "khach tat lop": phan biet o `chuan_hoa_lop` (tu
        choi som, truoc ffmpeg) va o day (log canh bao, khong nem, tru khi
        RONG toan bo).
    """
    vao, loc = bieu_thuc_nen(duong_stem, lop)

    Path(dich).parent.mkdir(parents=True, exist_ok=True)
    cmd = ([media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error"]
           + vao + ["-filter_complex", loc, "-map", "[ra]",
                    "-ac", str(SO_KENH_TACH), "-ar", str(TAN_SO_TACH),
                    "-c:a", "pcm_s16le", dich])
    try:
        r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired as exc:
        raise MediaError(_t('Trộn nhạc nền quá hạn.')) from exc
    if r.returncode != 0:
        loi = (r.stderr or b"").decode("utf-8", "replace")[-300:]
        raise MediaError(_t('Trộn nhạc nền thất bại: {loi}').format(loi=loi))
    return dich


def van_tay_tach(*, checksum_nguon: str, phien_ban_ffmpeg_: str,
                 lop: dict | None = None) -> str:
    """Van tay cua ban nen.

    Nam thanh phan, thieu bat cu cai nao deu lam cache noi doi: noi dung nguon,
    ten model, chinh sach stem, ho so BA LOP (B2), va phien ban cong cu.
    """
    goi = json.dumps({
        "nguon": checksum_nguon,
        "model": MODEL_TACH,
        "stem_giu": list(STEM_GIU),
        "lufs": LUFS_DICH,
        "dinh": DINH_THAT_DB,
        "tan_so": TAN_SO_TACH,
        "so_kenh": SO_KENH_TACH,
        "phien_ban": PHIEN_BAN_TACH,
        "lop": tu_cai_dat_lop(lop),
        "ffmpeg": phien_ban_ffmpeg_,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def do_am_luong(duong: str) -> dict:
    """Do am luong tich hop va dinh that bang `loudnorm` che do phan tich.

    Dung de KIEM ban ra (Prompt 09 muc 7), khong de sua no. Mot phep do tra ve
    con so thi kiem duoc; mot phep chuan hoa khong noi gi ve ket qua cua chinh no.
    """
    cmd = [media.ffmpeg_bin(), "-hide_banner", "-nostats", "-i", duong,
           "-af", f"loudnorm=I={LUFS_DICH}:TP={DINH_THAT_DB}:LRA=11:print_format=json",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=300)
    van_ban = (r.stderr or b"").decode("utf-8", "replace")

    # ⚠️ Phai cat CA HAI dau. `loudnorm` in khoi JSON ra stderr **giua chung**,
    #    roi ffmpeg in tiep dong tong ket sau no:
    #
    #        [Parsed_loudnorm_0 @ ...]
    #        { "input_i" : "-21.75", ... }
    #        [out#0/null @ ...] video:0KiB audio:1500KiB ...
    #        size=N/A time=00:00:02.00 bitrate=N/A ...
    #
    #    Ban dau cho nay lay tu `{` **den het chuoi**, nen `json.loads` luon vo
    #    vi hai dong duoi. Trieu chung la "khong do duoc am luong" — mot thong
    #    bao chi vao ffmpeg trong khi loi nam o day.
    dau, cuoi = van_ban.rfind("{"), van_ban.rfind("}")
    if dau < 0 or cuoi < dau:
        raise MediaError(_t('Không đo được âm lượng.'))
    try:
        goc = json.loads(van_ban[dau:cuoi + 1])
    except json.JSONDecodeError as exc:
        raise MediaError(_t('Không đo được âm lượng.')) from exc
    return {
        "lufs": float(goc.get("input_i", 0) or 0),
        "dinh_that": float(goc.get("input_tp", 0) or 0),
    }
