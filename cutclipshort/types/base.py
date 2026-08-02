"""Base domain primitives — shared across all layers.

These are the fundamental building blocks that every layer uses.
No dependencies on any other types module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


# ══════════════════════════════════════════════════════════════════════════
# ENUMS (cross-cutting)
# ══════════════════════════════════════════════════════════════════════════

class Genre(Enum):
    TALKING_HEAD = "talking_head"
    PODCAST = "podcast"
    INTERVIEW = "interview"
    HIGHLIGHT_REEL = "highlight_reel"
    STORYTELLING = "storytelling"
    COMEDY = "comedy"
    EDUCATION = "education"
    NEWS_COMMENTARY = "news_commentary"
    REVIEW = "review"
    NATURE = "nature"
    HISTORY = "history"
    ACTION = "action"
    KIDS_MUSIC = "kids_music"
    ANIMATION = "animation"


class ContentType(Enum):
    TALKING_HEAD = "talking_head"
    ACTION = "action"
    B_ROLL = "b_roll"
    MUSIC = "music"
    SILENCE = "silence"
    TRANSITION = "transition"
    SCREEN_SHARE = "screen_share"
    UNKNOWN = "unknown"


class AspectRatio(Enum):
    PORTRAIT_9_16 = "9:16"
    SQUARE_1_1 = "1:1"
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_4_5 = "4:5"


class JobState(Enum):
    IDLE = "idle"
    IMPORTING = "importing"
    ANALYZING = "analyzing"
    GENERATING_CANDIDATES = "generating_candidates"
    PREVIEW_RENDERING = "preview_rendering"
    AWAITING_REVIEW = "awaiting_review"
    FINAL_RENDERING = "final_rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisEngineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CACHED = "cached"


class RenderVariantType(Enum):
    PREVIEW = "preview"
    FINAL = "final"


class ClipIntent(Enum):
    """Legacy intent enum — use EditorialIntent from types.editorial instead.

    Kept for backward compatibility. Maps legacy values to new system.
    """
    HOOK = "hook"
    STORY = "story"
    PAYOFF = "payoff"
    SHOCK = "shock"
    INSIGHT = "insight"
    LOOP = "loop"
    VIRAL_MOMENT = "viral_moment"    # Legacy → SHOCK
    CONTROVERSIAL = "controversial"  # Legacy → SHOCK
    UNKNOWN = "unknown"


class NarrativeStage(Enum):
    INTRO = "intro"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    RESOLUTION = "resolution"


class RenderJobStatus(Enum):
    QUEUED = "queued"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ══════════════════════════════════════════════════════════════════════════
# DOMAIN PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TimeRange:
    """Immutable time interval in seconds."""
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def midpoint(self) -> float:
        return (self.start + self.end) / 2.0

    def overlaps(self, other: TimeRange) -> bool:
        return self.start < other.end and other.start < self.end

    def overlap_duration(self, other: TimeRange) -> float:
        overlap_start = max(self.start, other.start)
        overlap_end = min(self.end, other.end)
        return max(0.0, overlap_end - overlap_start)

    def contains(self, time_sec: float) -> bool:
        return self.start <= time_sec <= self.end

    def expand(self, padding_sec: float) -> TimeRange:
        return TimeRange(
            start=max(0.0, self.start - padding_sec),
            end=self.end + padding_sec,
        )


@dataclass(frozen=True)
class PersonDetection:
    """A detected person bounding box in a single frame."""
    x: float
    y: float
    w: float
    h: float
    confidence: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def area(self) -> float:
        return self.w * self.h

    @property
    def bbox_xyxy(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)
