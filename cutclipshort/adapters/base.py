"""Adapter protocol and base class for external tool wrappers.

Adapters isolate installation variability, capability detection,
and provide testable interfaces. Analysis/render never construct
subprocess commands directly — they go through adapters.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from cutclipshort.errors import AdapterError, AdapterNotFoundError

logger = logging.getLogger(__name__)


def _get_app_root() -> Path:
    """Get the application root directory (works for both dev and frozen exe)."""
    if getattr(sys, 'frozen', False):
        # PyInstaller frozen exe — _MEIPASS is the temp extract dir
        # but we want the directory where the exe lives
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


@runtime_checkable
class Adapter(Protocol):
    """Contract every external tool wrapper must implement."""

    @property
    def tool_name(self) -> str:
        """Name of the external tool. e.g. 'ffmpeg', 'whisper'."""
        ...

    def check_available(self) -> bool:
        """Return True if the tool is installed and functional.
        Must not raise; returns False on any failure."""
        ...

    def get_version(self) -> str | None:
        """Return tool version string, or None if unavailable."""
        ...

    def get_capabilities(self) -> dict[str, Any]:
        """Return capability dict. e.g. {'nvenc': True, 'cuda': True}.
        Used by higher layers to choose code paths."""
        ...


class BaseAdapter(ABC):
    """Abstract base class for adapters with common utilities."""

    def __init__(self, executable_path: str | Path | None = None) -> None:
        self._executable_path = Path(executable_path) if executable_path else None
        self._version_cache: str | None = None
        self._capabilities_cache: dict[str, Any] | None = None

    @property
    @abstractmethod
    def tool_name(self) -> str:
        ...

    @property
    def executable(self) -> str:
        """Resolved executable path or name."""
        if self._executable_path and self._executable_path.exists():
            return str(self._executable_path)
        return self._find_executable()

    def _find_executable(self) -> str:
        """Find executable in bundled locations, then PATH.

        Search order:
        1. tools/ subfolder next to exe (portable bundle)
        2. ffmpeg/ subfolder next to exe
        3. Same directory as exe
        4. System PATH
        """
        tool = self.tool_name
        ext = ".exe" if os.name == "nt" else ""
        exe_name = f"{tool}{ext}"

        app_root = _get_app_root()
        search_dirs = [
            app_root / "tools",
            app_root / "tools" / "ffmpeg",
            app_root / "tools" / "ffmpeg" / "bin",
            app_root / "ffmpeg",
            app_root / "ffmpeg" / "bin",
            app_root,
        ]

        for d in search_dirs:
            candidate = d / exe_name
            if candidate.is_file():
                logger.info("Found %s at: %s", tool, candidate)
                return str(candidate)

        # Fall back to system PATH
        found = shutil.which(tool)
        if found:
            return found

        # Build helpful error message
        hint_paths = "\n".join(f"  - {d}" for d in search_dirs[:3])
        raise AdapterNotFoundError(
            f"{tool} không tìm thấy!\n\n"
            f"Cách khắc phục:\n"
            f"1. Tải FFmpeg từ https://ffmpeg.org/download.html\n"
            f"2. Giải nén và đặt ffmpeg.exe + ffprobe.exe vào một trong:\n"
            f"{hint_paths}\n"
            f"3. Hoặc cài FFmpeg vào PATH hệ thống",
            tool_name=tool,
        )

    def check_available(self) -> bool:
        """Check if the tool is available."""
        try:
            self._find_executable()
            return True
        except AdapterNotFoundError:
            return False

    def _run_command(
        self,
        args: list[str],
        *,
        timeout: float | None = None,
        capture_output: bool = True,
        check: bool = True,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess:
        """Run a subprocess command with standard error handling.

        Raises AdapterError on failure with stderr content.
        """
        logger.debug("Running: %s", " ".join(args))
        try:
            result = subprocess.run(
                args,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=check,
                cwd=cwd,
                encoding="utf-8",
                errors="replace",
            )
            return result
        except subprocess.CalledProcessError as e:
            raise AdapterError(
                f"{self.tool_name} command failed (exit code {e.returncode})",
                tool_name=self.tool_name,
                stderr=e.stderr,
                details=f"Command: {' '.join(args)}",
            )
        except subprocess.TimeoutExpired:
            raise AdapterError(
                f"{self.tool_name} command timed out after {timeout}s",
                tool_name=self.tool_name,
            )
        except FileNotFoundError:
            raise AdapterNotFoundError(
                f"{self.tool_name} executable not found: {args[0]}",
                tool_name=self.tool_name,
            )
