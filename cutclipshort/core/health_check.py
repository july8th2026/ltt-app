"""Startup health check — pre-flight validation for all dependencies.

Runs automatically on first launch. Checks:
1. FFmpeg/FFprobe availability + version
2. Whisper model availability (or download needed)
3. YOLO model availability
4. GPU/CUDA status
5. RAM sufficiency
6. Disk space
7. Write permissions

Returns a HealthReport with all issues categorized by severity.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class Severity(Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CheckResult:
    name: str
    name_vi: str
    severity: Severity
    message: str
    detail: str = ""
    fix_hint: str = ""


@dataclass
class HealthReport:
    checks: list[CheckResult] = field(default_factory=list)
    total_time_ms: float = 0.0

    @property
    def has_critical(self) -> bool:
        return any(c.severity == Severity.CRITICAL for c in self.checks)

    @property
    def has_errors(self) -> bool:
        return any(c.severity == Severity.ERROR for c in self.checks)

    @property
    def all_ok(self) -> bool:
        return all(c.severity == Severity.OK for c in self.checks)

    @property
    def issues(self) -> list[CheckResult]:
        return [c for c in self.checks if c.severity != Severity.OK]

    def summary_vi(self) -> str:
        ok = sum(1 for c in self.checks if c.severity == Severity.OK)
        warn = sum(1 for c in self.checks if c.severity == Severity.WARNING)
        err = sum(1 for c in self.checks if c.severity == Severity.ERROR)
        crit = sum(1 for c in self.checks if c.severity == Severity.CRITICAL)
        parts = [f"{ok} OK"]
        if warn:
            parts.append(f"{warn} cảnh báo")
        if err:
            parts.append(f"{err} lỗi")
        if crit:
            parts.append(f"{crit} nghiêm trọng")
        return " | ".join(parts)


def run_health_check() -> HealthReport:
    """Run all health checks and return report."""
    import time
    t0 = time.perf_counter()
    report = HealthReport()

    report.checks.append(_check_ffmpeg())
    report.checks.append(_check_ffprobe())
    report.checks.append(_check_whisper())
    report.checks.append(_check_yolo())
    report.checks.append(_check_gpu())
    report.checks.append(_check_ram())
    report.checks.append(_check_disk_space())
    report.checks.append(_check_write_permissions())

    report.total_time_ms = (time.perf_counter() - t0) * 1000

    for c in report.checks:
        lvl = {"ok": "info", "warning": "warning", "error": "error", "critical": "critical"}
        getattr(logger, lvl.get(c.severity.value, "info"))(
            "Health [%s] %s: %s", c.severity.value.upper(), c.name_vi, c.message
        )

    logger.info("Health check: %s (%.0fms)", report.summary_vi(), report.total_time_ms)
    return report


# ══════════════════════════════════════════════════════════════════════════

def _check_ffmpeg() -> CheckResult:
    try:
        from cutclipshort.adapters.ffmpeg import FFmpegAdapter
        adapter = FFmpegAdapter()
        if not adapter.check_available():
            return CheckResult("ffmpeg", "FFmpeg", Severity.CRITICAL,
                               "FFmpeg không tìm thấy — không thể xử lý video",
                               fix_hint="Tải FFmpeg từ ffmpeg.org và đặt vào thư mục tools/")
        version = adapter.get_version() or "unknown"
        return CheckResult("ffmpeg", "FFmpeg", Severity.OK, "FFmpeg OK", detail=version)
    except Exception as e:
        return CheckResult("ffmpeg", "FFmpeg", Severity.CRITICAL, f"FFmpeg lỗi: {e}")


def _check_ffprobe() -> CheckResult:
    try:
        from cutclipshort.adapters.ffmpeg import FFprobeAdapter
        adapter = FFprobeAdapter()
        if not adapter.check_available():
            return CheckResult("ffprobe", "FFprobe", Severity.CRITICAL,
                               "FFprobe không tìm thấy",
                               fix_hint="FFprobe đi kèm FFmpeg. Tải từ ffmpeg.org")
        return CheckResult("ffprobe", "FFprobe", Severity.OK, "FFprobe OK")
    except Exception as e:
        return CheckResult("ffprobe", "FFprobe", Severity.CRITICAL, f"FFprobe lỗi: {e}")


def _check_whisper() -> CheckResult:
    try:
        import faster_whisper  # noqa: F401
        backend = "faster-whisper"
    except ImportError:
        try:
            import whisper  # noqa: F401
            backend = "openai-whisper"
        except ImportError:
            return CheckResult("whisper", "Chuyển giọng nói", Severity.ERROR,
                               "Whisper chưa cài — phụ đề không hoạt động",
                               fix_hint="Chạy: pip install faster-whisper")

    # Check cached models
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    models = [m for m in ["tiny", "base", "small", "medium", "large-v3"]
              if (cache_dir / f"models--Systran--faster-whisper-{m}").exists()]

    if not models and backend == "faster-whisper":
        return CheckResult("whisper", "Chuyển giọng nói", Severity.WARNING,
                           "Whisper OK nhưng chưa tải model — lần đầu sẽ tải 500MB-1.5GB",
                           fix_hint="Cần internet lần đầu để tải model tự động")

    return CheckResult("whisper", "Chuyển giọng nói", Severity.OK,
                       f"{backend} OK" + (f" — models: {', '.join(models)}" if models else ""),
                       detail=backend)


def _check_yolo() -> CheckResult:
    try:
        from ultralytics import YOLO  # noqa: F401
    except ImportError:
        return CheckResult("yolo", "Nhận diện hình ảnh", Severity.WARNING,
                           "YOLO chưa cài — nhận diện người bị tắt",
                           fix_hint="Chạy: pip install ultralytics")
    return CheckResult("yolo", "Nhận diện hình ảnh", Severity.OK, "YOLO OK")


def _check_gpu() -> CheckResult:
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            _props = torch.cuda.get_device_properties(0)
            vram = getattr(_props, 'total_memory', getattr(_props, 'total_mem', 0)) / (1024 ** 3)
            if vram < 4.0:
                return CheckResult("gpu", "GPU", Severity.WARNING,
                                   f"{name} ({vram:.0f}GB) — ít VRAM, dùng model nhỏ")
            return CheckResult("gpu", "GPU", Severity.OK,
                               f"{name} ({vram:.0f}GB VRAM)",
                               detail=f"CUDA {torch.version.cuda}")
        return CheckResult("gpu", "GPU", Severity.WARNING,
                           "Không có GPU CUDA — dùng CPU (chậm hơn 5-10x)",
                           fix_hint="Cài NVIDIA driver mới nhất để tăng tốc")
    except ImportError:
        return CheckResult("gpu", "GPU", Severity.WARNING,
                           "PyTorch chưa cài — AI chạy trên CPU")


def _check_ram() -> CheckResult:
    ram_gb = _get_ram_gb()
    if ram_gb < 4.0:
        return CheckResult("ram", "RAM", Severity.ERROR,
                           f"RAM {ram_gb:.0f}GB — quá ít, có thể crash",
                           fix_hint="Cần tối thiểu 8GB RAM")
    if ram_gb < 8.0:
        return CheckResult("ram", "RAM", Severity.WARNING,
                           f"RAM {ram_gb:.0f}GB — nên dùng mode 'Nhanh'")
    return CheckResult("ram", "RAM", Severity.OK, f"RAM {ram_gb:.0f}GB")


def _check_disk_space() -> CheckResult:
    try:
        if getattr(sys, 'frozen', False):
            drive = Path(sys.executable).drive or "C:"
        else:
            drive = Path(__file__).resolve().drive or "C:"
        _, _, free = shutil.disk_usage(drive + "\\")
        free_gb = free / (1024 ** 3)
        if free_gb < 2.0:
            return CheckResult("disk", "Ổ đĩa", Severity.ERROR,
                               f"Ổ {drive} còn {free_gb:.1f}GB — không đủ xuất video",
                               fix_hint="Cần ít nhất 5GB trống")
        if free_gb < 5.0:
            return CheckResult("disk", "Ổ đĩa", Severity.WARNING,
                               f"Ổ {drive} còn {free_gb:.1f}GB — có thể không đủ cho video dài")
        return CheckResult("disk", "Ổ đĩa", Severity.OK, f"Ổ {drive} còn {free_gb:.0f}GB")
    except Exception:
        return CheckResult("disk", "Ổ đĩa", Severity.OK, "Bỏ qua")


def _check_write_permissions() -> CheckResult:
    if getattr(sys, 'frozen', False):
        app_root = Path(sys.executable).parent
    else:
        app_root = Path(__file__).resolve().parent.parent.parent

    # Test multiple writable locations (exe dir first, then fallbacks)
    test_locations = [
        ("app_dir/logs", app_root / "logs"),
        ("app_dir/projects", app_root / "projects"),
    ]
    # Fallback: user home directory
    home_dir = Path.home() / ".cutclipshort"
    test_locations.append(("home_dir", home_dir))

    writable_count = 0
    issues = []
    for name, path in test_locations:
        try:
            path.mkdir(parents=True, exist_ok=True)
            tmp = path / "_test.tmp"
            tmp.write_text("ok", encoding="utf-8")
            tmp.unlink()
            writable_count += 1
        except (PermissionError, OSError):
            issues.append(name)

    if writable_count == 0:
        return CheckResult("write", "Quyền ghi", Severity.ERROR,
                           f"Không ghi được vào bất kỳ thư mục nào",
                           fix_hint="Chạy với quyền Administrator hoặc di chuyển app ra Desktop")
    if issues and writable_count > 0:
        # At least one location is writable — OK with note
        return CheckResult("write", "Quyền ghi", Severity.OK, "OK")
    return CheckResult("write", "Quyền ghi", Severity.OK, "OK")


def _get_ram_gb() -> float:
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        pass
    if os.name == "nt":
        try:
            import ctypes
            class MEMSTATEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            s = MEMSTATEX()
            s.dwLength = ctypes.sizeof(MEMSTATEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
            return s.ullTotalPhys / (1024 ** 3)
        except Exception:
            pass
    return 8.0
