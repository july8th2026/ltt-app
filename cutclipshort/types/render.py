"""Render layer types — render specs, framing, captions, export.

Dependencies: base (TimeRange, AspectRatio, RenderVariantType)
              analysis (TranscriptSegment)
Consumed by: render, export workers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cutclipshort.types.base import (
    AspectRatio,
    RenderJobStatus,
    RenderVariantType,
    TimeRange,
)
from cutclipshort.types.analysis import TranscriptSegment


@dataclass(frozen=True)
class FramingParams:
    """Pan/zoom framing for a single clip."""
    cx_start: float = 0.5
    cy_start: float = 0.5
    cx_end: float = 0.5
    cy_end: float = 0.5
    zoom_start: float = 1.0
    zoom_end: float = 1.0
    smooth_alpha: float = 0.07
    max_pan_px_per_sec: float = 900.0
    person_target_fraction: float = 0.70


@dataclass(frozen=True)
class AudioConfig:
    """Audio processing config for a clip."""
    demucs_enabled: bool = False
    demucs_model: str = "htdemucs"
    stem_gains: dict[str, float] = field(default_factory=lambda: {
        "vocals": 1.0, "drums": 0.0, "bass": 0.0, "other": 0.3,
    })
    loudnorm_enabled: bool = True
    loudnorm_lufs: float = -14.0
    loudnorm_true_peak_db: float = -1.5
    sfx_path: str | None = None
    sfx_gain_db: float = -6.0
    sfx_position: str = "start"


@dataclass(frozen=True)
class CaptionStyle:
    """Subtitle style configuration."""
    preset_name: str = "minimal"
    font_family: str = "Inter"
    font_size: int = 48
    font_color: str = "#FFFFFF"
    active_word_color: str = "#FFDD00"
    outline_color: str = "#000000"
    outline_width: int = 2
    shadow_enabled: bool = True
    shadow_color: str = "#00000080"
    bg_box_enabled: bool = False
    bg_box_color: str = "#00000099"
    position: str = "bottom"
    animation: str = "none"
    max_chars_per_line: int = 35


@dataclass(frozen=True)
class ClipSpec:
    """Complete render instruction for ONE clip."""
    clip_id: str
    source_range: TimeRange
    speed_factor: float = 1.0
    color_preset_name: str = "original"
    color_config: dict[str, Any] = field(default_factory=dict)
    primary_aspect_ratio: AspectRatio = AspectRatio.PORTRAIT_9_16
    primary_framing: FramingParams | None = None
    framing_variants: dict[str, FramingParams] = field(default_factory=dict)
    target_width: int = 1080
    target_height: int = 1920
    audio_config: AudioConfig = field(default_factory=AudioConfig)
    caption_enabled: bool = False
    caption_style: CaptionStyle | None = None
    caption_segments: list[TranscriptSegment] = field(default_factory=list)
    render_hash: str = ""


@dataclass(frozen=True)
class RenderSettings:
    """Global render settings from profile."""
    prefer_nvenc: bool = True
    nvenc_preset: str = "p4"
    x264_preset: str = "medium"
    crf: str = "20"
    pixel_format: str = "yuv420p"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    audio_sample_rate: int = 44100
    audio_channels: int = 2

    # Size control
    size_control_enabled: bool = True
    max_file_size_mb: float = 95.0
    encoding_mode: str = "crf_capped"  # "crf" | "crf_capped" | "2pass_abr"
    max_bitrate: str = ""  # VBV maxrate e.g. "10M", empty = auto
    bufsize: str = ""  # VBV bufsize e.g. "20M", empty = 2x maxrate

    # Resolution & FPS
    target_resolution: str = "1080p"  # "1080p" | "900p" | "720p" | "auto"
    target_fps: float = 30.0

    # Codec
    video_codec: str = "h264"  # "h264" | "h265"

    # Re-encode safety net
    auto_reencode_if_oversize: bool = True
    max_reencode_attempts: int = 2


@dataclass(frozen=True)
class RenderVariant:
    """Metadata for one rendered variant of a clip."""
    variant_id: str
    variant_type: RenderVariantType
    clip_id: str
    output_path: str
    render_hash: str
    elapsed_sec: float = 0.0
    output_size_bytes: int = 0
    created_at: str = ""


@dataclass
class RenderJob:
    """A render job tracking multiple clip renders."""
    job_id: str
    status: RenderJobStatus = RenderJobStatus.QUEUED
    clips_total: int = 0
    clips_completed: int = 0
    clips_failed: int = 0
    started_at: str = ""
    completed_at: str = ""
    variants: list[RenderVariant] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExportProfile:
    """Platform export profile."""
    name: str
    display_name: str
    aspect_ratio: AspectRatio
    width: int
    height: int
    max_duration_sec: float
    render_settings: RenderSettings = field(default_factory=RenderSettings)
    recommended_fps: float = 30.0
    max_file_size_mb: float = 0.0
    notes: str = ""


@dataclass(frozen=True)
class ExportedClip:
    """Metadata for one exported clip."""
    candidate_id: str
    variant_id: str
    profile_name: str
    output_path: str
    duration_sec: float = 0.0
    file_size_bytes: int = 0
    composite_score: float = 0.0
    exported_at: str = ""


@dataclass(frozen=True)
class ExportManifest:
    """Record of an export batch."""
    manifest_id: str
    timestamp: str
    profile_name: str
    source_hash: str
    clips: list[ExportedClip] = field(default_factory=list)
    total: int = 0
    successful: int = 0
    failed: int = 0
    elapsed_sec: float = 0.0
