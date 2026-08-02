"""MPV adapter for video playback in GUI.

Wraps libmpv for frame-accurate video playback embedded in PySide6.
Falls back to QMediaPlayer if mpv is unavailable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cutclipshort.adapters.base import BaseAdapter
from cutclipshort.errors import AdapterError

logger = logging.getLogger(__name__)


class MPVAdapter(BaseAdapter):
    """Adapter for MPV video player."""

    @property
    def tool_name(self) -> str:
        """Return adapter tool name."""
        return "mpv"

    def check_available(self) -> bool:
        """Check if python-mpv and libmpv are available."""
        try:
            import mpv  # noqa: F401
            return True
        except (ImportError, OSError):
            return False

    def get_version(self) -> str | None:
        """Return MPV version string or None."""
        try:
            import mpv
            player = mpv.MPV()
            version = player.mpv_version
            player.terminate()
            return version
        except Exception as exc:
            logger.debug("Failed to get MPV version: %s", exc)
            return None

    def get_capabilities(self) -> dict[str, Any]:
        """Return availability status."""
        return {"available": self.check_available()}

    def create_player(self, wid: int | None = None) -> Any:
        """Create an MPV player instance.

        Args:
            wid: Window ID for embedding (from Qt widget.winId()).

        Returns:
            mpv.MPV instance.
        """
        if not self.check_available():
            raise AdapterError(
                "python-mpv not installed or libmpv not found",
                tool_name="mpv",
            )

        import mpv

        kwargs: dict[str, Any] = {
            "input_default_bindings": True,
            "input_vo_keyboard": True,
            "osc": True,
        }
        if wid is not None:
            kwargs["wid"] = str(wid)

        player = mpv.MPV(**kwargs)
        return player
