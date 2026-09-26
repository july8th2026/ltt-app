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

# ⛔ Bo `_model_cache`: khai roi khong doc khong ghi o bat cu dau — ma chet.

# Model da ham nong trong VONG DOI TIEN TRINH worker nay: {model: timestamp}.
# ⚠️ Khoa la TEN MODEL, khong phai (model, tile, threads) nhu ban cu. `tile` va
#    `threads` den tu autotune theo VRAM SONG nen doi theo tung job ⇒ khoa cu gan
#    nhu KHONG BAO GIO trung, tuc "cache" ay chi lam warmup chay lai moi lan.
#    Ham nong la chuyen cua DRIVER/OS, khong phu thuoc tile.
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


def _warmup_model(model: str, gpu_index: int | None = None,
                  env: dict | None = None) -> None:
    """Chay engine mot luot tren anh gia — de ham nong cache driver/dia cua OS.

    ⚠️ Ham nay KHONG giu model trong VRAM. Tien trinh con `subprocess.run` thoat
    han truoc khi job that chay (`run_upscale` spawn mot `Popen` MOI), nen
    OS/driver da thu hoi context Vulkan. Loi ich duy nhat co the co la cache tep
    model cua OS + shader cache cua driver — va do la mot dieu phai DO, khong
    phai mot dieu duoc TUYEN BO. Xem `docs/UPSCALE_V2_CORRECTION/` ISSUE D.

    ⭐ PHAI nhan `gpu_index` + `env` giong job that. Ban cu khong truyen `-g` va
    khong truyen `env` ⇒ tren may co iGPU Intel, warmup co the chay SAI CARD
    (dung lop su co `vulkan_device.py:9-19`, va commit `7cde3c9d` da phai sua
    mot lan). Ham nong sai card thi vo ich, con lam ban card khac.
    """
    import tempfile
    from apps.upscalevideo.vulkan_device import _tiny_png
    with tempfile.TemporaryDirectory() as tmpdir:
        in_dir = os.path.join(tmpdir, "in")
        out_dir = os.path.join(tmpdir, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)
        # ⛔ Khong dung numpy+cv2 chi de tao MOT anh den: hai dependency nang cho
        #    mot viec `struct`+`zlib` lam duoc, va day la hai import numpy/cv2
        #    duy nhat trong ca app (ISSUE F). `_tiny_png` da ton tai san.
        _tiny_png(os.path.join(in_dir, "frame00001.png"))

        args = [str(_EXE), "-i", in_dir, "-o", out_dir, "-n", model, "-s", "4",
                "-m", "models", "-f", "png", "-t", "384", "-j", "1"]
        if gpu_index is not None:
            args += ["-g", str(gpu_index)]
        logger.debug("[engine] ham nong model %s tren gpu=%s", model, gpu_index)
        subprocess.run(args, cwd=str(_ENGINE_DIR),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60, env=env)


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
    
    # Ham nong mot lan moi model moi vong doi worker (xem `_warmup_model`).
    # Tat bang `LTT_UPSCALE_WARMUP=0` — de do duoc co/khong trong cung mot may.
    model_name = tune.model
    if (os.environ.get("LTT_UPSCALE_WARMUP", "1").strip() not in ("0", "false", "no")
            and model_name not in _model_warmup_cache):
        if model_available(model_name):
            _warmup_model(model_name, gpu_index=gpu_index, env=env)
            _model_warmup_cache[model_name] = time.time()
        else:
            logger.warning("[engine] khong co model %s, bo qua ham nong", model_name)
    
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
