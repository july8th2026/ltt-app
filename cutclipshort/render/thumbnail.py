"""Thumbnail generator — extracts keyframes from source video for clip cards.

Generates two thumbnails per candidate:
1. Hook frame: captured at clip start + 1s (the first impression frame)
2. Keyframe: captured at clip midpoint (representative content)

Thumbnails are stored in candidates/{id}/thumbnails/ and referenced by GUI.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cutclipshort.storage.paths import ProjectPaths

logger = logging.getLogger(__name__)

THUMB_WIDTH = 320  # px — enough for card display, small file


def generate_thumbnails(
    source_path: Path,
    paths: ProjectPaths,
    candidates: list[dict],
) -> dict[str, dict[str, str]]:
    """Generate thumbnails for all candidates.

    Args:
        source_path: Path to source video file.
        paths: ProjectPaths for thumbnail locations.
        candidates: List of candidate dicts with start_time/end_time.

    Returns:
        Dict mapping candidate_id → {"hook": path, "keyframe": path}
    """
    from cutclipshort.adapters.ffmpeg import FFmpegAdapter

    try:
        ffmpeg = FFmpegAdapter()
        if not ffmpeg.check_available():
            logger.warning("FFmpeg not available, skipping thumbnail generation")
            return {}
    except Exception as exc:
        logger.warning("FFmpeg check failed, skipping thumbnails")
        return {}

    results: dict[str, dict[str, str]] = {}

    for cand in candidates:
        cid = cand.get("candidate_id", "")
        start = cand.get("start_time", 0)
        end = cand.get("end_time", 0)
        duration = end - start

        if not cid or duration <= 0:
            continue

        hook_path = paths.candidate_hook_thumb(cid)
        key_path = paths.candidate_keyframe_thumb(cid)

        thumbs: dict[str, str] = {}

        # Hook frame: 1 second into clip (or start if very short)
        hook_time = start + min(1.0, duration * 0.1)
        try:
            ffmpeg.extract_thumbnail(
                source_path, hook_path,
                time_sec=hook_time, width=THUMB_WIDTH,
            )
            if hook_path.exists():
                thumbs["hook"] = str(hook_path)
        except Exception as e:
            logger.debug("Hook thumb failed for %s: %s", cid, e)

        # Keyframe: midpoint of clip
        mid_time = start + duration / 2
        try:
            ffmpeg.extract_thumbnail(
                source_path, key_path,
                time_sec=mid_time, width=THUMB_WIDTH,
            )
            if key_path.exists():
                thumbs["keyframe"] = str(key_path)
        except Exception as e:
            logger.debug("Keyframe thumb failed for %s: %s", cid, e)

        if thumbs:
            results[cid] = thumbs

    logger.info("Generated thumbnails for %d/%d candidates", len(results), len(candidates))
    return results
