"""Motion analysis engine.

Computes per-frame motion scores using frame differencing.
Ported from NerfWarAI's motion.py algorithm.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from cutclipshort.analysis.base import BaseAnalysisEngine
from cutclipshort.types import SourceAsset

logger = logging.getLogger(__name__)

DEFAULT_RESIZE_W, DEFAULT_RESIZE_H = 320, 180


class MotionEngine(BaseAnalysisEngine):
    """Frame-diff motion scoring at reduced resolution."""

    @property
    def name(self) -> str:
        return "motion"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def depends_on(self) -> list[str]:
        return ["scene"]

    def _relevant_config_keys(self, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "motion_sample_fps": config.get("motion_sample_fps", 5),
            "motion_resize_w": config.get("motion_resize_w", DEFAULT_RESIZE_W),
            "motion_resize_h": config.get("motion_resize_h", DEFAULT_RESIZE_H),
        }

    def run(
        self,
        source: Path,
        media_info: SourceAsset,
        config: dict[str, Any],
        cache_dir: Path,
        progress_callback: Callable[[float], None],
    ) -> dict[str, Any]:
        cached = self.load_cached(cache_dir)
        if cached is not None:
            return cached

        sample_fps = int(config.get("motion_sample_fps", 5))
        resize_w = int(config.get("motion_resize_w", DEFAULT_RESIZE_W))
        resize_h = int(config.get("motion_resize_h", DEFAULT_RESIZE_H))
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            from cutclipshort.errors import AnalysisError
            raise AnalysisError("Cannot open video", engine_name=self.name)

        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            step = max(1, int(round(fps / sample_fps)))

            prev_gray = None
            motion_rows: list[dict[str, float]] = []
            frame_idx = 0
            last_reported_pct = -1  # throttle: chi callback khi % thay doi

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % step == 0:
                    small = cv2.resize(frame, (resize_w, resize_h))
                    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

                    if prev_gray is not None:
                        diff = cv2.absdiff(gray, prev_gray)
                        score = float(np.mean(diff))
                        time_sec = frame_idx / fps
                        motion_rows.append({"time_sec": round(time_sec, 3), "score": round(score, 2)})

                    prev_gray = gray

                    if total_frames > 0:
                        cur_pct = int(min(95, frame_idx * 100 // total_frames))
                        if cur_pct != last_reported_pct:
                            last_reported_pct = cur_pct
                            progress_callback(min(0.95, frame_idx / total_frames))

                frame_idx += 1
        finally:
            cap.release()

        # Write CSV alongside JSON for compatibility
        csv_path = cache_dir / "motion.csv"
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["time_sec", "motion_score"])
                for row in motion_rows:
                    writer.writerow([row["time_sec"], row["score"]])
        except OSError as e:
            logger.warning("Không thể ghi motion CSV: %s — bỏ qua", e)

        # Normalize scores to 0.0-1.0 using 95th percentile (not global max)
        # This prevents a single spike from compressing all other scores
        if motion_rows:
            sorted_scores = sorted(r["score"] for r in motion_rows)
            p95_idx = int(len(sorted_scores) * 0.95)
            p95_score = sorted_scores[min(p95_idx, len(sorted_scores) - 1)] or 1.0
            for row in motion_rows:
                row["score_normalized"] = round(
                    min(1.0, row["score"] / max(p95_score, 1.0)), 3
                )

        # Compute summary per scene (if scenes available)
        scene_summary = self._summarize_with_scenes(motion_rows, cache_dir)

        result = {
            "motion_rows": motion_rows,
            "scene_summary": scene_summary,
            "score_range": "0.0-1.0 (normalized from pixel diff 0-255)",
        }
        self._save_cache(cache_dir, result)
        progress_callback(1.0)

        logger.info("Motion analysis: %d samples, max_raw=%.1f",
                     len(motion_rows),
                     max(r["score"] for r in motion_rows) if motion_rows else 0)
        return result

    def _summarize_with_scenes(
        self, motion_rows: list[dict[str, float]], cache_dir: Path
    ) -> list[dict[str, Any]]:
        """Compute per-scene motion averages if scene.json exists."""
        scenes_path = cache_dir / "scene.json"
        if not scenes_path.exists():
            return []

        with open(scenes_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        scenes = data.get("scenes", [])

        summary = []
        for scene in scenes:
            start = scene["start_time"]
            end = scene["end_time"]
            in_range = [r["score"] for r in motion_rows if start <= r["time_sec"] < end]
            avg = sum(in_range) / len(in_range) if in_range else 0.0
            mx = max(in_range) if in_range else 0.0
            summary.append({
                "scene_id": scene["id"],
                "motion_avg": round(avg, 2),
                "motion_max": round(mx, 2),
            })
        return summary
