"""Pacing evaluator v2.

Measures duration fitness, speed consistency, and actual rendered duration.

v2 changes:
- Graduated duration scoring (smooth curve, not step function)
- Probes actual rendered duration to verify render correctness
- Speed scoring is graduated (not binary 0.7/1.0)
- Platform-aware duration ranges
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from cutclipshort.types import AnalysisResult, ClipSpec, EvalMetric

logger = logging.getLogger(__name__)

# Platform-optimal duration ranges (seconds)
_PLATFORM_RANGES = {
    "9:16": (15, 60),   # TikTok/Shorts/Reels: 15-60s ideal
    "1:1": (15, 60),    # Instagram: similar
    "16:9": (30, 120),  # YouTube: longer OK
    "4:5": (15, 60),    # Instagram portrait
}
_DEFAULT_RANGE = (15, 60)
_SWEET_SPOT = (20, 45)  # Universal sweet spot


class PacingEvaluator:
    """Evaluates clip pacing, duration quality, and speed consistency."""

    @property
    def name(self) -> str:
        return "pacing"

    @property
    def weight(self) -> float:
        return 0.20

    def evaluate(
        self,
        rendered_path: Path,
        clip_spec: ClipSpec,
        analysis: AnalysisResult,
    ) -> EvalMetric:
        source_duration = clip_spec.source_range.duration
        speed = clip_spec.speed_factor
        effective_duration = source_duration / speed if speed > 0 else source_duration

        # Try to verify actual rendered duration
        actual_duration = _probe_duration(rendered_path)
        duration_mismatch = False
        if actual_duration is not None and actual_duration > 0:
            expected = effective_duration
            if abs(actual_duration - expected) > 1.0:
                duration_mismatch = True

        # Get platform range
        ar_str = clip_spec.primary_aspect_ratio.value
        plat_min, plat_max = _PLATFORM_RANGES.get(ar_str, _DEFAULT_RANGE)

        # 1. Duration fitness: smooth gaussian-like scoring
        dur_score = _score_duration(effective_duration, plat_min, plat_max)

        # 2. Speed naturalness: graduated penalty
        speed_score = _score_speed(speed)

        # 3. Render accuracy penalty
        render_penalty = 0.1 if duration_mismatch else 0.0

        score = max(0.0, min(1.0,
            dur_score * 0.60
            + speed_score * 0.35
            + 0.05  # Base for existence
            - render_penalty
        ))

        passed = score >= 0.4

        return EvalMetric(
            evaluator_name=self.name,
            score=round(score, 3),
            weight=self.weight,
            passed=passed,
            diagnostics={
                "source_duration_sec": round(source_duration, 1),
                "effective_duration_sec": round(effective_duration, 1),
                "actual_duration_sec": round(actual_duration, 1) if actual_duration else None,
                "duration_mismatch": duration_mismatch,
                "speed_factor": speed,
                "platform_range": f"{plat_min}-{plat_max}s",
                "duration_score": round(dur_score, 3),
                "speed_score": round(speed_score, 3),
            },
        )


def _score_duration(duration: float, plat_min: float, plat_max: float) -> float:
    """Graduated duration scoring with smooth falloff.

    Sweet spot (20-45s) = 1.0
    Platform range = 0.7-1.0
    Outside range = gradual decay
    """
    sweet_min, sweet_max = _SWEET_SPOT

    if sweet_min <= duration <= sweet_max:
        return 1.0

    if plat_min <= duration <= plat_max:
        # Inside platform range but outside sweet spot
        if duration < sweet_min:
            return 0.7 + 0.3 * (duration - plat_min) / (sweet_min - plat_min)
        else:
            return 0.7 + 0.3 * (plat_max - duration) / (plat_max - sweet_max)

    # Outside platform range: smooth decay
    if duration < plat_min:
        ratio = duration / plat_min if plat_min > 0 else 0
        return max(0.1, 0.7 * ratio)

    # Too long
    excess = (duration - plat_max) / plat_max
    return max(0.2, 0.7 - excess * 0.5)


def _score_speed(speed: float) -> float:
    """Graduated speed scoring.

    1.0x = perfect
    0.9-1.1x = excellent (0.95)
    0.75-1.25x = good (0.75)
    Beyond = declining
    """
    deviation = abs(speed - 1.0)

    if deviation <= 0.05:
        return 1.0
    if deviation <= 0.1:
        return 0.95
    if deviation <= 0.25:
        return 0.75
    if deviation <= 0.5:
        return 0.5
    return max(0.2, 1.0 - deviation)


def _probe_duration(rendered_path: Path) -> float | None:
    """Get actual duration of rendered file via ffprobe."""
    if not rendered_path.exists():
        return None
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(rendered_path),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, OSError):
        return None
