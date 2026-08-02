"""Analysis layer types — what the analysis engines produce.

Dependencies: base (TimeRange, PersonDetection, ContentType)
Consumed by: editorial, evaluation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cutclipshort.types.base import (
    ContentType,
    PersonDetection,
    TimeRange,
)


@dataclass(frozen=True)
class SourceAsset:
    """Complete metadata about the imported source video."""
    original_path: str
    source_hash: str
    file_name: str
    file_size_bytes: int
    duration_sec: float
    width: int
    height: int
    fps: float
    video_codec: str
    pixel_format: str
    bitrate_kbps: int
    audio_codec: str
    audio_sample_rate: int
    audio_channels: int
    audio_bitrate_kbps: int

    @property
    def aspect_ratio_float(self) -> float:
        return self.width / self.height if self.height > 0 else 0.0

    @property
    def is_portrait(self) -> bool:
        return self.height > self.width

    @property
    def total_frames(self) -> int:
        return int(self.duration_sec * self.fps)


@dataclass(frozen=True)
class TranscriptWord:
    """A single word with timestamp from speech-to-text."""
    word: str
    start: float
    end: float
    confidence: float


@dataclass(frozen=True)
class TranscriptSegment:
    """A transcript segment (sentence/phrase) with word-level timing."""
    id: int
    start: float
    end: float
    text: str
    words: list[TranscriptWord] = field(default_factory=list)
    speaker: str | None = None
    language: str = "en"

    @property
    def time_range(self) -> TimeRange:
        return TimeRange(start=self.start, end=self.end)

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass(frozen=True)
class SceneInfo:
    """A detected scene/shot with motion data."""
    id: int
    time_range: TimeRange
    motion_avg: float = 0.0
    motion_max: float = 0.0
    content_type: ContentType = ContentType.UNKNOWN
    content_type_confidence: float = 0.0
    dominant_person_bbox: PersonDetection | None = None


@dataclass(frozen=True)
class SceneDetections:
    """YOLO detections for a single scene."""
    scene_id: int
    time_sec: float
    persons: list[PersonDetection] = field(default_factory=list)


@dataclass(frozen=True)
class VisualSegment:
    """Enriched visual analysis combining scene + YOLO + motion."""
    id: int
    time_range: TimeRange
    scene_id: int
    content_type: ContentType
    content_type_confidence: float
    motion_avg: float
    motion_max: float
    motion_trend: str = "stable"
    has_person: bool = False
    person_count_max: int = 0
    person_bbox_start: PersonDetection | None = None
    person_bbox_end: PersonDetection | None = None
    is_static: bool = False
    has_text_overlay: bool = False


@dataclass(frozen=True)
class AudioSegment:
    """Audio analysis for a time range."""
    id: int
    time_range: TimeRange
    energy_avg: float
    energy_max: float
    energy_trend: str = "stable"
    has_speech: bool = True
    has_music: bool = False
    has_silence: bool = False
    silence_ratio: float = 0.0
    loudness_lufs: float = -14.0
    true_peak_db: float = -1.5
    speech_pace_wpm: float = 0.0


@dataclass(frozen=True)
class AnalysisResult:
    """Aggregated output of ALL analysis engines."""
    source: SourceAsset
    scenes: list[SceneInfo]
    visual_segments: list[VisualSegment]
    audio_segments: list[AudioSegment]
    transcript: list[TranscriptSegment]
    engine_versions: dict[str, str]
    engine_config_hashes: dict[str, str]
    analysis_completed_at: str
