"""Exception hierarchy for LTT CUT SHORT.

All domain-specific exceptions inherit from CutClipShortError.
Adapters catch subprocess/library errors and re-raise as AdapterError.
GUI catches CutClipShortError subtypes for user-friendly messages.
"""

from __future__ import annotations


class CutClipShortError(Exception):
    """Base exception for all LTT CUT SHORT errors."""

    def __init__(self, message: str, *, details: str | None = None) -> None:
        super().__init__(message)
        self.details = details


# ── Import ───────────────────────────────────────────────────────────────

class VideoImportError(CutClipShortError):
    """Source file issues: unreadable, unsupported codec, corrupt."""


# ── Analysis ─────────────────────────────────────────────────────────────

class AnalysisError(CutClipShortError):
    """Engine failure during analysis."""

    def __init__(
        self,
        message: str,
        *,
        engine_name: str | None = None,
        details: str | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.engine_name = engine_name


# ── Editorial ────────────────────────────────────────────────────────────

class EditorialError(CutClipShortError):
    """No candidates found, constraint violations, strategy failure."""


# ── Render ───────────────────────────────────────────────────────────────

class RenderError(CutClipShortError):
    """FFmpeg failure, disk space, encoding error."""

    def __init__(
        self,
        message: str,
        *,
        clip_id: int | None = None,
        details: str | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.clip_id = clip_id


# ── Evaluation ───────────────────────────────────────────────────────────

class EvaluationError(CutClipShortError):
    """Scoring or quality gate failure."""


# ── Adapters ─────────────────────────────────────────────────────────────

class AdapterError(CutClipShortError):
    """External tool not found, version mismatch, execution failure."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        stderr: str | None = None,
        details: str | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.tool_name = tool_name
        self.stderr = stderr


class AdapterNotFoundError(AdapterError):
    """External tool is not installed or not on PATH."""


# ── Storage ──────────────────────────────────────────────────────────────

class StorageError(CutClipShortError):
    """Disk I/O, corrupt project file, permission denied."""


class ProjectNotFoundError(StorageError):
    """Project directory or project.json does not exist."""


class ProjectCorruptError(StorageError):
    """Project file fails schema validation."""


# ── Config ───────────────────────────────────────────────────────────────

class ConfigError(CutClipShortError):
    """Invalid YAML, missing required keys, type mismatch."""


# ── Pipeline ─────────────────────────────────────────────────────────────

class PipelineCancelledError(CutClipShortError):
    """User cancelled the current pipeline operation."""


class PipelineResumeError(CutClipShortError):
    """Cannot resume: cache corrupt or incompatible version."""
