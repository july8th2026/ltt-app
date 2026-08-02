"""Subtitle density evaluator — checks caption readability and pacing.

Measures: words per second, characters per second, subtitle burst risk,
and compliance with platform subtitle guidelines.

Evaluates against ACTUAL rendered subtitle chunks (2-4 seconds each),
not raw transcript segments (which can be 5-30+ seconds long).
"""

from __future__ import annotations

from pathlib import Path

from cutclipshort.types import AnalysisResult, ClipSpec, EvalMetric

# Platform limits
_MAX_WPS = 3.5    # Words per second (above = too fast to read)
_MAX_CPS = 18.0   # Characters per second (above = subtitle burst)
_MAX_CHARS_LINE = 40  # Max characters per subtitle line
_IDEAL_WPS = (1.5, 3.0)


class SubtitleDensityEvaluator:
    """Evaluates whether captions are readable at playback speed."""

    @property
    def name(self) -> str:
        return "subtitle_density"

    @property
    def weight(self) -> float:
        return 0.05

    def evaluate(
        self, rendered_path: Path, clip_spec: ClipSpec, analysis: AnalysisResult,
    ) -> EvalMetric:
        if not clip_spec.caption_enabled:
            return EvalMetric(
                evaluator_name=self.name, score=0.9, weight=self.weight,
                passed=True, diagnostics={"reason": "Captions disabled"},
            )

        # Use clip's own caption_segments (already filtered by time range)
        segs = clip_spec.caption_segments
        if not segs:
            tr = clip_spec.source_range
            segs = [s for s in analysis.transcript if s.time_range.overlaps(tr)]

        if not segs:
            return EvalMetric(
                evaluator_name=self.name, score=0.8, weight=self.weight,
                passed=True, diagnostics={"reason": "No transcript for subtitle check"},
            )

        # Split segments into chunks (same logic as caption_renderer)
        # to evaluate ACTUAL rendered subtitle density
        try:
            from cutclipshort.render.caption_renderer import _segment_to_chunks
            chunks = []
            for seg in segs:
                lang = getattr(seg, "language", "") or ""
                chunks.extend(_segment_to_chunks(seg, max_chars=_MAX_CHARS_LINE, language=lang))
        except ImportError:
            # Fallback: evaluate raw segments
            chunks = None

        # Compute per-chunk metrics (or per-segment as fallback)
        total_words = 0
        total_chars = 0
        total_speech_dur = 0.0
        burst_count = 0
        long_lines = 0

        if chunks:
            for chunk in chunks:
                text = chunk.text.strip()
                words = text.split()
                dur = max(0.1, chunk.end - chunk.start)

                cps = len(text) / dur

                total_words += len(words)
                total_chars += len(text)
                total_speech_dur += dur

                if cps > _MAX_CPS:
                    burst_count += 1
                if len(text) > _MAX_CHARS_LINE * 2:
                    long_lines += 1

            eval_count = len(chunks)
        else:
            for seg in segs:
                text = seg.text.strip()
                words = text.split()
                dur = max(0.1, seg.end - seg.start)

                cps = len(text) / dur

                total_words += len(words)
                total_chars += len(text)
                total_speech_dur += dur

                if cps > _MAX_CPS:
                    burst_count += 1
                if len(text) > _MAX_CHARS_LINE * 2:
                    long_lines += 1

            eval_count = len(segs)

        overall_wps = total_words / max(0.1, total_speech_dur)
        overall_cps = total_chars / max(0.1, total_speech_dur)

        scores = {}

        # 1. WPS score
        if _IDEAL_WPS[0] <= overall_wps <= _IDEAL_WPS[1]:
            scores["wps"] = 1.0
        elif overall_wps <= _MAX_WPS:
            scores["wps"] = 0.7
        else:
            scores["wps"] = max(0.2, 1.0 - (overall_wps - _MAX_WPS) * 0.3)

        # 2. CPS score
        if overall_cps <= 14:
            scores["cps"] = 1.0
        elif overall_cps <= _MAX_CPS:
            scores["cps"] = 0.7
        else:
            scores["cps"] = max(0.2, 1.0 - (overall_cps - _MAX_CPS) * 0.1)

        # 3. Burst ratio
        burst_ratio = burst_count / max(1, eval_count)
        scores["burst"] = max(0.2, 1.0 - burst_ratio * 2)

        # 4. Line length compliance
        long_ratio = long_lines / max(1, eval_count)
        scores["line_length"] = max(0.3, 1.0 - long_ratio * 2)

        score = (
            scores["wps"] * 0.35
            + scores["cps"] * 0.25
            + scores["burst"] * 0.25
            + scores["line_length"] * 0.15
        )

        reason = []
        if overall_wps > _MAX_WPS:
            reason.append(f"too fast ({overall_wps:.1f} wps)")
        if burst_count > 0:
            reason.append(f"{burst_count} burst chunks")
        if long_lines > 0:
            reason.append(f"{long_lines} long lines")

        return EvalMetric(
            evaluator_name=self.name, score=round(score, 3), weight=self.weight,
            passed=score >= 0.35,
            diagnostics={
                "overall_wps": round(overall_wps, 1),
                "overall_cps": round(overall_cps, 1),
                "burst_chunks": burst_count,
                "total_chunks": eval_count,
                "total_segments": len(segs),
                "reason": "; ".join(reason) if reason else "readable subtitle pace",
                **{f"sub_{k}": round(v, 3) for k, v in scores.items()},
            },
        )
