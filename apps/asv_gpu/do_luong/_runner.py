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

#: Goc kho ma, neo bang TEN thu muc `apps/` — ⛔ KHONG dem cap (`parents[N]`).
#:
#: ⚠️ Vi sao khong dung `platform_core.frontend_bundle` nhu cac app khac: bon
#:    tep `*_runner.py` nay chay trong `qc-venv` (mot venv RIENG, khong co goc
#:    kho trong `sys.path`), nen chung phai tu tim goc TRUOC khi nhap duoc bat
#:    ky thu gi cua nen tang. Neo bang ten la cach duy nhat con lai — va no
#:    khong gay khi tep doi cho trong cay.
def _goc_kho() -> Path:
    for cha in Path(__file__).resolve().parents:
        if cha.name == "apps":
            return cha.parent
    raise RuntimeError(
        f"khong thay thu muc `apps/` tren duong di cua {__file__} — "
        "runner nay phai nam trong `apps/<app>/do_luong/`")


GOC = _goc_kho()


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
        # ⭐ HAI cau tra loi khac nhau, khong duoc tron thanh mot khoa VANG:
        #      · khong co `torch`/khong co CUDA  -> may nay khong do VRAM, binh
        #        thuong tren cay `torch+cpu` (V4-R05). Khong khai gi.
        #      · co CUDA ma phep do NO          -> mot LOI, va nguoi doc bao cao
        #        phai thay no. `test_450::test_VRAM_dinh_KHONG_vuot_con_so_app_
        #        dang_khai` doc dung khoa nay: mot khoa vang lam phep kiem do
        #        chuyen sang "khong do duoc" thay vi "do duoc va sai".
        try:
            import torch
        except ImportError:
            pass
        else:
            try:
                if torch.cuda.is_available():
                    ra["vram_torch_dinh_mb"] = round(
                        torch.cuda.max_memory_reserved() / 2**20, 1)
            except Exception as exc:            # noqa: BLE001
                ra["vram_ly_do"] = f"{type(exc).__name__}: {exc}"[:200]
        ra.update(them)
        return ra
