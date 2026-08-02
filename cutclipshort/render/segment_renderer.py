"""Single segment renderer.

Takes a ClipSpec and produces a rendered video segment.
This is the atomic render unit — one ClipSpec → one .mp4 file.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cutclipshort.render.filter_chain import (
    build_audio_filters,
    build_video_filters,
)
from cutclipshort.types import ClipSpec, RenderSettings

logger = logging.getLogger(__name__)

# ── Resolution presets (width, height) for portrait shorts ──
_RESOLUTION_MAP: dict[str, tuple[int, int]] = {
    "1080p": (1080, 1920),
    "900p": (900, 1600),
    "720p": (720, 1280),
}


def _parse_audio_bitrate_kbps(bitrate_str: str) -> int:
    """Parse audio bitrate string like '192k' to integer kbps."""
    s = bitrate_str.lower().strip().rstrip("k")
    try:
        return int(s)
    except ValueError:
        return 192


def _calculate_max_bitrate_kbps(
    duration_sec: float,
    max_file_size_mb: float,
    audio_bitrate_kbps: int,
    safety_margin: float = 0.92,
) -> int:
    """Calculate max video bitrate (kbps) to fit within file size budget."""
    max_bits = max_file_size_mb * 8 * 1024 * 1024 * safety_margin
    audio_bits = audio_bitrate_kbps * 1000 * duration_sec
    video_bits = max_bits - audio_bits
    video_bitrate_kbps = int(video_bits / duration_sec / 1000)
    return max(1000, video_bitrate_kbps)


def _auto_select_resolution(video_bitrate_kbps: int, aspect_ratio: float) -> tuple[int, int]:
    """Select resolution based on available bitrate budget.

    For portrait (9:16) shorts viewed on mobile, 720p is still sharp.
    """
    if video_bitrate_kbps >= 8000:
        w, h = 1080, 1920
    elif video_bitrate_kbps >= 4000:
        w, h = 900, 1600
    else:
        w, h = 720, 1280

    if aspect_ratio > 1.0:
        w, h = h, w
    return w, h


def _resolve_target_resolution(
    render_settings: RenderSettings,
    clip: ClipSpec,
    video_bitrate_kbps: int,
) -> tuple[int, int]:
    """Resolve target width/height from settings or auto-selection."""
    res = render_settings.target_resolution

    if res == "auto":
        aspect = clip.target_width / clip.target_height if clip.target_height else 1.0
        return _auto_select_resolution(video_bitrate_kbps, aspect)

    if res in _RESOLUTION_MAP:
        w, h = _RESOLUTION_MAP[res]
        if clip.target_width > clip.target_height:
            w, h = h, w
        return w, h

    return clip.target_width, clip.target_height


def _resolve_codec(render_settings: RenderSettings, is_preview: bool) -> str:
    """Resolve actual ffmpeg codec name from settings."""
    if is_preview:
        return "libx264"

    if render_settings.video_codec == "h265":
        if render_settings.prefer_nvenc:
            return "hevc_nvenc"
        return "libx265"

    if render_settings.prefer_nvenc:
        from cutclipshort.adapters.ffmpeg_hw import FFmpegHWAdapter
        hw = FFmpegHWAdapter()
        return hw.best_encoder(prefer_hw=True)

    return "libx264"


def render_segment(
    clip: ClipSpec,
    source_path: Path,
    output_path: Path,
    render_settings: RenderSettings,
    is_preview: bool = False,
) -> Path:
    """Render a single clip segment to a video file.

    Args:
        clip: Complete render instruction.
        source_path: Path to source video.
        output_path: Where to write the output.
        render_settings: Encoding settings.
        is_preview: If True, use fast preview settings.

    Returns:
        Path to the rendered file.
    """
    from cutclipshort.adapters.ffmpeg import FFmpegAdapter

    ffmpeg = FFmpegAdapter()

    # ── Size control: compute bitrate budget ──
    duration_sec = clip.source_range.duration / clip.speed_factor if clip.speed_factor else clip.source_range.duration
    audio_kbps = _parse_audio_bitrate_kbps(render_settings.audio_bitrate)
    max_bitrate_str = ""
    bufsize_str = ""
    video_bitrate_kbps = 0

    if not is_preview and render_settings.size_control_enabled and duration_sec > 0:
        video_bitrate_kbps = _calculate_max_bitrate_kbps(
            duration_sec=duration_sec,
            max_file_size_mb=render_settings.max_file_size_mb,
            audio_bitrate_kbps=audio_kbps,
        )
        if render_settings.encoding_mode in ("crf_capped", "2pass_abr"):
            if render_settings.max_bitrate:
                max_bitrate_str = render_settings.max_bitrate
            else:
                max_bitrate_str = f"{video_bitrate_kbps}k"
            bufsize_str = render_settings.bufsize or f"{video_bitrate_kbps * 2}k"

        logger.info(
            "Size control: duration=%.1fs, budget=%dkbps video, maxrate=%s",
            duration_sec, video_bitrate_kbps, max_bitrate_str or "none",
        )

    # ── Resolution ──
    crf = getattr(render_settings, 'preview_crf', "28") if is_preview else render_settings.crf
    preset = "fast" if is_preview else render_settings.x264_preset

    if is_preview:
        target_w = 480
        target_h = int(target_w * clip.target_height / clip.target_width)
    elif render_settings.size_control_enabled and video_bitrate_kbps > 0:
        target_w, target_h = _resolve_target_resolution(
            render_settings, clip, video_bitrate_kbps,
        )
    else:
        target_w, target_h = clip.target_width, clip.target_height

    # Build crop dict from framing params
    crop = None
    if clip.primary_framing and clip.target_height > clip.target_width:
        # Probe REAL source dimensions so the crop rect is clamped to the
        # actual frame. Without this, _compute_crop falls back to estimating
        # source height as cy*2 (the person's vertical center), which can
        # exceed the real frame height — producing an out-of-bounds crop
        # (e.g. crop h=1206 on a 1080-tall source) → FFmpeg EINVAL (-22).
        # NOTE: probe()/get_media_info() live on FFprobeAdapter, NOT FFmpegAdapter.
        # The previous code called FFmpegAdapter().probe() which raised
        # AttributeError, was swallowed by the except below, and left src=0 —
        # so the clamp never happened and the EINVAL crop bug persisted.
        from cutclipshort.adapters.ffmpeg import FFprobeAdapter
        src_w = src_h = 0
        try:
            _pinfo = FFprobeAdapter().probe(source_path)
            for _st in _pinfo.get("streams", []):
                if _st.get("codec_type") == "video":
                    src_w = int(_st.get("width", 0) or 0)
                    src_h = int(_st.get("height", 0) or 0)
                    break
        except Exception as _e:
            logger.warning("Could not probe source dims for crop clamp: %s", _e)
        if src_w <= 0 or src_h <= 0:
            logger.warning(
                "Source dims unavailable for %s — crop may fall back to estimate; "
                "clamping disabled this pass", clip.clip_id,
            )
        crop = _compute_crop(clip, source_width=src_w, source_height=src_h)

    vf = build_video_filters(
        color_config=clip.color_config,
        speed_factor=clip.speed_factor,
        crop=crop,
        target_width=target_w,
        target_height=target_h,
    )

    # [C2] Caption/subtitle integration — ASS system (unified)
    if clip.caption_enabled and clip.caption_style and clip.caption_segments:
        try:
            from cutclipshort.render.caption_renderer import generate_ass_file

            style = clip.caption_style
            ass_path = output_path.parent / f"{clip.clip_id}_captions.ass"

            keyword_cats: tuple[str, ...] = ()
            if hasattr(clip, "_keyword_categories"):
                keyword_cats = clip._keyword_categories

            caption_language = ""
            if clip.caption_segments:
                caption_language = getattr(clip.caption_segments[0], "language", "") or ""

            generate_ass_file(
                segments=clip.caption_segments,
                style=style,
                output_path=ass_path,
                clip_start_offset=clip.source_range.start,
                target_width=target_w,
                target_height=target_h,
                keyword_categories=keyword_cats,
                language=caption_language,
                speed_factor=clip.speed_factor,
            )

            if ass_path.exists() and ass_path.stat().st_size > 0:
                safe_ass = ass_path.as_posix().replace(":", r"\:")
                ass_filter = f"ass='{safe_ass}'"
                if vf:
                    vf = f"{vf},{ass_filter}"
                else:
                    vf = ass_filter
                logger.info(
                    "Caption (ASS) config: preset=%s, font=%s %dpx, color=%s, "
                    "outline=%s/%dpx, position=%s, shadow=%s, bg_box=%s, "
                    "max_chars=%d, segments=%d, target=%dx%d, lang=%s",
                    style.preset_name, style.font_family, style.font_size,
                    style.font_color, style.outline_color, style.outline_width,
                    style.position, style.shadow_enabled, style.bg_box_enabled,
                    style.max_chars_per_line, len(clip.caption_segments),
                    target_w, target_h, caption_language or "unknown",
                )
        except Exception as e:
            logger.warning("Caption generation failed (rendering without captions): %s", e)

    af = build_audio_filters(
        speed_factor=clip.speed_factor,
        loudnorm_enabled=clip.audio_config.loudnorm_enabled,
        loudnorm_lufs=clip.audio_config.loudnorm_lufs,
        loudnorm_true_peak_db=clip.audio_config.loudnorm_true_peak_db,
    )

    # ── Determine encoder ──
    codec = _resolve_codec(render_settings, is_preview)
    if not is_preview and "nvenc" in codec:
        from cutclipshort.adapters.ffmpeg_hw import FFmpegHWAdapter
        hw = FFmpegHWAdapter()
        preset = hw.encoder_preset(codec)

    # ── FPS ──
    target_fps = 0.0 if is_preview else render_settings.target_fps

    logger.info(
        "Rendering clip %s: %.1f-%.1fs, %s, %dx%d, mode=%s",
        clip.clip_id, clip.source_range.start, clip.source_range.end,
        codec, target_w, target_h,
        render_settings.encoding_mode if render_settings.size_control_enabled else "crf",
    )

    # ── Encode ──
    try:
        if (not is_preview
                and render_settings.size_control_enabled
                and render_settings.encoding_mode == "2pass_abr"
                and video_bitrate_kbps > 0):
            ffmpeg.encode_2pass(
                input_path=source_path,
                output_path=output_path,
                target_bitrate=f"{video_bitrate_kbps}k",
                video_filters=vf,
                audio_filters=af,
                codec=codec,
                preset=preset,
                pixel_format=render_settings.pixel_format,
                audio_bitrate=render_settings.audio_bitrate,
                audio_sample_rate=render_settings.audio_sample_rate,
                audio_channels=render_settings.audio_channels,
                start_time=clip.source_range.start,
                duration=clip.source_range.duration,
                max_bitrate=max_bitrate_str,
                target_fps=target_fps,
            )
        else:
            ffmpeg.encode(
                input_path=source_path,
                output_path=output_path,
                video_filters=vf,
                audio_filters=af,
                codec=codec,
                crf=crf,
                preset=preset,
                pixel_format=render_settings.pixel_format,
                audio_bitrate=render_settings.audio_bitrate,
                audio_sample_rate=render_settings.audio_sample_rate,
                audio_channels=render_settings.audio_channels,
                start_time=clip.source_range.start,
                duration=clip.source_range.duration,
                max_bitrate=max_bitrate_str,
                bufsize=bufsize_str,
                target_fps=target_fps,
            )
    except Exception as e:
        logger.error(
            "Render clip %s thất bại: %s (codec=%s, %dx%d, %.1f-%.1fs)",
            clip.clip_id, e, codec, target_w, target_h,
            clip.source_range.start, clip.source_range.end,
            exc_info=True,
        )
        raise RuntimeError(
            f"Xuất clip {clip.clip_id} thất bại: {e}. "
            f"Codec: {codec}, Resolution: {target_w}x{target_h}. "
            f"Kiểm tra FFmpeg hỗ trợ codec này và đủ dung lượng ổ đĩa."
        ) from e

    # ── Post-render size verification ──
    if (not is_preview
            and render_settings.size_control_enabled
            and render_settings.auto_reencode_if_oversize):
        output_path = _verify_and_reencode(
            output_path=output_path,
            clip=clip,
            source_path=source_path,
            render_settings=render_settings,
            vf=vf,
            af=af,
            target_fps=target_fps,
        )

    logger.info("Segment rendered: %s (%.1f MB)", output_path.name,
                output_path.stat().st_size / (1024 * 1024))
    return output_path


def _verify_and_reencode(
    output_path: Path,
    clip: ClipSpec,
    source_path: Path,
    render_settings: RenderSettings,
    vf: str,
    af: str,
    target_fps: float,
    attempt: int = 0,
) -> Path:
    """Check file size and re-encode with tighter params if over budget."""
    actual_mb = output_path.stat().st_size / (1024 * 1024)
    max_mb = render_settings.max_file_size_mb

    if actual_mb <= max_mb:
        return output_path

    if attempt >= render_settings.max_reencode_attempts:
        logger.warning(
            "Clip %s vẫn %.1fMB sau %d lần re-encode (target %.1fMB)",
            clip.clip_id, actual_mb, attempt, max_mb,
        )
        return output_path

    from cutclipshort.adapters.ffmpeg import FFmpegAdapter
    ffmpeg = FFmpegAdapter()

    overshoot = actual_mb / max_mb
    new_crf = str(min(28, int(render_settings.crf) + 2 + attempt))

    duration_sec = clip.source_range.duration / clip.speed_factor if clip.speed_factor else clip.source_range.duration
    audio_kbps = _parse_audio_bitrate_kbps(render_settings.audio_bitrate)
    tighter_bitrate = _calculate_max_bitrate_kbps(
        duration_sec=duration_sec,
        max_file_size_mb=max_mb,
        audio_bitrate_kbps=audio_kbps,
        safety_margin=0.85 - (attempt * 0.05),
    )

    # Reduce resolution on second+ attempt
    target_w, target_h = clip.target_width, clip.target_height
    if attempt >= 1:
        target_w = max(720, int(target_w * 0.83))
        target_h = int(target_w * clip.target_height / clip.target_width)
        vf = build_video_filters(
            color_config=clip.color_config,
            speed_factor=clip.speed_factor,
            crop=None,
            target_width=target_w,
            target_height=target_h,
        )

    logger.info(
        "Re-encode attempt %d: %.1fMB > %.1fMB, CRF %s→%s, maxrate %dk, %dx%d",
        attempt + 1, actual_mb, max_mb, render_settings.crf, new_crf,
        tighter_bitrate, target_w, target_h,
    )

    codec = _resolve_codec(render_settings, is_preview=False)
    preset = render_settings.x264_preset
    if "nvenc" in codec:
        from cutclipshort.adapters.ffmpeg_hw import FFmpegHWAdapter
        preset = FFmpegHWAdapter().encoder_preset(codec)

    try:
        ffmpeg.encode(
            input_path=source_path,
            output_path=output_path,
            video_filters=vf,
            audio_filters=af,
            codec=codec,
            crf=new_crf,
            preset=preset,
            pixel_format=render_settings.pixel_format,
            audio_bitrate=render_settings.audio_bitrate,
            audio_sample_rate=render_settings.audio_sample_rate,
            audio_channels=render_settings.audio_channels,
            start_time=clip.source_range.start,
            duration=clip.source_range.duration,
            max_bitrate=f"{tighter_bitrate}k",
            bufsize=f"{tighter_bitrate * 2}k",
            target_fps=target_fps,
        )
    except Exception as e:
        logger.error("Re-encode attempt %d failed: %s", attempt + 1, e)
        return output_path

    return _verify_and_reencode(
        output_path=output_path,
        clip=clip,
        source_path=source_path,
        render_settings=render_settings,
        vf=vf,
        af=af,
        target_fps=target_fps,
        attempt=attempt + 1,
    )


def _compute_crop(
    clip: ClipSpec,
    source_width: int = 0,
    source_height: int = 0,
) -> dict[str, int] | None:
    """Compute FFmpeg crop params from framing.

    Args:
        clip: Render instruction with framing + target dimensions.
        source_width: Actual source video width (pixels).
        source_height: Actual source video height (pixels).

    Returns:
        FFmpeg crop dict {w, h, x, y} or None if no framing needed.
    """
    framing = clip.primary_framing
    if framing is None:
        return None

    target_ratio = clip.target_width / clip.target_height

    zoom = framing.zoom_start
    cx = framing.cx_start
    cy = framing.cy_start

    # Use actual source height, not hardcoded 1080
    src_h = source_height if source_height > 0 else int(cy * 2)
    src_w = source_width if source_width > 0 else int(cx * 2)

    crop_h = int(src_h / zoom)
    crop_w = int(crop_h * target_ratio)

    # Clamp to source boundaries
    crop_w = min(crop_w, src_w)
    crop_h = min(crop_h, src_h)

    crop_x = max(0, min(int(cx - crop_w / 2), src_w - crop_w))
    crop_y = max(0, min(int(cy - crop_h / 2), src_h - crop_h))

    return {"w": crop_w, "h": crop_h, "x": crop_x, "y": crop_y}
