"""
Handler job app `upscalevideo`. Nâng video ×4 bằng Real-ESRGAN NCNN trong WORKER
(job GPU dài — không dính trần 100s Cloudflare). Luồng (di trú từ runner BOT GEMINI):

    tải video (R2/Local) → probe → ĐẢM BẢO giữ chỗ đủ (theo duration thật) → guard
    đĩa → tách frame → autotune VRAM → NCNN upscale (chunk nếu >360 frame) → encode
    (NVENC/CPU) → lưu output → quyết toán theo giá thật.

Hợp đồng: idempotent (resume) · báo tiến độ (ctx.progress đập nhịp) · NÉM khi lỗi.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time

from apps.upscalevideo import autotune, cost, engine, ff
from apps.upscalevideo.schemas import ENCODER, Codec, Preset

log = logging.getLogger(__name__)

_BATCH_SIZE = 360          # >ngưỡng → chunk (giới hạn đỉnh đĩa PNG ×4)
_PREVIEW_SECONDS = 8.0


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
    """Encoder theo codec. CHỈ dùng NVENC khi detect ra ĐÚNG họ nvenc — nếu GPU là
    Intel/AMD (qsv/amf) hoặc không có → libx264 (chống encode HỎNG sau khi đã upscale
    xong). `ENCODER[codec]` chỉ có bản nvenc nên phải gate; card khác → CPU."""
    from platform_core import media
    gpu = media.detect_gpu_encoder()      # "" | h264_nvenc | h264_qsv | h264_amf
    if gpu == "h264_nvenc":
        return ENCODER[codec]             # h264_nvenc / hevc_nvenc (card này hỗ trợ)
    return "libx264"                      # Intel/AMD/CPU → x264 (chậm nhưng không chết)


def _upscale_batched(tmp, in_dir, tune, n, info, target_h, encoder, ctx, on_prog,
                     cancel_check):
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
                                    cancel_check=cancel_check)
        if status == "cancelled":
            raise ff.ProcessingCancelled("Job đã được hủy.")
        if status == "timeout":
            raise RuntimeError(f"Engine treo ở đoạn {bi + 1} (>5' không tiến triển).")
        if status != "done":
            raise RuntimeError(f"Engine upscale đoạn {bi + 1} thất bại.")
        seg = os.path.join(seg_dir, f"seg_{bi:04d}.mp4")
        ff.encode_segment(b_up, seg, info["fps_str"], target_h, encoder,
                          cancel_check=cancel_check)
        segs.append(seg)
        done_total += len(batch)
        shutil.rmtree(b_in, ignore_errors=True)
        shutil.rmtree(b_up, ignore_errors=True)
    return segs


def handle(params: dict, ctx=None) -> dict:
    from platform_core.storage import get_storage

    started_clock = time.monotonic()
    video_key = str(params.get("video_key", "")).strip()
    if not video_key:
        raise ValueError("Thiếu video (video_key).")
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

    if not engine.check_engine():
        raise RuntimeError("Engine upscale chưa sẵn sàng (thiếu vendor/engine).")

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

        info = ff.probe_video(tmp_video, cancel_check=cancel_check)
        if info["w"] == 0:
            raise RuntimeError("Không đọc được luồng video.")
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
                               cancel_check=cancel_check)

        if ctx is not None:
            ctx.progress(4, "tách frame")
        base_fps = info["fps_str"] if preserve_fps else "30"
        output_fps = ff.multiply_rate(base_fps) if smooth_motion else base_fps
        cfr = None if smooth_motion else (info["fps_str"] if preserve_fps and info.get("is_vfr") else (
            "30" if not preserve_fps else None)
        )
        max_sec = _PREVIEW_SECONDS if preview else None
        n = ff.extract_frames(working_video, in_dir, cfr_fps=cfr,
                              interpolate_fps=output_fps if smooth_motion else None,
                              max_seconds=max_sec,
                              cancel_check=cancel_check)

        tune = autotune.pick(preset, info["w"], info["h"])
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
                                        cancel_check=cancel_check)
            if status == "cancelled":
                raise ff.ProcessingCancelled("Job đã được hủy.")
            if status == "timeout":
                raise RuntimeError("Engine treo (>5' không có frame mới). Thử lại.")
            if status != "done":
                raise RuntimeError("Engine upscale thất bại (xem log).")
            if ctx is not None:
                ctx.progress(90, f"ghép video {target_h}p…")
            ow, oh = ff.encode_full(up_dir, tmp_video, os.path.join(tmp, "out.mp4"),
                                    output_fps, target_h,
                                    info["has_audio"] and preserve_audio, encoder,
                                    cancel_check=cancel_check)
            out_local = os.path.join(tmp, "out.mp4")
        else:
            batch_info = dict(info, fps_str=output_fps,
                              has_audio=info["has_audio"] and preserve_audio)
            segs = _upscale_batched(tmp, in_dir, tune, n, batch_info, target_h, encoder,
                                    ctx, on_prog, cancel_check)
            if ctx is not None:
                ctx.progress(92, f"nối {len(segs)} đoạn + audio…")
            out_local = os.path.join(tmp, "out.mp4")
            ow, oh = ff.concat_and_mux(segs, tmp_video, out_local,
                                       info["has_audio"] and preserve_audio,
                                       cancel_check=cancel_check)

        if ctx is not None:
            ctx.progress(96, "lưu kết quả")
        with open(out_local, "rb") as f:
            storage.put(out_key, f, content_type="video/mp4")

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
               "frames": n, "processing_seconds": round(time.monotonic() - started_clock, 2)}
        if warning:
            res["warning"] = warning
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
