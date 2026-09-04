"""Trinh render: mot BAN DUNG da luu -> mot tep media da kiem.

## Doi chieu ba ban render truoc khi viet (Prompt 15 muc 1)

|  | `DUNGVIDEO-FULL/engine/assemble.py` | `Cut_only/…/ffmpeg_edit_cutonly.py` | `apps/autosubvideo/burn.py` |
|---|---|---|---|
| viec | cat clip + xfade + ma hoa lai | thay tieng, giu hinh | dot phu de |
| hinh | **ma hoa lai** libx264 | **`-c:v copy`** | ma hoa lai (bat buoc, phu de dot vao) |
| tron nhieu lop tieng theo moc | khong | khong | khong |
| tien do | khong | nhip 15 giay tu mot luong nen | **`-progress pipe:1`, doc `out_time`** |
| huy | khong | khong | **co** — `on_progress` nem thi giet tien trinh |
| chay bang | `subprocess.run`, danh sach doi so | `subprocess.run`, danh sach doi so | `Popen`, danh sach doi so |
| dung tep tam roi doi ten | khong | khong | khong |

⇒ **Khong ban nao dung nguyen duoc**, va ly do khong phai chat luong:

  * `assemble.py` la duong **cat**, ma `MVP_CONTRACT.md` §4 da hoan (D-ASV-02).
    Thu lay duoc tu no la chinh sach ma hoa tieng: `-c:a aac -ar 48000 -ac 2`
    va `-movflags +faststart` (`assemble.py:199-207`).
  * `replace_audio` (`ffmpeg_edit_cutonly.py:323`) dung **hinh dang** cua MVP —
    thay tieng, giu hinh — nhung no nhan **mot** tep tieng da tron san. Ta co N
    lop phai dat vao N moc thoi gian khac nhau, tuc phan kho nhat khong nam
    trong no.
  * `burn.py` co dung hai thu ma hai ban kia khong co (tien do that + huy hop
    tac), nen phan **cach chay** lay tu no.

⇒ Ta muon **chinh sach** cua ban thu nhat, **hinh dang** cua ban thu hai, va
  **cach chay** cua ban thu ba. Phan tron nhieu lop theo moc la moi.

## Vi sao dung `-c:v copy` — va vi sao dieu do quyet dinh ca lan nay

Hinh khong bi cham toi. Hai he qua that:

  1. **Khong dung GPU.** Prompt 15 muc 6 noi ro: chi xin GPU neu trinh render
     that su dung. Sao chep luong hinh + ma hoa AAC la viec cua CPU. Vi vay
     `pipeline.CHUOI` xep RENDER vao lan `asv_media` (ffmpeg) chu khong phai
     `asv_gpu`, va khong khai `tai_nguyen`. Xin mot suat GPU cho viec nay la
     giu mot thu khan hiem de khong dung toi.
  2. **Nhanh, va khong mat chat luong.** Mot video 10 phut xong trong vai chuc
     giay thay vi vai phut, va hinh cua khach ra dung bang bit no vao.

## Duong dan KHONG BAO GIO den tu chuoi cua khach

⛔ `shell=True` khong xuat hien o day, va do moi la lop phong thu thu hai. Lop
   thu nhat: moi duong trong argv deu do **ta** dung tu mot khoa luu tru da qua
   `assets.dat_khoa` (tung manh da kiem bang `_DOAN_HOP_LE`), roi tai ve mot thu
   muc tam **ta tu dat ten**. Ten tep goc cua khach khong bao gio di vao argv.
"""
from __future__ import annotations

import collections
import json
import logging
import re
import subprocess
import threading
import time
from pathlib import Path

from platform_core.i18n import _ as _t

from . import ban_dung
from .nhap_media import DaHuy, MediaError

log = logging.getLogger(__name__)

#: Am luong dich cua BAN RA. Cung so `tach_tieng` dung cho nhac nen va cung so
#: `qc` do lai — MOT nguon chan ly, khong phai ba con so tinh co bang nhau.
from .tach_tieng import DINH_THAT_DB as DINH_THAT_RA_DB
from .tach_tieng import LUFS_DICH as LUFS_DICH_RA

