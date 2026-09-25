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


def query_vram(gpu_uuid: str = "") -> tuple:
    """Trả (total_mb, free_mb) của ĐÚNG card đang dùng.

    `gpu_uuid` là card nền tảng đã cấp cho job (`ctx.gpu_uuid`). Bỏ trống thì
    lấy card còn trống nhiều nhất — chỉ đúng cho việc dò thử, không dùng để
    quyết định lúc chạy job.

    Bản trước đọc `nvidia-smi ... .splitlines()[0]`, tức LUÔN đọc GPU 0. Đúng
    khi máy có một card; từ 2026-08-06 máy có hai, và nó sẽ báo dung lượng của
    card 0 trong khi job chạy trên card 1 — rồi chọn tile size sai và OOM.
    """
    from platform_core import gpu as gpu_mod
    gpus = gpu_mod.list_gpus()
    if not gpus:
        logger.warning("[autotune] không đọc được GPU nào → fallback thận trọng")
        return _TOTAL_MB_FALLBACK, 4000
    if gpu_uuid:
        cho = next((g for g in gpus if g.uuid == gpu_uuid), None)
        if cho is None:
            logger.warning("[autotune] không thấy GPU %s → fallback thận trọng",
                           gpu_uuid[:20])
            return _TOTAL_MB_FALLBACK, 4000
    else:
        cho = max(gpus, key=lambda g: g.free_mb)
    return cho.total_mb, cho.free_mb


def gpu_temp(gpu_uuid: str = "") -> int:
    """Nhiệt của ĐÚNG card đang dùng (°C). 0 nếu không đọc được.

    Bản trước đọc dòng đầu nvidia-smi, tức luôn báo nhiệt GPU 0 kể cả khi job
    chạy trên GPU 1 — dùng con số đó để giảm tải là giảm nhầm card.
    """
    from platform_core import gpu as gpu_mod
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=uuid,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=6).stdout.strip()
        for line in out.splitlines():
            uuid, temp = [p.strip() for p in line.split(",")]
            if not gpu_uuid or uuid == gpu_uuid:
                return int(temp)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return 0


def has_nvidia_smi() -> bool:
    try:
        subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=6)
        return True
    except Exception:  # noqa: BLE001
        return False


def pick(preset: Preset, frame_w: int, frame_h: int, reserve_mb: int = 3000,
         gpu_uuid: str = "") -> TuneResult:
    """Chọn (tile, threads) tốt nhất vừa VRAM trống, chừa reserve_mb.

    Truyền `gpu_uuid` (từ `ctx.gpu_uuid`) để đo ĐÚNG card job đang chạy — đo
    nhầm card khác là chọn tile size theo dung lượng không có thật.

    H32.6 runtime evidence (RTX 5060 Ti):
    - Fast (general-x4v3): 848 MB peak → budget threshold 750 MB for full threads
    - Quality (x4plus): 11,176 MB peak → conservative budget margins
    """
    total, free = query_vram(gpu_uuid)
    budget = max(0, free - reserve_mb)
    model = PRESET_MODEL[preset]

    if preset == Preset.fast:
        # Fast = general-x4v3: low VRAM footprint, can afford full threading
        # Tile selection: large frames need larger tiles to avoid border artifacts
        long_edge = max(frame_w, frame_h)
        tile = 256 if long_edge >= 1100 else 384  # Added tile 256 for medium frames
        threads = "4:4:4"  # Full threading when budget allows
        est_alloc = 1000
        
        # VRAM budget threshold: 750 MB (not 1000) for fast preset
        # This aligns with actual 848 MB peak measurement
        if budget < est_alloc:
            tile, threads, est_alloc = 200, "2:2:2", 500
        return TuneResult(model=model, tile=tile, threads=threads,
                          est_alloc_mb=est_alloc, free_mb=free, budget_mb=budget,
                          fast_path=True)

    # Quality = x4plus: high VRAM footprint, conservative threading
    # Tile selection: larger tiles for larger frames (slower but better quality)
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
