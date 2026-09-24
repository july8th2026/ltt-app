"""Phan chung cua cac script runner chay TRONG `qc-venv` (khong dung o worker).

Giao thuc (`venv.chay`): `argv[1]` = JSON vao, `argv[2]` = JSON ra, thoat 0.
Thieu model/thu vien ⇒ in dong `KHONG_KHA_DUNG: <ly do>` roi thoat 3 — `venv.chay`
doi no thanh `KhongKhaDung`.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

#: Goc kho ma (…/apps/asv_gpu/do_luong/_runner.py -> parents[3]).
GOC = Path(__file__).resolve().parents[3]


def mo() -> tuple[dict, Path]:
    if str(GOC) not in sys.path:
        sys.path.insert(0, str(GOC))
    vao = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    return vao, Path(sys.argv[2])


def ghi(ra: Path, obj: dict) -> None:
    ra.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def khong_kha_dung(ly_do: str) -> None:
    print(f"KHONG_KHA_DUNG: {ly_do}", flush=True)
    sys.exit(3)


def chon_thiet_bi(vao: dict) -> tuple[str, str]:
    """(`"cuda"`|`"cpu"`, ly do) theo **lease** chu khong theo `is_available()`.

    🔑 Cung hop dong ma `apps/auto_scan_video/demucs_runner.chon_thiet_bi` da
       chot, va o day vi dung mot ly do: ban cu viet
       `"cuda" if torch.cuda.is_available() else "cpu"`, tuc **lay card khi
       KHONG co lease**. May A co MOT card, dung chung voi `voice_sidecar` dang
       phuc vu khach that, nen mot nguoi dung card ngoai so sach la dung cai ma
       `gpu_lease` sinh ra de chan.

    Hai truong hop, va phan biet chung la ca y nghia cua `buoc_gpu`:

      * `buoc_gpu=False` — nen tang **khong** cap card. CPU la duong DA KHAI,
        khong phai mot cho tut xuong. `venv.chay(chan_card=True)` con ghim
        `CUDA_VISIBLE_DEVICES=-1` nen torch cung khong thay card.
      * `buoc_gpu=True` — nen tang da giu cho mot card va da ghim no. Torch
        khong thay CUDA o day nghia la viec cap card DA HONG ⇒ phai keu
        (`KHONG_KHA_DUNG`), khong duoc im lang cham diem bang CPU: mot bo do
        lui im lang giu nguyen suat `tach_nguon_cuc_bo` hang phut trong khi
        bao cao doc y nhu mot luot chay tren card.
    """
    buoc_gpu = bool(vao.get("buoc_gpu"))
    try:
        import torch
        co = bool(torch.cuda.is_available())
    except Exception as exc:                    # noqa: BLE001 - torch hong
        if buoc_gpu:
            khong_kha_dung(f"nen tang cap card nhung torch khong nap duoc: {exc}")
        return "cpu", f"torch khong nap duoc: {type(exc).__name__}"
    if buoc_gpu:
        if not co:
            khong_kha_dung(
                "nen tang cap card (buoc_gpu) nhung torch.cuda.is_available() "
                "la False — viec cap/ghim card da hong")
        return "cuda", "nen tang cap card"
    if co:
        # ⛔ Thay card ma KHONG co lease ⇒ khong cham. Ghi ly do ra hop dong ket
        #    qua de mot lan chay CPU khong bao gio doc giong mot lan co card.
        return "cpu", "khong co lease (thay card nhung khong duoc cap)"
    return "cpu", "may khong co card"


def _rss_dinh_mb() -> float:
    """Dinh bo nho lam viec cua CHINH tien trinh nay (MB)."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        k32 = ctypes.WinDLL("kernel32")
        psapi = ctypes.WinDLL("psapi")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC),
                                               wintypes.DWORD]
        psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
        return round(pmc.PeakWorkingSetSize / 2**20, 1)
    import resource  # pragma: no cover - may dev khong phai Windows
    return round(resource.getrusage(  # type: ignore[attr-defined]
        resource.RUSAGE_SELF).ru_maxrss / 1024, 1)  # type: ignore[attr-defined]


class DongHo:
    """Do tai nguyen cua mot luot: tuong, CPU, RSS dinh, VRAM torch dinh."""

    def __init__(self):
        self.t0 = time.monotonic()
        self.c0 = time.process_time()
        self.moc: dict = {}

    def danh_dau(self, ten: str) -> None:
        self.moc[ten] = round(time.monotonic() - self.t0, 2)

    def ket(self, **them) -> dict:
        ra = {"giay_tuong": round(time.monotonic() - self.t0, 2),
              "giay_cpu": round(time.process_time() - self.c0, 2),
              "ram_dinh_mb": _rss_dinh_mb(), "moc": dict(self.moc)}
        try:
            import torch
            if torch.cuda.is_available():
                ra["vram_torch_dinh_mb"] = round(
                    torch.cuda.max_memory_reserved() / 2**20, 1)
        except Exception:                       # noqa: BLE001
            pass
        ra.update(them)
        return ra
