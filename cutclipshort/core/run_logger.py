"""Structured production run logger.

Dual output for every pipeline run:
1. Human-readable log file  — all module logs, timestamped, filterable
2. Structured JSON summary  — machine-readable metrics for GUI / analytics

The file handler is attached to the ROOT logger so it captures logs from
ALL cutclipshort.* modules, not just this module.

Usage:
    run = RunLogger(paths, "my_project")
    run.log_stage_start("analysis")
    run.log_engine_start("scene")
    run.log_engine_end("scene", {"scenes_found": 80})
    run.log_stage_end("analysis", {"total_engines": 6})
    run.log_stage_start("editorial")
    run.log_candidate("c001", score=0.75, hook_type="question", duration=25.3)
    run.log_stage_end("editorial", {"candidates": 5})
    run.log_stage_start("render")
    run.log_render("c001", elapsed=8.2, size_mb=15.0, has_captions=True)
    run.log_stage_end("render", {"clips_rendered": 5})
    summary_path = run.finalize()
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cutclipshort.storage.paths import ProjectPaths

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fmt_elapsed(seconds: float) -> str:
    """Format elapsed time as human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs:.0f}s"
    hours = int(minutes // 60)
    mins = minutes % 60
    return f"{hours}h {mins}m {secs:.0f}s"


class RunLogger:
    """Structured logger for a single pipeline run.

    Captures ALL cutclipshort.* module logs into a per-run log file.
    Collects structured metrics into a JSON summary.
    """

    def __init__(self, paths: ProjectPaths, project_name: str) -> None:
        self._paths = paths
        self._project_name = project_name
        self._timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._t0 = time.perf_counter()

        # Summary accumulator
        self._summary: dict[str, Any] = {
            "project": project_name,
            "started_at": _now_iso(),
            "stages": {},
            "engines": {},
            "candidates": [],
            "renders": [],
            "errors": [],
            "warnings": [],
        }

        # Set up file handler on the ROOT cutclipshort logger
        # This captures ALL logs from cutclipshort.* modules
        self._paths.logs_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = paths.run_log(self._timestamp)

        self._file_handler = logging.FileHandler(
            self._log_path, encoding="utf-8",
        )
        self._file_handler.setLevel(logging.DEBUG)
        self._file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))

        # Attach to cutclipshort root logger — captures ALL module logs
        self._root_logger = logging.getLogger("cutclipshort")
        self._root_logger.addHandler(self._file_handler)

        # Stage timing
        self._stage_timers: dict[str, float] = {}
        self._engine_timers: dict[str, float] = {}

        logger.info("=" * 70)
        logger.info("PIPELINE RUN: %s", project_name)
        logger.info("=" * 70)

    # ── Stage tracking ───────────────────────────────────────────────

    def log_stage_start(self, stage_name: str) -> None:
        """Record the start of a pipeline stage (probe, analysis, editorial, render, export)."""
        self._stage_timers[stage_name] = time.perf_counter()
        logger.info("── STAGE: %s ──────────────────────────────", stage_name.upper())

    def log_stage_end(
        self, stage_name: str, metrics: dict[str, Any] | None = None,
    ) -> None:
        """Record the end of a pipeline stage with optional metrics."""
        t_start = self._stage_timers.pop(stage_name, self._t0)
        elapsed = time.perf_counter() - t_start

        stage_data: dict[str, Any] = {
            "elapsed_sec": round(elapsed, 2),
            "elapsed_human": _fmt_elapsed(elapsed),
        }
        if metrics:
            stage_data.update(metrics)

        self._summary["stages"][stage_name] = stage_data
        logger.info(
            "── %s DONE (%s) ──────────────────────────",
            stage_name.upper(), _fmt_elapsed(elapsed),
        )

    # ── Engine tracking (per-analysis-engine) ────────────────────────

    def log_engine_start(self, engine_name: str) -> None:
        """Record start of an analysis engine."""
        self._engine_timers[engine_name] = time.perf_counter()
        logger.info("  [engine] %s: starting...", engine_name)

    def log_engine_end(
        self, engine_name: str, metrics: dict[str, Any] | None = None,
    ) -> None:
        """Record end of an analysis engine with metrics."""
        t_start = self._engine_timers.pop(engine_name, time.perf_counter())
        elapsed = time.perf_counter() - t_start

        engine_data: dict[str, Any] = {
            "elapsed_sec": round(elapsed, 2),
            "elapsed_human": _fmt_elapsed(elapsed),
        }
        if metrics:
            engine_data.update(metrics)

        self._summary["engines"][engine_name] = engine_data
        logger.info(
            "  [engine] %s: done in %s%s",
            engine_name, _fmt_elapsed(elapsed),
            f" ({metrics})" if metrics else "",
        )

    def log_engine_error(self, engine_name: str, error: str) -> None:
        """Log an engine failure (non-fatal, pipeline continues)."""
        self._summary["engines"][engine_name] = {
            "status": "failed",
            "error": error,
        }
        self._summary["warnings"].append({
            "type": "engine_failure",
            "engine": engine_name,
            "error": error,
            "at": _now_iso(),
        })
        logger.warning("  [engine] %s: FAILED — %s", engine_name, error)

    # ── Candidate tracking ───────────────────────────────────────────

    def log_candidate(
        self,
        clip_id: str,
        score: float = 0.0,
        hook_type: str = "",
        duration: float = 0.0,
        start: float = 0.0,
        end: float = 0.0,
        why: str = "",
    ) -> None:
        """Log a generated candidate clip."""
        self._summary["candidates"].append({
            "clip_id": clip_id,
            "score": round(score, 3),
            "hook_type": hook_type,
            "duration_sec": round(duration, 1),
            "time_range": f"{start:.1f}-{end:.1f}",
            "why_selected": why[:120],
        })
        logger.info(
            "  [candidate] %s: score=%.3f hook=%s [%.1f-%.1fs] %s",
            clip_id, score, hook_type, start, end, why[:60],
        )

    # ── Render tracking ──────────────────────────────────────────────

    def log_render(
        self,
        clip_id: str,
        elapsed: float = 0.0,
        size_mb: float = 0.0,
        has_captions: bool = False,
        has_demucs: bool = False,
        resolution: str = "",
        status: str = "success",
        error: str = "",
    ) -> None:
        """Log a rendered clip."""
        self._summary["renders"].append({
            "clip_id": clip_id,
            "elapsed_sec": round(elapsed, 1),
            "size_mb": round(size_mb, 1),
            "has_captions": has_captions,
            "has_demucs": has_demucs,
            "resolution": resolution,
            "status": status,
            "error": error[:200] if error else "",
        })
        if status == "success":
            logger.info(
                "  [render] %s: %s in %s (%.1fMB, captions=%s)",
                clip_id, resolution, _fmt_elapsed(elapsed), size_mb, has_captions,
            )
        else:
            logger.error("  [render] %s: FAILED — %s", clip_id, error[:100])

    # ── Error / Warning / Metric ─────────────────────────────────────

    def log_error(self, context: str, error: str) -> None:
        """Log a fatal or significant error."""
        self._summary["errors"].append({
            "context": context,
            "error": error,
            "at": _now_iso(),
        })
        logger.error("ERROR in %s: %s", context, error)

    def log_warning(self, context: str, message: str) -> None:
        """Log a non-fatal warning."""
        self._summary["warnings"].append({
            "context": context,
            "message": message,
            "at": _now_iso(),
        })
        logger.warning("WARNING in %s: %s", context, message)

    def log_metric(self, key: str, value: Any) -> None:
        """Log an arbitrary top-level metric."""
        self._summary[key] = value
        logger.info("[metric] %s: %s", key, value)

    # ── Finalize ─────────────────────────────────────────────────────

    def finalize(self) -> Path:
        """Write the JSON summary and close the file handler.

        Returns path to the summary JSON file.
        """
        total_elapsed = time.perf_counter() - self._t0
        self._summary["completed_at"] = _now_iso()
        self._summary["total_elapsed_sec"] = round(total_elapsed, 2)
        self._summary["total_elapsed_human"] = _fmt_elapsed(total_elapsed)

        logger.info("=" * 70)
        logger.info("PIPELINE COMPLETE: %s in %s", self._project_name, _fmt_elapsed(total_elapsed))
        logger.info(
            "  stages: %s | engines: %s | candidates: %s | renders: %s | errors: %s",
            len(self._summary["stages"]),
            len(self._summary["engines"]),
            len(self._summary["candidates"]),
            len(self._summary["renders"]),
            len(self._summary["errors"]),
        )
        logger.info("=" * 70)

        # Write JSON summary
        summary_path = self._paths.run_summary(self._timestamp)
        tmp = summary_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._summary, f, ensure_ascii=False, indent=2)
        os.replace(tmp, summary_path)

        # Update latest.log
        latest = self._paths.latest_log
        try:
            if latest.exists():
                latest.unlink()
            import shutil
            shutil.copy2(self._log_path, latest)
        except OSError:
            pass

        # Cleanup
        self._root_logger.removeHandler(self._file_handler)
        self._file_handler.close()

        return summary_path

    @property
    def summary(self) -> dict[str, Any]:
        return self._summary
