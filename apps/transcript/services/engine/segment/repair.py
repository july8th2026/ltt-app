"""
Segment Repair Logic

3-pass repair:
A) Split segments > max_s
B) Merge segments < min_s (only if result <= max_s)
C) Re-split any segments > max_s
"""
from __future__ import annotations

from typing import Dict, List

from .text_utils import clean_text, dur
from .word_utils import extract_words_from_segment
from .splitting import split_long_segment_with_words_v2
from .timeline import coerce_raw


def repair_speech_lengths(
    segs: List[Dict],
    min_s: float,
    max_s: float,
    *,
    hard_min: float,
    soft_min: float,
) -> List[Dict]:
    """
    Repair speech segment lengths with 3 passes
    
    UPDATED: Does NOT allow merge > max_s (removed 1.35x rule)
    """
    if not segs:
        return []

    # ========================================================
    # PASS A: Split > max_s (initial)
    # ========================================================
    expanded: List[Dict] = []
    for s in segs:
        if dur(s) > max_s + 1e-6:
            words = extract_words_from_segment(s) if "words" in s else None
            chunks, success = split_long_segment_with_words_v2(
                s, max_s=max_s, words=words, hard_min=hard_min, soft_min=soft_min
            )
            if success:
                expanded.extend(chunks)
            else:
                # Mark for aggressive split later
                s['needs_aggressive_split'] = True
                expanded.append(s)
        else:
            expanded.append(s)
    
    out = coerce_raw(expanded)

    # ========================================================
    # PASS B: Merge < min_s (ONLY if result <= max_s)
    # ========================================================
    out2 = [dict(s) for s in out]
    i = 0
    
    while i < len(out2):
        if len(out2) == 1:
            break

        d = dur(out2[i])
        if d >= min_s - 1e-6:
            i += 1
            continue

        merged = False

        # Try merge DOWN (with next)
        if i + 1 < len(out2):
            gap = float(out2[i + 1]["start"]) - float(out2[i]["end"])
            if gap <= 0.30:
                new_d = float(out2[i + 1]["end"]) - float(out2[i]["start"])
                # UPDATED: Only merge if <= max_s
                if new_d <= max_s + 1e-6:
                    out2[i + 1]["start"] = out2[i]["start"]
                    out2[i + 1]["text"] = clean_text(out2[i]["text"] + " " + out2[i + 1]["text"])
                    if "words" in out2[i] and "words" in out2[i + 1]:
                        out2[i + 1]["words"] = out2[i]["words"] + out2[i + 1]["words"]
                    out2.pop(i)
                    merged = True

        if merged:
            continue

        # Try merge UP (with prev)
        if i > 0:
            gap = float(out2[i]["start"]) - float(out2[i - 1]["end"])
            if gap <= 0.30:
                new_d = float(out2[i]["end"]) - float(out2[i - 1]["start"])
                # UPDATED: Only merge if <= max_s
                if new_d <= max_s + 1e-6:
                    out2[i - 1]["end"] = out2[i]["end"]
                    out2[i - 1]["text"] = clean_text(out2[i - 1]["text"] + " " + out2[i]["text"])
                    if "words" in out2[i - 1] and "words" in out2[i]:
                        out2[i - 1]["words"] = out2[i - 1]["words"] + out2[i]["words"]
                    out2.pop(i)
                    merged = True

        if not merged:
            # Cannot merge - mark for force handling
            if d < hard_min:
                out2[i]['needs_force_merge'] = True
            i += 1

    merged_out = coerce_raw(out2)

    # ========================================================
    # PASS C: Re-split until no seg > max_s
    # ========================================================
    stabilized: List[Dict] = merged_out
    
    for _ in range(8):
        any_long = False
        tmp: List[Dict] = []
        
        for s in stabilized:
            if dur(s) > max_s + 1e-6:
                any_long = True
                words = extract_words_from_segment(s) if "words" in s else None
                chunks, success = split_long_segment_with_words_v2(
                    s, max_s=max_s, words=words, hard_min=hard_min, soft_min=soft_min
                )
                if success:
                    tmp.extend(chunks)
                else:
                    s['needs_aggressive_split'] = True
                    tmp.append(s)
            else:
                tmp.append(s)
        
        stabilized = coerce_raw(tmp)
        if not any_long:
            break

    return stabilized