#: Doi khi doi cach dung lenh. Vao van tay (O13).
#:
#: ⭐ 1 → 2 o pha 18: them `loudnorm` tren ban tron cuoi. Neu khong nang so nay
#:    thi moi lan chay lai se dung lai tep cu tu cache va ban va **khong bao gio
#:    chay** — dung mon no ma pha 15 vua tra, va lan nay no duoc tra ngay.
PHIEN_BAN_KET_XUAT = 2

#: Bien do lech cho phep giua thoi luong MONG DOI (ban dung) va thoi luong DO
#: DUOC o tep ra. Khong phai mot con so tuy y: `-c:v copy` giu nguyen khung hinh
#: nen sai so chi den tu lam tron moc keyframe va do dai goi tieng cuoi.
LECH_THOI_LUONG_GIAY = 1.0

_OUT_TIME_US = re.compile(r"^out_time_us=(\d+)")
_OUT_TIME = re.compile(r"^out_time=(\d+):(\d+):([\d.]+)")


class KetXuatError(MediaError):
    """Render that bai."""


# ══════════════════════════════════════════════════════════════════════════════
#  1. Dung lenh — HAM THUAN, kiem duoc ma khong can ffmpeg
# ══════════════════════════════════════════════════════════════════════════════
#
# ⭐ Tach phan nay ra khoi phan chay la thu lam pha 15 kiem duoc that. Mot bo
#    render chi kiem duoc bang "chay thu roi xem tep ra" thi moi phep kiem deu
#    can ffmpeg, can vai giay, va khong noi duoc **vi sao** no sai. O day lenh
#    la mot gia tri: so sanh duoc, in ra duoc, che duoc.

# 🔴 **`_loc_am` da duoc GO o pha 17, va day la cho ghi lai vi sao.**
#
#    Ham do tron nen + N lop tieng + `loudnorm` **ngay trong lenh render**. Pha
#    16 dung mot BAN PHOI hoan chinh truoc do; giu ca hai nghia la chuan hoa am
#    luong HAI LAN tren cung mot dong tin hieu, va lan thu hai thang im lang.
#
# ⭐ Bon bai hoc cua no khong bi vut di — chung da tra gia va chung di theo sang
#    `am_master`, cung voi phep kiem cua chung:
#
#      * `amix ... normalize=0`   — mac dinh chia bien do cho so dau vao, tuc am
#                                   luong phu thuoc SO CAU NOI
#      * `adelay ... :all=1`      — thieu thi chi kenh dau bi tre, tieng lech tai
#      * `aformat` tung dau vao   — de `amix` tu chon la de no chon theo dau vao
#                                   dau tien
#      * `loudnorm ... dual_mono=true` — mot doan mono upmix len stereo bi do to
#                                   hon thuc te 3 dB neu thieu co nay
#
# ⛔ Xoa mot ham ma khong mang theo ly do ton tai cua no la cach chac chan de
#    nguoi sau viet lai dung cai ban dau da sai.


