"""
Handler job app `upscalevideo`. Nâng video ×4 bằng Real-ESRGAN NCNN trong WORKER
(job GPU dài — không dính trần 100s Cloudflare). Luồng (di trú từ runner BOT GEMINI):

    tải video (R2/Local) → probe → ĐẢM BẢO giữ chỗ đủ (theo duration thật) → guard
    đĩa → tách frame → autotune VRAM → NCNN upscale (chunk nếu >360 frame) → encode
    (NVENC/CPU) → lưu output → quyết toán theo giá thật.

Hợp đồng: idempotent (resume) · báo tiến độ (ctx.progress đập nhịp) · NÉM khi lỗi.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path

from apps.upscalevideo import autotune, cost, engine, ff
from apps.upscalevideo.schemas import (ENCODER, ENCODER_AMD, ENCODER_QSV,
                                        Codec, Preset)

log = logging.getLogger(__name__)

_BATCH_SIZE = 360          # >ngưỡng → chunk (giới hạn đỉnh đĩa PNG ×4)
_PREVIEW_SECONDS = 8.0


def _gpu_runtime(ctx) -> tuple[int | None, dict | None]:
    """Resolve the worker lease once and pin every child process to that GPU.

    Real-ESRGAN NCNN is Vulkan-based, so it needs the physical ``-g`` index;
    CUDA/NVENC subprocesses receive the UUID-scoped environment.  A vanished
    leased GPU is an infrastructure error, never permission to fall back to a
    different card and collide with another worker.
    """
    gpu_uuid = str(getattr(ctx, "gpu_uuid", "") or "")
    env_factory = getattr(ctx, "gpu_env", None)
    process_env = env_factory() if callable(env_factory) else None
    if not gpu_uuid:
        return None, process_env
    from platform_core import gpu
    selected = gpu.by_uuid(gpu_uuid)
    if selected is None:
        raise RuntimeError(_t("GPU đã được cấp không còn khả dụng; vui lòng thử lại."))
    # ⚠ `-g` của NCNN là chỉ số **Vulkan**, KHÔNG phải chỉ số nvidia-smi của lease. Hai hệ
    # đánh số độc lập: 11/09/2026, sau khi desktop trên máy chủ này chuyển sang iGPU Intel,
    # thứ tự Vulkan đảo thành [0]=Intel, [1]=NVIDIA — `selected.index` = 0 lúc đó trỏ thẳng
    # vào card onboard. Dịch theo TÊN card; không dò ra thì để lỗi nổ, đừng đoán (chạy nhầm
    # iGPU là hỏng ÂM THẦM: job vẫn "chạy", chỉ chậm thảm hoặc chết giữa chừng).
    from apps.upscalevideo import vulkan_device
    return vulkan_device.vulkan_index_for(selected.name), process_env


def _handle_image(params: dict, ctx=None) -> dict:
    from PIL import Image
    from platform_core.storage import get_storage
    image_key = str(params.get("image_key") or "").replace("\\", "/").strip("/")
    owner_id = str(params.get("owner_id") or "")
    parts = image_key.split("/")
    if not owner_id or len(parts) < 3 or parts[1] != owner_id:
        raise ValueError(_t('Ảnh không thuộc tài khoản đang chạy workflow.'))
    try:
        preset = Preset(str(params.get("preset") or "fast"))
    except ValueError:
        preset = Preset.fast
    if not engine.check_engine():
        raise RuntimeError(_t('Engine Real-ESRGAN chưa sẵn sàng.'))
    storage = get_storage(); job_id = getattr(ctx, "job_id", "adhoc")
    out_key = f"upscalevideo/{owner_id}/{job_id}/image-x4.png"
    if storage.exists(out_key):
        return {"image_key": out_key, "scale": 4,
                "credit_cost": 4 if preset == Preset.quality else 2}
    tmp = tempfile.mkdtemp(prefix="ltt_upscale_image_")
    try:
        input_dir = os.path.join(tmp, "input"); output_dir = os.path.join(tmp, "output")
        os.makedirs(input_dir, exist_ok=True)
        source = os.path.join(tmp, "source" + (os.path.splitext(image_key)[1] or ".png"))
        with storage.open(image_key) as src, open(source, "wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        with Image.open(source) as image:
            width, height = image.size
            image.convert("RGB").save(os.path.join(input_dir, "frame00001.png"), "PNG")
        tune = autotune.pick(preset, width, height,
                             gpu_uuid=getattr(ctx, "gpu_uuid", ""))
        if ctx is not None: ctx.progress(10, f"nâng ảnh bằng {tune.model}")
        gpu_index, process_env = _gpu_runtime(ctx)
        status = engine.run_upscale(input_dir, output_dir, tune, 1,
                                    progress_cb=(lambda done: ctx.progress(min(90, 10 + done * 80), "nâng chi tiết") if ctx else None),
                                    cancel_check=getattr(ctx, "is_cancelled", None),
                                    gpu_index=gpu_index, env=process_env)
        if status != "done":
            raise RuntimeError(f"Engine upscale ảnh thất bại ({status}).")
        result_path = next(Path(output_dir).glob("*.png"), None)
        if result_path is None:
            raise RuntimeError(_t('Engine không tạo output ảnh.'))
        with open(result_path, "rb") as stream:
            storage.put(out_key, stream, content_type="image/png")
        if ctx is not None: ctx.progress(100, "xong")
        return {"image_key": out_key, "scale": 4, "width": width * 4,
                "height": height * 4, "preset": preset.value,
                "credit_cost": 4 if preset == Preset.quality else 2}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _dam_bao_giu_cho(job_id: str, user_id: str, need: int) -> None:
    if not user_id or need <= 0:
        return
    from platform_core import credit
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        held = credit.so_da_giu(db, job_id)
        if held >= need:
            return
        try:
            credit.giu_cho(db, user_id, need - held, job_id)
            db.commit()
        except credit.ThieuCreditError as e:
            db.rollback()
            raise RuntimeError(f"Không đủ credit cho video dài thật ({need} credit): {e}") from e
    finally:
        try: next(gen)
        except StopIteration: pass


def _guard_disk(info: dict, frame_multiplier: int = 1) -> None:
    frames = max(info.get("nb_frames", 0) * max(1, frame_multiplier), 1)
    up_area = (info["w"] * 4) * (info["h"] * 4)
    src_area = max(info["w"] * info["h"], 1)
    batch = min(frames, _BATCH_SIZE)
    need = int((frames * src_area + batch * up_area) * 3 * 0.5 * 1.3)
    free = shutil.disk_usage(tempfile.gettempdir()).free
    if need > free:
        raise RuntimeError(
            f"Không đủ dung lượng đĩa tạm: cần ~{need // (1024**3)}GB, còn "
            f"~{free // (1024**3)}GB. Dùng video ngắn hơn hoặc giải phóng ổ đĩa.")


def _resolve_encoder(codec: Codec) -> str:
    """Encoder theo codec. CHAIN FALLOBACK:
    
    1. NVIDIA NVENC (h264_nvenc) — fastest
    2. Intel QSV (h264_qsv) — 5-10x faster than CPU
    3. AMD AMF (h264_amf) — 5-10x faster than CPU
    4. libx264 (CPU) — final fallback, slow
    
    This ensures GPU encode whenever possible, not just NVENC.
    """
    from platform_core import media
    gpu = media.detect_gpu_encoder()      # "" | h264_nvenc | h264_qsv | h264_amf
    
    if gpu == "h264_nvenc":
        return ENCODER[codec]             # NVIDIA NVENC (fastest)
    elif gpu == "h264_qsv":
        return ENCODER_QSV[codec]         # Intel QuickSync
    elif gpu == "h264_amf":
        return ENCODER_AMD[codec]         # AMD AMF
    return "libx264"                      # CPU fallback (slow but safe)


def _output_fps(fps_str: str, preserve_fps: bool, smooth_motion: bool) -> str:
    """Resolve the customer FPS intent without silently changing its base.

    Motion smoothing means *double the source cadence*.  It is not compatible
    with a promise to preserve the output FPS, but that must not turn a 24 fps
    source into a 30 fps source before interpolation (24→48, not 30→60).
    """
    if smooth_motion:
        return ff.multiply_rate(fps_str)
    return fps_str if preserve_fps else "30"


def _upscale_batched(tmp, in_dir, tune, n, info, target_h, encoder, ctx, on_prog,
                     cancel_check, gpu_index=None, process_env=None):
    """Video dài: chunk _BATCH_SIZE frame → upscale → encode segment → concat."""
    seg_dir = os.path.join(tmp, "seg"); os.makedirs(seg_dir, exist_ok=True)
    frame_files = sorted(f for f in os.listdir(in_dir) if f.endswith(".png"))
    segs = []
    done_total = 0
    n_batches = (n + _BATCH_SIZE - 1) // _BATCH_SIZE
    for bi, start in enumerate(range(0, n, _BATCH_SIZE)):
        batch = frame_files[start:start + _BATCH_SIZE]
        b_in = os.path.join(tmp, f"b{bi:04d}_in"); b_up = os.path.join(tmp, f"b{bi:04d}_up")
        os.makedirs(b_in, exist_ok=True)
        for idx, fn in enumerate(batch, 1):
            os.rename(os.path.join(in_dir, fn), os.path.join(b_in, f"f{idx:05d}.png"))
        if ctx is not None:
            ctx.progress(min(88, 5 + int(done_total * 83 / max(n, 1))),
                         f"nâng nét đoạn {bi + 1}/{n_batches}…")
        base = done_total
        status = engine.run_upscale(b_in, b_up, tune, len(batch),
                                    progress_cb=lambda d, _b=base: on_prog(_b + d),
                                    cancel_check=cancel_check,
                                    gpu_index=gpu_index, env=process_env)
        if status == "cancelled":
            raise ff.ProcessingCancelled("Job đã được hủy.")
        if status == "timeout":
            raise RuntimeError(f"Engine treo ở đoạn {bi + 1} (>5' không tiến triển).")
        if status != "done":
            raise RuntimeError(f"Engine upscale đoạn {bi + 1} thất bại.")
        seg = os.path.join(seg_dir, f"seg_{bi:04d}.mp4")
        ff.encode_segment(b_up, seg, info["fps_str"], target_h, encoder,
                          cancel_check=cancel_check, env=process_env)
        segs.append(seg)
        done_total += len(batch)
        
        # Checkpoint after each batch.
        #
        # 🔴 Truoc 26/09 dong nay goi `save_checkpoint(job_id, ...)` — ma `job_id`
        #    KHONG ton tai trong ham nay (`ruff F821`). Tuc MOI luot upscale cham
        #    toi day chet bang `NameError`, va no KHONG nam sau mot nhanh phan cung
        #    nao ca. Ham co tham so `ctx` (`JobContext`), va `JobContext.job_id` la
        #    cho dung (`platform_core/job_runner.py:128`).
        #
        # ⚠️ Va phai CANH `ctx is None`: ham nay duoc goi voi `ctx=None` o duong
        #    khong-co-job (xem `if ctx is not None: ctx.progress(...)` cung tep).
        #    Viet `ctx.job_id` tron chi doi `NameError` thanh `AttributeError`.
        # ⇒ Khong co job thi khong co gi de `resume`, nen BO QUA checkpoint la dung
        #   nghia — khong phai mot duong lui im lang.
        if ctx is not None:
            from apps.upscalevideo.checkpoint import save_checkpoint
            save_checkpoint(ctx.job_id, f"upscale_batch_{bi+1:03d}", {
                "batch": bi + 1,
                "total_batches": n_batches,
                "frames_processed": done_total,
                "total_frames": n,
            })
        
        shutil.rmtree(b_in, ignore_errors=True)
        shutil.rmtree(b_up, ignore_errors=True)
    return segs


def handle(params: dict, ctx=None) -> dict:
    from platform_core.storage import get_storage

    if params.get("image_key"):
        return _handle_image(params, ctx)

    started_clock = time.monotonic()
    video_key = str(params.get("video_key", "")).strip()
    if not video_key:
        raise ValueError(_t('Thiếu video (video_key).'))
    try:
        preset = Preset(str(params.get("preset", "fast")))
    except ValueError:
        preset = Preset.fast
    target_h = int(params.get("target_height", 1080) or 1080)
    if target_h not in (1080, 1440, 2160):
        target_h = 1080
    try:
        codec = Codec(str(params.get("codec", "h264")))
    except ValueError:
        codec = Codec.h264
    preview = bool(params.get("preview"))
    preserve_fps = bool(params.get("preserve_fps", True))
    preserve_audio = bool(params.get("preserve_audio", True))
    stabilize = bool(params.get("stabilize", False))
    smooth_motion = bool(params.get("smooth_motion", False))
    owner_id = str(params.get("owner_id", "")) or "unknown"
    job_id = getattr(ctx, "job_id", "") or "adhoc"
    cancel_check = getattr(ctx, "is_cancelled", None)
    gpu_index, process_env = _gpu_runtime(ctx)

    if not engine.check_engine():
        raise RuntimeError(_t('Engine upscale chưa sẵn sàng (thiếu vendor/engine).'))

    storage = get_storage()
    tag = "preview" if preview else f"{target_h}p"
    if stabilize:
        tag += "-stabilized"
    if smooth_motion:
        tag += "-smooth2x"
    out_key = f"upscalevideo/{owner_id}/{job_id}/output_{tag}.mp4"

    tmp = tempfile.mkdtemp(prefix="ltt_upscale_")
    in_dir = os.path.join(tmp, "in"); up_dir = os.path.join(tmp, "up")
    tmp_video = os.path.join(tmp, "src" + (os.path.splitext(video_key)[1] or ".mp4"))
    try:
        if ctx is not None:
            ctx.progress(2, "tải video")
        with storage.open(video_key) as src, open(tmp_video, "wb") as dst:
            while True:
                if cancel_check and cancel_check():
                    raise ff.ProcessingCancelled("Job đã được hủy.")
                block = src.read(1024 * 1024)
                if not block:
                    break
                dst.write(block)

        info = ff.probe_video(tmp_video, cancel_check=cancel_check, env=process_env)
        if info["w"] == 0:
            raise RuntimeError(_t('Không đọc được luồng video.'))
        eff_dur = min(info["duration"], _PREVIEW_SECONDS) if preview else info["duration"]
        true_cost = cost.uoc_luong_credit(info["duration"], target_h, preset.value,
                                          preview, stabilize, smooth_motion)
        _dam_bao_giu_cho(job_id, params.get("owner_id", ""), true_cost)

        if storage.exists(out_key):                 # resume
            if ctx is not None:
                ctx.progress(100, "xong")
            return {"video_key": out_key, "credit_cost": true_cost,
                    "duration_s": round(eff_dur, 1), "preset": preset.value,
                    "target_height": target_h}

        _guard_disk(info, frame_multiplier=2 if smooth_motion else 1)

        working_video = tmp_video
        if stabilize:
            if ctx is not None:
                ctx.progress(3, "phân tích và ổn định chuyển động…")
            working_video = os.path.join(tmp, "stabilized.mp4")
            ff.stabilize_video(tmp_video, working_video,
                               max_seconds=_PREVIEW_SECONDS if preview else None,
                               cancel_check=cancel_check, env=process_env)

            # Checkpoint after stabilization
            from apps.upscalevideo.checkpoint import save_checkpoint
            save_checkpoint(job_id, "stabilize_completed", {
                "working_video": working_video,
            })

        if ctx is not None:
            ctx.progress(4, "tách frame")
        output_fps = _output_fps(info["fps_str"], preserve_fps, smooth_motion)
        cfr = None if smooth_motion else (info["fps_str"] if preserve_fps and info.get("is_vfr") else (
            "30" if not preserve_fps else None)
        )
        max_sec = _PREVIEW_SECONDS if preview else None
        n = ff.extract_frames(working_video, in_dir, cfr_fps=cfr,
                              interpolate_fps=output_fps if smooth_motion else None,
                              max_seconds=max_sec,
                              cancel_check=cancel_check, env=process_env)

        # Checkpoint after frame extraction
        from apps.upscalevideo.checkpoint import save_checkpoint
        save_checkpoint(job_id, "frame_extraction_completed", {
            "n_frames": n,
            "target_height": target_h,
            "preset": preset.value,
        })

        tune = autotune.pick(preset, info["w"], info["h"],
                             gpu_uuid=getattr(ctx, "gpu_uuid", ""))
        warning = tune.warning or ""
        if info.get("is_vfr"):
            warning = (f"Nguồn VFR — đã chuẩn hoá CFR {info['fps']:.3f}fps. " + warning).strip()
        if ctx is not None:
            ctx.progress(5, f"nâng nét {tune.model} (tile {tune.tile})…")

        def on_prog(done: int) -> None:
            if ctx is not None:
                ctx.progress(min(88, 5 + int(83 * done / max(n, 1))), "nâng nét…")

        encoder = _resolve_encoder(codec)
        if n <= _BATCH_SIZE:
            status = engine.run_upscale(in_dir, up_dir, tune, n, progress_cb=on_prog,
                                        cancel_check=cancel_check,
                                        gpu_index=gpu_index, env=process_env)
            if status == "cancelled":
                raise ff.ProcessingCancelled("Job đã được hủy.")
            if status == "timeout":
                raise RuntimeError(_t("Engine treo (>5' không có frame mới). Thử lại."))
            if status != "done":
                raise RuntimeError(_t('Engine upscale thất bại (xem log).'))
            if ctx is not None:
                ctx.progress(90, f"ghép video {target_h}p…")
            ow, oh = ff.encode_full(up_dir, tmp_video, os.path.join(tmp, "out.mp4"),
                                    output_fps, target_h,
                                    info["has_audio"] and preserve_audio, encoder,
                                    cancel_check=cancel_check, env=process_env)
            out_local = os.path.join(tmp, "out.mp4")
        else:
            batch_info = dict(info, fps_str=output_fps,
                              has_audio=info["has_audio"] and preserve_audio)
            segs = _upscale_batched(tmp, in_dir, tune, n, batch_info, target_h, encoder,
                                    ctx, on_prog, cancel_check, gpu_index, process_env)
            if ctx is not None:
                ctx.progress(92, f"nối {len(segs)} đoạn + audio…")
            out_local = os.path.join(tmp, "out.mp4")
            ow, oh = ff.concat_and_mux(segs, tmp_video, out_local,
                                       info["has_audio"] and preserve_audio,
                                       cancel_check=cancel_check, env=process_env)

        if ctx is not None:
            ctx.progress(96, "lưu kết quả")
        with open(out_local, "rb") as f:
            storage.put(out_key, f, content_type="video/mp4")
        
        # Checkpoint output uploaded
        from apps.upscalevideo.checkpoint import save_checkpoint
        save_checkpoint(job_id, "output_uploaded", {
            "out_key": out_key,
        })
        
        # Quality gate check
        from apps.upscalevideo.quality_gate import run_quality_gates, GATE_THRESHOLDS
        preset = Preset(preset.value)
        thresholds = GATE_THRESHOLDS[preset]
        if ctx is not None:
            ctx.progress(98, "chất lượng...")
        quality_result = run_quality_gates(out_key, preset)
        quality_log = quality_result.get("error") or _t("Quality gates passed: PSNR{0}dB").format(quality_result['gates']['quality']['metrics'].get('psnr_db', 'N/A'))
        logger.info("[quality] %s", quality_log)
        
        if not quality_result["all_passed"]:
            logger.warning("[quality] gate failed: %s", quality_result["error"])
            # Log warning but don't fail job — keep backward compatibility
            # If needed, uncomment below to fail fast:
            # raise RuntimeError(quality_result["error"])
            res["quality_warning"] = quality_result["error"]
        
        if ctx is not None:
            ctx.progress(100, "xong")
        res = {"video_key": out_key, "credit_cost": true_cost,
               "duration_s": round(eff_dur, 1), "preset": preset.value,
               "target_height": target_h, "out_w": ow, "out_h": oh,
               "codec": codec.value, "encoder": encoder,
               "fps": float(output_fps.split("/")[0]) / float(output_fps.split("/")[1])
                      if "/" in output_fps else float(output_fps),
               "has_audio": bool(info["has_audio"] and preserve_audio),
               "preserve_fps": preserve_fps, "preserve_audio": preserve_audio,
               "stabilize": stabilize, "smooth_motion": smooth_motion,
               "frames": n, "processing_seconds": round(time.monotonic() - started_clock, 2),
               "quality_log": quality_log}
        if warning:
            res["warning"] = warning
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
