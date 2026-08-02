"""Render job protocol.

Defines the contract that the render engine accepts.
The render layer only reads EditPlan + source video — never analysis cache.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable

from cutclipshort.types import ClipSpec


@runtime_checkable
class RenderJob(Protocol):
    """Contract the render engine accepts for a single clip."""

    @property
    def clip_spec(self) -> ClipSpec:
        """The complete render instruction."""
        ...

    @property
    def source_path(self) -> Path:
        """Path to the source video file."""
        ...

    @property
    def output_path(self) -> Path:
        """Path where the rendered clip should be written."""
        ...

    @property
    def is_preview(self) -> bool:
        """True = low-res fast render. False = full quality export."""
        ...


class SimpleRenderJob:
    """Simple implementation of RenderJob."""

    def __init__(
        self,
        clip_spec: ClipSpec,
        source_path: Path,
        output_path: Path,
        is_preview: bool = False,
    ) -> None:
        self._clip_spec = clip_spec
        self._source_path = source_path
        self._output_path = output_path
        self._is_preview = is_preview

    @property
    def clip_spec(self) -> ClipSpec:
        return self._clip_spec

    @property
    def source_path(self) -> Path:
        return self._source_path

    @property
    def output_path(self) -> Path:
        return self._output_path

    @property
    def is_preview(self) -> bool:
        return self._is_preview