def dung_lenh(ban: dict, *, ffmpeg_bin: str, duong_video: str,
              duong_master: str,
              duong_lop: list[str], duong_ra: str,
              tien_do: bool = True) -> list[str]:
    """Ban dung + duong dan cuc bo -> argv. Khong cham mot tep nao.

    ⚠️ `duong_lop` phai **cung thu tu** voi `ban["tieng"]["lop"]`. Goi ham nay
       voi mot danh sach lech thu tu se ra mot ban long tieng trong do moi cau
       nam o cho cua mot cau khac — va no **khong hong**, no chi sai. Nen ham
       tu kiem thay vi tin nguoi goi.
    """
    from . import che_do_render as cdr

    lop = ban["tieng"]["lop"]
    if len(duong_lop) != len(lop):
        raise KetXuatError(
            _t('Số tệp tiếng ({co}) không khớp số lớp trong bản dựng ({can}).')
            .format(co=len(duong_lop), can=len(lop)))

    hinh = ban["hinh"]
    cach = str(hinh.get("cach_render") or cdr.SAO_CHEP)
    if cach not in cdr.CHE_DO:
        raise KetXuatError(_t('Bản dựng khai cách render không hợp lệ.'))

    # 🔴 **Cong cuoi cho loi hua cua preset giu hinh.**
    #
    #    Truoc pha 17 cho nay la mot chot VO DIEU KIEN: tu choi moi che do hinh
    #    khac `copy`. Pha 17 phai noi no ra vi preset CAT buoc phai ma hoa lai —
    #    nhung cach noi SAI la xoa han chot, vi khi do `localize_preserve_picture`
    #    mat lop bao ve **mot cach im lang**: khong phep kiem nao do, chi la mot
    #    ngay nao do mot khach chon "giu nguyen hinh anh" va nhan ve mot ban da
    #    ma hoa lai.
    #
    # ⇒ Chot khong bi xoa, no bi **thu hep**: preset nao thi cach render do, va
    #   doi chieu ngay tai day — cho cuoi cung truoc khi ton mot suat render.
    preset = str(ban.get("preset") or "")
    if preset:
        try:
            cho_phep = cdr.che_do_cho(preset)
        except cdr.CheDoError as exc:
            raise KetXuatError(str(exc)) from exc
        if cach != cho_phep:
            raise KetXuatError(
                _t('Bản dựng khai preset {p} nhưng xin cách render {c}.')
                .format(p=preset, c=cach))

    ra = ban["ra"]
    cmd = [ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
           "-i", duong_video, "-i", duong_master]

    if cach == cdr.SAO_CHEP:
        # ── Preset giu hinh: luong hinh di THANG tu nguon sang ban ra ─────
        #
        # ⛔ Khong giai ma, khong ma hoa, khong mat mat the he, khong ton mot
        #    suat GPU nao. Do la duong da chung minh cua V2 (D-ASV-03).
        cmd += ["-map", "0:v:0", "-c:v", str(hinh["che_do"])]
    else:
        # ── Preset cat: CAT-NOI roi ma hoa lai ───────────────────────────
        #
        # 🔴 Ma hoa lai o day khong phai mot lua chon toi uu hoa. Cat bang stream
        #    copy chi cat duoc tai KEYFRAME, va do that tren tep cua chinh chuoi
        #    nay cho **GOP 8,333 giay** — tuc diem cat bi day di toi 8,3 giay
        #    trong khi ban phoi am da dung theo diem cat CHINH XAC. Xem
        #    `che_do_render`.
        khoang = [(float(b), float(k)) for b, k in (hinh.get("khoang_giu") or ())]
        bo = str(hinh.get("bo_ma_hoa") or cdr.LUI_VE)
        cmd += ["-filter_complex", cdr.loc_cat_noi(khoang), "-map", "[ra]"]
        cmd += list(cdr.tham_so(bo))

    # ── Tieng: BAN PHOI cua pha 16, khong tron lai ───────────────────────
    #
    # ⭐ Ban phoi da tron nen + moi lop tieng va da chuan am luong MOT lan. Tron
    #    lai o day la chuan hoa hai lan tren cung mot dong tin hieu — va lan thu
    #    hai thang mot cach im lang.
    cmd += ["-map", "1:a:0"]

    cmd += [
        "-c:a", str(ra["codec_tieng"]),
        "-b:a", str(ra["bitrate_tieng"]),
        "-ar", str(ban["tieng"]["tan_so"]),
        "-ac", str(ban["tieng"]["so_kenh"]),
    ]
    if ra.get("faststart"):
        cmd += ["-movflags", "+faststart"]
    # `-shortest`: neu tieng dai hon hinh thi cat theo hinh. Khong co no, mot
    # doan tieng tran qua cuoi video se keo dai tep ra bang mot khung hinh dong
    # bang — dung nguyen van khuon cua `replace_audio`.
    cmd.append("-shortest")
    if tien_do:
        cmd += ["-progress", "pipe:1", "-nostats"]
    cmd.append(duong_ra)
    return cmd


# ══════════════════════════════════════════════════════════════════════════════
#  2. Ho so chan doan — CHE truoc khi luu (Prompt 15 muc 9)
# ══════════════════════════════════════════════════════════════════════════════

#: Nhung doan duong dan khong duoc ra ngoai. Duong tam mang ten may va ten
#: nguoi dung Windows (`C:\Users\<ten that>\AppData\...`), va mot ho so chan
#: doan duoc doc boi nguoi khong phai chu tep do.
_CHE = "<da-che>"


