"""
Subtitle adapter — orchestrates transcript → subtitle file generation.

Delegates to core modules:
  - transcript_normalizer: clean raw input
  - segmenter: re-chunk for display
  - style_registry: resolve style config
  - ass_builder: generate ASS/SRT files

This adapter is the single entry point called by runner.py.
"""
from __future__ import annotations

import logging

from apps.autosubvideo.schemas import SubtitleStyleConfig
from apps.autosubvideo.transcript_normalizer import normalize, NormConfig
from apps.autosubvideo.segmenter import segment, SegmentConfig, SegmentMode
from apps.autosubvideo.style_registry import get_config, get_highlight_mode, get_highlight_color
from apps.autosubvideo.ass_builder import build_ass, build_srt
from apps.autosubvideo.font_checker import check_font_with_fallback

logger = logging.getLogger(__name__)


def generate_subtitle_files(
    *,
    transcript_data: list[dict],
    style_id: str = "default",
    custom_style: SubtitleStyleConfig | None = None,
    segment_mode: SegmentMode = "sentence",
    output_dir: str,
    base_name: str = "subtitle",
    video_width: int = 1920,
    video_height: int = 1080,
    export_ass: bool = True,
    export_srt: bool = True,
) -> dict[str, str]:
    """
    Full pipeline: raw transcript → normalized → segmented → ASS + SRT files.

    Returns dict with keys: "ass_path", "srt_path" (if exported),
                            "font_warning" (if font not available).
    """
    # 1. Normalize transcript
    style_config = custom_style or get_config(style_id)
    norm_config = NormConfig(
        max_duration=8.0,
        min_duration=0.8,
    )
    normalized = normalize(transcript_data, config=norm_config)
    logger.info("[subtitle_adapter] normalized %d → %d segments",
                len(transcript_data), len(normalized))

    # 2. Segment for display
    seg_config = SegmentConfig(
        mode=segment_mode,
        max_chars_per_line=style_config.max_chars_per_line,
        max_lines=getattr(style_config, "max_lines", 2),
    )
    events = segment(normalized, config=seg_config)
    logger.info("[subtitle_adapter] segmented → %d subtitle events (mode=%s)",
                len(events), segment_mode)

    if not events:
        raise RuntimeError(
            f"Transcript không tạo được subtitle events nào "
            f"(input={len(transcript_data)}, normalized={len(normalized)}, mode={segment_mode})"
        )

    # 2b. Font availability check
    font_check = check_font_with_fallback(
        style_config.font_family,
        getattr(style_config, "font_fallback", ""),
    )
    if font_check["warning"]:
        logger.warning("[subtitle_adapter] %s", font_check["warning"])
        # Update the style config to use the resolved (available) font
        style_config = style_config.model_copy(
            update={"font_family": font_check["resolved"]}
        )

    # 3. Generate files
    result: dict[str, str] = {}
    if font_check["warning"]:
        result["font_warning"] = font_check["warning"]
    # Extract highlight settings: prefer custom_style fields, fall back to preset registry
    if custom_style and hasattr(custom_style, 'highlight_mode') and custom_style.highlight_mode != "none":
        highlight_mode = custom_style.highlight_mode
        highlight_color = getattr(custom_style, 'highlight_color', '#FFD700')
    elif custom_style and hasattr(custom_style, 'highlight_mode'):
        highlight_mode = custom_style.highlight_mode
        highlight_color = getattr(custom_style, 'highlight_color', '#FFD700')
    else:
        highlight_mode = get_highlight_mode(style_id)
        highlight_color = get_highlight_color(style_id)

    # Extract keyword highlight settings
    keyword_highlights = getattr(custom_style, "keyword_highlights", []) if custom_style else []
    keyword_highlight_color = getattr(custom_style, "keyword_highlight_color", "#FF4444") if custom_style else "#FF4444"

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
        logger.info("[subtitle_adapter] ASS written: %s", ass_path)

    if export_srt:
        srt_path = f"{output_dir}/{base_name}.srt"
        build_srt(events=events, output_path=srt_path)
        result["srt_path"] = srt_path
        logger.info("[subtitle_adapter] SRT written: %s", srt_path)

    return result
