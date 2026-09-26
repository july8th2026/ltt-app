"""
Handler job app `upscalevideo`. Nâng video ×4 bằng Real-ESRGAN NCNN trong WORKER
(job GPU dài — không dính trần 100s Cloudflare). Luồng (di trú từ runner BOT GEMINI):

    tải video (R2/Local) → probe → ĐẢM BẢO giữ chỗ đủ (theo duration thật) → guard
    đĩa → tách frame → autotune VRAM → NCNN upscale (chunk nếu >360 frame) → encode
    (NVENC/CPU) → lưu output → quyết toán theo giá thật.

Hợp đồng: báo tiến độ (ctx.progress đập nhịp) · NÉM khi lỗi · idempotent ở mức
CẢ JOB — `storage.exists(out_key)` bỏ qua job đã có đầu ra trên R2.
⛔ KHÔNG có resume theo chặng: `checkpoint.py` chỉ GHI SỔ, không ai đọc để bỏ qua
việc (ISSUE G, `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md`).
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path

from apps.upscalevideo import autotune, checkpoint, cost, engine, ff, quality_gate
from apps.upscalevideo.schemas import ENCODER, ENCODER_CPU, Codec, Preset

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
        if ctx is not None: ctx.progress(10, _t("nâng ảnh bằng {0}").format(tune.model))
        gpu_index, process_env = _gpu_runtime(ctx)
        status = engine.run_upscale(input_dir, output_dir, tune, 1,
                                    progress_cb=(lambda done: ctx.progress(min(90, 10 + done * 80), _t("nâng chi tiết")) if ctx else None),
                                    cancel_check=getattr(ctx, "is_cancelled", None),
                                    gpu_index=gpu_index, env=process_env)
        if status != "done":
            raise RuntimeError(_t("Engine upscale ảnh thất bại ({0}).").format(status))
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
            raise RuntimeError(_t("Không đủ credit cho video dài thật ({0} credit): {1}")
                              .format(need, e)) from e
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
            _t("Không đủ dung lượng đĩa tạm: cần ~{0}GB, còn ~{1}GB. Dùng video "
               "ngắn hơn hoặc giải phóng ổ đĩa.")
            .format(need // (1024**3), free // (1024**3)))


class CodecKhongPhucVuDuoc(RuntimeError):
    """Khách xin một codec máy này không thể giao trong thời gian chấp nhận được.

    Là `RuntimeError` để `job_runner` xử như mọi lỗi job khác (đỏ + nhả giữ chỗ);
    là lớp RIÊNG để test nhắm được đúng nó thay vì bắt `RuntimeError` chung.
    """


_hevc_phan_cung: bool | None = None       # cache theo VÒNG ĐỜI TIẾN TRÌNH


def co_hevc_phan_cung() -> bool:
    """`hevc_nvenc` trên máy này có **CHẠY** không. Dò thật, cache mỗi tiến trình.

    ⛔ Không suy ra từ `media.detect_gpu_encoder()`. Hàm đó chỉ thử
    `h264_nvenc`/`h264_qsv`/`h264_amf` (xem `platform_core.media`), **không thử
    một `hevc_*` nào** — nên "h264_nvenc chạy ⇒ hevc_nvenc chạy" là một SUY LUẬN,
    và lớp driver/SKU nơi nó sai (card không có bộ mã hoá HEVC) là chính lớp ta
    cần biết. Ta gọi thẳng `media._test_encoder` (một encode 256x256, `-f null`)
    để có một phép ĐO.

    ⚠️ Vì sao chuyện này đáng một hàm riêng: `ffmpeg -encoders` trên máy
    production này LIỆT KÊ `h264_qsv`/`hevc_qsv`/`h264_amf`/`hevc_amf`, mà cả bốn
    **chết lúc chạy** ("Nothing was written into output file") — đo 2026-09-26.
    Một bản LIỆT KÊ năng lực ⛔ không bao giờ là một phép DÒ năng lực.
    """
    global _hevc_phan_cung
    if _hevc_phan_cung is None:
        from platform_core import media
        try:
            _hevc_phan_cung = bool(media._test_encoder("hevc_nvenc"))
        except Exception:  # noqa: BLE001 — dò lỗi = coi như KHÔNG có
            log.warning("[encoder] dò hevc_nvenc thất bại → coi như không có",
                        exc_info=True)
            _hevc_phan_cung = False
        log.info("[encoder] hevc_nvenc khả dụng: %s", _hevc_phan_cung)
    return _hevc_phan_cung


def _resolve_encoder(codec: Codec) -> str:
    """Encoder cho `codec`. **Mọi giá trị trả về đều được `ff._venc_args` hiểu.**

    ⭐ Đây là bất biến của chỗ nối này, và bản đầu vi phạm nó hai lần (ISSUE I/J,
    `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md`):

    - nó trả `h264_qsv` / `hevc_qsv` / `h264_amf` / `hevc_amf`, nhưng
      `ff._venc_args` chỉ nhận diện `*_nvenc` ⇒ bốn tên kia **rơi âm thầm** xuống
      `libx264`. Hợp đồng nói "hỗ trợ QSV/AMF", runtime thì không.
    - đường CPU trả chuỗi `"libx264"` **bỏ luôn tham số `codec`** ⇒ xin HEVC
      nhận H.264.

    Chốt 2026-09-26: app này hỗ trợ **NVENC hoặc CPU**, không QSV/AMF. `-encoders`
    liệt kê QSV/AMF nhưng cả bốn chết lúc chạy trên máy này (đo, xem
    `co_hevc_phan_cung`). `platform_core.media` vẫn dò ba loại cho các app khác —
    ta chỉ **không nhận** hai loại ta không nói được.

    ## ⛔ HEVC: có phần cứng thì làm, không có thì NÉM

    Bản sửa đầu trả `ENCODER_CPU[Codec.hevc]` = `libx265 -preset medium`. Đó là
    cách tệ thứ hai sau việc giao H.264 mà khai HEVC:

    - `libx265 -preset medium` ở 2160p là **hàng GIỜ CPU**, chậm hơn `libx264`
      nhiều lần, và CHƯA ĐO ở đây;
    - `platform_core.job_runner` giết worker bằng `os._exit(3)` ở
      `RUNTIME_LIMIT_S` (2 h) ⇒ `finally` của `handle` **không chạy** ⇒ rò thư
      mục tạm cỡ GB + tiến trình engine/ffmpeg mồ côi giữ GPU (ISSUE L, chưa sửa).

    Nên: phần cứng HEVC chạy được ⇒ dùng; không ⇒ `CodecKhongPhucVuDuoc` với câu
    nói rõ khách phải làm gì. ⛔ Không im lặng giao H.264 (mandate §17), ⛔ không
    im lặng đốt hàng giờ CPU. `libx265` vẫn còn trong `ff._venc_args` cho đường
    ngoại tuyến/benchmark.
    """
    from platform_core import media

    if codec == Codec.hevc:
        if co_hevc_phan_cung():
            return ENCODER[Codec.hevc]        # hevc_nvenc
        raise CodecKhongPhucVuDuoc(_t(
            "Máy đang chạy không có bộ mã hoá HEVC (H.265) bằng phần cứng, và "
            "mã hoá HEVC bằng CPU quá chậm cho dịch vụ này (có thể hàng giờ cho "
            "một video). Vui lòng chọn codec H.264 — cùng độ phân giải, cùng "
            "chất lượng hình, chỉ tệp lớn hơn một chút."))

    gpu = media.detect_gpu_encoder()      # "" | h264_nvenc | h264_qsv | h264_amf
    if gpu == "h264_nvenc":
        return ENCODER[Codec.h264]        # h264_nvenc
    if gpu in ("h264_qsv", "h264_amf"):
        # Có GPU encoder nhưng KHÔNG phải loại app này biết dựng tham số cho.
        # Nói ra, rồi đi đường CPU đúng codec — thà chậm mà đúng. (`libx264` ở
        # `-preset medium` là chi phí ĐÃ BIẾT, khác hẳn `libx265`.)
        log.info("[encoder] bỏ qua %s (app chỉ hỗ trợ NVENC/CPU) → CPU %s",
                 gpu, ENCODER_CPU[Codec.h264])
    return ENCODER_CPU[Codec.h264]        # libx264


def _fps_float(fps_str: str) -> float:
    """`"30"` / `"30000/1001"` → float. `0.0` nếu không đọc được."""
    try:
        if "/" in str(fps_str):
            num, den = str(fps_str).split("/", 1)
            return float(num) / float(den) if float(den) else 0.0
        return float(fps_str)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _thoi_luong_hua(n_frames: int, fps_out_str: str, co_audio: bool,
                    thoi_luong_nguon_s: float) -> float:
    """Thời lượng CONTAINER mà chuỗi encode hứa, giây. `0.0` = không dự đoán được.

    ⭐ Đây là "lời hứa" duy nhất mà `quality_gate` được so, và nó KHÔNG phải
    `eff_dur`. Bản sửa đầu truyền `eff_dur` (8 s cho preview) trong khi:

    - preview cắt **KHUNG** (`ff.extract_frames(max_seconds=…)`), nên phần video
      dài `n_frames / fps_out`;
    - `ff.encode_full` map audio bằng `-i <nguồn đầy đủ>` `-map 1:a:0 -c:a copy`,
      **không** `-t` trên input audio và **không** `-shortest`, nên luồng audio
      dài bằng nguồn (vd 265 s);
    - thời lượng container MP4 = luồng DÀI NHẤT ⇒ ~265 s, lệch 257 s so với 8 s.

    ⇒ mọi preview có tiếng ăn một `quality_warning` giả. Công thức đúng là chính
    ngữ nghĩa mux ở trên: `max(video, audio)` khi có audio, `video` khi không.
    (⛔ Cắt audio theo preview là một câu hỏi SẢN PHẨM, không phải việc của cổng
    kiểm — nên ở đây ta sửa KỲ VỌNG cho khớp hành vi, không đổi hành vi.)
    """
    fps = _fps_float(fps_out_str)
    if n_frames <= 0 or fps <= 0:
        return 0.0                        # không đoán ⇒ cổng bỏ qua phép này
    video_s = n_frames / fps
    if co_audio and thoi_luong_nguon_s > 0:
        return max(video_s, thoi_luong_nguon_s)
    return video_s


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
                         _t("nâng nét đoạn {0}/{1}…").format(bi + 1, n_batches))
        base = done_total
        status = engine.run_upscale(b_in, b_up, tune, len(batch),
                                    progress_cb=lambda d, _b=base: on_prog(_b + d),
                                    cancel_check=cancel_check,
                                    gpu_index=gpu_index, env=process_env)
        if status == "cancelled":
            raise ff.ProcessingCancelled(_t("Job đã được hủy."))
        if status == "timeout":
            raise RuntimeError(_t("Engine treo ở đoạn {0} (>5' không tiến triển).")
                              .format(bi + 1))
        if status != "done":
            raise RuntimeError(_t("Engine upscale đoạn {0} thất bại.").format(bi + 1))
        seg = os.path.join(seg_dir, f"seg_{bi:04d}.mp4")
        ff.encode_segment(b_up, seg, info["fps_str"], target_h, encoder,
                          cancel_check=cancel_check, env=process_env)
        segs.append(seg)
        done_total += len(batch)
        
        # Checkpoint after each batch.
        #
        # 🔴 Truoc 26/09 dong nay goi `checkpoint.save_checkpoint(job_id, ...)` — ma `job_id`
        #    KHONG ton tai trong ham nay (`ruff F821`). Tuc MOI luot upscale cham
        #    toi day chet bang `NameError`, va no KHONG nam sau mot nhanh phan cung
        #    nao ca. Ham co tham so `ctx` (`JobContext`), va `JobContext.job_id` la
        #    cho dung (`platform_core.job_runner.JobContext.job_id` — tra theo TEN,
        #    khong theo so dong).
        #
        # ⚠️ Va phai CANH `ctx is None`: ham nay duoc goi voi `ctx=None` o duong
        #    khong-co-job (xem `if ctx is not None: ctx.progress(...)` cung tep).
        #    Viet `ctx.job_id` tron chi doi `NameError` thanh `AttributeError`.
        # ⇒ Khong co job thi khong co gi de `resume`, nen BO QUA checkpoint la dung
        #   nghia — khong phai mot duong lui im lang.
        if ctx is not None:
            checkpoint.save_checkpoint(ctx.job_id, f"upscale_batch_{bi+1:03d}", {
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

    # ⭐ Chốt encoder TRƯỚC khi tiêu bất cứ thứ gì. `_resolve_encoder` NÉM khi
    #    khách xin HEVC mà máy không có phần cứng HEVC; nổ ở đây nghĩa là chưa
    #    tải nguồn, chưa giữ chỗ credit, chưa tách một khung nào. Bản trước gọi
    #    nó sau `extract_frames` — tức trả giá cho cả khâu tách khung rồi mới
    #    biết là không giao được.
    encoder = _resolve_encoder(codec)

    # Sweeper sổ tiến độ: MỘT lần mỗi tiến trình worker, không bao giờ ném.
    # Đây là caller THẬT của `checkpoint.don_so_cu` (trước 26/09 nó không có
    # caller nào, y hệt khuyết điểm ISSUE G mà nó được viết ra để chữa).
    checkpoint.don_so_cu_mot_lan()

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
    thanh_cong = False          # xem `finally`: quyết định sổ tiến độ sống hay chết
    try:
        if ctx is not None:
            ctx.progress(2, _t("tải video"))
        with storage.open(video_key) as src, open(tmp_video, "wb") as dst:
            while True:
                if cancel_check and cancel_check():
                    raise ff.ProcessingCancelled(_t("Job đã được hủy."))
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
            thanh_cong = True
            return {"video_key": out_key, "credit_cost": true_cost,
                    "duration_s": round(eff_dur, 1), "preset": preset.value,
                    "target_height": target_h}

        _guard_disk(info, frame_multiplier=2 if smooth_motion else 1)

        working_video = tmp_video
        if stabilize:
            if ctx is not None:
                ctx.progress(3, _t("phân tích và ổn định chuyển động…"))
            working_video = os.path.join(tmp, "stabilized.mp4")
            ff.stabilize_video(tmp_video, working_video,
                               max_seconds=_PREVIEW_SECONDS if preview else None,
                               cancel_check=cancel_check, env=process_env)

            # Checkpoint after stabilization
            checkpoint.save_checkpoint(job_id, "stabilize_completed", {
                "working_video": working_video,
            })

        if ctx is not None:
            ctx.progress(4, _t("tách frame"))
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
        checkpoint.save_checkpoint(job_id, "frame_extraction_completed", {
            "n_frames": n,
            "target_height": target_h,
            "preset": preset.value,
        })

        tune = autotune.pick(preset, info["w"], info["h"],
                             gpu_uuid=getattr(ctx, "gpu_uuid", ""))
        warning = tune.warning or ""
        if info.get("is_vfr"):
            warning = (_t("Nguồn VFR — đã chuẩn hoá CFR {0:.3f}fps. ")
                      .format(info['fps']) + warning).strip()
        if ctx is not None:
            ctx.progress(5, _t("nâng nét {0} (tile {1})…").format(tune.model, tune.tile))

        def on_prog(done: int) -> None:
            if ctx is not None:
                ctx.progress(min(88, 5 + int(83 * done / max(n, 1))), _t("nâng nét…"))

        if n <= _BATCH_SIZE:
            status = engine.run_upscale(in_dir, up_dir, tune, n, progress_cb=on_prog,
                                        cancel_check=cancel_check,
                                        gpu_index=gpu_index, env=process_env)
            if status == "cancelled":
                raise ff.ProcessingCancelled(_t("Job đã được hủy."))
            if status == "timeout":
                raise RuntimeError(_t("Engine treo (>5' không có frame mới). Thử lại."))
            if status != "done":
                raise RuntimeError(_t('Engine upscale thất bại (xem log).'))
            if ctx is not None:
                ctx.progress(90, _t("ghép video {0}p…").format(target_h))
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
                ctx.progress(92, _t("nối {0} đoạn + audio…").format(len(segs)))
            out_local = os.path.join(tmp, "out.mp4")
            ow, oh = ff.concat_and_mux(segs, tmp_video, out_local,
                                       info["has_audio"] and preserve_audio,
                                       cancel_check=cancel_check, env=process_env)

        # ⭐ Cổng KỸ THUẬT chạy TRƯỚC upload, trên tệp LOCAL.
        #    Trước đây thành công chỉ dựa `os.path.isfile()` (`ff.encode_full`/`encode_segment`/`concat_and_mux`)
        #    nên một đầu ra hỏng-mà-khác-rỗng vẫn báo SUCCEEDED và vẫn thu tiền.
        #    Đặt ở đây vì đây là chỗ DUY NHẤT đường dẫn thật còn tồn tại — sau
        #    upload chỉ còn khoá R2, và lẫn hai thứ đó là đúng lỗi của bản cũ.
        canh_bao_chat_luong = None
        do_ky_thuat = None
        co_audio = bool(info["has_audio"] and preserve_audio)
        if quality_gate.bat_cong():
            if ctx is not None:
                ctx.progress(95, _t("soi đầu ra…"))
            # ⭐ MỌI kỳ vọng dưới đây độc lập với `out_local`. Bản trước truyền
            #    `expect_w=ow, expect_h=oh` — mà `ow/oh` chính là
            #    `ff.probe_video(out_local)` do `encode_full`/`concat_and_mux`
            #    trả về ⇒ cổng so tệp với CHÍNH NÓ, không bao giờ đỏ được
            #    (ISSUE M vẫn mở trong khi mã khai là đã đóng). Nay: lời hứa =
            #    `target_h` khách xin + tỉ lệ của khung NGUỒN.
            ket = quality_gate.kiem_tra_dau_ra(
                out_local, target_h=target_h,
                src_w=info["w"], src_h=info["h"], expect_encoder=encoder,
                expect_audio=co_audio,
                expect_duration_s=_thoi_luong_hua(n, output_fps, co_audio,
                                                  info["duration"]),
                cancel_check=cancel_check, env=process_env)
            do_ky_thuat = ket["do"]
            for c in ket["canh_bao"]:
                log.warning("[cong-ky-thuat] %s", c)
            if not ket["ok"]:
                # ⛔ KHÔNG upload, KHÔNG thu tiền một tệp không mở được.
                raise RuntimeError(_t("Đầu ra không đạt kiểm kỹ thuật: {0}")
                                   .format("; ".join(ket["loi"])))
            if ket["canh_bao"]:
                canh_bao_chat_luong = "; ".join(ket["canh_bao"])
            log.info("[cong-ky-thuat] đạt: %s", do_ky_thuat)

        if ctx is not None:
            ctx.progress(96, _t("lưu kết quả"))
        with open(out_local, "rb") as f:
            storage.put(out_key, f, content_type="video/mp4")
        
        # Checkpoint output uploaded
        checkpoint.save_checkpoint(job_id, "output_uploaded", {
            "out_key": out_key,
        })
        
        # ⛔ Bỏ hẳn cổng PSNR/SSIM/VMAF cũ ở đây. Nó gọi `ffprobe` cho ba đại
        #    lượng chỉ `ffmpeg` tính được, không có video tham chiếu, truyền khoá
        #    R2 như đường dẫn local, và đọc cả MP4 vào RAM cho `PIL` — tức LUÔN
        #    thất bại, dán một cảnh báo giả lên MỌI job khách và trả tiền egress
        #    R2 cho không. Chất lượng MÔ HÌNH cần tham chiếu ⇒ thuộc `qualitylab`
        #    ngoại tuyến. Chi tiết: `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md`
        #    ISSUE H. Thay bằng cổng kỹ thuật local phía trên (trước upload).
        if ctx is not None:
            ctx.progress(100, "xong")
        res = {"video_key": out_key, "credit_cost": true_cost,
               "duration_s": round(eff_dur, 1), "preset": preset.value,
               "target_height": target_h, "out_w": ow, "out_h": oh,
               # ⭐ `codec` là codec THẬT của luồng, không phải cái khách XIN.
               #    Bản cũ ghi `codec.value` (enum yêu cầu) nên khi rơi về CPU
               #    nó trả `{"codec":"hevc","encoder":"libx264"}` — trường
               #    `codec` nói dối API/UI (ISSUE J). `codec_requested` giữ lại
               #    ý muốn của khách để đối soát được.
               "codec": quality_gate.HO_CODEC.get(encoder, codec.value),
               "codec_requested": codec.value, "encoder": encoder,
               "fps": _fps_float(output_fps),
               "has_audio": co_audio,
               "preserve_fps": preserve_fps, "preserve_audio": preserve_audio,
               "stabilize": stabilize, "smooth_motion": smooth_motion,
               "frames": n, "processing_seconds": round(time.monotonic() - started_clock, 2)}
        if do_ky_thuat:
            res["tech_gate"] = do_ky_thuat
        if warning:
            res["warning"] = warning
        # ⚠️ Cung thanh ngu voi `warning` ngay tren. Ban cu ghi
        #    `res["quality_warning"]` NGAY TRONG khoi cong chat luong, nhung `res`
        #    chi duoc tao ~4 dong BEN DUOI => `NameError` moi khi mot cong hong,
        #    tuc dung o duong LOI.
        if canh_bao_chat_luong:
            res["quality_warning"] = canh_bao_chat_luong
        thanh_cong = True
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        # ⭐ So tien do: XOA khi job THANH CONG, GIU LAI khi job LOI.
        #    `checkpoint.py` ton tai de nguoi van hanh soi duoc "job chet o
        #    chang nao". Ban truoc `rmtree` so o MOI duong ke ca duong ngoai le
        #    ⇒ tu huy dung luc can dung. Job tot thi khong ai can so cua no.
        #    So cua job loi duoc thu hoi boi `checkpoint.don_so_cu_mot_lan()`
        #    (goi o dau `handle`) trong `checkpoint.TTL_NGAY` ngay — do cung la
        #    duong thu hoi cho ca khi worker bi `os._exit()` luc het gio cung
        #    (`platform_core.job_runner`, hang `RUNTIME_LIMIT_S`) va `finally`
        #    nay KHONG he chay.
        if thanh_cong:
            try:
                checkpoint.cleanup_job_checkpoints(job_id)
            except Exception:  # noqa: BLE001 — don rac khong duoc lam do mot job tot
                log.warning("[so-tien-do] khong don duoc so cua job %s", job_id)
