"""Content completeness evaluator v2.

Checks hook presence, idea completeness, sentence boundary alignment,
and speech pacing quality.

v2 changes:
- Graduated boundary scoring (distance-based, not binary)
- WPM (words per minute) analysis for subtitle readability
- Hook quality scoring uses first 3 words, not just presence
- Filler word detection at opening
"""

from __future__ import annotations

import logging
from pathlib import Path

from cutclipshort.types import AnalysisResult, ClipSpec, EvalMetric

logger = logging.getLogger(__name__)

_FILLER_STARTERS = {"um", "uh", "so um", "like", "yeah so", "uh so", "like um"}
_IDEAL_WPM_MIN = 120
_IDEAL_WPM_MAX = 180


class ContentEvaluator:
    """Evaluates content quality, completeness, and readability."""

    @property
    def name(self) -> str:
        return "content_completeness"

    @property
    def weight(self) -> float:
        return 0.25

    def evaluate(
        self,
        rendered_path: Path,
        clip_spec: ClipSpec,
        analysis: AnalysisResult,
    ) -> EvalMetric:
        tr = clip_spec.source_range

        # Find transcript segments in range
        segments_in_range = [
            seg for seg in analysis.transcript
            if seg.time_range.overlaps(tr)
        ]

        if not segments_in_range:
            return EvalMetric(
                evaluator_name=self.name,
                score=0.5,
                weight=self.weight,
                passed=True,
                diagnostics={"note": "No transcript data for this range"},
            )

        # ── 1. Boundary alignment (graduated) ────────────────────────
        first_seg = segments_in_range[0]
        last_seg = segments_in_range[-1]

        start_dist = abs(first_seg.start - tr.start)
        end_dist = abs(last_seg.end - tr.end)

        # Smooth scoring based on distance from boundary
        start_boundary_score = _distance_to_score(start_dist, ideal=0.3, max_penalty=2.0)
        end_boundary_score = _distance_to_score(end_dist, ideal=0.5, max_penalty=3.0)
        boundary_score = start_boundary_score * 0.4 + end_boundary_score * 0.6

        # ── 2. Hook quality (first 3 seconds) ────────────────────────
        hook_end = tr.start + 3.0
        hook_segs = [
            seg for seg in segments_in_range
            if seg.start < hook_end and seg.end > tr.start
        ]

        if hook_segs:
            hook_text = " ".join(s.text.strip() for s in hook_segs).lower()
            first_words = hook_text.split()[:5]
            first_phrase = " ".join(first_words)

            # Check for filler starters
            has_filler = any(
                first_phrase.startswith(f) for f in _FILLER_STARTERS
            )

            if has_filler:
                hook_score = 0.35  # Filler at start = weak hook
            elif len(first_words) >= 3:
                hook_score = 0.9  # Strong opening
            else:
                hook_score = 0.7  # Some speech but brief
        else:
            hook_score = 0.3  # No speech in first 3s

        # ── 3. Speech coverage ────────────────────────────────────────
        speech_duration = sum(
            min(seg.end, tr.end) - max(seg.start, tr.start)
            for seg in segments_in_range
        )
        speech_ratio = speech_duration / tr.duration if tr.duration > 0 else 0

        if speech_ratio >= 0.7:
            speech_score = 1.0
        elif speech_ratio >= 0.5:
            speech_score = 0.8
        elif speech_ratio >= 0.3:
            speech_score = 0.6
        else:
            speech_score = max(0.2, speech_ratio * 2)

        # ── 4. WPM / readability ──────────────────────────────────────
        full_text = " ".join(s.text.strip() for s in segments_in_range)
        word_count = len(full_text.split())
        speech_minutes = speech_duration / 60.0 if speech_duration > 0 else 0
        wpm = word_count / speech_minutes if speech_minutes > 0.1 else 0

        if _IDEAL_WPM_MIN <= wpm <= _IDEAL_WPM_MAX:
            wpm_score = 1.0
        elif wpm > 0:
            mid = (_IDEAL_WPM_MIN + _IDEAL_WPM_MAX) / 2
            deviation = abs(wpm - mid) / mid
            wpm_score = max(0.3, 1.0 - deviation)
        else:
            wpm_score = 0.5  # No speech = neutral

        # ── Composite ─────────────────────────────────────────────────
        score = (
            boundary_score * 0.25
            + hook_score * 0.30
            + speech_score * 0.25
            + wpm_score * 0.20
        )
        passed = score >= 0.4

        return EvalMetric(
            evaluator_name=self.name,
            score=round(score, 3),
            weight=self.weight,
            passed=passed,
            diagnostics={
                "start_distance_sec": round(start_dist, 2),
                "end_distance_sec": round(end_dist, 2),
                "boundary_score": round(boundary_score, 3),
                "hook_score": round(hook_score, 3),
                "speech_ratio": round(speech_ratio, 3),
                "wpm": round(wpm, 0),
                "wpm_score": round(wpm_score, 3),
                "word_count": word_count,
                "has_filler_start": hook_segs and any(
                    " ".join(s.text.strip().lower().split()[:5]).startswith(f)
                    for s in hook_segs[:1] for f in _FILLER_STARTERS
                ),
                "transcript_segments_count": len(segments_in_range),
            },
        )


def _distance_to_score(
    distance: float, ideal: float, max_penalty: float,
) -> float:
    """Convert distance from boundary to score.

    <= ideal → 1.0
    >= max_penalty → 0.2
    Linear interpolation between
    """
    if distance <= ideal:
        return 1.0
    if distance >= max_penalty:
        return 0.2
    ratio = (distance - ideal) / (max_penalty - ideal)
    return max(0.2, 1.0 - ratio * 0.8)
