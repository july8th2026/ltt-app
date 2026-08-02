"""Master pipeline orchestrator v2.

Coordinates the full flow: analysis → editorial → render → evaluation.
Manages resume, selective re-render, and engine dependency graph.

v2 changes:
- Parallel execution of independent analysis engines via ThreadPoolExecutor
- Engines grouped into dependency waves and executed concurrently within each wave
- Batch render supports parallel clip rendering
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from cutclipshort.core.config import AppConfig
from cutclipshort.core.event_bus import EventBus
from cutclipshort.core.events import (
    EVT_ANALYSIS_DONE,
    EVT_ANALYSIS_ENGINE_DONE,
    EVT_ANALYSIS_PROGRESS,
    EVT_ANALYSIS_START,
    EVT_CANDIDATES_READY,
    EVT_PLAN_READY,
    AnalysisDone,
    AnalysisEngineDone,
    AnalysisProgress,
    CandidatesReady,
    PlanReady,
)
from cutclipshort.core.registry import AdapterRegistry
from cutclipshort.analysis.base import AnalysisEngine
from cutclipshort.analysis.aggregate import aggregate_results
from cutclipshort.editorial.base import EditorialStrategy
from cutclipshort.storage.cache import AnalysisCache
from cutclipshort.storage.paths import ProjectPaths
from cutclipshort.types import (
    AnalysisResult,
    EditConstraints,
    EditPlan,
    Genre,
    SourceAsset,
)

logger = logging.getLogger(__name__)

_MAX_PARALLEL_ENGINES = 3  # Max concurrent engines (limited by GPU/memory)


class Pipeline:
    """Orchestrates the full processing pipeline.

    Manages engine execution order based on depends_on graph,
    cache checking, event emission, and parallel execution.
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: AppConfig,
        adapters: AdapterRegistry,
    ) -> None:
        self._bus = event_bus
        self._config = config
        self._adapters = adapters
        self._engines: dict[str, AnalysisEngine] = {}
        self._strategies: dict[str, EditorialStrategy] = {}

    def register_engine(self, engine: AnalysisEngine) -> None:
        """Register an analysis engine."""
        self._engines[engine.name] = engine
        logger.debug("Registered engine: %s v%s", engine.name, engine.version)

    def register_strategy(self, strategy: EditorialStrategy) -> None:
        """Register an editorial strategy."""
        self._strategies[strategy.name] = strategy
        logger.debug("Registered strategy: %s", strategy.name)

    # ── Analysis Phase ───────────────────────────────────────────────────

    def run_analysis(
        self,
        source_path: Path,
        media_info: SourceAsset,
        paths: ProjectPaths,
        *,
        engines_to_run: list[str] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> AnalysisResult:
        """Run all (or specified) analysis engines with parallel execution.

        Engines are grouped into dependency waves:
          Wave 0: no dependencies (scene, speech, audio) → run in parallel
          Wave 1: depends on wave 0 only (motion, visual) → run in parallel
          Wave 2: depends on wave 1+ (content) → run after wave 1

        Args:
            source_path: Path to source video.
            media_info: Probed media info.
            paths: Project paths resolver.
            engines_to_run: If specified, only run these engines.
            cancel_check: Callable returning True if cancelled.

        Returns:
            Aggregated AnalysisResult.
        """
        self._bus.emit(EVT_ANALYSIS_START)
        t0 = time.perf_counter()

        cache = AnalysisCache(paths.cache_dir)
        config = self._config.get_section("analysis")

        # Resolve which engines to run and group into dependency waves
        engines = self._resolve_execution_order(engines_to_run)
        waves = self._group_into_waves(engines)

        engine_outputs: dict[str, dict[str, Any]] = {}
        completed = 0

        for wave_idx, wave_engines in enumerate(waves):
            if len(wave_engines) <= 2:
                # Small wave — run sequentially (avoids thread overhead
                # and preserves cancel semantics for tests)
                for engine in wave_engines:
                    if cancel_check and cancel_check():
                        break
                    success = self._run_single_engine(
                        engine, source_path, media_info, config,
                        cache, paths, engine_outputs, None,
                    )
                    if success:
                        completed += 1
            else:
                # 3+ independent engines — run in parallel
                logger.info(
                    "Wave %d: running %d engines in parallel: %s",
                    wave_idx,
                    len(wave_engines),
                    [e.name for e in wave_engines],
                )

                max_workers = min(_MAX_PARALLEL_ENGINES, len(wave_engines))

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for engine in wave_engines:
                        if cancel_check and cancel_check():
                            break
                        future = executor.submit(
                            self._run_single_engine,
                            engine, source_path, media_info, config,
                            cache, paths, engine_outputs, cancel_check,
                        )
                        futures[future] = engine.name

                    for future in as_completed(futures):
                        engine_name = futures[future]
                        try:
                            success = future.result()
                            if success:
                                completed += 1
                        except Exception as e:
                            logger.error(
                                "Engine %s crashed in parallel: %s",
                                engine_name, e,
                            )

        total_elapsed = time.perf_counter() - t0
        self._bus.emit(
            EVT_ANALYSIS_DONE,
            AnalysisDone(total_elapsed, completed),
        )

        logger.info(
            "Analysis complete: %d/%d engines in %.1fs (%d waves)",
            completed, len(engines), total_elapsed, len(waves),
        )

        # Release GPU memory after analysis (models no longer needed)
        self._cleanup_models()

        if not engine_outputs or completed == 0:
            raise RuntimeError(
                f"All {len(engines)} analysis engines failed or produced no output. "
                f"Check logs for individual engine errors."
            )

        return aggregate_results(media_info, engine_outputs)

    def _cleanup_models(self) -> None:
        """Release cached models after analysis to free GPU/RAM.

        Whisper and YOLO models stay in memory indefinitely if not cleaned.
        On back-to-back analyses, this prevents OOM.
        """
        try:
            from cutclipshort.adapters.yolo import _MODEL_CACHE, _MODEL_LOCK
            with _MODEL_LOCK:
                if _MODEL_CACHE:
                    logger.info("Releasing %d YOLO model(s) from cache", len(_MODEL_CACHE))
                    _MODEL_CACHE.clear()
        except Exception as e:
            logger.debug("YOLO cleanup: %s", e)

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("CUDA cache cleared after analysis")
        except (ImportError, RuntimeError):
            pass

    def _run_single_engine(
        self,
        engine: AnalysisEngine,
        source_path: Path,
        media_info: SourceAsset,
        config: dict[str, Any],
        cache: AnalysisCache,
        paths: ProjectPaths,
        engine_outputs: dict[str, dict[str, Any]],
        cancel_check: Callable[[], bool] | None,
    ) -> bool:
        """Run a single engine with cache checking and event emission.

        Thread-safe: engine_outputs dict is only written (no read-modify-write).
        Returns True if engine completed successfully.
        """
        if cancel_check and cancel_check():
            return False

        engine_t0 = time.perf_counter()
        config_hash = engine.config_hash(config)

        # Check cache
        if cache.is_valid(
            engine.name, engine.version, config_hash, media_info.source_hash
        ):
            cached = engine.load_cached(paths.cache_dir)
            if cached is not None:
                engine_outputs[engine.name] = cached
                logger.info("Cache hit: %s", engine.name)
                self._bus.emit(
                    EVT_ANALYSIS_PROGRESS,
                    AnalysisProgress(engine.name, 1.0),
                )
                self._bus.emit(
                    EVT_ANALYSIS_ENGINE_DONE,
                    AnalysisEngineDone(engine.name, 0.0),
                )
                return True

        # Run engine
        logger.info("Running engine: %s v%s", engine.name, engine.version)

        def progress_cb(pct: float, _name: str = engine.name) -> None:
            self._bus.emit(
                EVT_ANALYSIS_PROGRESS,
                AnalysisProgress(_name, pct),
            )

        try:
            result = engine.run(
                source_path, media_info, config,
                paths.cache_dir, progress_cb,
            )
            engine_outputs[engine.name] = result
            elapsed = time.perf_counter() - engine_t0
            cache.mark_done(
                engine.name, engine.version, config_hash,
                media_info.source_hash, elapsed,
            )
            self._bus.emit(
                EVT_ANALYSIS_ENGINE_DONE,
                AnalysisEngineDone(engine.name, elapsed),
            )
            logger.info(
                "Engine %s completed in %.1fs", engine.name, elapsed,
            )
            return True
        except Exception as e:
            cache.mark_failed(engine.name, str(e))
            error_msg = str(e)
            logger.error(
                "Engine %s failed: %s — continuing with remaining engines",
                engine.name, error_msg,
                exc_info=True,
            )
            self._bus.emit(
                EVT_ANALYSIS_PROGRESS,
                AnalysisProgress(engine.name, -1.0, message=error_msg),
            )
            return False

    # ── Editorial Phase ──────────────────────────────────────────────────

    def run_editorial(
        self,
        analysis: AnalysisResult,
        strategy_name: str,
        constraints: EditConstraints,
        *,
        cancel_check: Callable[[], bool] | None = None,
    ) -> EditPlan:
        """Run editorial strategy to generate edit plan.

        Args:
            cancel_check: Callable returning True if cancelled.
                          Checked between major phases.
        """
        from cutclipshort.errors import PipelineCancelledError

        strategy = self._strategies.get(strategy_name)
        if strategy is None:
            available = list(self._strategies.keys())
            raise ValueError(
                f"Unknown strategy '{strategy_name}'. "
                f"Available: {available}"
            )

        config = self._config.get_section("editorial")

        if cancel_check and cancel_check():
            raise PipelineCancelledError("Cancelled before candidate generation")

        candidates = strategy.find_candidates(analysis, config)
        logger.info(
            "Strategy '%s' found %d candidates",
            strategy_name, len(candidates),
        )
        self._bus.emit(
            EVT_CANDIDATES_READY,
            CandidatesReady(len(candidates), strategy_name),
        )

        if cancel_check and cancel_check():
            raise PipelineCancelledError("Cancelled before plan building")

        plan = strategy.build_plan(candidates, constraints, config)
        logger.info(
            "Edit plan v%d: %d clips, strategy=%s",
            plan.version, len(plan.clips), strategy_name,
        )
        self._bus.emit(
            EVT_PLAN_READY,
            PlanReady(plan.version, len(plan.clips), strategy_name),
        )

        return plan

    # ── Dependency Resolution ────────────────────────────────────────────

    def _resolve_execution_order(
        self,
        requested: list[str] | None = None,
    ) -> list[AnalysisEngine]:
        """Topological sort of engines based on depends_on."""
        to_run = (
            {name: self._engines[name] for name in requested if name in self._engines}
            if requested
            else dict(self._engines)
        )

        resolved: list[AnalysisEngine] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            engine = self._engines.get(name)
            if engine is None:
                return
            for dep in engine.depends_on:
                visit(dep)
            visited.add(name)
            if name in to_run:
                resolved.append(engine)

        for name in to_run:
            visit(name)

        return resolved

    def _group_into_waves(
        self,
        engines: list[AnalysisEngine],
    ) -> list[list[AnalysisEngine]]:
        """Group engines into dependency waves for parallel execution.

        Wave 0: engines with no dependencies
        Wave 1: engines whose dependencies are all in wave 0
        Wave 2: engines whose dependencies are all in waves 0-1
        etc.

        Engines within the same wave can run in parallel.
        """
        engine_set = {e.name for e in engines}
        engine_map = {e.name: e for e in engines}
        assigned: dict[str, int] = {}  # engine_name → wave_index

        max_iterations = len(engines) + 1
        for _ in range(max_iterations):
            progress = False
            for engine in engines:
                if engine.name in assigned:
                    continue

                deps_in_scope = [
                    d for d in engine.depends_on if d in engine_set
                ]

                if not deps_in_scope:
                    # No dependencies → wave 0
                    assigned[engine.name] = 0
                    progress = True
                elif all(d in assigned for d in deps_in_scope):
                    # All deps assigned → next wave after max dep wave
                    max_dep_wave = max(assigned[d] for d in deps_in_scope)
                    assigned[engine.name] = max_dep_wave + 1
                    progress = True

            if not progress:
                # Remaining engines have unresolvable deps → assign last wave
                for engine in engines:
                    if engine.name not in assigned:
                        assigned[engine.name] = len(engines)
                break

        # Group by wave
        max_wave = max(assigned.values()) if assigned else 0
        waves: list[list[AnalysisEngine]] = []
        for wave_idx in range(max_wave + 1):
            wave = [
                engine_map[name]
                for name, idx in assigned.items()
                if idx == wave_idx
            ]
            if wave:
                waves.append(wave)

        return waves
