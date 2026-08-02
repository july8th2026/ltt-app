"""Clip planner: converts candidates into a concrete EditPlan.

Resolves all render parameters (framing, color, audio, captions)
into self-contained ClipSpec objects.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from cutclipshort.presets.color_presets import get_color_preset
from cutclipshort.types import (
    AnalysisResult,
    AspectRatio,
    AudioConfig,
    CandidateClip,
    CaptionStyle,
    ClipSpec,
    EditConstraints,
    EditPlan,
    FramingParams,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


def build_plan(
    candidates: list[CandidateClip],
    analysis: AnalysisResult,
    constraints: EditConstraints,
    config: dict[str, Any],
) -> EditPlan:
    """Build a complete EditPlan from selected candidates.

    For each candidate, resolves:
    - Framing parameters (from YOLO detections)
    - Color preset (from config)
    - Audio config (from config)
    - Caption segments (filtered from transcript)
    - Render hash (for selective re-render)
    """
    color_preset_name = config.get("default_color", "original")
    color_config = get_color_preset(color_preset_name)
    caption_enabled = config.get("caption_default", True)

    clips: list[ClipSpec] = []
    for cand in candidates:
        framing = _resolve_framing(cand, analysis, constraints)
        caption_segs = _extract_caption_segments(cand, analysis)

        spec = ClipSpec(
            clip_id=cand.candidate_id,
            source_range=cand.time_range,
            speed_factor=config.get("speed_factor", 1.0),
            color_preset_name=color_preset_name,
            color_config=color_config,
            primary_aspect_ratio=constraints.aspect_ratio,
            primary_framing=framing,
            framing_variants=_build_framing_variants(
                cand, analysis, constraints,
            ),
            target_width=constraints.target_width,
            target_height=constraints.target_height,
            audio_config=AudioConfig(
                loudnorm_enabled=True,
                demucs_enabled=config.get("demucs_enabled", False),
            ),
            caption_enabled=caption_enabled,
            caption_style=CaptionStyle() if caption_enabled else None,
            caption_segments=caption_segs,
        )

        # Compute render hash
        spec = ClipSpec(
            **{
                **{f.name: getattr(spec, f.name) for f in spec.__dataclass_fields__.values()},
                "render_hash": _compute_render_hash(spec),
            }
        )
        clips.append(spec)

    plan = EditPlan(
        plan_id=f"plan_{uuid.uuid4().hex[:8]}",
        version=1,
        strategy_name=config.get("strategy_name", "generic"),
        genre=config.get("genre", "talking_head"),
        constraints=constraints,
        clips=clips,
        source_hash=analysis.source.source_hash,
        analysis_versions=analysis.engine_versions,
        color_preset_name=color_preset_name,
        caption_preset_name="minimal",
        created_at=datetime.now(timezone.utc).isoformat(),
        modified_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.info("EditPlan built: %d clips, strategy=%s", len(clips), plan.strategy_name)
    return plan


def _resolve_framing(
    candidate: CandidateClip,
    analysis: AnalysisResult,
    constraints: EditConstraints,
    overrides: dict | None = None,
) -> FramingParams | None:
    """Resolve framing from YOLO detections. None if no reframe needed.

    framing_mode (from user_overrides):
      "auto_face" — auto-detect person bbox (default)
      "center"    — always center crop, ignore YOLO
      "none"      — no crop/reframe (passthrough)
    """
    framing_mode = (overrides or {}).get("framing_mode", "auto_face")

    # "none": no reframe at all
    if framing_mode == "none":
        return None

    if constraints.aspect_ratio == AspectRatio.LANDSCAPE_16_9:
        return None  # No crop needed for landscape source

    # "center": force center crop regardless of YOLO
    if framing_mode == "center":
        src = analysis.source
        return FramingParams(
            cx_start=src.width / 2.0,
            cy_start=src.height / 2.0,
            cx_end=src.width / 2.0,
            cy_end=src.height / 2.0,
            zoom_start=1.0,
            zoom_end=1.0,
            smooth_alpha=0.07,
            max_pan_px_per_sec=900.0,
            person_target_fraction=0.70,
        )

    # "auto_face" (default): use YOLO person bbox if available
    if candidate.dominant_person_bbox:
        bbox = candidate.dominant_person_bbox
        return FramingParams(
            cx_start=bbox.cx,
            cy_start=bbox.cy,
            cx_end=bbox.cx,
            cy_end=bbox.cy,
            zoom_start=1.3,
            zoom_end=1.3,
            smooth_alpha=0.07,
            max_pan_px_per_sec=900.0,
            person_target_fraction=0.70,
        )

    # Fallback: center crop
    src = analysis.source
    return FramingParams(
        cx_start=src.width / 2.0,
        cy_start=src.height / 2.0,
        cx_end=src.width / 2.0,
        cy_end=src.height / 2.0,
        zoom_start=1.0,
        zoom_end=1.0,
        smooth_alpha=0.07,
        max_pan_px_per_sec=900.0,
        person_target_fraction=0.70,
    )


def _build_framing_variants(
    candidate: CandidateClip,
    analysis: AnalysisResult,
    constraints: EditConstraints,
) -> dict[str, FramingParams]:
    """Build framing for additional aspect ratios."""
    variants: dict[str, FramingParams] = {}
    for ratio_str in constraints.additional_aspect_ratios:
        try:
            ratio = AspectRatio(ratio_str)
        except ValueError:
            continue
        if ratio == constraints.aspect_ratio:
            continue

        alt_constraints = EditConstraints(
            aspect_ratio=ratio,
            target_width=1080,
            target_height=1080 if ratio == AspectRatio.SQUARE_1_1 else 1920,
        )
        framing = _resolve_framing(candidate, analysis, alt_constraints)
        if framing:
            variants[ratio_str] = framing

    return variants


def _extract_caption_segments(
    candidate: CandidateClip,
    analysis: AnalysisResult,
) -> list[TranscriptSegment]:
    """Extract transcript segments that overlap with candidate time range."""
    return [
        seg for seg in analysis.transcript
        if seg.time_range.overlaps(candidate.time_range)
    ]


def _compute_render_hash(spec: ClipSpec) -> str:
    """Deterministic hash of render-affecting fields."""
    data = {
        "start": spec.source_range.start,
        "end": spec.source_range.end,
        "speed": spec.speed_factor,
        "color": spec.color_config,
        "width": spec.target_width,
        "height": spec.target_height,
        "framing": bool(spec.primary_framing),
        "caption": spec.caption_enabled,
        "audio_demucs": spec.audio_config.demucs_enabled,
    }
    raw = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
