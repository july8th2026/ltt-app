"""Project & app settings types.

Dependencies: base (AspectRatio), render (ClipSpec), editorial (EditConstraints)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cutclipshort.types.base import AspectRatio
from cutclipshort.types.render import ClipSpec


@dataclass(frozen=True)
class EditConstraints:
    """Platform and duration constraints for editorial."""
    min_clip_duration_sec: float = 15.0
    max_clip_duration_sec: float = 60.0
    target_clip_count: int = 5
    max_clip_count: int = 20
    platform: str = "tiktok"
    aspect_ratio: AspectRatio = AspectRatio.PORTRAIT_9_16
    target_width: int = 1080
    target_height: int = 1920
    additional_aspect_ratios: list[str] = field(default_factory=list)


@dataclass
class EditPlan:
    """The render contract — complete instructions for all clips."""
    plan_id: str
    version: int = 1
    strategy_name: str = ""
    genre: str = ""
    constraints: EditConstraints = field(default_factory=EditConstraints)
    clips: list[ClipSpec] = field(default_factory=list)
    created_at: str = ""
    modified_at: str = ""
    source_hash: str = ""
    analysis_versions: dict[str, str] = field(default_factory=dict)
    color_preset_name: str = "original"
    caption_preset_name: str = "minimal"
    user_modified_clip_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Project:
    """Top-level project entity."""
    project_id: str
    name: str
    project_dir: str
    source_video_path: str = ""
    source_hash: str = ""
    genre: str = "talking_head"
    quality_tier: str = "balanced"
    state: str = "idle"
    created_at: str = ""
    modified_at: str = ""
    clip_count: int = 0
    export_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterSettings:
    """External tool path settings."""
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    demucs_path: str = "demucs"


@dataclass(frozen=True)
class AnalysisSettings:
    """Analysis engine defaults."""
    whisper_model: str = "base"
    yolo_model: str = "yolov8n.pt"
    scene_threshold: float = 27.0


@dataclass(frozen=True)
class RenderDefaults:
    """Default render settings."""
    crf: str = "18"
    x264_preset: str = "medium"
    audio_bitrate: str = "192k"


@dataclass(frozen=True)
class UISettings:
    """GUI preferences."""
    theme: str = "light"
    sidebar_collapsed: bool = False
    recent_projects_max: int = 10


@dataclass(frozen=True)
class AppSettings:
    """Complete application settings."""
    adapters: AdapterSettings = field(default_factory=AdapterSettings)
    analysis: AnalysisSettings = field(default_factory=AnalysisSettings)
    render: RenderDefaults = field(default_factory=RenderDefaults)
    ui: UISettings = field(default_factory=UISettings)
