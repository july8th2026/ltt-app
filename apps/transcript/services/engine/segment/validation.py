"""
Segment Validation Logic
"""
from __future__ import annotations

from typing import Dict, List

from .text_utils import dur


def validate_speech_hard_or_error(
    segs: List[Dict],
    hard_min: float,
    hard_max: float,
    stage: str
) -> None:
    """
    Validate ALL speech segments are within [hard_min, hard_max]
    
    Raises ValueError if any violation found
    """
    for i, s in enumerate(segs):
        if str(s.get("type", "")).lower() != "speech":
            continue
        
        d = dur(s)
        if d < hard_min - 1e-6 or d > hard_max + 1e-6:
            raise ValueError(
                f"speech_minmax_hard_violation_after_{stage}: idx={i} "
                f"dur={d:.3f} start={s.get('start')} end={s.get('end')}"
            )


def count_violations(
    segs: List[Dict],
    hard_min: float,
    hard_max: float
) -> int:
    """
    Count number of speech segments outside [hard_min, hard_max]
    """
    count = 0
    for s in segs:
        if str(s.get("type", "")).lower() != "speech":
            continue
        
        d = dur(s)
        if d < hard_min - 1e-6 or d > hard_max + 1e-6:
            count += 1
    
    return count


def has_speech_outside_soft(
    segs: List[Dict],
    soft_min: float,
    soft_max: float
) -> bool:
    """
    Check if any speech segments are outside [soft_min, soft_max]
    Used for triggering soft rescue pass
    """
    for s in segs:
        if str(s.get("type", "")).lower() != "speech":
            continue
        
        d = dur(s)
        if d < soft_min - 1e-6 or d > soft_max + 1e-6:
            return True
    
    return False