def lenh_da_che(cmd: list[str], *, goc_tam: str = "") -> list[str]:
    """Lenh de LUU LAI, khong phai lenh de chay.

    ⛔ Giu nguyen ca duong dan la ro ri hai chieu: no lo bo cuc dia cua may chu
       cho nguoi doc ho so, va no lo ten that cua nguoi dung Windows.

    Giu lai **ten tep** vi do la thu lam ho so chan doan co ich (biet doan nao
    thieu), bo phan thu muc.
    """
    ra = []
    for x in cmd:
        s = str(x)
        if goc_tam and s.startswith(goc_tam):
            ra.append(f"{_CHE}/{Path(s).name}")
        elif len(s) > 3 and ("/" in s or "\\" in s) and Path(s).name != s:
            ra.append(f"{_CHE}/{Path(s).name}")
        else:
            ra.append(s)
    return ra


#: Duong dan tuyet doi trong mot dong van ban.
#:
#: 🔴 **Khong duoc dung `\s` lam dau cham het.** Duong dan Windows CO DAU CACH,
#:    va dung cai nam sau dau cach moi la thu phai giau: ban dau bo do nay dung
#:    `[^\s]` va no che `C:\Users\Thang` roi de nguyen `Tuong\AppData\...` —
#:    tuc **ten that cua nguoi dung** di ra nguyen ven ngay sau chuoi da-che.
#:
#: ⇒ Cham het la dau nhay, dau ngoac hay het dong — nhung thu ffmpeg thuc su
#:   dung de dong mot duong dan. Che qua tay o mot ho so chan doan la huong an
#:   toan; che thieu thi khong.
_DUONG_TRONG_VAN = re.compile(
    r"""(?:[A-Za-z]:[\\/]|\\\\|(?<![\w])/)[^\r\n'"<>|]*""")


def van_ban_da_che(van: str, *, goc_tam: str = "") -> str:
    """Che moi duong dan trong mot doan van ban, giu lai TEN TEP.

    🔴 **Pha 25: `lenh_da_che` chi che mot nua duong ro ri.** Ho so chan doan luu
       ca `stderr` cua ffmpeg, va ffmpeg in nguyen duong dan trong do:

           Output #0, mp4, to 'C:\\Users\\<ten that>\\AppData\\...\\ra.mp4'

       Nen cau lenh duoc che sach trong khi cung thong tin do di ra bang cua sau,
       vao dung mot ban ghi duoc luu lai de nguoi khac doc.

    ⭐ Giu lai ten tep vi do la thu lam ho so chan doan co ich; bo phan thu muc,
       vi do la thu lo bo cuc dia may chu va ten that cua nguoi dung Windows.
    """
    van = str(van or "")
    if goc_tam:
        van = van.replace(goc_tam, _CHE)

    def _thay(m: "re.Match[str]") -> str:
        s = m.group(0).rstrip(".,;:)")
        duoi = m.group(0)[len(s):]
        return f"{_CHE}/{Path(s).name}{duoi}"

    return _DUONG_TRONG_VAN.sub(_thay, van)


