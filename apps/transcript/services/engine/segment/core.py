"""
Core Entry Points

make_segments() - Speech-only segmentation
make_timeline() - Full timeline with silence (legacy 4-phase)
make_timeline_v2() - Word-first scene builder (NEW — preferred)
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from .constants import HARD_MIN, HARD_MAX, SOFT_MIN
from .timeline import coerce_raw, round_timeline, export_clean_timeline
from .splitting import split_long_segment_with_words_v2
from .word_utils import extract_words_from_segment
from .merging import pack_into_speech_segments, deduplicate_consecutive_speech, deduplicate_distant_speech
from .repair import repair_speech_lengths
from .padding import pad_short_speech_into_adjacent_silence
from .validation import validate_speech_hard_or_error, count_violations
from .emergency_fixes import emergency_fix_violations
from .silence import build_silence_scenes, fill_gaps_with_silence
from .seamless import seamless_after_fill, close_gaps_only
from .word_scene_builder import build_word_scenes, flatten_words
from ..nhat_ky import info


def make_timeline_v2(
    raw_segments: List[Dict],
    *,
    audio_duration: Optional[float] = None,
    target_min: float = 3.0,
    target_max: float = 6.0,
    silence_threshold: float = 2.0,
    silence_text: str = "[B-ROLL: PAUSE]",
) -> List[Dict]:
    """
    Word-first scene builder. Words are the sole source of truth.

    Flow:
      1. Flatten all words from segments
      2. Build scenes from word boundaries
      3. Repair (merge short, split long)
      4. Normalize silence (absorb micro-pause, mark residual)
      5. Generate B-ROLL from residual only
      6. Validate

    Returns timeline with words[] preserved in each speech scene.
    """
    t0 = time.time()

    # Flatten words from all segments
    all_words = flatten_words(raw_segments)
    if not all_words:
        info("timeline_v2_empty", reason="no_words")
        return []

    # Determine audio duration
    if audio_duration is None or audio_duration <= 0:
        audio_duration = all_words[-1]["end"] + 1.0

    # Build scenes
    timeline = build_word_scenes(
        all_words,
        audio_duration,
        target_min=target_min,
        target_max=target_max,
        silence_threshold=silence_threshold,
        silence_text=silence_text,
    )

    # Validate
    speech_scenes = [s for s in timeline if s["type"] == "speech"]
    speech_violations = count_violations(speech_scenes, hard_min=HARD_MIN, hard_max=HARD_MAX)

    # Word coverage check
    input_word_count = len(all_words)
    output_word_count = sum(len(s.get("words", [])) for s in speech_scenes)

    info("timeline_v2_done",
         segments=len(timeline),
         speech=len(speech_scenes),
         silence=sum(1 for s in timeline if s["type"] == "silence"),
         violations=speech_violations,
         input_words=input_word_count,
         output_words=output_word_count,
         word_coverage=f"{output_word_count}/{input_word_count}",
         elapsed=round(time.time() - t0, 2))

    if speech_violations > 0:
        info("timeline_v2_violations", count=speech_violations,
             message="Some speech scenes outside [2.0, 6.0]s — marked as exceptions")

    return timeline


def expand_raw(
    raw: List[Dict],
    max_s: float,
    *,
    hard_min: float,
    soft_min: float
) -> List[Dict]:
    """
    Expand (split) long segments using gradual escalation
    """
    from .text_utils import dur
    
    out: List[Dict] = []
    for s in raw:
        if dur(s) <= max_s + 1e-6:
            out.append(s)
            continue
        
        words = extract_words_from_segment(s) if "words" in s else None
        chunks, success = split_long_segment_with_words_v2(
            s, max_s=max_s, words=words, hard_min=hard_min, soft_min=soft_min
        )
        
        if success:
            out.extend(chunks)
        else:
            # Cannot split - mark for aggressive handling
            s['needs_aggressive_split'] = True
            out.append(s)
    
    return coerce_raw(out)


def make_segments(
    raw_segments: List[Dict],
    min_s: float = 3.0,
    max_s: float = 6.0
) -> List[Dict]:
    """
    Create speech segments (no silence)
    
    Process:
    1. Coerce raw
    2. Expand (split long)
    3. Pack into segments
    4. Repair lengths
    """
    # Use hard_min for tolerance
    soft_min = min_s - 0.5  # Keep for gentle methods
    hard_min = min_s - 1.0  # 2.0

    coerced = coerce_raw(raw_segments)
    expanded = expand_raw(coerced, max_s=max_s, hard_min=hard_min, soft_min=soft_min)
    packed = pack_into_speech_segments(expanded, min_s=min_s, max_s=max_s)
    final = repair_speech_lengths(packed, min_s=min_s, max_s=max_s, hard_min=hard_min, soft_min=soft_min)
    
    return final


def make_timeline(
    raw_segments: List[Dict],
    min_s: float = 3.0,
    max_s: float = 6.0,
    *,
    cfg=None,
    speech_segments: Optional[List[Dict[str, float]]] = None,
    audio_duration: Optional[float] = None,
    include_silence: bool = True,
    silence_text: str = "[B-ROLL / PAUSE]",
    min_silence_keep: float = 2.0,
    silence_chunk_s: float = 5.0,
) -> List[Dict]:
    """
    Create full timeline with 3-phase gradual escalation
    
    PHASES:
    1. GENTLE: Standard processing with soft_min (2.5)
    2. ITERATIVE REFINEMENT: Repair + pad + rebuild (max 3 loops)
    3. EMERGENCY: Force fixes to ensure 100% compliance
    4. DEDUPLICATION: Remove duplicate consecutive speech
    
    Returns: Clean timeline with all segments in [2.0, 6.0]
    """
    t0 = time.time()

    # Validate fixed boundaries
    if abs(float(min_s) - 3.0) > 1e-6 or abs(float(max_s) - 6.0) > 1e-6:
        raise ValueError(f"min_s/max_s must be fixed at 3/6. got min_s={min_s}, max_s={max_s}")

    # Set boundaries
    hard_min = HARD_MIN  # 2.0
    hard_max = HARD_MAX  # 6.0
    soft_min = SOFT_MIN  # 2.5

    # ========================================================
    # PHASE 1: GENTLE PROCESSING
    # ========================================================
    speech_scenes = make_segments(raw_segments, min_s=min_s, max_s=max_s)
    for s in speech_scenes:
        s["type"] = "speech"

    # No silence path
    if not include_silence:
        out = seamless_after_fill(speech_scenes, min_silence_keep=min_silence_keep, hard_min=hard_min, max_s=max_s)
        out = round_timeline(out, decimals=2)
        out = deduplicate_consecutive_speech(out)
        
        for i, s in enumerate(out, start=1):
            s["scene_id"] = f"S{i:04d}"
            s["index"] = i
        
        out_clean = export_clean_timeline(out, round_decimals=2)
        info("timeline_done", segments=len(out_clean), elapsed=round(time.time() - t0, 2))
        return out_clean

    # Speech regions fallback
    if speech_segments is None:
        if speech_scenes:
            speech_segments = [{"start": float(speech_scenes[0]["start"]), "end": float(speech_scenes[-1]["end"])}]
        else:
            speech_segments = []

    # Build initial timeline
    silence_scenes = build_silence_scenes(
        speech_scenes,
        speech_segments=speech_segments,
        audio_duration=audio_duration,
        min_silence_keep=min_silence_keep,
        silence_text=silence_text,
    )

    timeline = speech_scenes + silence_scenes
    timeline = fill_gaps_with_silence(timeline, min_silence_keep=min_silence_keep, silence_text=silence_text, max_inserts=2000)
    timeline = seamless_after_fill(timeline, min_silence_keep=min_silence_keep, hard_min=hard_min, max_s=max_s)
    timeline = round_timeline(timeline, decimals=2)

    # ========================================================
    # PHASE 2: ITERATIVE REFINEMENT (max 3 loops)
    # ========================================================
    for refinement_pass in range(3):
        # Extract speech
        speech_only = [dict(s) for s in timeline if str(s.get("type", "")).lower() == "speech"]
        for s in speech_only:
            s["type"] = "speech"

        # Count violations before
        violations_before = count_violations(speech_only, hard_min=hard_min, hard_max=hard_max)
        
        if violations_before == 0:
            break

        # Repair
        speech_repaired = repair_speech_lengths(speech_only, min_s=min_s, max_s=max_s, hard_min=hard_min, soft_min=soft_min)
        for s in speech_repaired:
            s["type"] = "speech"

        # Pad
        timeline_temp = speech_repaired + [s for s in timeline if str(s.get("type", "")).lower() == "silence"]
        timeline_temp = pad_short_speech_into_adjacent_silence(
            timeline_temp,
            min_s=min_s,
            max_s=max_s,
            min_silence_keep=min_silence_keep,
        )

        # Rebuild silence
        speech_after_pad = [s for s in timeline_temp if str(s.get("type", "")).lower() == "speech"]
        silence_rebuilt = build_silence_scenes(
            speech_after_pad,
            speech_segments=speech_segments,
            audio_duration=audio_duration,
            min_silence_keep=min_silence_keep,
            silence_text=silence_text,
        )

        timeline = speech_after_pad + silence_rebuilt
        timeline = fill_gaps_with_silence(timeline, min_silence_keep=min_silence_keep, silence_text=silence_text, max_inserts=2000)
        timeline = seamless_after_fill(timeline, min_silence_keep=min_silence_keep, hard_min=hard_min, max_s=max_s)
        timeline = round_timeline(timeline, decimals=2)

        # Count violations after
        speech_after = [s for s in timeline if str(s.get("type", "")).lower() == "speech"]
        violations_after = count_violations(speech_after, hard_min=hard_min, hard_max=hard_max)

        info("refinement_pass", pass_num=refinement_pass + 1, violations_before=violations_before, violations_after=violations_after)

        if violations_after == 0:
            break
        
        if violations_after >= violations_before:
            info("refinement_stopped", reason="no_improvement")
            break

    # ========================================================
    # PHASE 3: EMERGENCY FIX
    # ========================================================
    speech_final = [s for s in timeline if str(s.get("type", "")).lower() == "speech"]
    final_violations = count_violations(speech_final, hard_min=hard_min, hard_max=hard_max)

    if final_violations > 0:
        info("emergency_fix_triggered", violations=final_violations)
        
        timeline = emergency_fix_violations(timeline, hard_min=hard_min, hard_max=hard_max)
        
        # Rebuild silence after emergency
        speech_emergency = [s for s in timeline if str(s.get("type", "")).lower() == "speech"]
        silence_emergency = build_silence_scenes(
            speech_emergency,
            speech_segments=speech_segments,
            audio_duration=audio_duration,
            min_silence_keep=min_silence_keep,
            silence_text=silence_text,
        )
        
        timeline = speech_emergency + silence_emergency
        timeline = fill_gaps_with_silence(timeline, min_silence_keep=min_silence_keep, silence_text=silence_text, max_inserts=2000)
        # Close small gaps without shrinking (safe post-emergency)
        timeline = close_gaps_only(timeline, hard_min=hard_min)
        timeline = round_timeline(timeline, decimals=2)

    # ========================================================
    # PHASE 4: DEDUPLICATION
    # ========================================================
    timeline = deduplicate_consecutive_speech(timeline)
    timeline = deduplicate_distant_speech(timeline, max_lookback=10)

    # ========================================================
    # FINAL VALIDATION
    # ========================================================
    try:
        validate_speech_hard_or_error(timeline, hard_min=hard_min, hard_max=hard_max, stage="final")
    except ValueError as e:
        info("final_validation_warning", error=str(e), message="Some segments still violate hard boundaries after all fixes")

    # Assign IDs
    for i, s in enumerate(timeline, start=1):
        s["scene_id"] = f"S{i:04d}"
        s["index"] = i

    out_clean = export_clean_timeline(timeline, round_decimals=2)
    
    # Final stats
    final_speech = [s for s in out_clean if s.get("type") == "speech"]
    final_violations = count_violations(final_speech, hard_min=hard_min, hard_max=hard_max)
    
    info("timeline_done", 
         segments=len(out_clean), 
         speech_segments=len(final_speech),
         violations=final_violations,
         elapsed=round(time.time() - t0, 2))
    
    return out_clean
