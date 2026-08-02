"""Scene detection engine.

Detects shot boundaries using PySceneDetect ContentDetector.
Ported from NerfWarAI's scene_detect.py.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from cutclipshort.analysis.base import BaseAnalysisEngine
from cutclipshort.types import SourceAsset

logger = logging.getLogger(__name__)


class SceneEngine(BaseAnalysisEngine):
    """Detect scene (shot) boundaries in a video."""

    @property
    def name(self) -> str:
        return "scene"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _relevant_config_keys(self, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "scene_threshold": float(config.get("scene_threshold", 27.0)),
            "min_scene_len_sec": float(config.get("min_scene_len_sec", 1.5)),
        }

    def run(
        self,
        source: Path,
        media_info: SourceAsset,
        config: dict[str, Any],
        cache_dir: Path,
        progress_callback: Callable[[float], None],
    ) -> dict[str, Any]:
        # Check cache first
        cached = self.load_cached(cache_dir)
        if cached is not None:
            logger.info("Scene detection: using cache (%d scenes)", len(cached.get("scenes", [])))
            return cached

        progress_callback(0.0)

        from cutclipshort.adapters.scenedetect import SceneDetectAdapter

        adapter = SceneDetectAdapter()
        threshold = config.get("scene_threshold", 27.0)
        threshold = max(10.0, min(50.0, threshold))  # Clamp to safe range
        min_len = max(0.5, config.get("min_scene_len_sec", 1.5))

        try:
            boundaries = adapter.detect(
                source, threshold=threshold, min_scene_len_sec=min_len,
            )
        except Exception as e:
            logger.error("Scene detection failed: %s — creating single-scene fallback", e)
            # Fallback: treat entire video as one scene
            boundaries = []

        progress_callback(0.9)

        if boundaries:
            scenes = [
                {
                    "id": b.id,
                    "start_time": b.start_time,
                    "end_time": b.end_time,
                }
                for b in boundaries
            ]
        else:
            # No scenes detected or detection failed — create single-scene fallback
            duration = media_info.duration_sec if media_info else 60.0
            scenes = [{"id": 0, "start_time": 0.0, "end_time": duration}]
            logger.warning("Using single-scene fallback (entire video as 1 scene)")

        result = {"scenes": scenes}
        if not boundaries:
            result["warning"] = "Không phát hiện được ranh giới cảnh — sử dụng toàn bộ video."
        self._save_cache(cache_dir, result)
        progress_callback(1.0)

        logger.info("Scene detection: %d scenes found", len(scenes))
        return result
