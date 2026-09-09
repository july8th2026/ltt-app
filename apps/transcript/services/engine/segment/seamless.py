"""
Seamless Gap Handling

Close small gaps between segments while protecting speech boundaries
"""
from __future__ import annotations

from typing import Dict, List

from .text_utils import dur


def seamless_after_fill(
    tl: List[Dict],
    *,
    min_silence_keep: float,
    hard_min: float,
    max_s: float,
) -> List[Dict]:
    """
    Close small gaps seamlessly
    
    Rules:
    - Gap <= 0.03s: merge immediately
    - Gap < min_silence_keep: split at midpoint
      * Clamp prev.end to not exceed max_s
      * Protect current.start to keep duration >= hard_min
    - Larger gaps: keep as-is
    
    UPDATED: Uses hard_min (2.0) instead of soft_min (2.5) for protection
    """
    if not tl:
        return []

    def is_speech(x: Dict) -> bool:
        return str(x.get("type", "")).lower() == "speech"

    tl = sorted(tl, key=lambda x: (float(x["start"]), float(x["end"]), x.get("type", "")))

    fixed: List[Dict] = []
    
    for s in tl:
        st = float(s["start"])
        en = float(s["end"])
        
        if en <= st + 1e-6:
            continue

        if not fixed:
            fixed.append(dict(s))
            continue

        prev = fixed[-1]
        prev_end0 = float(prev["end"])
        gap = st - prev_end0

        # ========================================================
        # TINY GAP: Merge immediately
        # ========================================================
        if abs(gap) <= 0.03:
            st = prev_end0

        # ========================================================
        # OVERLAP: Resolve by splitting at midpoint (protect hard_min)
        # ========================================================
        elif gap < -0.03:
            mid = (st + prev_end0) / 2.0
            # Clamp: prev must keep >= hard_min duration
            if is_speech(prev):
                min_prev_end = float(prev["start"]) + hard_min
                mid = max(mid, min_prev_end)
            # Clamp: current must keep >= hard_min duration
            if is_speech(s):
                max_cur_start = float(s["end"]) - hard_min
                mid = min(mid, max_cur_start)
            prev["end"] = mid
            st = mid

        # ========================================================
        # SMALL GAP: Split at midpoint (with protections)
        # ========================================================
        elif gap > 0 and gap < min_silence_keep:
            mid = prev_end0 + gap / 2.0

            # Move prev.end toward mid (clamped at max_s)
            desired_prev_end = mid
            clamped = False
            
            if is_speech(prev):
                max_prev_end = float(prev["start"]) + max_s
                if desired_prev_end > max_prev_end + 1e-9:
                    desired_prev_end = max_prev_end
                    clamped = True

            prev["end"] = desired_prev_end
            prev_end = float(prev["end"])

            # Base start for current
            base = prev_end if clamped else mid

            # UPDATED: Protect current speech from dropping below HARD_MIN
            if is_speech(s):
                min_start_allowed = float(s["end"]) - hard_min  # 2.0 instead of 2.5
                base = min(base, min_start_allowed)

            st = max(prev_end, base)

        # ========================================================
        # Monotonic safety
        # ========================================================
        prev_end = float(prev["end"])
        if st < prev_end:
            st = prev_end

        s2 = dict(s)
        s2["start"] = st
        if float(s2["end"]) < st:
            s2["end"] = st

        d = float(s2["end"]) - float(s2["start"])
        
        # Filter out invalid segments
        if d < 0.05:
            continue
        if s2.get("type") == "silence" and d < min_silence_keep:
            continue

        fixed.append(s2)

    return fixed


def close_gaps_only(
    tl: List[Dict],
    *,
    hard_min: float,
) -> List[Dict]:
    """
    Post-emergency pass: close small gaps by extending prev.end to cur.start.
    NEVER shrinks any segment. Only extends silence or speech (if within hard limits).
    """
    if not tl:
        return []

    HARD_MAX = 6.0
    tl = sorted(tl, key=lambda x: (float(x["start"]), float(x["end"])))
    fixed = [dict(tl[0])]

    for s in tl[1:]:
        prev = fixed[-1]
        prev_end = float(prev["end"])
        cur_start = float(s["start"])
        gap = cur_start - prev_end

        if 0.001 < gap < 0.5:
            # Extend prev.end to close the gap (only if safe)
            prev_dur_after = cur_start - float(prev["start"])
            if prev.get("type") == "silence" or prev_dur_after <= HARD_MAX:
                prev["end"] = cur_start

        s2 = dict(s)
        # Ensure no overlap after extension
        if float(s2["start"]) < float(prev["end"]):
            s2["start"] = float(prev["end"])
        if float(s2["end"]) <= float(s2["start"]):
            continue

        fixed.append(s2)

    return fixed
