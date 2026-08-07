"""
Pydantic request / response schemas for auto_sub_video.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Transcript segment ───────────────────────────────────────────────────────

class TranscriptSegment(BaseModel):
    """Single segment from the uploaded transcript."""
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., gt=0, description="End time in seconds")
    text: str = Field(..., min_length=0)
    type: str = Field("speech", pattern=r"^(speech|silence)$")
    scene_id: str = ""
    index: int = Field(0, ge=0)


# ── Style config ─────────────────────────────────────────────────────────────

class SubtitleStyleConfig(BaseModel):
    """Subtitle styling options for burn-in render."""
    model_config = ConfigDict(extra="forbid")
    # Font
    font_family: str = Field("Arial", description="Font name")
    font_size: int = Field(48, ge=12, le=120, description="Font size in px")
    font_color: str = Field("#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$", description="Primary text color (hex)")
    bold: bool = True
    italic: bool = False
    font_fallback: str = Field(
        "Arial,Helvetica,sans-serif",
        description="Fallback font chain (comma-separated)",
    )

    # Outline & shadow
    outline_color: str = Field("#000000", pattern=r"^#[0-9A-Fa-f]{6}$", description="Outline/border color")
    outline_width: int = Field(2, ge=0, le=10)
    shadow_color: str = Field("#000000", pattern=r"^#[0-9A-Fa-f]{6}$", description="Shadow color")
    shadow_offset: int = Field(1, ge=0, le=10)

    # Position & spacing
    alignment: int = Field(2, ge=1, le=9, description="ASS alignment (numpad layout)")
    margin_v: int = Field(30, ge=0, le=200, description="Vertical margin from edge")
    margin_h: int = Field(20, ge=0, le=200, description="Horizontal margin")
    line_spacing: int = Field(0, ge=-20, le=40, description="Extra line spacing (px)")

    # Background box
    bg_box: bool = Field(False, description="Enable background box behind text")
    bg_color: str = Field("#000000", pattern=r"^#[0-9A-Fa-f]{6}$", description="Background box color")
    bg_opacity: float = Field(0.5, ge=0, le=1, description="Background box opacity")
    bg_padding: int = Field(10, ge=0, le=50, description="Background box padding (px)")

    # Safe area
    safe_area_percent: int = Field(
        0, ge=0, le=20,
        description="Safe area inset % — keeps subs away from edges (0=off, 10=10% inset)",
    )

    # Text layout
    max_chars_per_line: int = Field(42, ge=20, le=80)
    max_lines: int = Field(2, ge=1, le=4, description="Maximum number of display lines")

    # Highlight (karaoke) settings
    highlight_mode: str = Field(
        "none",
        pattern=r"^(none|word|bg_flash|underline|all_text|keyword)$",
        description="Highlight mode: none, word (karaoke), bg_flash, underline, all_text (全text accent), keyword (specific words)",
    )
    highlight_color: str = Field(
        "#FFD700",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Highlight accent color (hex)",
    )
    keyword_highlights: list[str] = Field(
        default_factory=list,
        description="List of keywords to highlight (used when highlight_mode='keyword')",
    )
    keyword_highlight_color: str = Field(
        "#FF4444",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Color for keyword highlights (hex)",
    )
    animation: Literal["none", "fade", "pop", "slide_up"] = "none"
    animation_ms: int = Field(default=180, ge=0, le=1000)


# ── Request models ───────────────────────────────────────────────────────────

class UploadRequest(BaseModel):
    """Metadata sent alongside file upload (multipart/form-data)."""
    pass


class RenderRequest(BaseModel):
    """Request to render video with burned-in subtitles."""
    upload_id: str = Field(..., description="ID returned from /upload")
    style_id: str = Field("default", description="Preset style ID or 'custom'")
    custom_style: Optional[SubtitleStyleConfig] = Field(
        None, description="Custom style (used when style_id='custom')"
    )
    segment_mode: str = Field("sentence", pattern=r"^(sentence|phrase|short_form|punchline|word_emphasis)$")
    export_srt: bool = Field(True, description="Also export .srt file")
    export_ass: bool = Field(True, description="Also export .ass file")
    output_format: str = Field("mp4", pattern=r"^(mp4|mkv|webm)$")
    quality: str = Field("standard", pattern=r"^(draft|standard|high)$", description="Render quality tier")
    # Bitrate control: "auto" = CRF-based, "match" = match source, or explicit e.g. "15M", "8000k"
    bitrate_mode: str = Field(
        "auto",
        pattern=r"^(auto|match|[0-9]+[kKmM])$",
        description="Bitrate mode: 'auto' (CRF), 'match' (source bitrate), or explicit like '15M'",
    )
    timeout: int = Field(600, ge=60, le=3600)


class PreviewRequest(BaseModel):
    """Request to render a short preview clip (5-10s)."""
    upload_id: str = Field(..., description="ID returned from /upload")
    style_id: str = Field("default", description="Preset style ID or 'custom'")
    custom_style: Optional[SubtitleStyleConfig] = None
    segment_mode: str = Field("sentence", pattern=r"^(sentence|phrase|short_form|punchline|word_emphasis)$")
    preview_duration: float = Field(8.0, ge=3.0, le=15.0, description="Preview clip length (s)")
    output_format: str = Field("mp4", pattern=r"^(mp4|mkv|webm)$")


# ── Response models ──────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    upload_id: str
    video_filename: str
    video_duration_s: float = 0.0
    video_bitrate_kbps: int = 0
    video_resolution: str = ""
    transcript_segments: int = 0
    validation: dict = {}
    status: str = "ready"


class StylePreset(BaseModel):
    id: str
    label: str
    description: str = ""
    config: Optional[SubtitleStyleConfig] = None
    highlight_mode: str = "none"
    highlight_color: str = "#FFD700"


class StyleListResponse(BaseModel):
    styles: list[StylePreset]


class RenderJobResponse(BaseModel):
    job_id: str
    status: str = "queued"


class PreviewJobResponse(BaseModel):
    job_id: str
    status: str = "queued"
    preview_duration: float = 8.0


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # "queued" | "rendering" | "completed" | "error" | "cancelled"
    mode: str = "full"  # "full" | "preview"
    progress: float = 0.0
    step: str = ""
    elapsed_s: float = 0.0
    output_video_url: Optional[str] = None
    output_srt_url: Optional[str] = None
    output_ass_url: Optional[str] = None
    error: Optional[str] = None


# ── Studio project schema v1 (Q49/Q50) ──────────────────────────────────────

class StudioWord(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def timing(self):
        if self.end <= self.start:
            raise ValueError(_t('word end phải lớn hơn start'))
        return self


class StudioCue(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(max_length=4000)
    speaker: str = Field(default="", max_length=80)
    words: list[StudioWord] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def timing(self):
        if self.end <= self.start:
            raise ValueError(_t('cue end phải lớn hơn start'))
        if any(word.start < self.start or word.end > self.end for word in self.words):
            raise ValueError(_t('word timing phải nằm trong cue'))
        return self


class StudioTrack(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    kind: Literal["source", "translation", "custom"] = "source"
    language: str = Field(default="vi", min_length=2, max_length=24)
    name: str = Field(default="Phụ đề", min_length=1, max_length=120)
    visible: bool = True
    z_index: int = Field(default=0, ge=0, le=99)
    style_id: str = Field(default="default", min_length=1, max_length=64)
    cues: list[StudioCue] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def unique_cues(self):
        ids = [cue.id for cue in self.cues]
        if len(ids) != len(set(ids)):
            raise ValueError(_t('cue id bị trùng trong track'))
        return self


class StudioSource(BaseModel):
    key: str = Field(default="", max_length=1000)
    filename: str = Field(default="", max_length=255)
    duration_s: float = Field(default=0, ge=0, le=86400)
    width: int = Field(default=0, ge=0, le=16384)
    height: int = Field(default=0, ge=0, le=16384)


class StudioOutput(BaseModel):
    resolution: Literal["source", "720p", "1080p", "4k"] = "source"
    format: Literal["mp4", "mkv", "webm"] = "mp4"
    quality: Literal["draft", "standard", "high"] = "standard"
    track_ids: list[str] = Field(default_factory=list, max_length=32)
    export_srt: bool = True
    export_vtt: bool = True
    export_json: bool = True
    export_ass: bool = True
    bundle_zip: bool = True


class StudioStyle(SubtitleStyleConfig):
    preset: str = Field(default="default", min_length=1, max_length=64)


class StudioProjectV1(BaseModel):
    schema_version: Literal[1] = 1
    active_step: Literal["upload", "transcript", "style", "render"] = "upload"
    source: StudioSource = Field(default_factory=StudioSource)
    tracks: list[StudioTrack] = Field(default_factory=list, max_length=32)
    speakers: dict[str, str] = Field(default_factory=dict, max_length=100)
    style: StudioStyle = Field(default_factory=StudioStyle)
    output: StudioOutput = Field(default_factory=StudioOutput)

    @model_validator(mode="after")
    def track_invariants(self):
        ids = [track.id for track in self.tracks]
        if len(ids) != len(set(ids)):
            raise ValueError(_t('track id bị trùng'))
        visible_z = [track.z_index for track in self.tracks if track.visible]
        if len(visible_z) != len(set(visible_z)):
            raise ValueError(_t('z_index của track đang hiện bị trùng'))
        cue_ids = [cue.id for track in self.tracks for cue in track.cues]
        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError(_t('cue id phải duy nhất toàn project'))
        if any(not key or len(key) > 80 or len(value.strip()) > 80
               for key, value in self.speakers.items()):
            raise ValueError(_t('speaker id/tên hiển thị không hợp lệ'))
        return self


def empty_studio_project() -> dict:
    return StudioProjectV1().model_dump(mode="json")
