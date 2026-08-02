"""
autotune.py — chọn tile size + số luồng NCNN theo VRAM trống (di trú từ BOT GEMINI).

Benchmark thực đo trên RTX 5060 Ti 16GB:
  fast (general-x4v3, nhẹ): alloc ~600-900MiB, gần như luôn vừa, luồng cao.
  quality (x4plus, nặng): CHỈ nhanh ở tile 512 (~10GB alloc); thiếu VRAM → rất chậm.

Bản nền tảng dùng ĐỒNG BỘ (worker 1 tiến trình 1 job) — bỏ các wrapper async.
"""
from __future__ import annotations

import logging
import subprocess

from apps.upscalevideo.schemas import Preset, PRESET_MODEL, TuneResult

logger = logging.getLogger(__name__)

_TOTAL_MB_FALLBACK = 16311     # RTX 5060 Ti 16GB


def query_vram() -> tuple:
    """Trả (total_mb, free_mb). Fallback thận trọng nếu nvidia-smi lỗi."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip().splitlines()[0]
        total, free = [int(x.strip()) for x in out.split(",")]
        return total, free
    except Exception as exc:  # noqa: BLE001
        logger.warning("[autotune] nvidia-smi lỗi (%s) → fallback thận trọng", exc)
        return _TOTAL_MB_FALLBACK, 4000


def gpu_temp() -> int:
    """Nhiệt GPU (°C). 0 nếu không đọc được."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=6,
        ).stdout.strip().splitlines()[0]
        return int(out)
    except Exception:  # noqa: BLE001
        return 0


def has_nvidia_smi() -> bool:
    try:
        subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=6)
        return True
    except Exception:  # noqa: BLE001
        return False


def pick(preset: Preset, frame_w: int, frame_h: int, reserve_mb: int = 3000) -> TuneResult:
    """Chọn (tile, threads) tốt nhất vừa VRAM trống, chừa reserve_mb."""
    total, free = query_vram()
    budget = max(0, free - reserve_mb)
    model = PRESET_MODEL[preset]

    if preset == Preset.fast:
        long_edge = max(frame_w, frame_h)
        tile = 256 if long_edge >= 1100 else 384
        threads = "4:4:4"
        est_alloc = 1000
        if budget < est_alloc:
            tile, threads, est_alloc = 200, "2:2:2", 500
        return TuneResult(model=model, tile=tile, threads=threads,
                          est_alloc_mb=est_alloc, free_mb=free, budget_mb=budget,
                          fast_path=True)

    # Quality = x4plus: chỉ nhanh ở tile 512 (~10GB alloc)
    FAST_TILE, FAST_ALLOC, SAFETY = 512, 10024, 500
    if budget >= FAST_ALLOC + SAFETY:
        return TuneResult(model=model, tile=FAST_TILE, threads="1:2:2",
                          est_alloc_mb=FAST_ALLOC, free_mb=free, budget_mb=budget,
                          fast_path=True)
    if budget >= 9314:
        tile, est = 448, 9314
    elif budget >= 7025:
        tile, est = 384, 7025
    elif budget >= 5000:
        tile, est = 320, 5095
    else:
        tile, est = 256, 3513
    warn = (f"GPU đang bận (trống {free}MiB, budget {budget}MiB). Quality (x4plus) "
            f"sẽ RẤT chậm. Nên chuyển sang Fast hoặc chạy khi GPU rảnh.")
    logger.warning("[autotune] %s", warn)
    return TuneResult(model=model, tile=tile, threads="1:2:2",
                      est_alloc_mb=est, free_mb=free, budget_mb=budget,
                      fast_path=False, warning=warn)
