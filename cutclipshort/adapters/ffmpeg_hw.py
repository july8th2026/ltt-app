"""Hardware acceleration detection for FFmpeg.

Detects NVENC (NVIDIA), QSV (Intel), and VideoToolbox (macOS).
Falls back gracefully to software encoding.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from cutclipshort.adapters.base import BaseAdapter
from cutclipshort.errors import AdapterError

logger = logging.getLogger(__name__)


class FFmpegHWAdapter(BaseAdapter):
    """Hardware encoder detection and selection."""

    def __init__(self, ffmpeg_path: str | Path | None = None) -> None:
        super().__init__(ffmpeg_path)
        self._hw_cache: dict[str, bool] | None = None

    @property
    def tool_name(self) -> str:
        """Return adapter tool name."""
        return "ffmpeg"

    def get_version(self) -> str | None:
        """Return None; version is provided by FFmpegAdapter."""
        return None  # Delegates to FFmpegAdapter

    def get_capabilities(self) -> dict[str, Any]:
        """Return NVENC and QSV availability."""
        return {
            "nvenc": self.has_nvenc(),
            "qsv": self.has_qsv(),
        }

    def _test_encoder(self, encoder: str) -> bool:
        """Test if an encoder works by encoding a tiny black frame."""
        try:
            with tempfile.TemporaryDirectory() as tmp:
                test_out = Path(tmp) / "test.mp4"
                # NVENC trên một số GPU/driver (đặc biệt RTX 50xx) từ chối
                # frame 64x64 dù encoder hoạt động bình thường với video thật.
                # Probe 256x256 thống nhất với platform_core.media để không
                # báo âm giả rồi lùi cả job về libx264.
                args = [
                    self.executable,
                    "-y",
                    "-f", "lavfi",
                    "-i", "color=black:s=256x256:d=0.1",
                    "-pix_fmt", "yuv420p",
                    "-c:v", encoder,
                    "-frames:v", "1",
                    str(test_out),
                ]
                subprocess.run(
                    args,
                    capture_output=True,
                    timeout=10,
                    check=True,
                )
                return test_out.exists() and test_out.stat().st_size > 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _detect_all(self) -> dict[str, bool]:
        """Detect all hardware encoders."""
        if self._hw_cache is not None:
            return self._hw_cache

        self._hw_cache = {
            "h264_nvenc": self._test_encoder("h264_nvenc"),
            "h264_qsv": self._test_encoder("h264_qsv"),
        }

        for name, available in self._hw_cache.items():
            if available:
                logger.info("Hardware encoder available: %s", name)
            else:
                logger.debug("Hardware encoder not available: %s", name)

        return self._hw_cache

    def has_nvenc(self) -> bool:
        """Check if NVIDIA NVENC is available."""
        return self._detect_all().get("h264_nvenc", False)

    def has_qsv(self) -> bool:
        """Check if Intel QSV is available."""
        return self._detect_all().get("h264_qsv", False)

    def best_encoder(self, prefer_hw: bool = True) -> str:
        """Return the best available H.264 encoder.

        Priority: h264_nvenc > h264_qsv > libx264
        """
        if prefer_hw:
            hw = self._detect_all()
            if hw.get("h264_nvenc"):
                return "h264_nvenc"
            if hw.get("h264_qsv"):
                return "h264_qsv"

        return "libx264"

    def encoder_preset(self, encoder: str) -> str:
        """Return appropriate preset for the encoder."""
        presets = {
            "h264_nvenc": "p5",
            "h264_qsv": "medium",
            "libx264": "medium",
        }
        return presets.get(encoder, "medium")
