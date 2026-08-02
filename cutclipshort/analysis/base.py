"""Analysis engine protocol and base class.

Every analysis engine must implement the AnalysisEngine protocol.
Engines are independent, cacheable, and resumable.

v2 changes:
- Cache now stores config_hash alongside engine_version for double validation
- load_cached() validates both version AND config_hash
- Added cache metadata (timestamp, elapsed_sec)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable

from cutclipshort.types import SourceAsset

logger = logging.getLogger(__name__)


@runtime_checkable
class AnalysisEngine(Protocol):
    """Contract every analysis engine must implement."""

    @property
    def name(self) -> str:
        """Unique engine identifier. e.g. 'scene', 'motion', 'speech'."""
        ...

    @property
    def version(self) -> str:
        """Semantic version. Cache invalidates when version changes."""
        ...

    @property
    def depends_on(self) -> list[str]:
        """Names of engines that must run before this one. [] if independent."""
        ...

    def config_hash(self, config: dict[str, Any]) -> str:
        """Deterministic hash of config keys that affect output.
        Used for cache invalidation."""
        ...

    def run(
        self,
        source: Path,
        media_info: SourceAsset,
        config: dict[str, Any],
        cache_dir: Path,
        progress_callback: Callable[[float], None],
    ) -> dict[str, Any]:
        """Execute analysis. Returns engine-specific result dict.

        Must write cacheable artifacts to cache_dir.
        Must be idempotent: if cache_dir already has valid output, return it.
        Raises AnalysisError on failure.
        """
        ...

    def load_cached(self, cache_dir: Path) -> dict[str, Any] | None:
        """Load previously computed result from cache_dir.
        Returns None if cache is missing or invalid."""
        ...


class BaseAnalysisEngine(ABC):
    """Abstract base class with common cache utilities.

    Validates cache by checking BOTH engine version AND config hash.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        ...

    @property
    def depends_on(self) -> list[str]:
        return []

    def config_hash(self, config: dict[str, Any]) -> str:
        """Default config hash: JSON-serialize relevant keys and SHA-256."""
        relevant = self._relevant_config_keys(config)
        raw = json.dumps(relevant, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _relevant_config_keys(self, config: dict[str, Any]) -> dict[str, Any]:
        """Override to select which config keys affect output.
        Default: return entire config dict."""
        return config

    def _cache_path(self, cache_dir: Path) -> Path:
        """Standard cache file path for this engine."""
        return cache_dir / f"{self.name}.json"

    def load_cached(
        self,
        cache_dir: Path,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Load cached result if available.

        Validates both engine version and config hash (if config provided).
        """
        path = self._cache_path(cache_dir)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate cache version
            cached_version = data.get("_engine_version")
            if cached_version != self.version:
                logger.info(
                    "Cache version mismatch for %s: %s != %s",
                    self.name, cached_version, self.version,
                )
                return None

            # Validate config hash (if config provided and hash stored)
            if config is not None:
                current_hash = self.config_hash(config)
                cached_hash = data.get("_config_hash")
                if cached_hash is not None and cached_hash != current_hash:
                    logger.info(
                        "Cache config mismatch for %s: %s != %s",
                        self.name, cached_hash, current_hash,
                    )
                    return None

            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load cache for %s: %s", self.name, e)
            return None

    def _save_cache(
        self,
        cache_dir: Path,
        data: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> None:
        """Save result to cache with metadata."""
        cache_dir.mkdir(parents=True, exist_ok=True)
        data["_engine_version"] = self.version
        data["_engine_name"] = self.name
        data["_cached_at"] = time.time()

        # Store config hash for downstream validation
        if config is not None:
            data["_config_hash"] = self.config_hash(config)

        path = self._cache_path(cache_dir)
        tmp_path = path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            import os
            os.replace(tmp_path, path)
            logger.debug("Cache saved: %s", path)
        except OSError as e:
            logger.error("Failed to save cache for %s: %s", self.name, e)