def ho_so_chan_doan(ban: dict, cmd: list[str], *, goc_tam: str = "",
                    duoi_stderr: str = "") -> dict:
    """Thu de tra lai mot lan render that bai, KHONG kem bi mat nao."""
    return {
        "phien_ban_ket_xuat": PHIEN_BAN_KET_XUAT,
        "lenh": lenh_da_che(cmd, goc_tam=goc_tam),
        "tom_tat_ban_dung": ban_dung.tom_tat(ban),
        # Duoi cua stderr la thu noi ffmpeg khong thich cai gi. Cat ngan de mot
        # lan hong khong bien thanh mot cot CSDL vai megabyte — va CHE duong
        # dan, vi ffmpeg in ca duong dan day du vao day.
        "stderr": van_ban_da_che((duoi_stderr or "")[-2000:], goc_tam=goc_tam),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  3. Chay — tien do that, huy hop tac, khong bao gio de lai tep dang do
# ══════════════════════════════════════════════════════════════════════════════

def _chay_co_tien_do(cmd: list[str], *, tong_giay: float, timeout: int,
                     hoi_huy=None, bao_tien_do=None) -> str:
    """Chay ffmpeg, doc `-progress`, tra ve duoi cua stderr.

    Khuon lay tu `apps/autosubvideo/burn.py:40 _run_with_cleanup`. Khac mot cho
    co y: ban do dua vao viec `on_progress` **nem** de huy, nen phep huy chi xay
    ra khi ffmpeg co in ra mot dong tien do. Mot lan render ket o cho khong in
    gi (vd doc mot tep hong) se khong huy duoc. O day `hoi_huy` duoc hoi tu mot
    luong rieng theo dong ho, nen huy khong phu thuoc vao viec ffmpeg co noi gi.
    """
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    duoi: collections.deque[str] = collections.deque(maxlen=12)
    da_huy = threading.Event()
    han = time.monotonic() + timeout

    def _hut_stderr():
        try:
            for dong in proc.stderr:            # type: ignore[union-attr]
                if dong.strip():
                    duoi.append(dong.strip())
        except Exception as exc:      # noqa: BLE001 - luong phu, khong duoc lam sap
            log.debug("hut stderr cua ffmpeg dut: %s", exc)

    def _canh():
        """Hoi `hoi_huy` va dong ho moi 0,5 giay, doc lap voi dau ra cua ffmpeg."""
        while proc.poll() is None:
            if hoi_huy is not None and hoi_huy():
                da_huy.set()
                proc.kill()
                return
            if time.monotonic() > han:
                proc.kill()
                return
            time.sleep(0.5)

    t1 = threading.Thread(target=_hut_stderr, daemon=True)
    t2 = threading.Thread(target=_canh, daemon=True)
    t1.start()
    t2.start()
    try:
        for tho in proc.stdout:                 # type: ignore[union-attr]
            dong = tho.strip()
            giay = None
            m = _OUT_TIME_US.match(dong)
            if m:
                giay = int(m.group(1)) / 1_000_000
            else:
                m = _OUT_TIME.match(dong)
                if m:
                    giay = (int(m.group(1)) * 3600 + int(m.group(2)) * 60
                            + float(m.group(3)))
            if giay is not None and tong_giay > 0 and bao_tien_do:
                bao_tien_do(min(99.0, round(giay / tong_giay * 100, 1)))
        proc.wait(timeout=max(1, int(han - time.monotonic()) + 5))
    except BaseException:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        raise
    finally:
        t1.join(timeout=5)
        t2.join(timeout=5)

    if da_huy.is_set():
        raise DaHuy(_t('Phiên chạy đã bị huỷ giữa chừng.'))
    if time.monotonic() > han and proc.returncode != 0:
        raise subprocess.TimeoutExpired(cmd, timeout)
    if proc.returncode != 0:
        raise KetXuatError(
            _t('ffmpeg lỗi (mã {ma}).').format(ma=proc.returncode))
    return " | ".join(duoi)


def kiem_tep_ra(duong: str, ban: dict, *, soi) -> dict:
    """ffprobe tren tep VUA RENDER, truoc khi no duoc coi la ket qua.

    ⛔ Day la cho phan biet "ffmpeg tra ve 0" voi "co mot tep dung duoc". Chung
       khong bang nhau: ffmpeg tra ve 0 roi de lai mot tep 48 byte khong luong
       nao la mot ket cuc that su xay ra khi dau vao hong theo dung kieu.
    """
    p = Path(duong)
    if not p.is_file() or p.stat().st_size <= 0:
        raise KetXuatError(_t('Render xong nhưng không có tệp kết quả.'))

    tt = soi(duong)
    if not tt.get("co_video"):
        raise KetXuatError(_t('Tệp kết quả không có luồng hình.'))
    if not tt.get("co_tieng"):
        raise KetXuatError(_t('Tệp kết quả không có luồng tiếng.'))

    mong = float((ban.get("ra") or {}).get("thoi_luong_giay") or 0)
    that = float(tt.get("thoi_luong") or 0)
    if mong > 0 and abs(that - mong) > LECH_THOI_LUONG_GIAY:
        # 🔑 Muc 8 doi mot buoc kiem TRUOC khi promote, va day la phep kiem co
        #    y nghia nhat: mot ban long tieng dai sai la mot ban trong do tieng
        #    va hinh lech nhau, tuc hong dung thu ma san pham nay ban.
        raise KetXuatError(
            _t('Tệp kết quả dài {that:.1f}s, bản dựng mong đợi {mong:.1f}s.')
            .format(that=that, mong=mong))
    return tt
