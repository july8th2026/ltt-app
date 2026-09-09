"""
Silence Handling Logic
"""
from __future__ import annotations

import random
import re
from typing import Dict, List, Optional

from .text_utils import dur
from ..nhat_ky import info


def build_silence_gaps_from_speech_regions(
    speech_regions: List[Dict[str, float]],
    audio_duration: Optional[float] = None,
) -> List[Dict]:
    """
    Build silence gaps from speech regions
    
    Returns gaps:
    - Before first speech
    - Between speeches
    - After last speech (if audio_duration provided)
    """
    if not speech_regions:
        return []

    regs = sorted(speech_regions, key=lambda x: (float(x["start"]), float(x["end"])))
    gaps: List[Dict] = []

    # Gap before first speech
    if float(regs[0]["start"]) > 1e-6:
        gaps.append({"start": 0.0, "end": float(regs[0]["start"])})

    # Gaps between speeches
    for i in range(len(regs) - 1):
        e1 = float(regs[i]["end"])
        s2 = float(regs[i + 1]["start"])
        if s2 > e1 + 1e-6:
            gaps.append({"start": e1, "end": s2})

    # Gap after last speech
    if audio_duration is not None and audio_duration > float(regs[-1]["end"]) + 1e-6:
        gaps.append({"start": float(regs[-1]["end"]), "end": audio_duration})

    return gaps


def split_silence_segments_random_2_5(
    silence_gaps: List[Dict],
    min_silence_keep: float,
    *,
    min_chunk: float = 2.0,
    max_chunk: float = 5.0,
) -> List[Dict]:
    """
    Split long silence gaps into random 2-5s chunks
    
    Logic:
    - If gap < min_silence_keep: skip
    - While gap > max_chunk + min_silence_keep: create random chunks
    - Handle remainder intelligently
    """
    out: List[Dict] = []
    
    for g in silence_gaps:
        st = float(g["start"])
        en = float(g["end"])
        d = en - st
        
        if d < min_silence_keep:
            continue

        cur = st
        remain = d

        # Create chunks while enough remains
        while remain > (max_chunk + min_silence_keep) + 1e-6:
            size = random.uniform(min_chunk, max_chunk)
            size = max(min_chunk, min(max_chunk, size))
            out.append({"start": cur, "end": cur + size})
            cur += size
            remain = en - cur

        # Handle remainder
        if remain < min_silence_keep - 1e-6:
            # Too small - merge into last chunk
            if out and out[-1]["end"] <= cur + 1e-6 and out[-1]["end"] > st + 1e-6:
                out[-1]["end"] = en
        elif remain <= max_chunk + 1e-6:
            # Good size - add as final chunk
            out.append({"start": cur, "end": en})
        else:
            # Split remainder into 2 chunks
            lo = max(min_chunk, remain - max_chunk)
            hi = min(max_chunk, remain - min_chunk)
            if lo > hi:
                mid = cur + remain / 2.0
                out.append({"start": cur, "end": mid})
                out.append({"start": mid, "end": en})
            else:
                c1 = random.uniform(lo, hi)
                out.append({"start": cur, "end": cur + c1})
                out.append({"start": cur + c1, "end": en})

    return out


def smart_silence_tag(prev_text: str, next_text: str, duration: float, default: str) -> str:
    """
    Generate contextual silence tag based on surrounding speech
    
    Rules:
    - Chapter break: "Chương X" or "Hồi X"
    - Reaction: ends with !, ?, …
    - Tension: emotional keywords
    - Environment: long silence (>= 4.5s)
    - Transition: no word overlap between prev/next
    - Default: fallback
    """
    t_prev = (prev_text or "").strip()
    t_next = (next_text or "").strip()

    # Chapter break
    if re.search(r"\b(Chương|Hồi)\s*\d+\b", t_prev, re.IGNORECASE):
        return "[B-ROLL: CHAPTER_BREAK]"

    # Reaction
    if t_prev.endswith(("!", "?", "…", "...")):
        return "[B-ROLL: REACTION]"

    # Tension
    emo_kw = ["im lặng", "khóc", "sợ", "lặng", "nặng nề", "đau", "buồn", "nước mắt", "run"]
    low = t_prev.lower()
    if any(k in low for k in emo_kw):
        return "[B-ROLL: TENSION]"

    # Environment
    if duration >= 4.5:
        return "[B-ROLL: ENVIRONMENT]"

    # Transition
    if t_prev and t_next:
        prev_tail = set(t_prev.lower().split()[-6:])
        next_head = set(t_next.lower().split()[:6])
        if len(prev_tail & next_head) == 0:
            return "[B-ROLL: TRANSITION]"

    return default


def build_silence_scenes(
    speech_scenes: List[Dict],
    *,
    speech_segments: List[Dict[str, float]],
    audio_duration: Optional[float],
    min_silence_keep: float,
    silence_text: str,
) -> List[Dict]:
    """
    Build silence scenes with smart tags
    
    Process:
    1. Build gaps from speech regions
    2. Split gaps into 2-5s chunks
    3. Tag each chunk based on context
    """
    sil_gaps = build_silence_gaps_from_speech_regions(speech_segments, audio_duration=audio_duration)
    sil_chunks = split_silence_segments_random_2_5(sil_gaps, min_silence_keep=min_silence_keep)

    silence_scenes: List[Dict] = []
    
    # Get sorted speech for context lookup
    sp = sorted(
        [s for s in speech_scenes if str(s.get("type", "")).lower() == "speech"],
        key=lambda x: (float(x["start"]), float(x["end"]))
    )
    sp_i = 0

    for g in sil_chunks:
        gst = float(g["start"])
        gen = float(g["end"])
        d = gen - gst
        
        if d < min_silence_keep:
            continue

        # Find prev/next speech for context
        while sp_i < len(sp) and float(sp[sp_i]["end"]) <= gst + 1e-6:
            sp_i += 1

        prev_text = sp[sp_i - 1]["text"] if 0 <= sp_i - 1 < len(sp) else ""
        next_text = sp[sp_i]["text"] if sp_i < len(sp) else ""

        tag = smart_silence_tag(prev_text, next_text, d, silence_text)
        silence_scenes.append({"start": gst, "end": gen, "text": tag, "type": "silence"})

    return silence_scenes


def fill_gaps_with_silence(
    tl: List[Dict],
    *,
    min_silence_keep: float,
    silence_text: str,
    max_inserts: int = 2000,
) -> List[Dict]:
    """
    Fill gaps between segments with silence
    
    Safety: max_inserts to prevent infinite loops
    """
    if not tl:
        return tl

    tl = sorted(tl, key=lambda x: (float(x["start"]), float(x["end"]), x.get("type", "")))
    out: List[Dict] = []
    inserts = 0

    for s in tl:
        if not out:
            out.append(s)
            continue

        prev = out[-1]
        gap = float(s["start"]) - float(prev["end"])

        if gap > 1e-6 and gap >= min_silence_keep and inserts < max_inserts:
            st = float(prev["end"])
            en = float(s["start"])
            
            chunks = split_silence_segments_random_2_5(
                [{"start": st, "end": en}],
                min_silence_keep=min_silence_keep,
                min_chunk=2.0,
                max_chunk=5.0,
            )
            
            for c in chunks:
                if inserts >= max_inserts:
                    break
                out.append({
                    "start": float(c["start"]),
                    "end": float(c["end"]),
                    "text": silence_text,
                    "type": "silence"
                })
                inserts += 1

        out.append(s)

    if inserts >= max_inserts:
        info("gap_fill_guard", message="Too many gap inserts, stopped", inserts=inserts)

    return out
