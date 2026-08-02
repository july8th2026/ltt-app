"""Project lifecycle manager.

Creates, opens, saves, and closes projects.
Manages the recent projects list and project directory structure.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cutclipshort.constants import APP_DATA_DIR, MAX_RECENT_PROJECTS, PROJECTS_DIR
from cutclipshort.core.config import AppConfig
from cutclipshort.core.event_bus import EventBus
from cutclipshort.core.job import JobStateMachine
from cutclipshort.errors import ProjectNotFoundError, StorageError, VideoImportError
from cutclipshort.storage.media_index import compute_source_hash
from cutclipshort.storage.paths import ProjectPaths
from cutclipshort.storage.project_store import create_project, load_project, save_project
from cutclipshort.types import Genre, JobState, Project, SourceAsset

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectManager:
    """Manages project lifecycle: create, open, save, close.

    Only one project is active at a time. Opening a new project
    closes the current one.
    """

    def __init__(self, config: AppConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._current: Project | None = None
        self._current_paths: ProjectPaths | None = None
        self._state_machine: JobStateMachine | None = None
        self._projects_dir = Path(
            config.get("app", "projects_dir", "") or str(PROJECTS_DIR)
        )
        self._projects_dir.mkdir(parents=True, exist_ok=True)

    @property
    def current(self) -> Project | None:
        return self._current

    @property
    def paths(self) -> ProjectPaths | None:
        return self._current_paths

    @property
    def state_machine(self) -> JobStateMachine | None:
        return self._state_machine

    @property
    def has_project(self) -> bool:
        return self._current is not None

    # ── Create ───────────────────────────────────────────────────────

    def create_from_video(
        self,
        video_path: Path,
        name: str | None = None,
        genre: Genre = Genre.TALKING_HEAD,
    ) -> Project:
        """Create a new project from a video file.

        Args:
            video_path: Path to source video.
            name: Project name (defaults to filename stem).
            genre: Content genre for editorial strategy.

        Returns:
            The created Project.
        """
        if not video_path.exists():
            raise VideoImportError(f"Video file not found: {video_path}")

        project_name = name or video_path.stem
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        project_dir = self._projects_dir / f"{project_name}_{project_id}"

        paths = ProjectPaths(project_dir)
        paths.create_all()

        # Compute source hash
        logger.info("Computing source hash for %s", video_path.name)
        source_hash = compute_source_hash(video_path)

        # Write hash file
        paths.source_hash_file.write_text(source_hash, encoding="utf-8")

        # Probe source media with ffprobe
        logger.info("Probing media: %s", video_path.name)
        from cutclipshort.adapters.ffmpeg import FFprobeAdapter
        ffprobe = FFprobeAdapter()
        source_asset = ffprobe.get_media_info(video_path, source_hash)

        # Save media info to disk
        import json as _json
        paths.media_info_json.parent.mkdir(parents=True, exist_ok=True)
        with open(paths.media_info_json, "w", encoding="utf-8") as f:
            # Serialize SourceAsset to dict
            from dataclasses import asdict
            _json.dump(asdict(source_asset), f, ensure_ascii=False, indent=2, default=str)

        project = Project(
            project_id=project_id,
            name=project_name,
            schema_version=2,
            source=source_asset,
            genre=genre,
            strategy_name=genre.value,
            state=JobState.IDLE,
            created_at=_now_iso(),
            modified_at=_now_iso(),
            last_opened_at=_now_iso(),
        )

        # SourceAsset will be populated after ffprobe runs in the import step
        self._current = project
        self._current_paths = paths
        self._state_machine = JobStateMachine(
            initial_state=project.state,
            on_transition=self._on_state_change,
        )

        self._save_current()
        self._add_to_recent(project_dir, project_name)

        logger.info("Project created: %s at %s", project_name, project_dir)
        return project

    # ── Open / Close ─────────────────────────────────────────────────

    def open_project(self, project_dir: Path) -> Project:
        """Open an existing project."""
        if self._current is not None:
            self.close_project()

        paths = ProjectPaths(project_dir)
        if not paths.project_json.exists():
            raise ProjectNotFoundError(f"No project.json in {project_dir}")

        # Load project.json
        with open(paths.project_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        project = Project(
            project_id=data.get("project_id", ""),
            name=data.get("name", ""),
            schema_version=data.get("schema_version", 1),
            genre=Genre(data.get("genre", "talking_head")),
            strategy_name=data.get("strategy_name", "talking_head"),
            state=JobState(data.get("state", "idle")),
            state_message=data.get("state_message", ""),
            candidate_count=data.get("candidate_count", 0),
            current_plan_version=data.get("current_plan_version", 0),
            total_plan_versions=data.get("total_plan_versions", 0),
            export_count=data.get("export_count", 0),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
            last_opened_at=_now_iso(),
        )

        # Load SourceAsset if available
        if paths.media_info_json.exists():
            with open(paths.media_info_json, "r", encoding="utf-8") as f:
                source_data = json.load(f)
            project.source = SourceAsset(**source_data)

        # Load analysis engine statuses
        from cutclipshort.types import AnalysisEngineStatus
        for eng_name, eng_status in data.get("analysis_engines", {}).items():
            project.analysis_engines[eng_name] = AnalysisEngineStatus(eng_status)

        self._current = project
        self._current_paths = paths
        self._state_machine = JobStateMachine(
            initial_state=project.state,
            on_transition=self._on_state_change,
        )

        self._add_to_recent(project_dir, project.name)
        logger.info("Project opened: %s (state=%s)", project.name, project.state.value)
        return project

    def close_project(self) -> None:
        """Save and close the current project."""
        if self._current is not None:
            self._save_current()
            logger.info("Project closed: %s", self._current.name)
        self._current = None
        self._current_paths = None
        self._state_machine = None

    # ── Save ─────────────────────────────────────────────────────────

    def save(self) -> None:
        """Save current project state to disk."""
        self._save_current()

    def _save_current(self) -> None:
        if self._current is None or self._current_paths is None:
            return
        self._current.modified_at = _now_iso()

        data: dict[str, Any] = {
            "schema_version": self._current.schema_version,
            "project_id": self._current.project_id,
            "name": self._current.name,
            "genre": self._current.genre.value,
            "strategy_name": self._current.strategy_name,
            "state": self._current.state.value,
            "state_message": self._current.state_message,
            "state_progress": self._current.state_progress,
            "analysis_engines": {
                k: v.value for k, v in self._current.analysis_engines.items()
            },
            "candidate_count": self._current.candidate_count,
            "candidates_generation": self._current.candidates_generation,
            "current_plan_version": self._current.current_plan_version,
            "total_plan_versions": self._current.total_plan_versions,
            "export_count": self._current.export_count,
            "last_export_at": self._current.last_export_at,
            "export_manifest_ids": self._current.export_manifest_ids,
            "created_at": self._current.created_at,
            "modified_at": self._current.modified_at,
            "last_opened_at": self._current.last_opened_at,
            "last_error": self._current.last_error,
            "last_error_detail": self._current.last_error_detail,
        }

        path = self._current_paths.project_json
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    # ── State ────────────────────────────────────────────────────────

    def _on_state_change(
        self, previous: JobState, current: JobState, reason: str
    ) -> None:
        if self._current is not None:
            self._current.state = current
            self._save_current()
        self._bus.emit("job.state_changed", {
            "previous": previous.value,
            "current": current.value,
            "reason": reason,
        })

    # ── Recent Projects ──────────────────────────────────────────────

    def get_recent_projects(self) -> list[dict[str, str]]:
        """Return list of recent projects [{name, path, modified_at}]."""
        recent_path = APP_DATA_DIR / "recent_projects.json"
        if not recent_path.exists():
            return []
        try:
            with open(recent_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _add_to_recent(self, project_dir: Path, name: str) -> None:
        recent = self.get_recent_projects()
        dir_str = str(project_dir)

        # Remove if already exists
        recent = [r for r in recent if r.get("path") != dir_str]

        # Prepend
        recent.insert(0, {
            "name": name,
            "path": dir_str,
            "modified_at": _now_iso(),
        })

        # Trim
        recent = recent[:MAX_RECENT_PROJECTS]

        # Save
        recent_path = APP_DATA_DIR / "recent_projects.json"
        recent_path.parent.mkdir(parents=True, exist_ok=True)
        with open(recent_path, "w", encoding="utf-8") as f:
            json.dump(recent, f, ensure_ascii=False, indent=2)
