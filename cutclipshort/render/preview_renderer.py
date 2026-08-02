"""Preview renderer.

Fast low-resolution render for user review before final export.
480p, CRF 28, veryfast preset — targets 2-5 seconds per 30s clip.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cutclipshort.render.segment_renderer import render_segment
from cutclipshort.storage.paths import ProjectPaths
from cutclipshort.types import ClipSpec, RenderSettings

logger = logging.getLogger(__name__)

PREVIEW_SETTINGS = RenderSettings(
    prefer_nvenc=False,
    x264_preset="veryfast",
    crf="28",
    audio_bitrate="128k",
    audio_sample_rate=44100,
    audio_channels=2,
)


def render_preview(
    clip: ClipSpec,
    source_path: Path,
    paths: ProjectPaths,
    variant_version: int = 1,
) -> Path:
    """Render a low-res preview for a clip.

    Returns path to the preview .mp4 file.
    """
    variant_id = f"preview_v{variant_version:03d}"
    output_path = paths.render_variant_video(clip.clip_id, variant_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    render_segment(
        clip=clip,
        source_path=source_path,
        output_path=output_path,
        render_settings=PREVIEW_SETTINGS,
        is_preview=True,
    )

    # Generate thumbnail
    _extract_thumbnail(source_path, clip, paths)

    logger.info("Preview rendered: %s → %s", clip.clip_id, variant_id)
    return output_path


def render_batch_previews(
    clips: list[ClipSpec],
    source_path: Path,
    paths: ProjectPaths,
    variant_version: int = 1,
    progress_callback=None,
) -> list[Path]:
    """Render previews for multiple clips."""
    results: list[Path] = []
    for i, clip in enumerate(clips):
        try:
            path = render_preview(clip, source_path, paths, variant_version)
            results.append(path)
        except Exception as e:
            logger.error("Preview render failed for %s: %s", clip.clip_id, e)
        if progress_callback:
            progress_callback((i + 1) / len(clips))
    return results


def _extract_thumbnail(
    source_path: Path,
    clip: ClipSpec,
    paths: ProjectPaths,
) -> None:
    """Extract a thumbnail at the hook frame (3s into clip)."""
    import cv2

    thumb_path = paths.candidate_hook_thumb(clip.clip_id)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(source_path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        hook_time = clip.source_range.start + min(3.0, clip.source_range.duration / 2)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(hook_time * fps))
        ret, frame = cap.read()
        if ret:
            # Resize to thumbnail width
            thumb_w = 320
            h, w = frame.shape[:2]
            thumb_h = int(thumb_w * h / w)
            thumb = cv2.resize(frame, (thumb_w, thumb_h))
            cv2.imwrite(str(thumb_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 85])
    except Exception as e:
        logger.debug("Thumbnail extraction failed: %s", e)
    finally:
        cap.release()
