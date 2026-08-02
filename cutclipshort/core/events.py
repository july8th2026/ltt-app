"""All event dataclasses for the EventBus.

Events are emitted by core/workers and consumed by GUI controllers.
Each event is a frozen dataclass for immutability.
Event names follow the pattern: "{module}.{action}".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cutclipshort.types import JobState, ClipScore, ExportManifest


# ── Event Names (constants) ──────────────────────────────────────────────

# Import
EVT_IMPORT_START = "import.start"
EVT_IMPORT_PROGRESS = "import.progress"
EVT_IMPORT_DONE = "import.done"
EVT_IMPORT_ERROR = "import.error"

# Analysis
EVT_ANALYSIS_START = "analysis.start"
EVT_ANALYSIS_PROGRESS = "analysis.progress"
EVT_ANALYSIS_ENGINE_DONE = "analysis.engine_done"
EVT_ANALYSIS_DONE = "analysis.done"
EVT_ANALYSIS_ERROR = "analysis.error"

# Editorial
EVT_CANDIDATES_READY = "editorial.candidates_ready"
EVT_PLAN_READY = "editorial.plan_ready"
EVT_EDITORIAL_ERROR = "editorial.error"

# Preview
EVT_PREVIEW_START = "preview.start"
EVT_PREVIEW_PROGRESS = "preview.progress"
EVT_PREVIEW_CLIP_READY = "preview.clip_ready"
EVT_PREVIEW_DONE = "preview.done"

# Render
EVT_RENDER_START = "render.start"
EVT_RENDER_PROGRESS = "render.progress"
EVT_RENDER_CLIP_DONE = "render.clip_done"
EVT_RENDER_DONE = "render.done"
EVT_RENDER_ERROR = "render.error"

# Evaluation
EVT_EVAL_CLIP_SCORED = "evaluation.clip_scored"
EVT_EVAL_DONE = "evaluation.done"

# Export
EVT_EXPORT_START = "export.start"
EVT_EXPORT_PROGRESS = "export.progress"
EVT_EXPORT_COMPLETE = "export.complete"
EVT_EXPORT_ERROR = "export.error"

# Job lifecycle
EVT_JOB_STATE_CHANGED = "job.state_changed"
EVT_JOB_ERROR = "job.error"
EVT_JOB_CANCELLED = "job.cancelled"


# ── Event Data Classes ───────────────────────────────────────────────────

@dataclass(frozen=True)
class ImportProgress:
    stage: str  # "copying", "probing", "hashing"
    pct: float  # 0.0 - 1.0


@dataclass(frozen=True)
class ImportDone:
    project_dir: Path
    source_hash: str


@dataclass(frozen=True)
class AnalysisProgress:
    engine_name: str
    pct: float  # 0.0 - 1.0
    message: str = ""


@dataclass(frozen=True)
class AnalysisEngineDone:
    engine_name: str
    elapsed_sec: float


@dataclass(frozen=True)
class AnalysisDone:
    total_elapsed_sec: float
    engine_count: int


@dataclass(frozen=True)
class CandidatesReady:
    count: int
    strategy_name: str


@dataclass(frozen=True)
class PlanReady:
    version: int
    clip_count: int
    strategy_name: str


@dataclass(frozen=True)
class PreviewProgress:
    clip_id: int
    pct: float


@dataclass(frozen=True)
class PreviewClipReady:
    clip_id: int
    preview_path: Path
    thumbnail_path: Path | None = None


@dataclass(frozen=True)
class RenderProgress:
    clip_id: int
    pct: float
    stage: str = ""  # "encoding", "framing", "audio", "captions"


@dataclass(frozen=True)
class RenderClipDone:
    clip_id: int
    output_path: Path
    elapsed_sec: float


@dataclass(frozen=True)
class EvalClipScored:
    clip_id: int
    score: ClipScore


@dataclass(frozen=True)
class ExportProgress:
    clip_id: int
    pct: float
    clips_done: int
    clips_total: int


@dataclass(frozen=True)
class ExportComplete:
    manifest: ExportManifest


@dataclass(frozen=True)
class JobStateChanged:
    previous: JobState
    current: JobState
    reason: str = ""


@dataclass(frozen=True)
class JobError:
    state: JobState
    error_type: str
    message: str
    details: str = ""
