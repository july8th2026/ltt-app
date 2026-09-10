"""Do TAI THAT cua may trong luc mot lan chay dien ra (pha 24).

## Vi sao lay mau thay vi do truoc/sau

Mot phep do "truoc va sau" cho ra mot con so trung binh, va trung binh la thu
giau di dung cai ta can thay: **dinh**. Mot giai doan chay 40 giay o 30% CPU roi
2 giay o 100% co cung trung binh voi mot giai doan chay deu 33% — nhung chi mot
trong hai lam may khac ngat.

⇒ Lay mau lien tuc o mot nhip co dinh, roi quy tung mau ve giai doan dang chay
  tai thoi diem do. Nho vay moi giai doan co ca **dinh** lan **trung binh**, va
  hai con so do tra loi hai cau hoi khac nhau.

## Cai ma bo do nay KHONG do duoc, va no phai noi ra

⛔ `psutil.cpu_percent` la CPU **toan may**, khong phai cua rieng tien trinh. Tren
   may nay do la lua chon dung — no dang phuc vu khach, va cau hoi cua pha 24 la
   "lan chay nay co lam may bao hoa khong", chu khong phai "tien trinh nay ngon
   bao nhieu". Nhung no co nghia moi con so o day **gom ca tai cua nguoi khac**,
   va bao cao phai ghi lai tai nen do duoc luc bat dau.

⚠️ VRAM doc qua `nvidia-smi`, tuc **toan card**, khong tach duoc phan cua ta. Cung
   ly do va cung cach doc: so nay tra loi "con bao nhieu cho tren card", khong
   tra loi "ta chiem bao nhieu".
"""
from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field

import psutil

#: Nhip lay mau. 0,5 giay du day de thay mot dinh ffmpeg vai giay, du thua de
#: chinh bo do khong thanh mot phan cua phep do.
NHIP_S = 0.5

#: Doc VRAM bao lau mot lan. `nvidia-smi` la mot tien trinh con ~50-120 ms, nen
#: goi no moi nhip la tu them tai vao dung thu dang do.
NHIP_VRAM_S = 2.0


@dataclass
class Mau:
    luc: float
    cpu: float
    ram_dung_mb: float
    ram_trong_mb: float
    doc_mb: float
    ghi_mb: float
    vram_mb: tuple[int, ...] = ()
    nhan: str = ""


@dataclass
class MocGiaiDoan:
    ten: str
    bat: float
    ket: float = 0.0


