"""
Subtitle pipeline — orchestrates transcript → subtitle file generation.

Delegates to core modules:
  - normalizer: clean raw input
  - segmenter: re-chunk for display
  - style_registry: resolve style config
  - ass_builder: generate ASS/SRT files
  - font_checker: verify font availability
  - burner: FFmpeg burn-in

This is the single entry point called by engine/runner.py.

Extracted from BOT GEMINI auto_sub_video/adapters/subtitle_adapter.py.
"""
from __future__ import annotations

import logging
from typing import Optional

from .schemas import SubtitleStyleConfig
from .normalizer import normalize, NormConfig
from .segmenter import segment, SegmentConfig, SegmentMode
from .style_registry import get_config, get_highlight_mode, get_highlight_color
from .ass_builder import build_ass, build_srt
from .font_checker import check_font_with_fallback
from .burner import burn_subtitles, probe_video

logger = logging.getLogger(__name__)


def generate_subtitle_files(
    *,
    transcript_data: list[dict],
    style_id: str = "default",
    custom_style: Optional[SubtitleStyleConfig] = None,
    segment_mode: SegmentMode = "sentence",
    output_dir: str,
    base_name: str = "subtitle",
    video_width: int = 1920,
    video_height: int = 1080,
    export_ass: bool = True,
    export_srt: bool = True,
    segment_timing: Optional[list[dict]] = None,
) -> dict[str, str]:
    """
    Full pipeline: raw transcript → normalized → segmented → ASS + SRT files.

    Args:
        segment_timing: Optional list from segment_timing.json (video assembly).
            If provided, transcript timestamps are remapped from voice timeline
            to actual video cumulative positions before normalization.

    Returns dict with keys: "ass_path", "srt_path" (if exported),
                            "font_warning" (if font not available).
    """
    # 0. Remap timestamps to video timeline (if timing data available)
    if segment_timing:
        transcript_data = _remap_to_video_timeline(transcript_data, segment_timing)
        logger.info("[subtitle_pipeline] remapped %d segments to video timeline", len(transcript_data))

    # 1. Normalize transcript
    style_config = custom_style or get_config(style_id)
    norm_config = NormConfig(
        max_duration=8.0,
        min_duration=0.8,
    )
    normalized = normalize(transcript_data, config=norm_config)
    logger.info("[subtitle_pipeline] normalized %d -> %d segments",
                len(transcript_data), len(normalized))

    # 2. Segment for display
    seg_config = SegmentConfig(
        mode=segment_mode,
        max_chars_per_line=style_config.max_chars_per_line,
        max_lines=getattr(style_config, "max_lines", 2),
    )
    events = segment(normalized, config=seg_config)
    logger.info("[subtitle_pipeline] segmented -> %d subtitle events (mode=%s)",
                len(events), segment_mode)

    if not events:
        raise RuntimeError(
            f"Transcript produced no subtitle events "
            f"(input={len(transcript_data)}, normalized={len(normalized)}, mode={segment_mode})"
        )

    # 2b. Font availability check
    font_check = check_font_with_fallback(
        style_config.font_family,
        getattr(style_config, "font_fallback", ""),
    )
    if font_check["warning"]:
        logger.warning("[subtitle_pipeline] %s", font_check["warning"])
        # Update the style config to use the resolved (available) font
        style_config = style_config.copy_with(
            font_family=font_check["resolved"]
        )

    # 3. Generate files
    result: dict[str, str] = {"event_count": str(len(events))}
    if font_check["warning"]:
        result["font_warning"] = font_check["warning"]

    # Extract highlight settings: custom_style fields take priority, then preset registry
    if custom_style:
        highlight_mode = custom_style.highlight_mode
        highlight_color = custom_style.highlight_color
        keyword_highlights = custom_style.keyword_highlights or []
        keyword_highlight_color = custom_style.keyword_highlight_color or "#FF4444"
    else:
        highlight_mode = get_highlight_mode(style_id)
        highlight_color = get_highlight_color(style_id)
        keyword_highlights = []
        keyword_highlight_color = "#FF4444"

    if export_ass:
        ass_path = f"{output_dir}/{base_name}.ass"
        build_ass(
            events=events,
            style=style_config,
            output_path=ass_path,
            video_width=video_width,
            video_height=video_height,
            highlight_mode=highlight_mode,
            highlight_color=highlight_color,
            keyword_highlights=keyword_highlights,
            keyword_highlight_color=keyword_highlight_color,
        )
        result["ass_path"] = ass_path
        logger.info("[subtitle_pipeline] ASS written: %s", ass_path)

    if export_srt:
        srt_path = f"{output_dir}/{base_name}.srt"
        build_srt(events=events, output_path=srt_path)
        result["srt_path"] = srt_path
        logger.info("[subtitle_pipeline] SRT written: %s", srt_path)

    return result


# ── Internal helpers ────────────────────────────────────────────────────────

def _remap_to_video_timeline(
    transcript_data: list[dict],
    segment_timing: list[dict],
) -> list[dict]:
    """Remap transcript timestamps from voice timeline to video cumulative positions.

    Voice timestamps come from Whisper (relative to the voice WAV file).
    Video positions come from segment_timing.json (cumulative after assembly).

    Uses scene_id as primary key, index as fallback.
    """
    # Build lookup: scene_id → timing entry
    timing_by_scene: dict[str, dict] = {}
    for st in segment_timing:
        sid = st.get("scene_id", "")
        if sid:
            timing_by_scene[sid] = st

    # Fallback: index-based lookup
    timing_by_index: dict[int, dict] = {st["index"]: st for st in segment_timing}

    remapped: list[dict] = []
    mapped_count = 0
    for seg in transcript_data:
        seg = dict(seg)  # Don't mutate original
        scene_id = seg.get("scene_id", "")
        idx = seg.get("index", 0) - 1  # transcript is 1-based, timing is 0-based

        timing = timing_by_scene.get(scene_id) or timing_by_index.get(idx)
        if timing:
            seg["start"] = timing["video_start"]
            seg["end"] = timing["video_end"]
            mapped_count += 1
        remapped.append(seg)

    if mapped_count < len(transcript_data):
        logger.warning(
            "[subtitle_pipeline] remap: %d/%d segments mapped (some had no timing match)",
            mapped_count, len(transcript_data),
        )

    return remapped
