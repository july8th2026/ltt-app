"""Analysis result cache with invalidation.

Cache is keyed by (source_hash, engine_name, engine_version, config_hash).
Invalidation occurs when any key component changes.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from cutclipshort.errors import StorageError

logger = logging.getLogger(__name__)


class AnalysisCache:
    """Manages analysis cache with smart invalidation.

    Cache manifest tracks what was cached and with which parameters.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._manifest_path = cache_dir / "analysis_manifest.json"
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, Any]:
        if self._manifest_path.exists():
            try:
                with open(self._manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupt cache manifest, starting fresh")
        return {"engines": {}}

    def _save_manifest(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._manifest_path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._manifest, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._manifest_path)
        except OSError as e:
            logger.error("Failed to save cache manifest: %s", e)

    def is_valid(
        self,
        engine_name: str,
        engine_version: str,
        config_hash: str,
        source_hash: str,
    ) -> bool:
        """Check if cached result is still valid."""
        entry = self._manifest.get("engines", {}).get(engine_name)
        if entry is None:
            return False
        return (
            entry.get("engine_version") == engine_version
            and entry.get("config_hash") == config_hash
            and entry.get("source_hash") == source_hash
            and entry.get("status") == "done"
        )

    def mark_done(
        self,
        engine_name: str,
        engine_version: str,
        config_hash: str,
        source_hash: str,
        elapsed_sec: float = 0.0,
    ) -> None:
        """Mark an engine's cache as valid."""
        if "engines" not in self._manifest:
            self._manifest["engines"] = {}

        self._manifest["engines"][engine_name] = {
            "engine_version": engine_version,
            "config_hash": config_hash,
            "source_hash": source_hash,
            "status": "done",
            "elapsed_sec": round(elapsed_sec, 2),
        }
        self._save_manifest()

    def mark_failed(self, engine_name: str, error: str) -> None:
        """Mark an engine's cache as failed."""
        if "engines" not in self._manifest:
            self._manifest["engines"] = {}

        self._manifest["engines"][engine_name] = {
            "status": "failed",
            "error": error,
        }
        self._save_manifest()

    def invalidate(self, engine_name: str) -> None:
        """Invalidate a specific engine's cache."""
        self._manifest.get("engines", {}).pop(engine_name, None)
        self._save_manifest()
        logger.info("Cache invalidated for engine: %s", engine_name)

    def invalidate_all(self) -> None:
        """Invalidate all cached results."""
        self._manifest = {"engines": {}}
        self._save_manifest()
        logger.info("All cache invalidated")

    def get_status(self) -> dict[str, str]:
        """Get status of all engines. Returns {engine_name: status}."""
        return {
            name: entry.get("status", "unknown")
            for name, entry in self._manifest.get("engines", {}).items()
        }
