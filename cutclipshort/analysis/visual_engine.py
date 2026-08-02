"""Visual analysis engine v2.

Runs YOLO person detection on multiple sampled frames per scene.

v2 changes:
- Multi-sample per scene: 3 frames (25%, 50%, 75%) instead of just midpoint
- Aggregated person presence (presence_ratio instead of binary has_person)
- Best person bbox selected by highest confidence across samples
- Configurable samples_per_scene via config
- Tracks person count consistency across samples
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

import cv2

from cutclipshort.analysis.base import BaseAnalysisEngine
from cutclipshort.types import SourceAsset

logger = logging.getLogger(__name__)

_DEFAULT_SAMPLES_PER_SCENE = 3
_SAMPLE_POSITIONS = [0.25, 0.50, 0.75]  # Fraction of scene duration


class VisualEngine(BaseAnalysisEngine):
    """YOLO person detection with multi-frame sampling per scene."""

    @property
    def name(self) -> str:
        return "visual"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def depends_on(self) -> list[str]:
        return ["scene"]

    def _relevant_config_keys(self, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "yolo_conf": float(config.get("yolo_conf", 0.35)),
            "yolo_imgsz": int(config.get("yolo_imgsz", 640)),
            "samples_per_scene": int(config.get("samples_per_scene", _DEFAULT_SAMPLES_PER_SCENE)),
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

        progress_callback(0.0)

        # Load scenes
        import json
        scenes_path = cache_dir / "scene.json"
        if not scenes_path.exists():
            logger.warning("No scene.json, returning empty detections")
            result: dict[str, Any] = {"detections": []}
            self._save_cache(cache_dir, result)
            return result

        with open(scenes_path, "r", encoding="utf-8") as f:
            scenes_data = json.load(f)
        scenes = scenes_data.get("scenes", [])

        # Try loading YOLO
        from cutclipshort.adapters.yolo import YOLOAdapter
        yolo = YOLOAdapter(config.get("yolo_model", "yolov8n.pt"))

        if not yolo.check_available():
            logger.warning("YOLO not available — install: pip install ultralytics")
            result = {
                "detections": [],
                "warning": "Nhận diện hình ảnh KHÔNG khả dụng — chưa cài ultralytics. "
                           "Phân loại nội dung sẽ thiếu chính xác.",
            }
            self._save_cache(cache_dir, result)
            progress_callback(1.0)
            return result

        conf = config.get("yolo_conf", 0.35)
        imgsz = config.get("yolo_imgsz", 640)
        base_samples = config.get("samples_per_scene", _DEFAULT_SAMPLES_PER_SCENE)

        # [Phase2] Dynamic sampling: base positions + scale with duration
        # max_samples cap de tranh qua nhieu frames cho scene rat dai
        _MAX_SAMPLES_PER_SCENE = 10

        def _compute_positions(scene_duration: float) -> list[float]:
            """
            [Phase2] Dynamic: scale samples theo scene duration.
            - Scene < 5s: 2 samples (25%, 75%)
            - Scene 5-15s: 3 samples (default)
            - Scene 15-30s: 1 sample per 5s
            - Scene > 30s: 1 sample per 5s, cap tai max
            """
            if scene_duration < 2.0:
                return [0.5]
            if scene_duration < 5.0:
                return [0.25, 0.75]

            n = max(base_samples, int(scene_duration / 5.0))
            n = min(n, _MAX_SAMPLES_PER_SCENE)

            if n <= 1:
                return [0.5]
            return [(i + 1) / (n + 1) for i in range(n)]

        detections = []
        cap = cv2.VideoCapture(str(source))

        # [Phase4] Verify video opened successfully
        if not cap.isOpened():
            logger.error("VideoCapture failed to open: %s", source)
            result = {"detections": [], "warning": "Không mở được video để phân tích hình ảnh."}
            self._save_cache(cache_dir, result)
            progress_callback(1.0)
            return result

        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

            for i, scene in enumerate(scenes):
                start = scene["start_time"]
                end = scene["end_time"]
                duration = end - start

                # [Phase2] Dynamic positions based on scene duration
                positions = _compute_positions(duration)

                # Sample multiple frames within the scene
                sample_results: list[dict[str, Any]] = []
                all_persons_across_samples: list[dict[str, Any]] = []
                samples_with_person = 0

                for pos_frac in positions:
                    sample_time = start + duration * pos_frac
                    frame_num = int(sample_time * fps)

                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                    ret, frame = cap.read()
                    if not ret:
                        continue

                    try:
                        persons = yolo.detect_persons(frame, conf=conf, imgsz=imgsz)
                    except Exception as yolo_err:
                        logger.warning(
                            "YOLO detection failed at %.1fs: %s — skipping frame",
                            sample_time, yolo_err,
                        )
                        continue

                    person_dicts = [
                        {
                            "x": round(p.x, 1),
                            "y": round(p.y, 1),
                            "w": round(p.w, 1),
                            "h": round(p.h, 1),
                            "confidence": round(p.confidence, 3),
                        }
                        for p in persons
                    ]

                    sample_results.append({
                        "time_sec": round(sample_time, 3),
                        "person_count": len(person_dicts),
                        "persons": person_dicts,
                    })

                    if person_dicts:
                        samples_with_person += 1
                        all_persons_across_samples.extend(person_dicts)

                # Aggregate: presence ratio + best person
                total_samples = len(sample_results)
                presence_ratio = (
                    samples_with_person / total_samples
                    if total_samples > 0 else 0.0
                )

                # Select best person (highest confidence across all samples)
                best_person: dict[str, Any] | None = None
                if all_persons_across_samples:
                    best_person = max(
                        all_persons_across_samples,
                        key=lambda p: p["confidence"],
                    )

                # Average person count (for multi-person detection)
                avg_person_count = (
                    sum(s["person_count"] for s in sample_results) / total_samples
                    if total_samples > 0 else 0.0
                )

                det_entry: dict[str, Any] = {
                    "scene_id": scene["id"],
                    "time_sec": round((start + end) / 2, 3),
                    "persons": [best_person] if best_person else [],
                    "presence_ratio": round(presence_ratio, 3),
                    "avg_person_count": round(avg_person_count, 1),
                    "samples": sample_results,
                    "samples_total": total_samples,
                    "samples_with_person": samples_with_person,
                }
                detections.append(det_entry)
                progress_callback(min(0.95, (i + 1) / max(1, len(scenes))))
        finally:
            cap.release()

        result = {"detections": detections}
        self._save_cache(cache_dir, result)
        progress_callback(1.0)

        has_person_count = sum(
            1 for d in detections if d["presence_ratio"] > 0.3
        )
        total_samples_taken = sum(d.get("samples_total", 0) for d in detections)
        logger.info(
            "Visual engine: %d scenes analyzed (%d total samples, dynamic), "
            "%d with persons (>30%% presence)",
            len(detections), total_samples_taken, has_person_count,
        )
        return result