def doc_vram() -> tuple[int, ...]:
    """VRAM dang dung tren tung card (MiB), hoac rong neu khong doc duoc."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10)
    except Exception:                       # noqa: BLE001
        return ()
    ra = []
    for dong in (r.stdout or "").splitlines():
        dong = dong.strip()
        if dong.isdigit():
            ra.append(int(dong))
    return tuple(ra)


class BoDo:
    """Lay mau nen trong suot mot lan chay. Dung `with`.

    ⛔ Luong lay mau la **daemon** va co `dung` rieng: mot bo do khong duoc phep
       giu tien trinh song sau khi phep do da xong.
    """

    def __init__(self, *, nhip_s: float = NHIP_S):
        self.nhip_s = float(nhip_s)
        self.mau: list[Mau] = []
        self.moc: list[MocGiaiDoan] = []
        self._dung = threading.Event()
        self._luong: threading.Thread | None = None
        self._nhan = ""
        self.nen: dict = {}

    # ── vong doi ────────────────────────────────────────────────────────────
    def __enter__(self) -> "BoDo":
        psutil.cpu_percent(interval=None)          # mo dau cua so do
        self.nen = self._chup_nen()
        self._luong = threading.Thread(target=self._chay, daemon=True)
        self._luong.start()
        return self

    def __exit__(self, *loi) -> None:
        self._dung.set()
        if self._luong is not None:
            self._luong.join(timeout=5)

    #: Do tai nen trong bao lau. Mot cua so 0,3 giay bat duoc ca mot dinh ngan
    #: cua tien trinh khac va goi do la "nen"; 2 giay cho ra mot con so on hon.
    CUA_SO_NEN_S = 2.0

    def _chup_nen(self) -> dict:
        vm = psutil.virtual_memory()
        return {"cpu_nen": psutil.cpu_percent(interval=self.CUA_SO_NEN_S),
                "ram_trong_mb_nen": round(vm.available / 2 ** 20, 1),
                "vram_mb_nen": list(doc_vram())}

    # ── moc giai doan ───────────────────────────────────────────────────────
    def bat_dau(self, ten: str) -> None:
        self.moc.append(MocGiaiDoan(ten=ten, bat=time.time()))
        self._nhan = ten

    def ket_thuc(self, ten: str) -> None:
        for m in reversed(self.moc):
            if m.ten == ten and not m.ket:
                m.ket = time.time()
                break
        self._nhan = ""

    # ── vong lay mau ────────────────────────────────────────────────────────
    def _chay(self) -> None:
        io_dau = psutil.disk_io_counters()
        vram = doc_vram()
        lan_vram = time.time()
        while not self._dung.wait(self.nhip_s):
            gio = time.time()
            if gio - lan_vram >= NHIP_VRAM_S:
                vram = doc_vram()
                lan_vram = gio
            vm = psutil.virtual_memory()
            io = psutil.disk_io_counters()
            self.mau.append(Mau(
                luc=gio,
                cpu=psutil.cpu_percent(interval=None),
                ram_dung_mb=round((vm.total - vm.available) / 2 ** 20, 1),
                ram_trong_mb=round(vm.available / 2 ** 20, 1),
                doc_mb=round(((io.read_bytes - io_dau.read_bytes) if io and io_dau
                              else 0) / 2 ** 20, 1),
                ghi_mb=round(((io.write_bytes - io_dau.write_bytes) if io and io_dau
                              else 0) / 2 ** 20, 1),
                vram_mb=vram, nhan=self._nhan))

    # ── ket qua ─────────────────────────────────────────────────────────────
    def theo_giai_doan(self, *, tran_cpu: float = 90.0) -> list[dict]:
        """Mot dong cho moi giai doan, kem CA dinh lan trung binh.

        🔑 **`cpu_tren_tran_giay` moi la thu tra loi cau hoi "co bao hoa khong".**
           Mot mau 0,5 giay o 97% luc ffmpeg khoi dong la mot dinh, khong phai
           bao hoa; thu lam dich vu khac cham lai la **giu** muc do trong nhieu
           giay lien. Nen bo do tra ve ca ba: dinh (thay duoc cai gai), trung
           binh (thay duoc tai duy tri), va so giay o TREN tran (thay duoc bao
           lau).

        ⚠️ `tran_cpu` la tham so chu khong phai hang so o day: nguong la mot
           **chinh sach**, va chinh sach thuoc ve noi doc ket qua, khong thuoc ve
           cai can.
        """
        ra = []
        for m in self.moc:
            ket = m.ket or time.time()
            trong = [s for s in self.mau if m.bat <= s.luc <= ket]
            ra.append({
                "ten": m.ten,
                "giay": round(ket - m.bat, 2),
                "so_mau": len(trong),
                "cpu_dinh": round(max((s.cpu for s in trong), default=0.0), 1),
                "cpu_tb": round(
                    sum(s.cpu for s in trong) / len(trong), 1) if trong else 0.0,
                "cpu_tren_tran_giay": round(
                    sum(1 for s in trong if s.cpu >= tran_cpu) * self.nhip_s, 2),
                "ram_dung_dinh_mb": round(
                    max((s.ram_dung_mb for s in trong), default=0.0), 1),
                "ram_trong_thap_nhat_mb": round(
                    min((s.ram_trong_mb for s in trong), default=0.0), 1),
                "vram_dinh_mb": [
                    max((s.vram_mb[i] for s in trong if len(s.vram_mb) > i),
                        default=0)
                    for i in range(max((len(s.vram_mb) for s in trong), default=0))
                ],
                "doc_mb": round(
                    (max((s.doc_mb for s in trong), default=0.0)
                     - min((s.doc_mb for s in trong), default=0.0)), 1),
                "ghi_mb": round(
                    (max((s.ghi_mb for s in trong), default=0.0)
                     - min((s.ghi_mb for s in trong), default=0.0)), 1),
            })
        return ra

    def tong(self) -> dict:
        return {
            "nen": self.nen,
            "so_mau": len(self.mau),
            "nhip_s": self.nhip_s,
            "cpu_dinh": round(max((s.cpu for s in self.mau), default=0.0), 1),
            "cpu_tb": round(sum(s.cpu for s in self.mau) / len(self.mau), 1)
            if self.mau else 0.0,
            "ram_trong_thap_nhat_mb": round(
                min((s.ram_trong_mb for s in self.mau), default=0.0), 1),
            "vram_dinh_mb": [
                max((s.vram_mb[i] for s in self.mau if len(s.vram_mb) > i),
                    default=0)
                for i in range(max((len(s.vram_mb) for s in self.mau), default=0))
            ],
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Dem cong viec LAP LAI
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class BoDem:
    """Dem so lan mot lan chay goi lai cung mot loai viec dat tien.

    🔑 Pha 24 doi mot cuoc ra soat "doc lai kho, bam lai checksum, chay lai
       ffmpeg". Mot cuoc ra soat bang mat se bo sot; mot bo dem thi khong.
    """

    ffmpeg: int = 0
    ffprobe: int = 0
    bam_tep: int = 0
    doc_kho: int = 0
    chi_tiet: dict = field(default_factory=dict)

    def dem(self, ten: str, mo_ta: str = "") -> None:
        setattr(self, ten, getattr(self, ten) + 1)
        if mo_ta:
            self.chi_tiet.setdefault(ten, []).append(mo_ta[:120])

    def sang_dict(self) -> dict:
        return {"ffmpeg": self.ffmpeg, "ffprobe": self.ffprobe,
                "bam_tep": self.bam_tep, "doc_kho": self.doc_kho}


def gan_bo_dem(monkeypatch, bo_dem: BoDem) -> BoDem:
    """Gan bo dem vao BON cua that: chay lenh, ffprobe, bam tep, doc kho.

    ⛔ Dem o CUA chu khong dem o tung nguoi goi: mot nguoi goi moi them vao ngay
       mai se duoc dem ma khong ai phai nho sua cho nay. `nhap_media._chay` la
       cho duy nhat ca chuoi goi ffmpeg (tach tieng, phoi am, ket xuat, QC deu
       di qua no), va `nhap_media.soi` la cho duy nhat goi ffprobe.
    """
    from platform_core.storage import get_storage

    from apps.auto_scan_video import assets, nhap_media

    chay_that, soi_that, bam_that = (nhap_media._chay, nhap_media.soi,
                                     assets.bam_tep)

    def dem_chay(cmd, **kw):
        # Ten cong cu + bo loc, du de doc ra "lenh nay lam gi" ma khong lo duong
        # dan cua may.
        ten = str(cmd[0]).rsplit("\\", 1)[-1] if cmd else "?"
        loc = next((c for c in cmd if str(c).startswith("-")
                    and str(c) in ("-filter_complex", "-af", "-vf", "-c:v")), "")
        bo_dem.dem("ffmpeg", f"{ten} {loc}".strip())
        return chay_that(cmd, **kw)

    def dem_soi(duong, **kw):
        bo_dem.dem("ffprobe", str(duong).rsplit("\\", 1)[-1])
        return soi_that(duong, **kw)

    def dem_bam(duong):
        bo_dem.dem("bam_tep", str(duong).rsplit("\\", 1)[-1])
        return bam_that(duong)

    monkeypatch.setattr(nhap_media, "_chay", dem_chay)
    monkeypatch.setattr(nhap_media, "soi", dem_soi)
    monkeypatch.setattr(assets, "bam_tep", dem_bam)

    kho = get_storage()
    if kho is not None and hasattr(kho, "open"):
        mo_that = kho.open

        def dem_mo(khoa, *a, **kw):
            bo_dem.dem("doc_kho", str(khoa).rsplit("/", 1)[-1])
            return mo_that(khoa, *a, **kw)

        monkeypatch.setattr(kho, "open", dem_mo)
    return bo_dem
