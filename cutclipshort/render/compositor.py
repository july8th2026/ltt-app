"""Render compositor — orchestrates rendering of a complete clip.

Full pipeline for one clip:
  1. Render video segment (crop + color + speed + loudnorm + captions via ASS)
  2. Process audio with demucs (if enabled) + replace audio track
  3. Produce final output

Captions are burned in Step 1 as part of the video filter chain (single-pass).
Each step is fail-safe: if demucs fails, original audio is kept.
If caption generation fails, video without captions is kept.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Any, Callable

from cutclipshort.storage.paths import ProjectPaths
from cutclipshort.types import ClipSpec, ExportProfile, RenderSettings, RenderVariantType

logger = logging.getLogger(__name__)


class Compositor:
    """Orchestrates the full render of a single clip."""

    def __init__(self, source_path: Path, paths: ProjectPaths) -> None:
        self._source = source_path
        self._paths = paths

    def render_clip(
        self,
        clip: ClipSpec,
        variant_type: RenderVariantType,
        profile: ExportProfile | None = None,
        variant_version: int = 1,
        progress_callback: Callable[[float], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
        max_retries: int = 2,
    ) -> Path:
        """Render a single clip through the full pipeline.

        Args:
            cancel_check: Callable that returns True if render should abort.
            max_retries: Max attempts before giving up (default 2).

        Returns:
            Path to the final rendered .mp4 file.

        Raises:
            RenderError: If all retry attempts fail.
            PipelineCancelledError: If cancel_check returns True.
        """
        for attempt in range(max_retries):
            try:
                return self._render_pipeline(
                    clip, variant_type, profile, variant_version,
                    progress_callback, cancel_check,
                )
            except Exception as e:
                if cancel_check and cancel_check():
                    raise
                if attempt < max_retries - 1:
                    logger.warning(
                        "Render attempt %d/%d failed for %s: %s",
                        attempt + 1, max_retries, clip.clip_id, e,
                    )
                    import time as _t
                    _t.sleep(0.5)
                else:
                    raise
        raise RuntimeError("Unreachable")  # Satisfy type checker

    def _render_pipeline(
        self,
        clip: ClipSpec,
        variant_type: RenderVariantType,
        profile: ExportProfile | None,
        variant_version: int,
        progress_callback: Callable[[float], None] | None,
        cancel_check: Callable[[], bool] | None,
    ) -> Path:
        """Internal: single-attempt render pipeline."""
        t0 = time.perf_counter()
        is_preview = variant_type == RenderVariantType.PREVIEW

        if is_preview:
            variant_id = f"preview_v{variant_version:03d}"
        else:
            ar_str = clip.primary_aspect_ratio.value.replace(":", "x")
            variant_id = f"final_{ar_str}_v{variant_version:03d}"

        output_path = self._paths.render_variant_video(clip.clip_id, variant_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        settings = profile.render_settings if profile else RenderSettings()

        def _progress(pct: float) -> None:
            if progress_callback:
                progress_callback(pct)

        # ── Cancel check before heavy work ──
        if cancel_check and cancel_check():
            from cutclipshort.errors import PipelineCancelledError
            raise PipelineCancelledError("Render cancelled before start")

        # ── Step 1: Render video segment (crop + color + speed + loudnorm) ──
        _progress(0.05)
        from cutclipshort.render.segment_renderer import render_segment

        render_segment(
            clip=clip,
            source_path=self._source,
            output_path=output_path,
            render_settings=settings,
            is_preview=is_preview,
            cancel_check=cancel_check,
        )
        _progress(0.60)

        current_output = output_path

        # ── Cancel check between steps ──
        if cancel_check and cancel_check():
            from cutclipshort.errors import PipelineCancelledError
            raise PipelineCancelledError("Render cancelled after video segment")

        # ── Step 2: Demucs audio processing (FINAL only) ────────────────
        if clip.audio_config.demucs_enabled and not is_preview:
            current_output = self._apply_demucs(clip, current_output, output_path)
            _progress(0.80)

        # Captions are now burned in Step 1 (segment_renderer) via ASS filter
        # — unified single-pass rendering, no separate Step 3 needed.

        _progress(1.0)

        elapsed = time.perf_counter() - t0

        # Render diagnostics
        output_size = current_output.stat().st_size if current_output.exists() else 0
        clip_dur = clip.source_range.end - clip.source_range.start
        speed_ratio = clip_dur / elapsed if elapsed > 0 else 0

        logger.info(
            "Compositor: %s → %s in %.1fs (%.1fx realtime, %.1fMB, %s)",
            clip.clip_id, variant_id, elapsed, speed_ratio,
            output_size / (1024 * 1024),
            "preview" if is_preview else "final",
        )

        # Save render variant metadata
        self._save_variant_metadata(
            clip.clip_id, variant_id, variant_type,
            elapsed, output_size, current_output,
        )

        return current_output

    def _save_variant_metadata(
        self,
        clip_id: str,
        variant_id: str,
        variant_type: RenderVariantType,
        elapsed_sec: float,
        output_size_bytes: int,
        output_path: Path,
    ) -> None:
        """Save metadata about the rendered variant."""
        import json
        meta = {
            "variant_id": variant_id,
            "variant_type": variant_type.value,
            "clip_id": clip_id,
            "output_path": str(output_path),
            "elapsed_sec": round(elapsed_sec, 2),
            "output_size_bytes": output_size_bytes,
            "output_size_mb": round(output_size_bytes / (1024 * 1024), 2),
        }
        meta_path = self._paths.render_variant_json(clip_id, variant_id)
        try:
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Failed to save variant metadata: %s", e)

    # ── Step 2 implementation ────────────────────────────────────────

    def _apply_demucs(
        self, clip: ClipSpec, video_path: Path, final_path: Path,
    ) -> Path:
        """Run demucs audio separation and replace audio track.

        Fail-safe: if demucs fails, returns original video unchanged.
        """
        try:
            from cutclipshort.render.audio_mixer import process_audio
            from cutclipshort.adapters.ffmpeg import FFmpegAdapter

            work_dir = video_path.parent / f"_audio_{clip.clip_id}"
            work_dir.mkdir(parents=True, exist_ok=True)

            processed_audio = work_dir / "processed.wav"
            process_audio(
                source_path=self._source,
                output_path=processed_audio,
                audio_config=clip.audio_config,
                start_time=clip.source_range.start,
                duration=clip.source_range.duration,
            )

            if not processed_audio.exists():
                logger.warning("Demucs: processed audio not found, keeping original")
                return video_path

            # Replace audio in video
            ffmpeg = FFmpegAdapter()
            demucs_output = video_path.parent / f"_demucs_{video_path.name}"
            ffmpeg.replace_audio(video_path, processed_audio, demucs_output)

            if demucs_output.exists():
                # Replace original with demucs version
                shutil.move(str(demucs_output), str(final_path))
                logger.info("Demucs audio applied: %s", clip.clip_id)
                return final_path
            else:
                logger.warning("Demucs output missing, keeping original")
                return video_path

        except Exception as e:
            logger.warning(
                "Demucs failed for %s, keeping original audio: %s",
                clip.clip_id, e,
            )
            return video_path
        finally:
            # Cleanup work dir
            work_dir = video_path.parent / f"_audio_{clip.clip_id}"
            if work_dir.exists():
                try:
                    shutil.rmtree(work_dir, ignore_errors=True)
                except Exception as e:
                    logger.debug("Cleanup failed for %s: %s", work_dir, e)

    # ── Batch rendering ──────────────────────────────────────────────

    def render_batch(
        self,
        clips: list[ClipSpec],
        variant_type: RenderVariantType,
        profile: ExportProfile | None = None,
        progress_callback: Callable[[float], None] | None = None,
        max_parallel: int = 2,
    ) -> tuple[list[Path], list[str]]:
        """Render multiple clips with optional parallel execution.

        Args:
            max_parallel: Max concurrent renders. Set to 1 for sequential.
                          Default 2 to balance CPU/GPU and disk I/O.

        Returns:
            Tuple of (successful_paths, failed_clip_ids).
        """
        if max_parallel <= 1 or len(clips) <= 1:
            return self._render_batch_sequential(
                clips, variant_type, profile, progress_callback,
            )

        return self._render_batch_parallel(
            clips, variant_type, profile, progress_callback, max_parallel,
        )

    def _render_batch_sequential(
        self,
        clips: list[ClipSpec],
        variant_type: RenderVariantType,
        profile: ExportProfile | None,
        progress_callback: Callable[[float], None] | None,
    ) -> tuple[list[Path], list[str]]:
        """Sequential rendering (original behavior)."""
        results: list[Path] = []
        failed: list[str] = []

        for i, clip in enumerate(clips):
            try:
                path = self.render_clip(clip, variant_type, profile)
                results.append(path)
            except Exception as e:
                logger.error(
                    "Render failed for %s: %s", clip.clip_id, e, exc_info=True,
                )
                failed.append(clip.clip_id)

            if progress_callback:
                progress_callback((i + 1) / len(clips))

        if failed:
            logger.warning(
                "Batch render: %d/%d succeeded, %d failed: %s",
                len(results), len(clips), len(failed), ", ".join(failed),
            )
        return results, failed

    def _render_batch_parallel(
        self,
        clips: list[ClipSpec],
        variant_type: RenderVariantType,
        profile: ExportProfile | None,
        progress_callback: Callable[[float], None] | None,
        max_parallel: int,
    ) -> tuple[list[Path], list[str]]:
        """Parallel rendering using ThreadPoolExecutor."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results: list[Path] = []
        failed: list[str] = []
        completed_count = 0
        total = len(clips)

        logger.info(
            "Batch parallel render: %d clips, max %d concurrent",
            total, max_parallel,
        )

        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {}
            for clip in clips:
                future = executor.submit(
                    self.render_clip, clip, variant_type, profile,
                )
                futures[future] = clip.clip_id

            for future in as_completed(futures):
                clip_id = futures[future]
                completed_count += 1
                try:
                    path = future.result()
                    results.append(path)
                except Exception as e:
                    logger.error(
                        "Parallel render failed for %s: %s",
                        clip_id, e, exc_info=True,
                    )
                    failed.append(clip_id)

                if progress_callback:
                    progress_callback(completed_count / total)

        if failed:
            logger.warning(
                "Batch parallel render: %d/%d succeeded, %d failed: %s",
                len(results), total, len(failed), ", ".join(failed),
            )
        else:
            logger.info("Batch parallel render: %d/%d all succeeded", total, total)

        return results, failed
