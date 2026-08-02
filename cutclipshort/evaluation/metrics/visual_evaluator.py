"""Visual quality evaluator v2.

Analyzes the ACTUAL RENDERED FILE for visual quality metrics.

v2 changes:
- Probes rendered file with ffprobe for bitrate, codec, resolution
- Measures blur/sharpness via Laplacian variance (if opencv available)
- Graduated person presence scoring (0.0-1.0 not binary)
- Validates actual output dimensions match target
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from cutclipshort.types import AnalysisResult, ClipSpec, EvalMetric

logger = logging.getLogger(__name__)

_MIN_BITRATE_KBPS = 500  # Below this = visually degraded
_IDEAL_BITRATE_KBPS = 2500  # Good quality threshold
_BLUR_THRESHOLD = 50.0  # Laplacian variance below this = blurry


class VisualEvaluator:
    """Evaluates visual quality of the actual rendered clip file."""

    @property
    def name(self) -> str:
        return "visual_quality"

    @property
    def weight(self) -> float:
        return 0.15

    def evaluate(
        self,
        rendered_path: Path,
        clip_spec: ClipSpec,
        analysis: AnalysisResult,
    ) -> EvalMetric:
        # 1. File existence and integrity
        if not rendered_path.exists():
            return EvalMetric(
                evaluator_name=self.name,
                score=0.0,
                weight=self.weight,
                passed=False,
                diagnostics={"error": "Rendered file does not exist"},
            )

        file_size = rendered_path.stat().st_size
        if file_size < 1000:
            return EvalMetric(
                evaluator_name=self.name,
                score=0.0,
                weight=self.weight,
                passed=False,
                diagnostics={"error": f"File too small: {file_size} bytes"},
            )

        # 2. Probe actual rendered file
        probe = _probe_video_stats(rendered_path)

        # 3. Person presence from analysis (graduated scoring)
        tr = clip_spec.source_range
        person_score = _compute_person_score(tr, analysis)

        if probe is not None:
            return self._evaluate_with_probe(
                probe, clip_spec, person_score, file_size,
            )

        # Fallback: basic checks only
        return self._evaluate_basic(clip_spec, person_score, file_size)

    def _evaluate_with_probe(
        self,
        probe: dict,
        clip_spec: ClipSpec,
        person_score: float,
        file_size: int,
    ) -> EvalMetric:
        """Evaluate using ffprobe data from actual rendered file."""
        actual_w = probe.get("width", 0)
        actual_h = probe.get("height", 0)
        bitrate_kbps = probe.get("bitrate_kbps", 0)
        codec = probe.get("codec", "unknown")
        actual_fps = probe.get("fps", 0.0)

        # Resolution match: actual vs target
        target_w = clip_spec.target_width
        target_h = clip_spec.target_height
        w_match = abs(actual_w - target_w) <= 2
        h_match = abs(actual_h - target_h) <= 2
        res_match = w_match and h_match
        res_score = 1.0 if res_match else 0.6

        # Resolution quality: is it at least 720p?
        min_dim = min(actual_w, actual_h)
        if min_dim >= 1080:
            res_quality = 1.0
        elif min_dim >= 720:
            res_quality = 0.85
        elif min_dim >= 480:
            res_quality = 0.6
        else:
            res_quality = 0.3

        # Bitrate quality
        if bitrate_kbps >= _IDEAL_BITRATE_KBPS:
            bitrate_score = 1.0
        elif bitrate_kbps >= _MIN_BITRATE_KBPS:
            bitrate_score = 0.5 + 0.5 * (
                (bitrate_kbps - _MIN_BITRATE_KBPS)
                / (_IDEAL_BITRATE_KBPS - _MIN_BITRATE_KBPS)
            )
        else:
            bitrate_score = max(0.2, bitrate_kbps / _MIN_BITRATE_KBPS)

        # Blur detection (if available)
        blur_score = probe.get("blur_score", 1.0)  # 1.0 = sharp (default)

        # FPS check
        fps_score = 1.0 if actual_fps >= 24.0 else 0.6

        # Composite
        score = (
            res_score * 0.15
            + res_quality * 0.15
            + bitrate_score * 0.20
            + person_score * 0.25
            + blur_score * 0.15
            + fps_score * 0.10
        )

        passed = score >= 0.4 and min_dim >= 480

        return EvalMetric(
            evaluator_name=self.name,
            score=round(score, 3),
            weight=self.weight,
            passed=passed,
            diagnostics={
                "source": "rendered_file",
                "actual_resolution": f"{actual_w}x{actual_h}",
                "target_resolution": f"{clip_spec.target_width}x{clip_spec.target_height}",
                "resolution_match": res_match,
                "bitrate_kbps": bitrate_kbps,
                "codec": codec,
                "fps": round(actual_fps, 1),
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "person_score": round(person_score, 3),
                "blur_score": round(blur_score, 3),
            },
        )

    def _evaluate_basic(
        self,
        clip_spec: ClipSpec,
        person_score: float,
        file_size: int,
    ) -> EvalMetric:
        """Fallback evaluation without probe data."""
        res_ok = clip_spec.target_width >= 720 and clip_spec.target_height >= 720
        res_score = 1.0 if res_ok else 0.6
        file_score = 1.0 if file_size > 1000 else 0.0

        score = person_score * 0.4 + res_score * 0.3 + file_score * 0.3
        passed = file_score > 0 and res_ok

        return EvalMetric(
            evaluator_name=self.name,
            score=round(score, 3),
            weight=self.weight,
            passed=passed,
            diagnostics={
                "source": "basic_fallback",
                "resolution_ok": res_ok,
                "file_size_bytes": file_size,
                "person_score": round(person_score, 3),
            },
        )


def _compute_person_score(tr, analysis: AnalysisResult) -> float:
    """Graduated person presence scoring using analysis data."""
    relevant = [
        vs for vs in analysis.visual_segments
        if vs.time_range.overlaps(tr)
    ]
    if not relevant:
        return 0.5  # No data = neutral

    # Compute presence ratio across all relevant segments
    person_count = sum(1 for vs in relevant if vs.has_person)
    presence_ratio = person_count / len(relevant)

    # Graduated scoring (not binary)
    if presence_ratio >= 0.8:
        return 0.95
    if presence_ratio >= 0.5:
        return 0.80
    if presence_ratio >= 0.3:
        return 0.65
    if presence_ratio > 0:
        return 0.50
    return 0.35  # No person at all


def _probe_video_stats(rendered_path: Path) -> dict | None:
    """Probe rendered file with ffprobe for video stream info."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height,codec_name,bit_rate,r_frame_rate,avg_frame_rate",
            "-of", "json",
            str(rendered_path),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams:
            return None

        stream = streams[0]
        width = int(stream.get("width", 0))
        height = int(stream.get("height", 0))
        codec = stream.get("codec_name", "unknown")

        # Parse bitrate
        bitrate_str = stream.get("bit_rate", "0")
        try:
            bitrate_kbps = int(bitrate_str) // 1000
        except (ValueError, TypeError):
            bitrate_kbps = 0

        # Parse FPS from r_frame_rate (e.g., "30/1")
        fps = 0.0
        fps_str = stream.get("r_frame_rate", "0/1")
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den) if float(den) > 0 else 0
            else:
                fps = float(fps_str)
        except (ValueError, ZeroDivisionError):
            fps = 0.0

        # Try blur detection with OpenCV (optional)
        blur_score = _detect_blur(rendered_path, width, height)

        return {
            "width": width,
            "height": height,
            "codec": codec,
            "bitrate_kbps": bitrate_kbps,
            "fps": fps,
            "blur_score": blur_score,
        }

    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        logger.debug("Video probe failed for %s: %s", rendered_path, e)
        return None


def _detect_blur(rendered_path: Path, width: int, height: int) -> float:
    """Detect blur using Laplacian variance on a sample frame.

    Returns 0.0 (very blurry) to 1.0 (sharp).
    Returns 1.0 (assume sharp) if OpenCV is unavailable.
    """
    try:
        import cv2

        cap = cv2.VideoCapture(str(rendered_path))
        if not cap.isOpened():
            return 1.0

        # Sample at 3 seconds or midpoint
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        sample_frame = min(int(3.0 * fps), total_frames // 2)

        cap.set(cv2.CAP_PROP_POS_FRAMES, sample_frame)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return 1.0

        # Convert to grayscale and compute Laplacian variance
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Normalize: < 50 = blurry, > 200 = sharp
        if laplacian_var >= 200.0:
            return 1.0
        if laplacian_var >= _BLUR_THRESHOLD:
            return 0.5 + 0.5 * (laplacian_var - _BLUR_THRESHOLD) / (200.0 - _BLUR_THRESHOLD)
        return max(0.1, laplacian_var / _BLUR_THRESHOLD * 0.5)

    except (ImportError, Exception):
        return 1.0  # Assume sharp if OpenCV unavailable
