"""Demucs adapter for audio source separation.

Wraps demucs CLI for stem separation (vocals, drums, bass, other).
Ported from NerfWarAI's audio.py demucs patterns.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cutclipshort.adapters.base import BaseAdapter
from cutclipshort.errors import AdapterError

logger = logging.getLogger(__name__)

STEM_NAMES = ("vocals", "drums", "bass", "other")


@dataclass(frozen=True)
class StemPaths:
    """Paths to separated audio stems."""
    vocals: Path
    drums: Path
    bass: Path
    other: Path

    def as_dict(self) -> dict[str, Path]:
        """Return stem paths as a name-to-path dictionary."""
        return {
            "vocals": self.vocals,
            "drums": self.drums,
            "bass": self.bass,
            "other": self.other,
        }


class DemucsAdapter(BaseAdapter):
    """Adapter for Demucs audio source separation."""

    def __init__(self, executable_path: str | Path | None = None) -> None:
        super().__init__(executable_path)

    @property
    def tool_name(self) -> str:
        """Return adapter tool name."""
        return "demucs"

    def _find_executable(self) -> str:
        """Demucs can be called as python -m demucs or as CLI."""
        import shutil
        found = shutil.which("demucs")
        if found:
            return found
        # Try python module
        return "demucs"

    def check_available(self) -> bool:
        """Check if demucs is installed as library or CLI."""
        try:
            import demucs  # noqa: F401
            return True
        except ImportError:
            import shutil
            return shutil.which("demucs") is not None

    def get_version(self) -> str | None:
        """Return demucs version string or None."""
        try:
            import demucs
            return f"demucs {getattr(demucs, '__version__', 'unknown')}"
        except ImportError:
            return None

    def get_capabilities(self) -> dict[str, Any]:
        """Return availability and CUDA status."""
        caps: dict[str, Any] = {"available": self.check_available()}
        if caps["available"]:
            try:
                import torch
                caps["cuda"] = torch.cuda.is_available()
            except ImportError:
                caps["cuda"] = False
        return caps

    def separate(
        self,
        audio_path: Path,
        output_dir: Path,
        *,
        model: str = "htdemucs",
        two_stems: str | None = None,
    ) -> StemPaths:
        """Separate audio into stems.

        Args:
            audio_path: Input audio file (WAV recommended).
            output_dir: Directory to write stems into.
            model: Demucs model name.
            two_stems: If set (e.g. "vocals"), only separate into
                       vocals and accompaniment.

        Returns:
            StemPaths with paths to each stem WAV file.
        """
        if not self.check_available():
            raise AdapterError(
                "Demucs not available",
                tool_name="demucs",
            )

        output_dir.mkdir(parents=True, exist_ok=True)

        args = [
            "python", "-m", "demucs",
            "-n", model,
            "-o", str(output_dir),
        ]
        if two_stems:
            args += ["--two-stems", two_stems]
        args.append(str(audio_path))

        logger.info("Running demucs: model=%s, input=%s", model, audio_path.name)
        self._run_command(args, timeout=600)  # 10 min timeout

        # Find output directory (demucs creates model_name/input_stem/)
        stem_name = audio_path.stem
        track_dir = output_dir / model / stem_name

        if not track_dir.exists():
            # Try to find it
            for d in (output_dir / model).iterdir():
                if d.is_dir():
                    track_dir = d
                    break

        if not track_dir.exists():
            raise AdapterError(
                f"Demucs output directory not found: {track_dir}",
                tool_name="demucs",
            )

        stems = {}
        for name in STEM_NAMES:
            stem_path = track_dir / f"{name}.wav"
            if stem_path.exists():
                stems[name] = stem_path
            else:
                logger.warning("Stem not found: %s", stem_path)
                stems[name] = stem_path  # May not exist for two_stems mode

        return StemPaths(**stems)

    def available_models(self) -> list[str]:
        """Return list of common demucs models."""
        return ["htdemucs", "htdemucs_ft", "mdx_extra"]
