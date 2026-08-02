"""Adapter and engine registry.

Discovers, instantiates, and provides adapters and engines via
dependency injection. Called at startup to wire the application.
"""

from __future__ import annotations

import logging
from typing import Any

from cutclipshort.adapters.base import Adapter
from cutclipshort.adapters.ffmpeg import FFmpegAdapter, FFprobeAdapter
from cutclipshort.adapters.ffmpeg_hw import FFmpegHWAdapter
from cutclipshort.adapters.whisper import WhisperAdapter
from cutclipshort.adapters.yolo import YOLOAdapter
from cutclipshort.adapters.demucs import DemucsAdapter
from cutclipshort.adapters.mpv import MPVAdapter
from cutclipshort.adapters.scenedetect import SceneDetectAdapter
from cutclipshort.core.config import AppConfig

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Central registry for all external tool adapters.

    Instantiates adapters based on config and checks availability.
    Provides adapters to engines and renderers via simple attribute access.
    """

    def __init__(self, config: AppConfig) -> None:
        adapter_cfg = config.get_section("adapters")

        self.ffmpeg = FFmpegAdapter(adapter_cfg.get("ffmpeg_path"))
        self.ffprobe = FFprobeAdapter(adapter_cfg.get("ffprobe_path"))
        self.ffmpeg_hw = FFmpegHWAdapter(adapter_cfg.get("ffmpeg_path"))
        self.whisper = WhisperAdapter(
            model_size=config.get("analysis", "whisper_model", "base"),
            compute_type=config.get("analysis", "whisper_compute_type", "auto"),
        )
        self.yolo = YOLOAdapter(config.get("analysis", "yolo_model", "yolov8n.pt"))
        self.demucs = DemucsAdapter(adapter_cfg.get("demucs_path"))
        self.mpv = MPVAdapter()
        self.scenedetect = SceneDetectAdapter()

        self._all: dict[str, Adapter] = {
            "ffmpeg": self.ffmpeg,
            "ffprobe": self.ffprobe,
            "ffmpeg_hw": self.ffmpeg_hw,
            "whisper": self.whisper,
            "yolo": self.yolo,
            "demucs": self.demucs,
            "mpv": self.mpv,
            "scenedetect": self.scenedetect,
        }

    def check_all(self) -> dict[str, bool]:
        """Check availability of all adapters.

        Returns {adapter_name: is_available}.
        """
        status: dict[str, bool] = {}
        for name, adapter in self._all.items():
            available = adapter.check_available()
            status[name] = available
            level = logging.INFO if available else logging.WARNING
            logger.log(
                level,
                "Adapter '%s': %s",
                name,
                "available" if available else "NOT AVAILABLE",
            )
        return status

    def check_tier_compatibility(self, config) -> list[str]:
        """Check if current tier's requirements are met by available adapters.

        Returns list of warning messages (empty = all OK).
        """
        warnings: list[str] = []
        demucs_enabled = config.get("audio", "demucs_enabled", False)
        if demucs_enabled and not self.demucs.check_available():
            warnings.append(
                "Tier yêu cầu Demucs (tách vocals) nhưng Demucs chưa cài. "
                "Audio sẽ dùng nguyên bản. Cài: pip install demucs"
            )
            logger.warning("Demucs required by tier but unavailable — audio separation disabled")

        prefer_gpu = config.get("render", "prefer_nvenc", False)
        if prefer_gpu and not self.ffmpeg_hw.check_available():
            warnings.append(
                "Tier ưu tiên NVENC (GPU render) nhưng NVENC không khả dụng. "
                "Sẽ dùng x264 CPU (chậm hơn 2-5x)."
            )
            logger.warning("NVENC preferred but unavailable — falling back to x264 CPU")

        return warnings

    def get_capabilities(self) -> dict[str, dict[str, Any]]:
        """Get capabilities of all adapters."""
        return {
            name: adapter.get_capabilities()
            for name, adapter in self._all.items()
        }

    def update_from_config(self, config: AppConfig) -> None:
        """Update adapters when quality tier changes mid-session.

        Re-reads model paths and compute types from config.
        Only updates adapters that have tier-controlled parameters.
        """
        new_whisper_model = config.get("analysis", "whisper_model", "base")
        new_compute_type = config.get("analysis", "whisper_compute_type", "auto")
        new_yolo_model = config.get("analysis", "yolo_model", "yolov8n.pt")

        # Update Whisper if model or compute changed
        if (new_whisper_model != self.whisper._model_size
                or new_compute_type != self.whisper._compute_type):
            self.whisper = WhisperAdapter(
                model_size=new_whisper_model,
                compute_type=new_compute_type,
            )
            self._all["whisper"] = self.whisper
            logger.info("Whisper adapter updated: model=%s compute=%s",
                        new_whisper_model, new_compute_type)

        # Update YOLO if model changed
        if new_yolo_model != self.yolo._model_path:
            self.yolo.set_model_path(new_yolo_model)
            logger.info("YOLO adapter updated: model=%s", new_yolo_model)

    def get(self, name: str) -> Adapter | None:
        """Get an adapter by name."""
        return self._all.get(name)
