"""PySceneDetect adapter for scene boundary detection.

Wraps scenedetect library's ContentDetector.
Ported from NerfWarAI's scene_detect.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cutclipshort.adapters.base import BaseAdapter
from cutclipshort.errors import AdapterError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SceneBoundary:
    """A detected scene boundary."""
    id: int
    start_time: float  # seconds
    end_time: float  # seconds


class SceneDetectAdapter(BaseAdapter):
    """Adapter for PySceneDetect."""

    @property
    def tool_name(self) -> str:
        """Return adapter tool name."""
        return "scenedetect"

    def _find_executable(self) -> str:
        return "scenedetect"  # Python library

    def check_available(self) -> bool:
        """Check if scenedetect is installed."""
        try:
            import scenedetect  # noqa: F401
            return True
        except ImportError:
            return False

    def get_version(self) -> str | None:
        """Return scenedetect version string or None."""
        try:
            import scenedetect
            return f"scenedetect {scenedetect.__version__}"
        except (ImportError, AttributeError):
            return None

    def get_capabilities(self) -> dict[str, Any]:
        """Return availability status."""
        return {"available": self.check_available()}

    def detect(
        self,
        video_path: Path,
        *,
        threshold: float = 27.0,
        min_scene_len_sec: float = 1.5,
    ) -> list[SceneBoundary]:
        """Detect scene boundaries in a video.

        Args:
            video_path: Path to video file.
            threshold: Content detection threshold (higher = fewer scenes).
            min_scene_len_sec: Minimum scene length in seconds.

        Returns:
            List of SceneBoundary objects.
        """
        if not self.check_available():
            raise AdapterError(
                "scenedetect not installed",
                tool_name="scenedetect",
            )

        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector

        logger.info(
            "Detecting scenes: threshold=%.1f, min_len=%.1fs",
            threshold, min_scene_len_sec,
        )

        video = open_video(str(video_path))
        fps = video.frame_rate
        min_scene_len_frames = int(min_scene_len_sec * fps)

        manager = SceneManager()
        manager.add_detector(ContentDetector(
            threshold=threshold,
            min_scene_len=min_scene_len_frames,
        ))
        manager.detect_scenes(video)
        scene_list = manager.get_scene_list()

        boundaries = [
            SceneBoundary(
                id=i,
                start_time=scene[0].get_seconds(),
                end_time=scene[1].get_seconds(),
            )
            for i, scene in enumerate(scene_list)
        ]

        logger.info("Detected %d scenes", len(boundaries))
        return boundaries
