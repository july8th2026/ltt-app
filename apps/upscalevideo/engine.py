"""
engine.py — gọi realesrgan-ncnn-vulkan (subprocess ĐỒNG BỘ) upscale 1 thư mục frame.

Di trú từ BOT GEMINI `video_upscale/adapters/engine_adapter.py` (bản async) sang mô
hình worker đồng bộ. Giữ nguyên:
- cwd = engine dir để `-m models` (tương đối) tránh lỗi đường dẫn có dấu cách.
- progress = đếm PNG trong out_dir (robust hơn parse stdout).
- STALL watchdog: kill nếu >5 phút không có frame mới (GPU treo/driver TDR).
- Safety fallback: OOM tile lớn → thử tile/2 một lần.

Vendor engine nằm trong app: `apps/upscalevideo/vendor/engine/` (copy từ BOT GEMINI,
gitignored). exe là Windows — nền tảng cũng chạy Windows nên dùng thẳng.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from apps.upscalevideo.schemas import TuneResult

logger = logging.getLogger(__name__)

# Model cache: model_name -> (param_path, bin_path)
_model_cache = {}

# Model warmup cache: model_name -> timestamp of last warmup
_model_warmup_cache = {}

_STALL_TIMEOUT_S = 300.0

_ENGINE_DIR = Path(__file__).resolve().parent / "vendor" / "engine"
_EXE = _ENGINE_DIR / "realesrgan-ncnn-vulkan.exe"


def engine_dir() -> Path:
    return _ENGINE_DIR


def check_engine() -> bool:
    return _EXE.is_file() and (_ENGINE_DIR / "models").is_dir()


def model_available(model: str) -> bool:
    m = _ENGINE_DIR / "models"
    return (m / f"{model}.param").is_file() and (m / f"{model}.bin").is_file()


def _warmup_model(model: str) -> None:
    """Warm up model by loading it in a separate process."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy input/output dirs
        in_dir = os.path.join(tmpdir, "in")
        out_dir = os.path.join(tmpdir, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)
        
        # Create dummy frame
        import numpy as np
        frame = np.zeros((512, 512, 3), dtype=np.uint8)
        frame[:, :, 0] = 128
        frame[:, :, 1] = 128
        frame[:, :, 2] = 128
        import cv2
        cv2.imwrite(os.path.join(in_dir, "frame00001.png"), frame)
        
        # Run engine with dummy data to warm up model
        args = [str(_EXE), "-i", in_dir, "-o", out_dir, "-n", model, "-s", "4",
                "-m", "models", "-f", "png", "-t", "384", "-j", "1"]
        logger.debug("[engine] warming up model: %s", model)
        subprocess.run(args, cwd=str(_ENGINE_DIR), 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        logger.debug("[engine] model warmed up: %s", model)


def _count_png(d: str) -> int:
    try:
        return sum(1 for f in os.scandir(d) if f.name.endswith(".png"))
    except FileNotFoundError:
        return 0


def run_upscale(in_dir: str, out_dir: str, tune: TuneResult, n_frames: int,
                progress_cb: Optional[Callable[[int], None]] = None,
                cancel_check: Optional[Callable[[], bool]] = None,
                gpu_index: int | None = None,
                env: dict | None = None,
                _allow_fallback: bool = True) -> str:
    """Upscale mọi PNG trong in_dir → out_dir. Trả "done"|"cancelled"|"timeout"|"error"."""
    os.makedirs(out_dir, exist_ok=True)
    
    # Model warmup check
    model_name = tune.model
    warmup_cache_key = f"{model_name}_tile{tune.tile}_j{tune.threads}"
    
    if warmup_cache_key not in _model_warmup_cache:
        if model_available(model_name):
            _warmup_model(model_name)
            _model_warmup_cache[warmup_cache_key] = time.time()
        else:
            logger.warning("[engine] model %s not available, skipping warmup", model_name)
    
    args = [str(_EXE), "-i", in_dir, "-o", out_dir, "-n", tune.model, "-s", "4",
            "-m", "models", "-f", "png", "-t", str(tune.tile), "-j", tune.threads]
    if gpu_index is not None:
        # NCNN dùng Vulkan nên CUDA_VISIBLE_DEVICES một mình không ghim được card.
        # `-g` là GPU index vật lý lấy từ UUID lease của worker.
        args += ["-g", str(gpu_index)]
    logger.info("[engine] %s tile=%d j=%s gpu=%s (%d frames)", tune.model,
                tune.tile, tune.threads, gpu_index, n_frames)
    proc = subprocess.Popen(args, cwd=str(_ENGINE_DIR),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env=env)
    last_done, last_t = -1, time.monotonic()
    try:
        while True:
            try:
                proc.wait(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                pass
            if cancel_check and cancel_check():
                proc.kill(); proc.wait()
                return "cancelled"
            done_now = _count_png(out_dir)
            if progress_cb:
                progress_cb(done_now)
            if done_now > last_done:
                last_done, last_t = done_now, time.monotonic()
            elif time.monotonic() - last_t > _STALL_TIMEOUT_S:
                proc.kill(); proc.wait()
                logger.error("[engine] STALL >%.0fs (%d/%d) → kill",
                             _STALL_TIMEOUT_S, done_now, n_frames)
                return "timeout"
    except BaseException:
        proc.kill(); proc.wait()
        raise

    done = _count_png(out_dir)
    if progress_cb:
        progress_cb(done)
    if proc.returncode == 0 and done >= n_frames:
        return "done"

    # OOM tile lớn → thử tile nhỏ hơn 1 lần.
    if _allow_fallback and tune.tile > 200:
        smaller = max(200, tune.tile // 2)
        logger.warning("[engine] rc=%s done=%d/%d → fallback tile %d→%d",
                       proc.returncode, done, n_frames, tune.tile, smaller)
        tune2 = tune.model_copy(update={"tile": smaller})
        return run_upscale(in_dir, out_dir, tune2, n_frames, progress_cb,
                           cancel_check, gpu_index=gpu_index, env=env,
                           _allow_fallback=False)
    logger.error("[engine] thất bại rc=%s frames=%d/%d", proc.returncode, done, n_frames)
    return "error"
