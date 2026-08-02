"""Opening strength evaluator — scores the first 3 seconds of the clip.

Checks: speech presence, filler words, energy level, hook text quality.
This evaluator works on analysis data (no rendered file needed).
"""

from __future__ import annotations

import re
from pathlib import Path

from cutclipshort.types import AnalysisResult, ClipSpec, EvalMetric

_HOOK_WINDOW = 3.0
_ENERGY_BASELINE = 0.15  # Normalized energy considered "normal" opening energy
_FILLER_STARTERS = {"um", "uh", "so um", "like", "yeah so", "uh so", "like um", "okay so um"}


class OpeningEvaluator:
    """Evaluates the first 3 seconds of a clip for hook strength."""

    @property
    def name(self) -> str:
        return "opening_strength"

    @property
    def weight(self) -> float:
        return 0.15

    def evaluate(
        self, rendered_path: Path, clip_spec: ClipSpec, analysis: AnalysisResult,
    ) -> EvalMetric:
        tr = clip_spec.source_range
        hook_end = tr.start + _HOOK_WINDOW

        # Get transcript in hook window
        hook_segs = [
            s for s in analysis.transcript
            if s.start < hook_end and s.end > tr.start
        ]

        if not hook_segs:
            # No speech in first 3s
            return EvalMetric(
                evaluator_name=self.name, score=0.25, weight=self.weight,
                passed=False,
                diagnostics={"reason": "No speech in first 3 seconds", "has_hook": False},
            )

        hook_text = " ".join(s.text.strip() for s in hook_segs).lower()
        first_words = hook_text.split()[:6]
        first_phrase = " ".join(first_words)

        scores = {}

        # 1. Filler penalty — check if ANY filler word appears in first 3 words
        first_3 = " ".join(first_words[:3])
        has_filler = any(f in first_3 for f in _FILLER_STARTERS)
        scores["filler"] = 0.2 if has_filler else 1.0

        # 2. Hook type detection
        has_question = "?" in hook_text
        has_number = bool(re.search(r'\b\d+\b', hook_text))
        has_direct = any(w in first_words for w in ("you", "your", "imagine", "look"))

        hook_type_score = 0.4  # baseline
        if has_question:
            hook_type_score = 0.95
        elif has_number:
            hook_type_score = 0.90
        elif has_direct:
            hook_type_score = 0.80
        scores["hook_type"] = hook_type_score

        # 3. Opening energy
        hook_audio = [
            s for s in analysis.audio_segments
            if s.time_range.overlaps(clip_spec.source_range.expand(0))
               and s.time_range.start < hook_end
        ]
        if hook_audio:
            avg_energy = sum(a.energy_avg for a in hook_audio) / len(hook_audio)
            scores["energy"] = min(1.0, avg_energy / _ENERGY_BASELINE)
        else:
            scores["energy"] = 0.5

        # 4. Word count (enough content in hook?)
        word_count = len(first_words)
        scores["word_count"] = min(1.0, word_count / 5)

        # Composite
        score = (
            scores["filler"] * 0.20
            + scores["hook_type"] * 0.35
            + scores["energy"] * 0.25
            + scores["word_count"] * 0.20
        )

        reason = []
        if has_filler:
            reason.append("starts with filler")
        if has_question:
            reason.append("question hook")
        elif has_number:
            reason.append("number hook")
        elif has_direct:
            reason.append("direct address")

        return EvalMetric(
            evaluator_name=self.name, score=round(score, 3), weight=self.weight,
            passed=score >= 0.35,
            diagnostics={
                "hook_text": hook_text[:60],
                "has_filler": has_filler,
                "has_question": has_question,
                "has_number": has_number,
                "reason": "; ".join(reason) if reason else "organic opening",
                **{f"sub_{k}": round(v, 3) for k, v in scores.items()},
            },
        )
