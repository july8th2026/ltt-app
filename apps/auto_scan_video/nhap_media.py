"""Giai doan MEDIA_PREPARE: soi, thi hanh chinh sach dau vao, chuan hoa tieng.

Engine THAT dau tien cua Auto Scan (pha 08). Truoc pha nay moi giai doan la gia.

## Chuan hoa o day nghia la gi — va KHONG nghia la gi

`MVP_CONTRACT.md` D-ASV-03: MVP **sao chep** luong video chu khong ma hoa lai, vi
khong giai doan nao doi mot diem anh. Nen "chuan hoa" o day **khong** dung toi
video. No sinh ra dung mot thu: mot ban tieng 16 kHz mot kenh, la dang ma tang
chep loi can.

⭐ Ban goc duoc GIU NGUYEN. Artifact chuan hoa la mot dong lineage MOI tro ve no
   (`parent_keys`), khong phai mot ban thay the. Mat ban goc la mat kha nang
   tinh lai moi thu ha nguon.

## Vi sao co mot ham soi rieng thay vi dung thang `platform_core.media.probe`

`media.probe` tra ve duration/width/height/codec/fps/audio_codec/size/bitrate —
du cho phan lon app, thieu cho cho nay. Chinh sach dau vao cua
`MVP_CONTRACT.md` muc 2 va duong sao chep D-ASV-03 con can:

    co luong tieng khong        -> tu choi ngay luc nop neu khong
    codec video co copy duoc    -> H.264/HEVC moi vao duoc MP4
    so kenh / tan so lay mau    -> quyet dinh cach chuan hoa
    nhip hinh co bien thien     -> VFR lam moc thoi gian troi
    xoay man hinh               -> doc/ngang

Nen o day goi thang `ffprobe` de lay ca `streams`. Khong sua `platform_core`:
day la nhu cau cua mot app, va O20 noi ro chi mo rong loi khi khong con duong
o cap app.

## Chay tien trinh con: khuon lay tu `apps/upscalevideo/ff.py:36`

Cung hinh dang (Popen + hoi huy + tran thoi gian), viet lai ~25 dong thay vi
import cheo app. `ff.py` la be mat cua mot app khac va chua nhieu thu rieng cua
no (on dinh hinh, trich khung, chon encoder); keo mot canh phu thuoc lien-app
cho hai muoi dong la mot cai gia dat hon la chep mot **khuon**.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from platform_core import media
from platform_core.i18n import _ as _t

from .tables import KIND_AUDIO

# ── Chinh sach dau vao (MVP_CONTRACT.md muc 2) ───────────────────────────────
#
# ⭐ Ke thua tu hai app dang chay that, khong bia ra:
#    `apps/autosubvideo/routes.py:47-49,368` va `apps/upscalevideo/routes.py:32-34`.
THOI_LUONG_TOI_DA_S = 7200.0          # 2 gio
#: ⛔ `video/webm` bi loai CO Y du `upscalevideo` nhan no: VP8/VP9 khong copy
#:    duoc vao MP4, ma duong sao chep la nen cua D-ASV-03.
CODEC_COPY_DUOC = frozenset({"h264", "hevc"})

# ── Cau hinh chuan hoa tieng ─────────────────────────────────────────────────
#
# 16 kHz mot kenh la dang vao chuan cua Whisper/faster-whisper. Chuyen o day mot
# lan thay vi de tang chep loi tu lam: no lam moi lan chay lai deu ton lai cong
# giai ma, va no dat mot quyet dinh dinh dang vao trong mot engine co the doi.
TAN_SO_ASR = 16000
SO_KENH_ASR = 1
#: Doi phien ban nay khi doi bat cu tham so nao o tren. No di vao van tay, nen
#: mot lan doi se lam moi cache cu vo hieu — dung nhu O13 doi.
PHIEN_BAN_CHUAN_HOA = 1


class MediaError(ValueError):
    """Dau vao khong dat chinh sach, hoac ffmpeg/ffprobe that bai."""


class DaHuy(RuntimeError):
    """Job bi huy trong luc mot tien trinh con dang chay."""


# ══════════════════════════════════════════════════════════════════════════════
#  Chay tien trinh con an toan
# ══════════════════════════════════════════════════════════════════════════════

def _chay(cmd: list[str], *, timeout: int = 900, hoi_huy=None) -> subprocess.CompletedProcess:
    """Chay mot lenh. Danh sach doi so, KHONG BAO GIO `shell=True`.

    ⛔ `shell=True` voi mot duong dan do khach dat ten la mot duong tiem lenh.
       Ten tep den tu `filename` cua ve tai len; du nen tang da loc, mot lop
       phong thu dua vao viec do la mot lop phong thu.

    `hoi_huy` duoc hoi moi 0,5 giay. Huy la **hop tac**: ta giet tien trinh con
    roi nem `DaHuy`, thay vi de mot lan render dai chay tiep sau khi khach da
    bam huy va da duoc hoan tien.
    """
    if hoi_huy is None:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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


def phien_ban_ffmpeg() -> str:
    """`ffmpeg version <x>` — di vao van tay (Prompt 08 muc 8).

    Vi sao can: mot ban ffmpeg khac co the sinh ra ban tieng khac o cung mot bo
    tham so. Neu phien ban khong nam trong van tay thi sau khi nang cong cu, moi
    lan chay lai se **dung lai ket qua cu** ma khong ai biet — dung kieu hong ma
    O13 sinh ra de chan.

    🔴 **Nhanh loi tung tra hang so `"khong-ro"` (sua 27/09), va no pha DUNG cai
       ma doan tren noi nay de chan.** `"khong-ro"` giong nhau cho MOI ban ffmpeg,
       nen hai ban khac nhau ma phep soi truot deu ra CUNG mot khoa cache: nang
       cong cu xong, `van_tay_chuan_hoa` khong doi, va lan chay sau dung lai ban
       tieng cua cong cu CU. Ho loi *"mot gia tri ganh hai trang thai"* — o day
       la *"phien ban X"* va *"⛔ khong biet phien ban"*.

       Phep soi truot that su xay ra: `timeout=30` tren may dang 100 % CPU, va
       stdout rong khi worker chay duoi `LocalSystem` (PATH khac phien nguoi dung).

    ⭐ **Truot thi lui ve DANH TINH CUA TEP, ⛔ khong ve mot hang so.** `size` +
       `mtime` + duong dan da phan biet duoc hai ban dung: cache VAN trung khi
       cong cu khong doi (nen ta ⛔ khong tra tien tinh lai vo co), va no TU khac
       khi cong cu doi — dung viec ma truong nay ton tai de lam.

    ⛔ Va khi ca `stat` cung khong duoc thi tra mot gia tri **DUY NHAT cho moi
       lan goi**: cache truot han. Huong hong la "tinh lai", ⛔ khong bao gio la
       "dung lai mot ket qua ta khong the chung minh la cung cong cu".
    """
    try:
        r = subprocess.run([media.ffmpeg_bin(), "-version"],
                           capture_output=True, text=True, timeout=30)
        dong = (r.stdout or "").splitlines()[0]
        m = re.match(r"ffmpeg version (\S+)", dong)
        return m.group(1) if m else dong[:64]
    except (OSError, subprocess.SubprocessError, IndexError):
        return _danh_tinh_tep_ffmpeg()


def _danh_tinh_tep_ffmpeg() -> str:
    """Danh tinh ban dung khi `ffmpeg -version` khong chay duoc. Xem
    `phien_ban_ffmpeg`. Tien to `khong-ro-` giu lai cho nguoi doc log biet day la
    duong LUI, ⛔ khong phai mot so phien ban that."""
    import hashlib
    import uuid

    try:
        p = Path(media.ffmpeg_bin())
        st = p.stat()
        mau = f"{p.resolve()}|{st.st_size}|{int(st.st_mtime)}"
        return "khong-ro-" + hashlib.sha256(mau.encode("utf-8")).hexdigest()[:16]
    except (OSError, MediaError, ValueError):
        # ⛔ Khong chung minh duoc la cung cong cu => khong duoc dung lai cache.
        return "khong-ro-" + uuid.uuid4().hex[:16]


# ══════════════════════════════════════════════════════════════════════════════
#  Soi
# ══════════════════════════════════════════════════════════════════════════════

def _nhip(chuoi: str) -> float:
    """`"30000/1001"` -> 29.97. Tra 0.0 khi khong doc duoc."""
    try:
        if "/" in str(chuoi):
            tu, mau = str(chuoi).split("/", 1)
            return (float(tu) / float(mau)) if float(mau) else 0.0
        return float(chuoi)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _giay(tho) -> float | None:
    """`duration` cua mot luong -> giay, hoac `None` khi luong khong khai."""
    if tho in (None, ""):
        return None
    try:
        return float(tho)
    except (TypeError, ValueError):
        return None


def soi(duong: str, *, hoi_huy=None) -> dict:
    """Soi day du bang ffprobe. Nem `MediaError` neu khong doc duoc.

    Tra ve mot tu dien PHANG, co chu dinh: nhung thu chinh sach can tra loi phai
    o ngay tang tren, khong phai chon trong mot cay `streams` ma moi cho goi lai
    phai tu duyet.
    """
    cmd = [media.ffprobe_bin(), "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", duong]
    try:
        r = _chay(cmd, timeout=120, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired as exc:
        raise MediaError(_t('Không đọc được thông tin tệp (quá hạn).')) from exc
    if r.returncode != 0:
        raise MediaError(_t('Không đọc được tệp media.'))
    try:
        goc = json.loads(r.stdout.decode("utf-8", "replace"))
    except json.JSONDecodeError as exc:
        raise MediaError(_t('Không đọc được thông tin tệp.')) from exc

    luong = goc.get("streams") or []
    dinh_dang = goc.get("format") or {}
    v = next((s for s in luong if s.get("codec_type") == "video"), None)
    a = next((s for s in luong if s.get("codec_type") == "audio"), None)

    #: VFR: `r_frame_rate` la nhip danh dinh, `avg_frame_rate` la nhip trung binh
    #: that. Lech dang ke nghia la nhip bien thien, va moc thoi gian se troi neu
    #: giai doan ha nguon gia dinh nhip co dinh.
    r_fps = _nhip((v or {}).get("r_frame_rate", 0))
    avg_fps = _nhip((v or {}).get("avg_frame_rate", 0))
    vfr = bool(r_fps and avg_fps and abs(r_fps - avg_fps) / max(r_fps, avg_fps) > 0.01)

    xoay = 0
    for phu in ((v or {}).get("side_data_list") or []):
        if "rotation" in phu:
            try:
                xoay = int(float(phu["rotation"])) % 360
            except (TypeError, ValueError):
                xoay = 0

    rong = int((v or {}).get("width") or 0)
    cao = int((v or {}).get("height") or 0)
    # Xoay 90/270 doi cho hai chieu khi hien thi.
    doc = (cao > rong) if xoay % 180 == 0 else (rong > cao)

    return {
        "co_video": v is not None,
        "co_tieng": a is not None,
        "thoi_luong": float(dinh_dang.get("duration") or 0.0),
        "co_byte": int(dinh_dang.get("size") or 0),
        "codec_video": (v or {}).get("codec_name") or "",
        "codec_tieng": (a or {}).get("codec_name") or "",
        # ⭐ Do dai TUNG LUONG, ben canh do dai container o tren. Hai thu khac
        #    nhau, va cho chung lech nhau chinh la cho tieng va hinh lech nhau
        #    — dung thu san pham nay ban. QC T16 doc hai truong nay.
        #
        # ⚠️ `None` khi luong khong tu khai `duration`, va do KHONG phai `0`:
        #    MP4 duoc phep bo qua truong nay. Nguoi doc phai phan biet *"khong
        #    khai"* voi *"dai 0 giay"* — doan bang `0` se bien mot tep hoan toan
        #    binh thuong thanh mot bao cao hong.
        "thoi_luong_video": _giay((v or {}).get("duration")),
        "thoi_luong_tieng": _giay((a or {}).get("duration")),
        "rong": rong,
        "cao": cao,
        "fps": r_fps,
        "fps_tb": avg_fps,
        "vfr": vfr,
        "xoay": xoay,
        "doc": doc,
        "so_kenh": int((a or {}).get("channels") or 0),
        "tan_so": int((a or {}).get("sample_rate") or 0),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Chinh sach dau vao
# ══════════════════════════════════════════════════════════════════════════════

def nhip_that(tt: dict) -> float:
    """Nhip THAT cua luong hinh trong mot ho so `soi`, hay `0.0` khi ⛔ khong biet.

    ⭐ **MOT noi tra loi cau *"video nay chay bao nhieu khung mot giay"*.** `soi`
       ghi BA truong — `fps` (`r_frame_rate`, nhip DANH DINH), `fps_tb`
       (`avg_frame_rate`, nhip THAT) va `vfr` — va ai doc rieng MOT truong thi
       doc sai mot nua ca video: voi nguon VFR, `r_frame_rate` thuong CAO hon
       nhip that, nen khai no o `-r` se bat bo ma hoa NHAN BAN khung.

    ⚠️ `0.0` = *"⛔ khong biet"*, KHAC han *"nhip bang 0"*. Noi goi phai phan
       biet hai ca do va ⛔ KHONG doan mot con so khi ⛔ khong biet — ep video
       cua khach ve mot nhip ta bia ra thi te hon la de bo ma hoa tu chon.
    """
    try:
        nhip = float((tt.get("fps_tb") if tt.get("vfr") else tt.get("fps")) or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return nhip if nhip > 0 else 0.0


def kiem_chinh_sach(tt: dict) -> None:
    """Thi hanh `MVP_CONTRACT.md` muc 2. Nem `MediaError` kem ly do doc duoc.

    Moi thong bao noi ro **cai gi sai** va **gioi han la bao nhieu**. Mot loi
    "dinh dang khong hop le" bat khach doan, va ho se doan sai roi thu lai —
    moi lan thu lai la mot lan tra tien cho mot cau tra loi ta da biet truoc.
    """
    if not tt.get("co_video"):
        raise MediaError(_t('Tệp không có luồng hình.'))

    # ⛔ Tu choi NGAY LUC NOP, khong phai o giai doan chep loi. Mot video cam
    #    khong co gi de long tieng; phat hien dieu do sau ba giai doan co tinh
    #    tien la mot lan hoan tien, va hoan tien la cach dat de noi "khong".
    if not tt.get("co_tieng"):
        raise MediaError(_t('Tệp không có luồng tiếng nên không có gì để lồng tiếng.'))

    thoi_luong = float(tt.get("thoi_luong") or 0.0)
    if thoi_luong <= 0:
        raise MediaError(_t('Không đọc được thời lượng — tệp có thể đã hỏng.'))
    if thoi_luong > THOI_LUONG_TOI_DA_S:
        raise MediaError(_t('Video dài {co} phút, vượt giới hạn {tran} phút.')
                         .format(co=f"{thoi_luong / 60:.0f}",
                                 tran=f"{THOI_LUONG_TOI_DA_S / 60:.0f}"))

    codec = (tt.get("codec_video") or "").lower()
    if codec not in CODEC_COPY_DUOC:
        # 🔑 D-ASV-03: MVP sao chep luong video. Mot codec khong copy duoc vao
        #    MP4 se buoc phai ma hoa lai — tuc tieu GPU cua khach va lam mat chat
        #    luong cho mot viec ho khong yeu cau. Tu choi to ro hon la lam lang.
        raise MediaError(
            _t('Định dạng hình {codec} chưa hỗ trợ; cần H.264 hoặc HEVC '
               'trong MP4/MOV.').format(codec=codec or _t('không rõ')))


# ══════════════════════════════════════════════════════════════════════════════
#  Chuan hoa
# ══════════════════════════════════════════════════════════════════════════════

def van_tay_chuan_hoa(*, checksum_nguon: str, phien_ban_cong_cu: str) -> str:
    """Van tay cua ban tieng chuan hoa (Prompt 08 muc 8).

    Ba thanh phan, va thieu bat cu cai nao deu lam cache noi doi:
      `checksum_nguon`     doi tep vao   -> phai tinh lai
      cau hinh chuan hoa   doi tham so   -> phai tinh lai
      `phien_ban_cong_cu`  doi ffmpeg    -> phai tinh lai
    """
    import hashlib
    goi = json.dumps({
        "nguon": checksum_nguon,
        "tan_so": TAN_SO_ASR,
        "so_kenh": SO_KENH_ASR,
        "phien_ban": PHIEN_BAN_CHUAN_HOA,
        "ffmpeg": phien_ban_cong_cu,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def tach_tieng_cho_asr(nguon: str, dich: str, *, hoi_huy=None,
                       timeout: int = 1800) -> str:
    """Rut tieng ra WAV 16 kHz mot kenh. Tra ve `dich`.

    ⭐ `-vn` (bo hinh) chu khong phai `-c:v copy`: ta dang lam ra vat lieu cho
       tang chep loi, khong phai mot ban video thu hai. Ban goc **khong bi cham**.

    ⛔ Ghi ra tep TAM roi de nguoi goi promote. Ghi thang vao khoa ben vung se
       lam mot lan ffmpeg chet giua chung de lai mot tep cut duoi mot cai ten
       chinh thuc — dung dieu ADR-001 D7 sinh ra de chan.
    """
    Path(dich).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
        "-i", nguon,
        "-vn",                                  # chi lay tieng
        "-ac", str(SO_KENH_ASR),                # tron ve mot kenh
        "-ar", str(TAN_SO_ASR),
        "-c:a", "pcm_s16le",                    # PCM: khong mat mat, ai cung doc duoc
        dich,
    ]
    try:
        r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired as exc:
        raise MediaError(_t('Tách tiếng quá hạn.')) from exc
    if r.returncode != 0:
        loi = (r.stderr or b"").decode("utf-8", "replace")[-400:]
        raise MediaError(_t('Tách tiếng thất bại: {loi}').format(loi=loi))
    if not Path(dich).exists() or Path(dich).stat().st_size == 0:
        raise MediaError(_t('Tách tiếng xong nhưng tệp rỗng.'))
    return dich


#: Loai artifact ma giai doan nay sinh ra.
KIND_BAN_TIENG = KIND_AUDIO
