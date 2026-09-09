"""
Segment Merging Logic
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .constants import CUT_HINT_RE
from .text_utils import clean_text, is_junk_text, normalize_text_for_comparison, dur
from .word_utils import extract_words_from_segment
from ..nhat_ky import info


def pack_into_speech_segments(raw: List[Dict], min_s: float, max_s: float) -> List[Dict]:
    """
    Pack raw segments into speech segments
    
    Logic:
    - Gap > 0.5s: flush (new sentence/scene)
    - Gap >= 0.25s + punctuation: flush (natural break)
    - Otherwise: continue buffering if <= max_s
    """
    if not raw:
        return []

    packed: List[Dict] = []
    buf_text: List[str] = []
    buf_start: Optional[float] = None
    buf_end: Optional[float] = None
    buf_words: List[Dict] = []

    def flush(force: bool) -> None:
        nonlocal buf_text, buf_start, buf_end, buf_words
        
        if buf_start is None or buf_end is None or not buf_text:
            buf_text, buf_start, buf_end, buf_words = [], None, None, []
            return

        txt = clean_text(" ".join(buf_text))
        if is_junk_text(txt):
            buf_text, buf_start, buf_end, buf_words = [], None, None, []
            return

        d = buf_end - buf_start
        if not force and d < min_s:
            return

        seg = {"start": float(buf_start), "end": float(buf_end), "text": txt}
        if buf_words:
            seg["words"] = buf_words.copy()

        packed.append(seg)
        buf_text, buf_start, buf_end, buf_words = [], None, None, []

    for s in raw:
        st, en = float(s["start"]), float(s["end"])
        txt = clean_text(s["text"])
        
        if is_junk_text(txt) or (en - st) < 0.05:
            continue

        seg_words = extract_words_from_segment(s) if "words" in s else []

        if buf_start is None:
            buf_start, buf_end = st, en
            buf_text = [txt]
            buf_words = seg_words
            continue

        gap = st - float(buf_end)

        # Large gap => flush
        if gap > 0.50:
            flush(force=True)
            buf_start, buf_end = st, en
            buf_text = [txt]
            buf_words = seg_words
            continue

        cand_end = en
        cand_d = cand_end - float(buf_start)

        if cand_d <= max_s + 1e-6:
            buf_end = cand_end
            buf_text.append(txt)
            buf_words.extend(seg_words)

            has_natural_pause = gap >= 0.25
            has_punctuation = CUT_HINT_RE.search(txt) is not None

            if cand_d >= min_s and (has_natural_pause or has_punctuation):
                flush(force=True)
            else:
                flush(force=False)
            continue

        # Exceeds max => flush and start new buffer
        flush(force=True)
        buf_start, buf_end = st, en
        buf_text = [txt]
        buf_words = seg_words
        flush(force=False)

    flush(force=True)
    return packed


def force_merge_short_segments(
    timeline: List[Dict],
    hard_min: float,
    max_s: float,
) -> List[Dict]:
    """
    AGGRESSIVE: Force merge segments < hard_min
    
    Context-aware:
    - Only merge if gap <= 0.5s (likely same context)
    - Only merge if result <= max_s
    - Iterative until no more merges possible (max 5 iterations)
    """
    def is_speech(x: Dict) -> bool:
        return str(x.get("type", "")).lower() == "speech"
    
    tl = sorted(timeline, key=lambda x: float(x.get("start", 0.0)))
    changed = True
    max_iterations = 5
    iteration = 0
    
    while changed and iteration < max_iterations:
        changed = False
        iteration += 1
        i = 0
        
        while i < len(tl):
            seg = tl[i]
            if not is_speech(seg):
                i += 1
                continue
            
            d = dur(seg)
            if d >= hard_min - 1e-6:
                i += 1
                continue
            
            # TRY merge with next
            if i + 1 < len(tl) and is_speech(tl[i + 1]):
                gap = float(tl[i + 1]["start"]) - float(seg["end"])
                if gap <= 0.5:  # Context threshold
                    new_d = float(tl[i + 1]["end"]) - float(seg["start"])
                    if new_d <= max_s + 1e-6:
                        # Merge
                        tl[i + 1]["start"] = seg["start"]
                        tl[i + 1]["text"] = clean_text(seg["text"] + " " + tl[i + 1]["text"])
                        if "words" in seg and "words" in tl[i + 1]:
                            tl[i + 1]["words"] = seg.get("words", []) + tl[i + 1].get("words", [])
                        tl.pop(i)
                        changed = True
                        continue
            
            # TRY merge with prev
            if i > 0 and is_speech(tl[i - 1]):
                gap = float(seg["start"]) - float(tl[i - 1]["end"])
                if gap <= 0.5:
                    new_d = float(seg["end"]) - float(tl[i - 1]["start"])
                    if new_d <= max_s + 1e-6:
                        # Merge
                        tl[i - 1]["end"] = seg["end"]
                        tl[i - 1]["text"] = clean_text(tl[i - 1]["text"] + " " + seg["text"])
                        if "words" in tl[i - 1] and "words" in seg:
                            tl[i - 1]["words"] = tl[i - 1].get("words", []) + seg.get("words", [])
                        tl.pop(i)
                        changed = True
                        continue
            
            i += 1
    
    return tl


def deduplicate_consecutive_speech(timeline: List[Dict]) -> List[Dict]:
    """
    Remove or merge consecutive speech segments with identical text
    
    Detects duplicates by:
    - Normalizing text (removing [1/2] suffixes)
    - Comparing consecutive speech segments
    - Merging if text matches
    """
    def is_speech(x: Dict) -> bool:
        return str(x.get("type", "")).lower() == "speech"
    
    if not timeline:
        return timeline
    
    result = []
    i = 0
    
    while i < len(timeline):
        seg = timeline[i]
        
        if not is_speech(seg):
            result.append(seg)
            i += 1
            continue
        
        # Check duplicate with next segment
        if i + 1 < len(timeline):
            next_seg = timeline[i + 1]
            if is_speech(next_seg):
                text1 = normalize_text_for_comparison(seg.get("text", ""))
                text2 = normalize_text_for_comparison(next_seg.get("text", ""))
                
                if text1 and text2 and text1 == text2:
                    # DUPLICATE! Merge them
                    merged = {
                        "start": seg["start"],
                        "end": next_seg["end"],
                        "text": seg.get("text", ""),  # Keep original text
                        "type": "speech"
                    }
                    
                    # Merge words if available
                    if "words" in seg and "words" in next_seg:
                        merged["words"] = seg.get("words", []) + next_seg.get("words", [])
                    elif "words" in seg:
                        merged["words"] = seg.get("words", [])
                    elif "words" in next_seg:
                        merged["words"] = next_seg.get("words", [])
                    
                    result.append(merged)
                    i += 2  # Skip next segment
                    info("dedup_merge", text=text1[:50], merged_duration=dur(merged))
                    continue
        
        # Not duplicate
        result.append(seg)
        i += 1

    return result


def deduplicate_distant_speech(timeline: List[Dict], max_lookback: int = 10) -> List[Dict]:
    """
    Remove speech segments whose normalized text matches any of the
    previous N speech segments (catches hallucination loops separated by silence).
    """
    if not timeline or max_lookback < 1:
        return timeline

    from collections import deque

    result: List[Dict] = []
    recent_texts: deque = deque(maxlen=max_lookback)

    for seg in timeline:
        if str(seg.get("type", "")).lower() != "speech":
            result.append(seg)
            continue

        norm = normalize_text_for_comparison(seg.get("text", ""))
        if not norm:
            result.append(seg)
            continue

        if norm in recent_texts:
            info("dedup_distant", text=norm[:50])
            continue

        result.append(seg)
        recent_texts.append(norm)

    return result
