"""Retention potential evaluator — predicts viewer retention curve shape.

Scores based on: energy arc (should rise/sustain, not drop), speech consistency,
dead air avoidance, and payoff at end.
"""

from __future__ import annotations

from pathlib import Path

from cutclipshort.types import AnalysisResult, ClipSpec, EvalMetric, TimeRange


class RetentionEvaluator:
    """Predicts whether viewers will watch the full clip or drop off."""

    @property
    def name(self) -> str:
        return "retention_potential"

    @property
    def weight(self) -> float:
        return 0.15

    def evaluate(
        self, rendered_path: Path, clip_spec: ClipSpec, analysis: AnalysisResult,
    ) -> EvalMetric:
        tr = clip_spec.source_range
        duration = tr.duration
        if duration < 5:
            return EvalMetric(
                evaluator_name=self.name, score=0.1, weight=self.weight,
                passed=False, diagnostics={"reason": "Clip too short for retention analysis"},
            )

        # Divide clip into 3 acts
        act1_end = tr.start + duration * 0.33
        act2_end = tr.start + duration * 0.66
        act1 = TimeRange(tr.start, act1_end)
        act2 = TimeRange(act1_end, act2_end)
        act3 = TimeRange(act2_end, tr.end)

        def _act_energy(act_range: TimeRange) -> float:
            segs = [s for s in analysis.audio_segments if s.time_range.overlaps(act_range)]
            if not segs:
                return 0.0
            return sum(s.energy_avg for s in segs) / len(segs)

        def _act_speech_ratio(act_range: TimeRange) -> float:
            segs = [s for s in analysis.transcript if s.time_range.overlaps(act_range)]
            speech_dur = sum(s.time_range.overlap_duration(act_range) for s in segs)
            return speech_dur / max(0.1, act_range.duration)

        e1, e2, e3 = _act_energy(act1), _act_energy(act2), _act_energy(act3)
        sr1, sr2, sr3 = _act_speech_ratio(act1), _act_speech_ratio(act2), _act_speech_ratio(act3)

        scores = {}

        # 1. Energy arc: should NOT drop dramatically mid-clip
        if e1 > 0 and e2 > 0:
            mid_drop = (e1 - e2) / max(0.01, e1)
            if mid_drop > 0.5:
                scores["energy_arc"] = 0.3  # Big drop in middle = viewer leaves
            elif mid_drop > 0.2:
                scores["energy_arc"] = 0.6
            else:
                scores["energy_arc"] = 0.9
        else:
            scores["energy_arc"] = 0.5

        # 2. Sustained speech: no long dead air gaps in middle
        silence_segs = [
            s for s in analysis.audio_segments
            if s.time_range.overlaps(act2) and s.has_silence and s.silence_ratio > 0.5
        ]
        dead_air_ratio = len(silence_segs) / max(1, len([
            s for s in analysis.audio_segments if s.time_range.overlaps(act2)
        ]))
        scores["sustained_speech"] = max(0.2, 1.0 - dead_air_ratio * 2)

        # 3. Payoff strength: ending should have energy/content
        scores["ending_energy"] = min(1.0, e3 / max(0.01, (e1 + e2) / 2) * 1.2)

        # 4. Speech consistency across acts
        avg_sr = (sr1 + sr2 + sr3) / 3
        sr_variance = sum((s - avg_sr) ** 2 for s in (sr1, sr2, sr3)) / 3
        scores["speech_consistency"] = max(0.0, min(1.0, 1.0 - sr_variance * 5))

        # 5. Opening engagement (first act should be strong)
        scores["opening_pull"] = max(0.0, min(1.0, (e1 + sr1 * 0.3) / 0.2)) if e1 > 0 else 0.4

        # Composite
        score = (
            scores["energy_arc"] * 0.25
            + scores["sustained_speech"] * 0.20
            + scores["ending_energy"] * 0.20
            + scores["speech_consistency"] * 0.15
            + scores["opening_pull"] * 0.20
        )

        reason = []
        if scores["energy_arc"] < 0.5:
            reason.append("energy drops mid-clip")
        if scores["sustained_speech"] < 0.5:
            reason.append("dead air in middle")
        if scores["ending_energy"] < 0.4:
            reason.append("weak ending")

        return EvalMetric(
            evaluator_name=self.name, score=round(score, 3), weight=self.weight,
            passed=score >= 0.35,
            diagnostics={
                "act1_energy": round(e1, 3), "act2_energy": round(e2, 3), "act3_energy": round(e3, 3),
                "act1_speech": round(sr1, 2), "act2_speech": round(sr2, 2), "act3_speech": round(sr3, 2),
                "reason": "; ".join(reason) if reason else "good retention curve",
                **{f"sub_{k}": round(v, 3) for k, v in scores.items()},
            },
        )
