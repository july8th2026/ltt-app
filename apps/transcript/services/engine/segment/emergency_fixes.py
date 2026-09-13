"""
Emergency Fix Logic

Last resort fixes when all gentle/moderate/aggressive methods fail
Ensures 100% segments are within [hard_min, hard_max]
"""
from __future__ import annotations

from typing import Dict, List

from .text_utils import dur
from .splitting import mandatory_split_equal
from .merging import force_merge_short_segments
from ..nhat_ky import info


def force_split_long_segments(
    timeline: List[Dict],
    max_s: float,
    hard_min: float,
) -> List[Dict]:
    """
    Force split ALL segments > max_s using mandatory_split_equal
    """
    def is_speech(x: Dict) -> bool:
        return str(x.get("type", "")).lower() == "speech"
    
    result = []
    for seg in timeline:
        if not is_speech(seg):
            result.append(seg)
            continue
        
        if dur(seg) <= max_s + 1e-6:
            result.append(seg)
            continue
        
        # Force split
        chunks = mandatory_split_equal(seg, hard_min=hard_min, max_s=max_s)
        result.extend(chunks)
    
    return result


def emergency_fix_violations(
    timeline: List[Dict],
    hard_min: float,
    hard_max: float,
) -> List[Dict]:
    """
    EMERGENCY fix: Ensure 100% segments are within [hard_min, hard_max]
    
    3-step process:
    1. Force merge short segments (< hard_min)
    2. Force split long segments (> hard_max)
    3. Extend any remaining short segments
    """
    def is_speech(x: Dict) -> bool:
        return str(x.get("type", "")).lower() == "speech"
    
    # ========================================================
    # STEP 1: Force merge short
    # ========================================================
    tl = force_merge_short_segments(timeline, hard_min=hard_min, max_s=hard_max)
    
    # ========================================================
    # STEP 2: Force split long
    # ========================================================
    tl = force_split_long_segments(tl, max_s=hard_max, hard_min=hard_min)
    
    # ========================================================
    # STEP 3: Handle remaining violations (extend or drop)
    # ========================================================
    result = []
    for seg in tl:
        if not is_speech(seg):
            result.append(seg)
            continue
        
        d = dur(seg)
        
        if d < hard_min - 1e-6:
            # Still too short after all attempts - force extend
            deficit = hard_min - d
            seg["end"] = float(seg["end"]) + deficit
            info("emergency_extend", idx=len(result), duration=d, new_duration=dur(seg))
        
        if dur(seg) >= 0.05:
            result.append(seg)
    
    return result
