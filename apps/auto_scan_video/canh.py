"""Tach CANH va lay khung hinh dai dien — tat dinh, va khong goi model nao.

## Bo tach: PySceneDetect (BSD-3-Clause), da benchmark — khong tu che

⭐ ASV final (lan ky-thuat) do bon ung vien tren 9 clip tong hop co moc cat BIET
   TRUOC + 2 video that gan nhan tay (`docs/auto_scan_video_final/L_KY_THUAT.md`):
   ffmpeg `select=gt(scene,T)`, ffmpeg `scdet`, PySceneDetect Content/Adaptive/
   Hash. Ban cu (`select` 0,4, nguong "CHUA DO") thua ro: bo sot moi mot cat
   giua hai canh tinh (talking head) va moi cat trong canh toi. Da xoa.

🔑 Bo nho: PySceneDetect doc TUNG khung (OpenCV) va thu nho tu dong
   (`auto_downscale`) truoc khi so — bo nho khong doi theo do dai video, khong
   giu mot danh sach khung nao.

## 🔑 Tat dinh nghia la gi o day

Cung mot tep + cung `PHIEN_BAN_CANH` => cung danh sach moc. Khong lay mau ngau
nhien, khong dung thoi gian thuc. `thi_hanh.phien_ban_engine` gom
`PHIEN_BAN_CANH`, nen doi bo tach/tham so la doi van tay va cache truot dung cach.

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
import threading
from dataclasses import dataclass, field

from platform_core import media

log = logging.getLogger(__name__)

#: Bo tach canh: PySceneDetect `ContentDetector`. Chon bang benchmark
#: (`docs/auto_scan_video_final/L_KY_THUAT.md` §3): tren 9 clip tong hop + 2 video
#: that gan nhan tay, F1 = 0,95 (P 0,92 / R 0,98) — dung dau, tren ca
#: `AdaptiveDetector` (0,93) va bo cu `select=gt(scene,0.4)` (0,73).
BO_TACH = "pyscenedetect.ContentDetector"
#: `threshold` cua `ContentDetector`. **Da do**, khong phai mac dinh thu vien
#: (27): 35 bo bot bao dong gia o canh quay lia / canh dong nhanh ma khong mat
#: mot cat nao trong bo do (27: FP 25, 35: FP 14, cung 3-4 FN).
NGUONG_DOI_CANH = 35.0
#: So khung toi thieu mot canh cua detector (mac dinh thu vien, 15 khung).
KHUNG_CANH_TOI_THIEU = 15

#: Vao van tay giai doan (`thi_hanh.phien_ban_engine`). Doi bo tach, tham so,
#: hay phien ban lon cua thu vien => doi chuoi nay => cache truot.
PHIEN_BAN_CANH = f"psd0.6/{BO_TACH}/{NGUONG_DOI_CANH}/{KHUNG_CANH_TOI_THIEU}/v1"

#: Canh ngan hon nay thi gop vao canh truoc.
#:
#: 🔑 Moi bo tach deu bao dong tren mot cu chop den (benchmark: chop trang 3
#:    khung la FP o MOI bo), va nhung "canh" 0,2 giay do khong phai canh. Gop chung lai truoc
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

def tim_moc(duong: str, *, hoi_huy=None, timeout: int = 1800) -> list[float]:
    """Moc doi canh (giay) cua `duong` theo `BO_TACH`. Adapter DUY NHAT cua
    PySceneDetect — moi tham so doc tu hang so o dau tep.

    ⭐ Huy/qua han: mot luong canh goi `SceneManager.stop()` (an toan luong theo
       tai lieu thu vien) — `detect_scenes` dung o khung ke tiep.
    """
    try:
        from scenedetect import ContentDetector, SceneManager, open_video
    except ImportError as exc:        # pragma: no cover - moi truong thieu goi
        raise CanhError(f"thieu PySceneDetect: {exc}") from exc

    try:
        video = open_video(str(duong), backend="opencv")
    except Exception as exc:          # noqa: BLE001 - tep hong / khong mo duoc
        raise CanhError(f"khong mo duoc video: {exc}") from exc
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=NGUONG_DOI_CANH,
                                    min_scene_len=KHUNG_CANH_TOI_THIEU))

    xong = threading.Event()
    ly_do: list[str] = []

    def _canh():
        import time
        bat = time.monotonic()
        while not xong.wait(0.5):
            if hoi_huy is not None and hoi_huy():
                ly_do.append("da huy")
            elif time.monotonic() - bat > timeout:
                ly_do.append("qua han")
            if ly_do:
                sm.stop()
                return

    t = threading.Thread(target=_canh, daemon=True)
    t.start()
    try:
        sm.detect_scenes(video, show_progress=False)
    except Exception as exc:          # noqa: BLE001 - loi giai ma giua chung
        raise CanhError(f"PySceneDetect loi: {exc}") from exc
    finally:
        xong.set()
        t.join(timeout=2)
    if not ly_do and hoi_huy is not None and hoi_huy():
        ly_do.append("da huy")      # huy trong nua giay cuoi, truoc luot canh
    if ly_do:
        raise CanhError(ly_do[0])
    return sorted({round(c.get_seconds(), 3) for c in sm.get_cut_list()})


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
    """Tach canh mot lan, tra ve `ChiMucCanh`.

    `nguong` chi de ghi vao chi muc; bo tach luon dung `NGUONG_DOI_CANH` (mot
    nguon chan ly, nam trong `PHIEN_BAN_CANH`).
    """
    if thoi_luong <= 0:
        thoi_luong = float(media.duration_seconds(duong) or 0.0)
    if thoi_luong <= 0:
        raise CanhError("khong doc duoc thoi luong nguon")

    moc = tim_moc(duong, hoi_huy=hoi_huy, timeout=timeout)
    khoang = gop_canh_ngan(moc, thoi_luong)

    canh = [Canh(f"canh_{i:04d}", b, k, tuple(moc_khung_mau(b, k)))
            for i, (b, k) in enumerate(khoang, start=1)]
    canh = chan_so_khung(canh)

    return ChiMucCanh(tuple(canh), thoi_luong, nguong, {
        "bo_tach": BO_TACH,
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
