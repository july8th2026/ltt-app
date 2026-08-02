"""Project file persistence.

Save/load project.json with schema versioning and migration.
Atomic writes to prevent corruption.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from cutclipshort.constants import PROJECT_FILE, PROJECT_SCHEMA_VERSION
from cutclipshort.errors import ProjectCorruptError, ProjectNotFoundError, StorageError
from cutclipshort.storage.paths import ProjectPaths
from cutclipshort.types import AnalysisEngineStatus, Genre, JobState

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_project(paths: ProjectPaths, config: Any) -> None:
    """Save project config to project.json with atomic write."""
    data = {
        "schema_version": config.schema_version,
        "name": config.name,
        "source_path": str(config.source_path),
        "source_hash": config.source_hash,
        "genre": config.genre.value,
        "created_at": config.created_at,
        "modified_at": _now_iso(),
        "state": config.state.value,
        "analysis_status": {
            k: v.value for k, v in config.analysis_status.items()
        },
        "current_plan_version": config.current_plan_version,
        "export_history": config.export_history,
    }

    paths.root.mkdir(parents=True, exist_ok=True)
    tmp_path = paths.project_json.with_suffix(".tmp")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, paths.project_json)
        logger.info("Project saved: %s", paths.project_json)
    except OSError as e:
        raise StorageError(f"Failed to save project: {e}", details=str(e))


def save_project_simple(
    project_dir: Path,
    name: str,
    genre: str,
    state: str,
    candidate_count: int = 0,
    source_path: str = "",
) -> None:
    """Save minimal project state for GUI persistence (simple dict approach).

    This is a lightweight save that doesn't require the full Any.
    Used by app_controller to persist state between sessions.
    """
    paths = ProjectPaths(project_dir)
    paths.root.mkdir(parents=True, exist_ok=True)

    data = {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "name": name,
        "source_path": source_path,
        "source_hash": "",
        "genre": genre,
        "state": state,
        "candidate_count": candidate_count,
        "created_at": _now_iso(),
        "modified_at": _now_iso(),
        "analysis_status": {},
        "current_plan_version": 0,
        "export_history": [],
    }

    # Merge with existing data if file exists (preserve fields)
    if paths.project_json.exists():
        try:
            with open(paths.project_json, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing.update({k: v for k, v in data.items() if v is not None})
            data = existing
            data["modified_at"] = _now_iso()
        except (json.JSONDecodeError, OSError):
            pass

    tmp_path = paths.project_json.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, paths.project_json)
    except OSError as e:
        logger.warning("Failed to save project simple: %s", e)


def load_project(project_dir: Path) -> Any:
    """Load project config from project.json."""
    paths = ProjectPaths(project_dir)

    if not paths.project_json.exists():
        raise ProjectNotFoundError(
            f"Project file not found: {paths.project_json}",
        )

    try:
        with open(paths.project_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ProjectCorruptError(
            f"Invalid JSON in project file: {paths.project_json}",
            details=str(e),
        )

    # Schema migration
    schema_version = data.get("schema_version", 1)
    if schema_version > PROJECT_SCHEMA_VERSION:
        raise ProjectCorruptError(
            f"Project schema version {schema_version} is newer than "
            f"supported version {PROJECT_SCHEMA_VERSION}",
        )

    try:
        source_path = data.get("source_path", "")
        source = SimpleNamespace(original_path=source_path) if source_path else None
        genre_val = data.get("genre", "talking_head")
        try:
            genre = Genre(genre_val)
        except ValueError:
            genre = Genre.TALKING_HEAD

        config = SimpleNamespace(
            name=data.get("name", project_dir.stem),
            source=source,
            source_path=Path(source_path) if source_path else None,
            source_hash=data.get("source_hash", ""),
            genre=genre,
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", _now_iso()),
            state=JobState(data.get("state", "idle")),
            candidate_count=data.get("candidate_count", 0),
            current_plan_version=data.get("current_plan_version", 0),
            export_history=data.get("export_history", []),
            schema_version=schema_version,
        )
        logger.info("Project loaded: %s (state=%s)", config.name, config.state.value)
        return config
    except (KeyError, ValueError) as e:
        raise ProjectCorruptError(
            f"Invalid data in project file: {e}",
            details=str(e),
        )


def create_project(
    project_dir: Path,
    name: str,
    source_path: Path,
    source_hash: str,
    genre: Genre,
) -> Any:
    """Create a new project with directory structure."""
    paths = ProjectPaths(project_dir)
    paths.create_all()

    config = Any(
        name=name,
        source_path=source_path,
        source_hash=source_hash,
        genre=genre,
        created_at=_now_iso(),
        modified_at=_now_iso(),
        state=JobState.IDLE,
        schema_version=PROJECT_SCHEMA_VERSION,
    )

    save_project(paths, config)
    logger.info("Project created: %s at %s", name, project_dir)
    return config
