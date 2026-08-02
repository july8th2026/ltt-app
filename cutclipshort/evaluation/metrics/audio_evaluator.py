"""Audio quality evaluator v2.

Analyzes the ACTUAL RENDERED FILE for audio quality, not just pre-computed data.

v2 changes:
- Probes rendered file with ffprobe for actual loudness stats
- Measures peak levels and clipping detection
- Checks actual vs target LUFS compliance
- Falls back to analysis data if probe fails
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from cutclipshort.types import AnalysisResult, ClipSpec, EvalMetric

logger = logging.getLogger(__name__)


class AudioEvaluator:
    """Evaluates audio quality of the actual rendered clip file."""

    @property
    def name(self) -> str:
        return "audio_loudness"

    @property
    def weight(self) -> float:
        return 0.20

    def evaluate(
        self,
        rendered_path: Path,
        clip_spec: ClipSpec,
        analysis: AnalysisResult,
    ) -> EvalMetric:
        # Try to analyze actual rendered file first
        rendered_stats = _probe_audio_stats(rendered_path)

        if rendered_stats is not None:
            return self._evaluate_from_rendered(
                rendered_stats, clip_spec, rendered_path,
            )

        # Fallback to pre-computed analysis data
        return self._evaluate_from_analysis(clip_spec, analysis)

    def _evaluate_from_rendered(
        self,
        stats: dict,
        clip_spec: ClipSpec,
        rendered_path: Path,
    ) -> EvalMetric:
        """Evaluate using actual rendered file probe results."""
        measured_lufs = stats.get("integrated_loudness", -24.0)
        true_peak = stats.get("true_peak", -1.0)
        loudness_range = stats.get("loudness_range", 10.0)
        has_audio = stats.get("has_audio", True)

        if not has_audio:
            return EvalMetric(
                evaluator_name=self.name,
                score=0.1,
                weight=self.weight,
                passed=False,
                diagnostics={"error": "No audio stream in rendered file"},
            )

        target_lufs = clip_spec.audio_config.loudnorm_lufs

        # 1. LUFS compliance: how close to target?
        lufs_diff = abs(measured_lufs - target_lufs)
        if lufs_diff <= 1.0:
            lufs_score = 1.0  # Within 1 LU of target
        elif lufs_diff <= 2.0:
            lufs_score = 0.85
        elif lufs_diff <= 4.0:
            lufs_score = 0.65
        else:
            lufs_score = max(0.2, 1.0 - lufs_diff * 0.08)

        # 2. True peak: should be below -1.0 dBTP for streaming
        if true_peak <= -1.0:
            peak_score = 1.0
        elif true_peak <= 0.0:
            peak_score = 0.7  # Acceptable but not ideal
        else:
            peak_score = 0.3  # Clipping!

        # 3. Loudness range: 5-15 LU is ideal
        if 5.0 <= loudness_range <= 15.0:
            range_score = 1.0
        elif 3.0 <= loudness_range <= 20.0:
            range_score = 0.7
        else:
            range_score = 0.4

        # 4. Not too quiet
        quiet_penalty = 0.0
        if measured_lufs < -30.0:
            quiet_penalty = 0.2  # Very quiet content

        score = min(1.0, (
            lufs_score * 0.45
            + peak_score * 0.25
            + range_score * 0.15
            + 0.15  # Base for having audio
            - quiet_penalty
        ))

        passed = score >= 0.4 and true_peak <= 0.0

        return EvalMetric(
            evaluator_name=self.name,
            score=round(score, 3),
            weight=self.weight,
            passed=passed,
            diagnostics={
                "source": "rendered_file",
                "measured_lufs": round(measured_lufs, 1),
                "target_lufs": target_lufs,
                "lufs_deviation": round(lufs_diff, 1),
                "true_peak_dbtp": round(true_peak, 1),
                "loudness_range_lu": round(loudness_range, 1),
                "clipping_detected": true_peak > 0.0,
                "lufs_score": round(lufs_score, 3),
                "peak_score": round(peak_score, 3),
            },
        )

    def _evaluate_from_analysis(
        self,
        clip_spec: ClipSpec,
        analysis: AnalysisResult,
    ) -> EvalMetric:
        """Fallback: evaluate using pre-computed analysis data."""
        tr = clip_spec.source_range
        overlapping = [
            seg for seg in analysis.audio_segments
            if seg.time_range.overlaps(tr)
        ]

        if not overlapping:
            return EvalMetric(
                evaluator_name=self.name,
                score=0.7,
                weight=self.weight,
                passed=True,
                diagnostics={
                    "source": "analysis_fallback",
                    "note": "No audio analysis data, using default score",
                },
            )

        avg_energy = sum(s.energy_avg for s in overlapping) / len(overlapping)
        silence_ratio = sum(s.silence_ratio for s in overlapping) / len(overlapping)
        has_speech = any(s.has_speech for s in overlapping)

        energy_score = min(1.0, avg_energy / 0.3) if avg_energy > 0 else 0.3
        silence_penalty = max(0.0, 1.0 - silence_ratio * 3)
        speech_bonus = 0.1 if has_speech else 0.0

        score = min(1.0, energy_score * 0.5 + silence_penalty * 0.4 + speech_bonus)
        passed = score >= 0.4 and silence_ratio < 0.5

        return EvalMetric(
            evaluator_name=self.name,
            score=round(score, 3),
            weight=self.weight,
            passed=passed,
            diagnostics={
                "source": "analysis_fallback",
                "avg_energy": round(avg_energy, 3),
                "silence_ratio": round(silence_ratio, 3),
                "has_speech": has_speech,
            },
        )


def _probe_audio_stats(rendered_path: Path) -> dict | None:
    """Probe rendered file for actual audio loudness using ffprobe/ffmpeg.

    Uses the EBU R128 loudnorm filter to measure:
    - Integrated loudness (LUFS)
    - True peak (dBTP)
    - Loudness range (LU)
    """
    if not rendered_path.exists():
        return None

    try:
        # First check if file has audio
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name,sample_rate,channels",
            "-of", "json",
            str(rendered_path),
        ]
        probe_result = subprocess.run(
            probe_cmd, capture_output=True, text=True, timeout=10,
        )
        if probe_result.returncode != 0:
            return None

        probe_data = json.loads(probe_result.stdout)
        streams = probe_data.get("streams", [])
        if not streams:
            return {"has_audio": False}

        # Measure loudness with loudnorm filter (2-pass measurement)
        loudnorm_cmd = [
            "ffmpeg", "-v", "error",
            "-i", str(rendered_path),
            "-af", "loudnorm=print_format=json",
            "-f", "null", "-",
        ]
        result = subprocess.run(
            loudnorm_cmd, capture_output=True, text=True, timeout=60,
        )

        # Parse loudnorm JSON from stderr
        stderr = result.stderr
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            loudnorm_data = json.loads(stderr[json_start:json_end])
            return {
                "has_audio": True,
                "integrated_loudness": float(loudnorm_data.get("input_i", -24.0)),
                "true_peak": float(loudnorm_data.get("input_tp", -1.0)),
                "loudness_range": float(loudnorm_data.get("input_lra", 10.0)),
                "threshold": float(loudnorm_data.get("input_thresh", -34.0)),
            }

        return None

    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError, ValueError) as e:
        logger.debug("Audio probe failed for %s: %s", rendered_path, e)
        return None
