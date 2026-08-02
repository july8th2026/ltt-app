"""Semantic completeness evaluator — checks idea completeness and coherence.

Goes beyond sentence boundaries to measure whether the clip contains
a complete thought with setup and resolution.
"""

from __future__ import annotations

import re
from pathlib import Path

from cutclipshort.types import AnalysisResult, ClipSpec, EvalMetric


_INCOMPLETE_ENDINGS = frozenset({
    "and", "but", "or", "so", "because", "which", "that", "when",
    "if", "while", "although", "since", "before", "after", "the",
    "a", "an", "to", "for", "with", "in", "of", "is", "are",
})

_RESOLUTION_MARKERS = frozenset({
    "so that", "and that", "in conclusion", "bottom line", "takeaway",
    "the point is", "the result", "finally", "therefore", "in short",
})


class SemanticEvaluator:
    """Evaluates whether the clip contains a complete thought."""

    @property
    def name(self) -> str:
        return "semantic_completeness"

    @property
    def weight(self) -> float:
        return 0.15

    def evaluate(
        self, rendered_path: Path, clip_spec: ClipSpec, analysis: AnalysisResult,
    ) -> EvalMetric:
        tr = clip_spec.source_range
        segs = [s for s in analysis.transcript if s.time_range.overlaps(tr)]

        if not segs:
            return EvalMetric(
                evaluator_name=self.name, score=0.5, weight=self.weight,
                passed=True, diagnostics={"reason": "No transcript data"},
            )

        full_text = " ".join(s.text.strip() for s in segs)
        words = full_text.split()

        scores = {}

        # 1. Opening completeness: starts at sentence boundary
        first_word = words[0].lower() if words else ""
        # Capitalized or starts with common sentence starters
        starts_clean = (
            first_word[0].isupper() if first_word else False
        ) or first_word in {"so", "now", "the", "this", "here", "let", "if", "when", "how", "why", "what"}
        scores["clean_start"] = 0.9 if starts_clean else 0.4

        # 2. Ending completeness: last word/punctuation check
        last_text = segs[-1].text.strip()
        last_word = words[-1].lower().rstrip(".,!?;:") if words else ""

        if last_text.endswith((".", "!", "?")):
            scores["clean_end"] = 1.0
        elif last_word in _INCOMPLETE_ENDINGS:
            scores["clean_end"] = 0.15  # Cut mid-sentence
        else:
            scores["clean_end"] = 0.5  # Ambiguous

        # 3. Resolution presence: does the clip resolve its setup?
        lower_text = full_text.lower()
        has_resolution = any(m in lower_text for m in _RESOLUTION_MARKERS)
        # Also check for sentence-final punctuation in last 30% of clip
        last_30_segs = segs[-(max(1, len(segs) // 3)):]
        has_closing_sentences = any(
            s.text.strip().endswith((".", "!", "?")) for s in last_30_segs
        )
        if has_resolution:
            scores["resolution"] = 0.95
        elif has_closing_sentences:
            scores["resolution"] = 0.7
        else:
            scores["resolution"] = 0.3

        # 4. Idea density: unique concepts vs word count
        from cutclipshort.editorial.semantic_scorer import _extract_concepts
        concepts = _extract_concepts(full_text)
        concept_ratio = len(concepts) / max(1, len(words))
        # Ideal: 0.15-0.35 unique concepts per word
        if 0.15 <= concept_ratio <= 0.35:
            scores["idea_density"] = 0.9
        elif concept_ratio > 0.35:
            scores["idea_density"] = 0.75  # Very dense (might be hard to follow)
        else:
            scores["idea_density"] = max(0.3, concept_ratio / 0.15)

        # 5. Coherence: do sentences relate to each other?
        if len(segs) >= 3:
            seg_concepts = [_extract_concepts(s.text) for s in segs]
            overlaps = []
            for i in range(len(seg_concepts) - 1):
                a, b = seg_concepts[i], seg_concepts[i + 1]
                if a and b:
                    overlaps.append(len(a & b) / max(1, len(a | b)))
            scores["coherence"] = sum(overlaps) / len(overlaps) if overlaps else 0.5
        else:
            scores["coherence"] = 0.6

        # Composite
        score = (
            scores["clean_start"] * 0.15
            + scores["clean_end"] * 0.25
            + scores["resolution"] * 0.25
            + scores["idea_density"] * 0.15
            + scores["coherence"] * 0.20
        )

        reason = []
        if scores["clean_end"] < 0.3:
            reason.append("cut mid-sentence")
        if scores["resolution"] < 0.4:
            reason.append("no resolution/closure")
        if scores["coherence"] < 0.3:
            reason.append("incoherent")

        return EvalMetric(
            evaluator_name=self.name, score=round(score, 3), weight=self.weight,
            passed=score >= 0.30,
            diagnostics={
                "word_count": len(words),
                "unique_concepts": len(concepts),
                "concept_ratio": round(concept_ratio, 3),
                "ends_with_punctuation": last_text.endswith((".", "!", "?")),
                "has_resolution": has_resolution,
                "reason": "; ".join(reason) if reason else "semantically complete",
                **{f"sub_{k}": round(v, 3) for k, v in scores.items()},
            },
        )
