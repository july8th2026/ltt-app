"""Analysis runner — high-level entry point for the analysis pipeline.

This is the single function to call for end-to-end analysis:
  source video → ffprobe → register engines → run pipeline → save artifacts

Usage:
    from cutclipshort.core.analysis_runner import run_full_analysis
    result = run_full_analysis(
        video_path=Path("my_video.mp4"),
        project_dir=Path("projects/my_project"),
        genre="talking_head",
    )
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from cutclipshort.core.config import AppConfig
from cutclipshort.core.event_bus import EventBus
from cutclipshort.core.pipeline import Pipeline
from cutclipshort.core.registry import AdapterRegistry
from cutclipshort.core.run_logger import RunLogger
from cutclipshort.storage.media_index import compute_source_hash
from cutclipshort.storage.paths import ProjectPaths
from cutclipshort.types import AnalysisResult, SourceAsset

logger = logging.getLogger(__name__)


def run_full_analysis(
    video_path: Path,
    project_dir: Path,
    *,
    genre: str = "talking_head",
    config: AppConfig | None = None,
    event_bus: EventBus | None = None,
    engines_to_run: list[str] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[str, float], None] | None = None,
) -> AnalysisResult:
    """Run full analysis pipeline on a video.

    This is the main entry point. It:
    1. Creates project directory structure
    2. Probes source media with ffprobe
    3. Registers all available analysis engines
    4. Runs pipeline with cache/resume support
    5. Saves artifacts to project workspace

    Args:
        video_path: Path to source video file.
        project_dir: Root directory for this project.
        genre: Content genre (affects content classification thresholds).
        config: App config (uses defaults if None).
        event_bus: Event bus for progress events (creates one if None).
        engines_to_run: If set, only run these engines. None = all.
        cancel_check: Callable returning True to abort.
        progress_callback: Called with (engine_name, pct) during analysis.

    Returns:
        AnalysisResult with all engine outputs aggregated.
    """
    t0 = time.perf_counter()

    config = config or AppConfig()
    event_bus = event_bus or EventBus()
    paths = ProjectPaths(project_dir)
    paths.create_all()

    run_log = RunLogger(paths, project_dir.name)

    # ── Step 1: Probe source ─────────────────────────────────────────
    run_log.log_stage_start("probe")
    source_asset = _probe_source(video_path, paths)
    run_log.log_stage_end("probe", {
        "duration_sec": source_asset.duration_sec,
        "resolution": f"{source_asset.width}x{source_asset.height}",
        "fps": source_asset.fps,
        "video_codec": source_asset.video_codec,
        "audio_codec": source_asset.audio_codec,
    })

    logger.info(
        "Source: %s — %.1fs, %dx%d, %.1ffps, %s/%s",
        source_asset.file_name,
        source_asset.duration_sec,
        source_asset.width, source_asset.height,
        source_asset.fps,
        source_asset.video_codec, source_asset.audio_codec,
    )

    # ── Step 2: Register engines ─────────────────────────────────────
    adapters = AdapterRegistry(config)
    adapter_status = adapters.check_all()
    run_log.log_metric("adapters", adapter_status)

    pipeline = Pipeline(event_bus, config, adapters)
    _register_engines(pipeline, config)

    # Wire progress callback to event bus
    # progress_callback(engine_name, pct, message="") — pct=-1.0 signals failure
    if progress_callback:
        import inspect
        # Support both 2-arg and 3-arg callbacks
        _accepts_msg = len(inspect.signature(progress_callback).parameters) >= 3

        def _on_progress(data):
            if _accepts_msg:
                progress_callback(data.engine_name, data.pct, data.message)
            else:
                progress_callback(data.engine_name, data.pct)

        event_bus.on("analysis.progress", _on_progress)

    # Wire per-engine timing into RunLogger
    event_bus.on("analysis.engine.done", lambda data: run_log.log_engine_end(
        data.engine_name, {"elapsed_sec": round(data.elapsed_sec, 2)},
    ))

    # ── Step 3: Run analysis pipeline ────────────────────────────────
    run_log.log_stage_start("analysis")

    try:
        result = pipeline.run_analysis(
            source_path=video_path,
            media_info=source_asset,
            paths=paths,
            engines_to_run=engines_to_run,
            cancel_check=cancel_check,
        )
    except Exception as e:
        run_log.log_error("analysis", str(e))
        run_log.finalize()
        raise

    run_log.log_stage_end("analysis", {
        "scenes": len(result.scenes),
        "transcript_segments": len(result.transcript),
        "visual_segments": len(result.visual_segments),
        "audio_segments": len(result.audio_segments),
        "engine_versions": result.engine_versions,
    })

    # ── Step 4: Save summary ─────────────────────────────────────────
    summary_path = run_log.finalize()

    elapsed = time.perf_counter() - t0
    logger.info(
        "Analysis complete: %d scenes, %d transcript segments in %.1fs. "
        "Summary: %s",
        len(result.scenes), len(result.transcript), elapsed,
        summary_path,
    )

    return result


def _probe_source(video_path: Path, paths: ProjectPaths) -> SourceAsset:
    """Probe video and save/load media info."""
    # Check if already probed — validate source hash to detect changed video
    if paths.media_info_json.exists():
        try:
            current_hash = compute_source_hash(video_path)
            saved_hash = paths.source_hash_file.read_text(encoding="utf-8").strip() if paths.source_hash_file.exists() else ""
            if current_hash == saved_hash:
                with open(paths.media_info_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return SourceAsset(**data)
            else:
                logger.info("Source video changed (hash mismatch), re-probing")
        except (json.JSONDecodeError, TypeError, KeyError):
            logger.warning("Corrupt media_info.json, re-probing")

    # Probe
    from cutclipshort.adapters.ffmpeg import FFprobeAdapter
    source_hash = compute_source_hash(video_path)

    ffprobe = FFprobeAdapter()
    source_asset = ffprobe.get_media_info(video_path, source_hash)

    # Save
    paths.source_dir.mkdir(parents=True, exist_ok=True)
    with open(paths.media_info_json, "w", encoding="utf-8") as f:
        json.dump(asdict(source_asset), f, ensure_ascii=False, indent=2, default=str)

    paths.source_hash_file.write_text(source_hash, encoding="utf-8")

    return source_asset


def _register_engines(pipeline: Pipeline, config: AppConfig) -> None:
    """Register all analysis engines with the pipeline."""
    from cutclipshort.analysis.scene_engine import SceneEngine
    from cutclipshort.analysis.motion_engine import MotionEngine
    from cutclipshort.analysis.speech_engine import SpeechEngine
    from cutclipshort.analysis.audio_engine import AudioEngine
    from cutclipshort.analysis.visual_engine import VisualEngine
    from cutclipshort.analysis.content_engine import ContentEngine

    engines = [
        SceneEngine(),
        MotionEngine(),
        SpeechEngine(),
        AudioEngine(),
        VisualEngine(),
        ContentEngine(),
    ]

    for engine in engines:
        pipeline.register_engine(engine)
        logger.debug("Registered engine: %s v%s (deps: %s)",
                      engine.name, engine.version, engine.depends_on)
