"""Tach CANH va lay khung hinh dai dien — tat dinh, re, va khong goi model nao.

## Vi sao ffmpeg lam viec nay chu khong phai Python

⛔ Giai ma tung khung hinh vao Python roi so sanh la cach de nhat de bien mot
   video 40 phut thanh mot lan hong bo nho. Mot khung 1080p la ~6 MB o dang tho;
   60.000 khung la 350 GB di qua RAM.

⭐ `ffmpeg` co san bo loc `select='gt(scene,T)'`: no so sanh **trong luong** hai
   khung lien tiep va chi in ra moc thoi gian nhung cho doi canh. Ta doc `stderr`,
   khong doc pixel nao. Bo nho gan nhu khong doi theo do dai video — va do la
   dieu `long-video memory bound` cua pha nay doi.

## 🔑 Tat dinh nghia la gi o day

Cung mot tep + cung `NGUONG_DOI_CANH` => cung danh sach moc. Khong lay mau ngau
nhien, khong dung thoi gian thuc, khong dua vao so nhan CPU. `van_tay` cua giai
doan gom ca nguong, nen doi nguong la doi van tay va cache truot dung cach.

⚠️ **`scene` cua ffmpeg khong phai mot ngưỡng tuyet doi ve "canh moi"** — no la
   mot phep do khac biet, va gia tri tot phu thuoc noi dung. 0,4 la con so bo
   loc nay thuong duoc dung; no CHUA DUOC DO tren tep that cua khach. Ghi ro o
   day de khong ai doc no nhu mot hang so da chot.

## Vi sao so khung mau bi CHAN

Pha 11 gui khung nay cho VLM, va `ai.cua_so_ngu_canh(DOC_CANH)` do duoc **65.536
token** cho ban thi giac — nho hon ban van ban mot nua. Mot video 200 canh x 3
khung se vuot cua so do truoc khi ai kip dem. Nen tran nam o **day**, o cho sinh
ra chung, chu khong o cho tieu thu — mot cua chan dat sau cho tieu tien la mot
cua chan dat sai cho.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from platform_core import media

log = logging.getLogger(__name__)

#: Nguong doi canh cua bo loc `select='gt(scene,T)'`.
#:
#: ⚠️ CHUA DO tren tep that cua khach — xem docstring dau tep.
NGUONG_DOI_CANH = 0.4

#: Canh ngan hon nay thi gop vao canh truoc.
#:
#: 🔑 Bo loc `scene` bao dong tren mot cu chop den hay mot khung nhieu, va nhung
#:    "canh" 0,2 giay do khong phai canh — chung la nhieu. Gop chung lai truoc
#:    khi lay mau, neu khong ta tra tien VLM cho mot khung nhieu.
CANH_NGAN_NHAT_S = 1.0

#: Toi da bao nhieu khung mau moi canh. Xem docstring dau tep.
KHUNG_MOI_CANH = 2

#: Toi da bao nhieu khung cho CA lan chay — chan tren cung.
#:
#: ⛔ Tran moi canh khong du: mot video 300 canh van ra 600 khung. Tran nay la
#:    thu chan mot hoa don VLM khong ai luong truoc.
KHUNG_TOI_DA = 60

#: Canh dai cua khung mau. Nho de vua cua so thi giac, du de doc duoc noi dung.
CANH_DAI_KHUNG = 512

#: Chat luong JPEG (2 = tot nhat, 31 = te nhat trong thang cua ffmpeg).
CHAT_LUONG_JPEG = 4


class CanhError(ValueError):
    """Khong tach duoc canh, hoac ket qua khong dung hinh dang."""


@dataclass(frozen=True)
class Canh:
    """MOT canh. `ma` on dinh theo thu tu, khong theo noi dung."""

    ma: str
    bat: float
    ket: float
    #: Moc cua cac khung mau trong canh nay.
    khung: tuple[float, ...] = ()

    @property
    def dai(self) -> float:
        return max(0.0, self.ket - self.bat)


@dataclass(frozen=True)
class ChiMucCanh:
    """`SceneIndex`: ket qua tat dinh cua mot lan phan tich."""

    canh: tuple[Canh, ...]
    thoi_luong: float
    nguong: float = NGUONG_DOI_CANH
    #: Vi sao so canh lai la so nay — cho nguoi doc bao cao.
    ghi_chu: dict = field(default_factory=dict)

    def tom_tat(self) -> dict:
        return {
            "so_canh": len(self.canh),
            "so_khung": sum(len(c.khung) for c in self.canh),
            "thoi_luong": round(self.thoi_luong, 3),
            "nguong": self.nguong,
            **dict(self.ghi_chu),
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Tim ranh gioi canh
# ══════════════════════════════════════════════════════════════════════════════

_MOC = re.compile(r"pts_time:([0-9]+\.?[0-9]*)")


def doc_moc_tu_ffmpeg(stderr: str) -> list[float]:
    """Doc moc doi canh tu dau ra `metadata=print` cua ffmpeg.

    ⭐ Tach thanh ham rieng de phep kiem chay duoc **khong can ffmpeg**: mot bo
       do phu thuoc mot nhi phan ben ngoai la mot bo do khong chay tren may
       khong co no, va luc do no im lang thay vi do.
    """
    ra = []
    for m in _MOC.finditer(stderr or ""):
        try:
            ra.append(float(m.group(1)))
        except ValueError:
            continue
    return sorted(set(ra))


def gop_canh_ngan(moc: list[float], thoi_luong: float,
                  *, ngan_nhat: float = CANH_NGAN_NHAT_S) -> list[tuple]:
    """Bien danh sach moc thanh cac khoang, gop nhung khoang qua ngan.

    ⛔ Giu NGUYEN thu tu nguon. Pha nay khong duoc sap xep lai gi — mot chi muc
       canh lech thu tu se lam moi quyet dinh bien tap phia sau tro vao sai cho.
    """
    if thoi_luong <= 0:
        raise CanhError("thoi luong nguon phai duong")

    diem = [0.0] + [m for m in moc if 0.0 < m < thoi_luong] + [thoi_luong]
    ra: list[tuple] = []
    for i in range(len(diem) - 1):
        bat, ket = diem[i], diem[i + 1]
        if ra and (ket - bat) < ngan_nhat:
            # ⭐ Gop vao canh TRUOC chu khong bo di: bo mot khoang la lam mat
            #    mot doan cua nguon, va chi muc se khong con phu het video.
            ra[-1] = (ra[-1][0], ket)
        else:
            ra.append((bat, ket))
    # Canh dau co the ngan hon nguong; gop no vao canh sau.
    if len(ra) > 1 and (ra[0][1] - ra[0][0]) < ngan_nhat:
        ra[1] = (ra[0][0], ra[1][1])
        ra.pop(0)
    return ra


def moc_khung_mau(bat: float, ket: float, *, so: int = KHUNG_MOI_CANH) -> list[float]:
    """Moc lay khung trong mot canh. TAT DINH: chia deu, khong ngau nhien.

    ⚠️ Tranh dung hai dau: khung ngay tai ranh gioi thuong la khung chuyen canh
       (mo, den, chong hinh) — no khong dai dien cho canh nao ca.
    """
    dai = max(0.0, ket - bat)
    if dai <= 0 or so <= 0:
        return []
    return [round(bat + dai * (i + 1) / (so + 1), 3) for i in range(so)]


def chan_so_khung(canh: list, *, toi_da: int = KHUNG_TOI_DA) -> list:
    """Ha so khung deu tay cho ca lan chay khi vuot tran.

    🔑 Ha DEU thay vi cat duoi: cat duoi lam nua sau video khong co khung nao,
       va mot ho so noi dung dung tren nua dau la mot ho so sai ve ca video.
    """
    tong = sum(len(x.khung) for x in canh)
    if tong <= toi_da or not canh:
        return canh

    # 🔴 **Ban dau doan nay cap 1 khung cho tung canh cho toi khi het cho**, va
    #    voi 100 canh / tran 60 thi 60 canh dau moi canh mot khung, con 40 canh
    #    CUOI khong duoc khung nao. Do dung la "cat duoi" ma chinh docstring noi
    #    la khong duoc lam. `test_ha_so_khung_DEU_TAY_chu_khong_cat_duoi` bat
    #    duoc no ngay luot dau.
    #
    # ⭐ Cach dung: trai PHANG toan bo (canh, moc) theo thu tu nguon roi chon
    #    `toi_da` diem cach deu tren danh sach do. Phep chon nay khong biet
    #    "canh" la gi — no chi rai deu tren truc thoi gian, va do chinh xac la
    #    dieu ta muon: mot ho so noi dung phai dua tren CA video.
    phang = [(i, m) for i, x in enumerate(canh) for m in x.khung]
    buoc = len(phang) / float(toi_da)
    chon: set = {phang[min(len(phang) - 1, int(k * buoc))] for k in range(toi_da)}

    ra = []
    for i, x in enumerate(canh):
        giu = tuple(m for m in x.khung if (i, m) in chon)
        ra.append(Canh(x.ma, x.bat, x.ket, giu))
    return ra


def phan_tich(duong: str, *, thoi_luong: float = 0.0, nguong: float = NGUONG_DOI_CANH,
              hoi_huy=None, timeout: int = 1800) -> ChiMucCanh:
    """Chay ffmpeg mot lan, tra ve `ChiMucCanh`. KHONG doc pixel nao vao Python."""
    if thoi_luong <= 0:
        thoi_luong = float(media.duration_seconds(duong) or 0.0)
    if thoi_luong <= 0:
        raise CanhError("khong doc duoc thoi luong nguon")

    cmd = [media.ffmpeg_bin(), "-hide_banner", "-nostdin", "-i", str(duong),
           "-filter:v", f"select='gt(scene,{nguong})',metadata=print",
           "-an", "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise CanhError(f"ffmpeg khong chay duoc: {exc}") from exc
    if hoi_huy is not None and hoi_huy():
        raise CanhError("da huy")

    loi = (r.stderr or b"").decode("utf-8", "replace")
    moc = doc_moc_tu_ffmpeg(loi)
    khoang = gop_canh_ngan(moc, thoi_luong)

    canh = [Canh(f"canh_{i:04d}", b, k, tuple(moc_khung_mau(b, k)))
            for i, (b, k) in enumerate(khoang, start=1)]
    canh = chan_so_khung(canh)

    return ChiMucCanh(tuple(canh), thoi_luong, nguong, {
        "moc_tho": len(moc),
        "da_gop": len(moc) + 1 - len(khoang) if moc else 0,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Rut khung mau
# ══════════════════════════════════════════════════════════════════════════════

def lenh_rut_khung(duong: str, moc: float, ra: str,
                   *, canh_dai: int = CANH_DAI_KHUNG) -> list[str]:
    """Lenh ffmpeg rut MOT khung. Tach ra de phep kiem doc duoc no.

    ⭐ `-ss` truoc `-i` la tim NHANH (khong giai ma tu dau). Voi mot video dai
       do la khac biet giua vai giay va vai phut moi khung.

    ⚠️ Giu ti le: `scale` chi ep canh dai, canh kia `-2` (boi cua 2, ffmpeg tu
       tinh). Ep ca hai canh se lam meo hinh, va mot khung meo la mot khung model
       doc sai.
    """
    return [media.ffmpeg_bin(), "-hide_banner", "-nostdin",
            "-ss", f"{max(0.0, float(moc)):.3f}", "-i", str(duong),
            "-frames:v", "1",
            "-vf", f"scale='min({int(canh_dai)},iw)':-2",
            "-q:v", str(CHAT_LUONG_JPEG), "-y", str(ra)]


def kiem_chi_muc(ci: ChiMucCanh) -> None:
    """Kiem hinh dang truoc khi luu. Nem `CanhError` neu sai.

    ⛔ Ba dieu, va ca ba deu tung la mot lop loi that o cac giai doan khac:
       phu HET nguon · KHONG chong lan · dung THU TU nguon.
    """
    if not ci.canh:
        raise CanhError("chi muc khong co canh nao")

    truoc_ket = None
    for c in ci.canh:
        if c.ket <= c.bat:
            raise CanhError(f"{c.ma}: khoang rong hoac am")
        if truoc_ket is not None and abs(c.bat - truoc_ket) > 1e-6:
            raise CanhError(
                f"{c.ma}: bat dau {c.bat} khong noi tiep {truoc_ket} — "
                f"chi muc canh phai phu HET nguon va khong chong lan")
        truoc_ket = c.ket
        for m in c.khung:
            if not (c.bat <= m <= c.ket):
                raise CanhError(f"{c.ma}: moc khung {m} nam ngoai canh")

    if abs(ci.canh[-1].ket - ci.thoi_luong) > 0.05:
        raise CanhError(
            f"canh cuoi ket thuc o {ci.canh[-1].ket} nhung nguon dai "
            f"{ci.thoi_luong} — chi muc khong phu het video")

    tong = sum(len(c.khung) for c in ci.canh)
    if tong > KHUNG_TOI_DA:
        raise CanhError(f"{tong} khung vuot tran {KHUNG_TOI_DA}")


def tu_dict(goi: dict) -> ChiMucCanh:
    """Doc lai chi muc canh tu dang da luu. Nua con lai cua `sang_json`.

    ⭐ Cung ly do nhu `ban_bien_tap.BanBienTap.tu_dict`: pha 10 va 12 ghi chi muc
       ra kho ma khong co duong doc lai, nen dinh dang luu tru chua tung duoc mot
       nguoi doc nao kiem chung. Pha 14 la nguoi doc do.
    """
    goi = dict(goi or {})
    return ChiMucCanh(
        canh=tuple(Canh(ma=str(c.get("ma") or ""),
                        bat=float(c.get("bat") or 0.0),
                        ket=float(c.get("ket") or 0.0),
                        khung=tuple(float(m) for m in (c.get("khung") or ())))
                   for c in (goi.get("canh") or [])),
        thoi_luong=float(goi.get("thoi_luong") or 0.0),
        nguong=float(goi.get("nguong") or NGUONG_DOI_CANH),
        ghi_chu=dict(goi.get("ghi_chu") or {}))


def tu_json(van_ban: str) -> ChiMucCanh:
    """`tu_dict` tren mot chuoi JSON."""
    return tu_dict(json.loads(van_ban))


def sang_json(ci: ChiMucCanh) -> str:
    """Dang luu tru. Tat dinh: khoa sap xep, so lam tron."""
    return json.dumps({
        "nguong": ci.nguong,
        "thoi_luong": round(ci.thoi_luong, 3),
        "canh": [{"ma": c.ma, "bat": round(c.bat, 3), "ket": round(c.ket, 3),
                  "khung": [round(m, 3) for m in c.khung]} for c in ci.canh],
        "ghi_chu": dict(ci.ghi_chu),
    }, ensure_ascii=False, sort_keys=True)
