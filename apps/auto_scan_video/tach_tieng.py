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
import subprocess
import sys
from pathlib import Path

from platform_core import media
from platform_core.i18n import _ as _t

from .demucs_runner import ThieuCard
from .nhap_media import DaHuy, MediaError, _chay, phien_ban_ffmpeg

#: Dang vao cua htdemucs. 44,1 kHz stereo la dang model duoc huan luyen tren.
TAN_SO_TACH = 44100
SO_KENH_TACH = 2

#: Stem giu lai lam nen. `vocals` bi bo — do la ca muc dich.
STEM_GIU = ("drums", "bass", "other")
STEM_BO = ("vocals",)

#: Chuan am luong cua ban nen. Ke thua tu
#: `Cut_only ver2/nerf_engine/stages/audio.py:54` — do la con so da chay that.
LUFS_DICH = -14.0
DINH_THAT_DB = -1.5

#: Doi khi doi bat cu thu gi o tren. Di vao van tay (O13).
PHIEN_BAN_TACH = 1

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


def tach_nguon(vao_wav: str, thu_muc_ra: str, *, gpu_env: dict | None = None,
               buoc_gpu: bool = False, hoi_huy=None, timeout: int = 5400) -> dict:
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
    cmd = [sys.executable, "-m", "apps.auto_scan_video.demucs_runner",
           vao_wav, thu_muc_ra]
    if buoc_gpu:
        cmd.append("--buoc-gpu")

    import os
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


def tron_nen(duong_stem: dict, dich: str, *, hoi_huy=None,
             timeout: int = 900) -> str:
    """Tron cac stem GIU LAI thanh ban nen, roi chuan am luong.

    Khuon `amix` lay tu `Cut_only ver2/nerf_engine/stages/audio.py:95 mix_stems`.
    Khac hai cho, ca hai co y:

      * ban di san cho tung stem mot he so `volume` rieng (no dang lam mot ban
        phoi sang tao). MVP **khong** phoi lai — no giu nguyen tuong quan giua
        cac nhac cu ma tac gia da dung. Nen moi stem giu he so 1,0.
      * them `loudnorm` ngay trong cung mot lan chay ffmpeg thay vi mot lan thu
        hai: it hon mot vong giai ma/ma hoa, va it hon mot tep tam de thanh rac.
    """
    giu = [(ten, duong_stem[ten]) for ten in STEM_GIU if ten in duong_stem]
    if not giu:
        raise MediaError(_t('Không tìm thấy phần nhạc nền sau khi tách.'))

    vao: list[str] = []
    for _, duong in giu:
        vao += ["-i", duong]
    nhan = "".join(f"[{i}:a]" for i in range(len(giu)))
    loc = (f"{nhan}amix=inputs={len(giu)}:normalize=0[tron];"
           f"[tron]loudnorm=I={LUFS_DICH}:TP={DINH_THAT_DB}:LRA=11[ra]")

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


def van_tay_tach(*, checksum_nguon: str, phien_ban_ffmpeg_: str) -> str:
    """Van tay cua ban nen.

    Bon thanh phan, thieu bat cu cai nao deu lam cache noi doi: noi dung nguon,
    ten model, chinh sach stem, va phien ban cong cu.
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
