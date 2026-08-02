"""Artifact store: manages rendered segments, previews, exports.

Supports selective re-render by computing render hashes.
If a ClipSpec hasn't changed, its rendered segment is reused.

Uses per-candidate render directories (not a global segments dir).
Index stored at candidates/.render_index.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from cutclipshort.storage.paths import ProjectPaths
from cutclipshort.types import ClipSpec

logger = logging.getLogger(__name__)


def clip_render_hash(clip: ClipSpec) -> str:
    """Compute a deterministic hash of render-affecting fields.

    Used to detect if a clip needs re-rendering after an EditPlan change.
    Only fields that affect the rendered output are included.
    """
    framing_data = None
    if clip.primary_framing:
        f = clip.primary_framing
        framing_data = {
            "cx_start": f.cx_start, "cy_start": f.cy_start,
            "cx_end": f.cx_end, "cy_end": f.cy_end,
            "zoom_start": f.zoom_start, "zoom_end": f.zoom_end,
        }

    # Capture ALL caption fields that affect the burned output, not just the
    # preset name. Position, font size, colors, outline, box and chars/line all
    # change pixels — omitting them meant edits (e.g. moving sub from center to
    # bottom) reused a stale render. Only hashed when captions are actually on,
    # so toggling style while sub is off doesn't force a pointless re-render.
    caption_style_data = None
    if clip.caption_enabled and clip.caption_style:
        cs = clip.caption_style
        caption_style_data = {
            "preset_name": cs.preset_name,
            "font_family": cs.font_family,
            "font_size": cs.font_size,
            "font_color": cs.font_color,
            "active_word_color": cs.active_word_color,
            "outline_color": cs.outline_color,
            "outline_width": cs.outline_width,
            "shadow_enabled": cs.shadow_enabled,
            "shadow_color": cs.shadow_color,
            "bg_box_enabled": cs.bg_box_enabled,
            "bg_box_color": cs.bg_box_color,
            "position": cs.position,
            "max_chars_per_line": cs.max_chars_per_line,
        }

    data = {
        "source_range_start": clip.source_range.start,
        "source_range_end": clip.source_range.end,
        "speed_factor": clip.speed_factor,
        "color_config": clip.color_config,
        "framing": framing_data,
        "audio_demucs": clip.audio_config.demucs_enabled if clip.audio_config else False,
        "audio_gains": clip.audio_config.stem_gains if clip.audio_config else {},
        "audio_lufs": clip.audio_config.loudnorm_lufs if clip.audio_config else -14.0,
        "caption_enabled": clip.caption_enabled,
        "caption_style": caption_style_data,
        "target_width": clip.target_width,
        "target_height": clip.target_height,
    }
    raw = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class ArtifactStore:
    """Manages rendered artifacts with hash-based reuse.

    Tracks which clips have been rendered and with what parameters.
    Enables selective re-render: only clips whose render hash changed
    need to be re-rendered.

    Index file: {project}/candidates/.render_index.json
    Rendered files: {project}/candidates/{clip_id}/renders/
    """

    def __init__(self, paths: ProjectPaths) -> None:
        self._paths = paths
        self._index_path = paths.candidates_dir / ".render_index.json"
        self._index = self._load_index()

    def _load_index(self) -> dict[str, str]:
        """Load render index: {clip_id: render_hash}."""
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupt render index, starting fresh")
                return {}
        return {}

    def _save_index(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._index_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._index_path)

    def needs_render(
        self,
        clip: ClipSpec,
        variant_type: str = "preview",
        variant_version: int = 1,
    ) -> bool:
        """Check if a clip needs (re-)rendering.

        Returns True if:
        - render hash has changed (edit plan modified)
        - rendered file doesn't exist on disk
        """
        current_hash = clip_render_hash(clip)
        # Key includes variant type to track preview vs final separately
        cache_key = f"{clip.clip_id}:{variant_type}"

        if self._index.get(cache_key) != current_hash:
            return True

        # Check if file actually exists
        if variant_type == "preview":
            variant_id = f"preview_v{variant_version:03d}"
        else:
            ar_str = clip.primary_aspect_ratio.value.replace(":", "x")
            variant_id = f"final_{ar_str}_v{variant_version:03d}"

        video_path = self._paths.render_variant_video(clip.clip_id, variant_id)
        return not video_path.exists()

    def mark_rendered(
        self,
        clip: ClipSpec,
        variant_type: str = "preview",
    ) -> None:
        """Mark a clip+variant as successfully rendered."""
        cache_key = f"{clip.clip_id}:{variant_type}"
        self._index[cache_key] = clip_render_hash(clip)
        self._save_index()

    def get_changed_clips(
        self,
        clips: list[ClipSpec],
        variant_type: str = "preview",
    ) -> list[ClipSpec]:
        """Return only clips that need re-rendering."""
        return [
            clip for clip in clips
            if self.needs_render(clip, variant_type)
        ]

    def invalidate(self, clip_id: str) -> None:
        """Invalidate all cached renders for a clip (after user edits)."""
        keys_to_remove = [
            k for k in self._index if k.startswith(f"{clip_id}:")
        ]
        for k in keys_to_remove:
            del self._index[k]
        if keys_to_remove:
            self._save_index()
            logger.info("Invalidated render cache for %s", clip_id)

    def clean_orphaned(self, active_clip_ids: set[str]) -> int:
        """Remove render index entries for clips no longer in the plan."""
        removed = 0
        for key in list(self._index.keys()):
            clip_id = key.split(":")[0]
            if clip_id not in active_clip_ids:
                del self._index[key]
                removed += 1

        if removed:
            self._save_index()
            logger.info("Cleaned %d orphaned render index entries", removed)
        return removed
