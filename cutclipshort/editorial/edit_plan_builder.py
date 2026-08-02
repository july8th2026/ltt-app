"""Edit plan builder — assembles a complete EditPlan from ranked candidates.

This is the final step of the editorial pipeline:
1. Takes ranked CandidateClip list
2. Resolves framing parameters (from person detection data)
3. Applies style decisions (from style_planner)
4. Extracts caption segments
5. Computes render hashes for selective re-render
6. Produces a self-contained EditPlan

The EditPlan is the ONLY artifact the render layer needs.
It never reads analysis cache — everything is resolved here.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.editorial.style_planner import plan_style
from cutclipshort.presets.color_presets import get_color_preset
from cutclipshort.types import (
    AnalysisResult,
    AspectRatio,
    CandidateClip,
    ClipSpec,
    EditConstraints,
    EditPlan,
    FramingParams,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


def build_edit_plan(
    candidates: list[CandidateClip],
    analysis: AnalysisResult,
    constraints: EditConstraints,
    profile: GenreProfile,
    user_overrides: dict | None = None,
) -> EditPlan:
    """Build a complete, self-contained EditPlan.

    Args:
        candidates: Ranked candidates from clip_ranker.
        analysis: Full analysis result (for framing + caption data).
        constraints: Platform constraints.
        profile: Genre profile.
        user_overrides: Optional user style overrides.

    Returns:
        EditPlan ready for the render layer.
    """
    overrides = user_overrides or {}

    clips: list[ClipSpec] = []
    for cand in candidates:
        # Resolve style for this candidate
        style = plan_style(cand, profile, overrides)

        # Resolve framing from person detection data (respects framing_mode override)
        framing = _resolve_framing(cand, analysis, constraints, overrides)
        framing_variants = _resolve_framing_variants(
            cand, analysis, constraints,
        )

        # Extract caption segments for this clip's time range
        caption_segs = _extract_captions(cand, analysis)

        spec = ClipSpec(
            clip_id=cand.candidate_id,
            source_range=cand.time_range,
            speed_factor=style["speed_factor"],
            color_preset_name=style["color_preset_name"],
            color_config=style["color_config"],
            primary_aspect_ratio=constraints.aspect_ratio,
            primary_framing=framing,
            framing_variants=framing_variants,
            target_width=constraints.target_width,
            target_height=constraints.target_height,
            audio_config=style["audio_config"],
            caption_enabled=style["caption_enabled"],
            caption_style=style["caption_style"],
            caption_segments=caption_segs,
        )

        # Compute render hash (for selective re-render)
        render_hash = _compute_render_hash(spec)
        # Rebuild with hash (frozen dataclass)
        spec = ClipSpec(
            **{
                **{
                    f.name: getattr(spec, f.name)
                    for f in spec.__dataclass_fields__.values()
                },
                "render_hash": render_hash,
            }
        )
        clips.append(spec)

    now = datetime.now(timezone.utc).isoformat()

    plan = EditPlan(
        plan_id=f"plan_{uuid.uuid4().hex[:8]}",
        version=1,
        strategy_name=profile.name,
        genre=profile.name,
        constraints=constraints,
        clips=clips,
        source_hash=analysis.source.source_hash,
        analysis_versions=analysis.engine_versions,
        color_preset_name=overrides.get("color_preset", profile.default_color_preset),
        caption_preset_name=overrides.get("caption_preset", "minimal"),
        created_at=now,
        modified_at=now,
    )

    logger.info(
        "EditPlan built: %d clips, strategy=%s, genre=%s",
        len(clips), plan.strategy_name, plan.genre,
    )
    return plan


# ── Framing Resolution ───────────────────────────────────────────────────

def _resolve_framing(
    candidate: CandidateClip,
    analysis: AnalysisResult,
    constraints: EditConstraints,
    overrides: dict | None = None,
) -> FramingParams | None:
    """Resolve crop/zoom framing for the primary aspect ratio."""
    if constraints.aspect_ratio == AspectRatio.LANDSCAPE_16_9:
        return None  # No reframing needed for landscape output from landscape source

    src = analysis.source

    # Use candidate's person bbox if available
    if candidate.dominant_person_bbox:
        bbox = candidate.dominant_person_bbox
        return FramingParams(
            cx_start=bbox.cx,
            cy_start=bbox.cy,
            cx_end=bbox.cx,
            cy_end=bbox.cy,
            zoom_start=1.3,
            zoom_end=1.3,
        )

    # Try to find person detection from visual segments
    person_bbox = _find_best_person_bbox(candidate, analysis)
    if person_bbox:
        return FramingParams(
            cx_start=person_bbox[0],
            cy_start=person_bbox[1],
            cx_end=person_bbox[0],
            cy_end=person_bbox[1],
            zoom_start=1.3,
            zoom_end=1.3,
        )

    # Default: center crop
    return FramingParams(
        cx_start=src.width / 2.0,
        cy_start=src.height / 2.0,
        cx_end=src.width / 2.0,
        cy_end=src.height / 2.0,
        zoom_start=1.0,
        zoom_end=1.0,
    )


def _find_best_person_bbox(
    candidate: CandidateClip,
    analysis: AnalysisResult,
) -> tuple[float, float] | None:
    """Find the best person center position from visual segments."""
    for vs in analysis.visual_segments:
        if vs.time_range.overlaps(candidate.time_range) and vs.has_person:
            if vs.person_bbox_start:
                return (vs.person_bbox_start.cx, vs.person_bbox_start.cy)
    return None


def _resolve_framing_variants(
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

        # Resolve correct dimensions per aspect ratio
        _RATIO_DIMS = {
            AspectRatio.PORTRAIT_9_16: (1080, 1920),
            AspectRatio.SQUARE_1_1: (1080, 1080),
            AspectRatio.LANDSCAPE_16_9: (1920, 1080),
            AspectRatio.PORTRAIT_4_5: (1080, 1350),
        }
        w, h = _RATIO_DIMS.get(ratio, (1080, 1920))
        alt_constraints = EditConstraints(
            aspect_ratio=ratio,
            target_width=w,
            target_height=h,
        )
        framing = _resolve_framing(candidate, analysis, alt_constraints)
        if framing:
            variants[ratio_str] = framing

    return variants


# ── Caption Extraction ───────────────────────────────────────────────────

def _extract_captions(
    candidate: CandidateClip,
    analysis: AnalysisResult,
) -> list[TranscriptSegment]:
    """Extract transcript segments overlapping with the candidate range."""
    return [
        seg for seg in analysis.transcript
        if seg.time_range.overlaps(candidate.time_range)
    ]


# ── Render Hash ──────────────────────────────────────────────────────────

def _compute_render_hash(spec: ClipSpec) -> str:
    """Deterministic hash of all render-affecting parameters.

    Used for selective re-render: if hash unchanged, skip re-render.
    """
    data = {
        "start": spec.source_range.start,
        "end": spec.source_range.end,
        "speed": spec.speed_factor,
        "color": spec.color_preset_name,
        "width": spec.target_width,
        "height": spec.target_height,
        "aspect": spec.primary_aspect_ratio.value if spec.primary_aspect_ratio else "",
        "framing": bool(spec.primary_framing),
        "caption": spec.caption_enabled,
        "caption_preset": spec.caption_style.preset_name if spec.caption_style else "",
        "demucs": spec.audio_config.demucs_enabled,
        "loudnorm_lufs": spec.audio_config.loudnorm_lufs,
    }
    raw = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
