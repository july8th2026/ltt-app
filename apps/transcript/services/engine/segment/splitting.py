"""
Segment Splitting Logic (Gradual Escalation)
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from .constants import HARD_MIN, SOFT_MIN
from .text_utils import clean_text, is_junk_text, split_text_by_sentence, split_text_smart, dur
from .word_utils import (
    extract_words_from_segment,
    choose_word_cut_index,
    find_closest_word_boundary,
    punct_strength,
)


def split_long_segment_by_text(seg: Dict, max_s: float) -> List[Dict]:
    """
    Fallback split method when no word-level timestamps available
    Splits by sentence or word count
    """
    st, en = float(seg["start"]), float(seg["end"])
    txt = clean_text(seg.get("text", ""))
    duration = en - st
    
    if duration <= max_s + 1e-6 or duration <= 0.0:
        return [seg]

    parts = split_text_by_sentence(txt)
    if len(parts) <= 1:
        words = txt.split()
        if not words:
            return [seg]
        n = max(2, int(math.ceil(duration / max_s)))
        step = max(1, int(math.ceil(len(words) / n)))
        parts = []
        for i in range(0, len(words), step):
            p = " ".join(words[i:i + step]).strip()
            if p:
                parts.append(p)
        if not parts:
            return [seg]

    weights = [max(1, len(p)) for p in parts]
    total = float(sum(weights))

    cur = st
    out: List[Dict] = []
    for i, p in enumerate(parts):
        frac = weights[i] / total
        seg_dur = max(0.15, duration * frac)
        nxt = cur + seg_dur
        if i == len(parts) - 1:
            nxt = en
        out.append({"start": cur, "end": nxt, "text": clean_text(p)})
        cur = nxt

    out[0]["start"] = st
    out[-1]["end"] = en
    for i in range(1, len(out)):
        if out[i]["start"] < out[i - 1]["end"]:
            out[i]["start"] = out[i - 1]["end"]
        if out[i]["end"] < out[i]["start"]:
            out[i]["end"] = out[i]["start"]

    return [x for x in out if not is_junk_text(x["text"]) and dur(x) >= 0.05]


def split_long_segment_with_words_v2(
    seg: Dict,
    max_s: float,
    words: Optional[List[Dict]] = None,
    *,
    hard_min: float = HARD_MIN,
    soft_min: float = SOFT_MIN,
) -> Tuple[List[Dict], bool]:
    """
    GRADUAL ESCALATION split with word boundaries
    
    Priority:
    1. GENTLE: Try soft_min (2.5s)
    2. MODERATE: Fallback to hard_min (2.0s)
    3. AGGRESSIVE: Find best punctuation cut
    
    Returns: (chunks, success)
    - success=True: All chunks in [hard_min, max_s]
    - success=False: Cannot split, needs emergency handling
    """
    st, en = float(seg["start"]), float(seg["end"])
    duration = en - st
    
    if duration <= max_s + 1e-6 or duration <= 0.0:
        return [seg], True

    txt = clean_text(seg.get("text", ""))

    if words:
        # Filter words inside segment
        w = [ww for ww in words if float(ww["end"]) > st + 1e-6 and float(ww["start"]) < en - 1e-6]
        
        if len(w) >= 2:
            pieces: List[Dict] = []
            cur_start = st
            cur_words = w
            cur_end = en

            # Iterative split (safety: max 12 iterations)
            for iteration in range(12):
                cur_d = cur_end - cur_start
                
                if cur_d <= max_s + 1e-6:
                    # Pack remaining
                    piece_words = [ww for ww in cur_words if float(ww["start"]) >= cur_start - 1e-6 and float(ww["end"]) <= cur_end + 1e-6]
                    piece_text = " ".join([ww["word"] for ww in piece_words]).strip()
                    if piece_text and not is_junk_text(piece_text):
                        pieces.append({
                            "start": cur_start,
                            "end": cur_end,
                            "text": piece_text,
                            "words": piece_words
                        })
                    break

                # PRIORITY 1: Try soft_min (GENTLE)
                cut_i = choose_word_cut_index(
                    cur_words,
                    seg_start=cur_start,
                    seg_end=cur_end,
                    max_s=max_s,
                    min_chunk1=soft_min,  # 2.5
                    min_chunk2=soft_min,
                    target=5.6,
                )
                
                # PRIORITY 2: Fallback hard_min (MODERATE)
                if cut_i is None:
                    cut_i = choose_word_cut_index(
                        cur_words,
                        seg_start=cur_start,
                        seg_end=cur_end,
                        max_s=max_s,
                        min_chunk1=hard_min,  # 2.0
                        min_chunk2=hard_min,
                        target=5.6,
                    )

                # PRIORITY 3: Find best punctuation cut (AGGRESSIVE)
                if cut_i is None:
                    t_target = min(cur_start + max_s, cur_end - hard_min)
                    best_j = None
                    best_score = -1e18
                    
                    for j in range(len(cur_words) - 1):
                        cand_t = float(cur_words[j]["end"])
                        cand_next = float(cur_words[j + 1]["start"])
                        c1 = cand_t - cur_start
                        c2 = cur_end - cand_next
                        
                        if c1 > max_s + 1e-6:
                            continue
                        if c2 < hard_min - 1e-6:
                            continue
                        
                        # Score: prioritize punctuation
                        punct = punct_strength(cur_words[j]["word"])
                        dist_pen = abs(cand_t - t_target)
                        score = (punct * 2.0) - (dist_pen * 0.3)
                        
                        if score > best_score:
                            best_score = score
                            best_j = j
                    
                    cut_i = best_j

                if cut_i is None:
                    # Cannot split - signal failure
                    return [seg], False

                cut_end = float(cur_words[cut_i]["end"])
                next_start = float(cur_words[cut_i + 1]["start"])

                left_words = cur_words[: cut_i + 1]
                left_text = " ".join([ww["word"] for ww in left_words]).strip()
                if left_text and not is_junk_text(left_text):
                    pieces.append({
                        "start": cur_start,
                        "end": cut_end,
                        "text": left_text,
                        "words": left_words
                    })

                # Move window to right
                cur_start = next_start
                cur_words = cur_words[cut_i + 1 :]

                if len(cur_words) < 2:
                    # Remaining too small
                    rem_text = " ".join([ww["word"] for ww in cur_words]).strip()
                    if rem_text and not is_junk_text(rem_text) and (cur_end - cur_start) >= 0.05:
                        pieces.append({
                            "start": cur_start,
                            "end": cur_end,
                            "text": rem_text,
                            "words": cur_words
                        })
                    break

            if pieces:
                # Validate all chunks >= hard_min
                all_valid = all(dur(p) >= hard_min - 1e-6 for p in pieces)
                return pieces, all_valid

    # Fallback: text-based split
    if txt:
        chunks = split_long_segment_by_text(seg, max_s)
        all_valid = all(dur(c) >= hard_min - 1e-6 for c in chunks)
        return chunks, all_valid

    return [seg], False


def mandatory_split_equal(
    seg: Dict,
    hard_min: float = HARD_MIN,
    max_s: float = 6.0,
) -> List[Dict]:
    """
    EMERGENCY split: Chia đều nhưng vẫn TRY tìm word boundaries
    Used only when gentle/moderate/aggressive methods all fail
    """
    duration = dur(seg)
    st = float(seg["start"])
    en = float(seg["end"])
    
    # Calculate chunks needed
    target_chunk = 4.0
    n_chunks = max(2, math.ceil(duration / max_s))
    chunk_size = duration / n_chunks
    
    # Safety: ensure chunk_size >= hard_min
    if chunk_size < hard_min:
        n_chunks = max(2, int(duration / hard_min))
        chunk_size = duration / n_chunks
    
    words = extract_words_from_segment(seg) if "words" in seg else []
    chunks = []
    cur = st
    
    if words and len(words) >= n_chunks:
        # TRY find word boundaries near cut points
        for i in range(n_chunks):
            if i == n_chunks - 1:
                actual_end = en
            else:
                target_end = cur + chunk_size
                closest = find_closest_word_boundary(words, target_end, tolerance=0.4)
                actual_end = closest if closest else target_end
            
            # Extract text for range
            chunk_words = [w for w in words if float(w["start"]) >= cur - 1e-6 and float(w["end"]) <= actual_end + 1e-6]
            chunk_text = " ".join([w["word"] for w in chunk_words]).strip() if chunk_words else ""
            
            # UPDATED: Use smart text split to avoid duplicates
            if not chunk_text:
                text_chunks = split_text_smart(seg.get("text", ""), n_chunks)
                chunk_text = text_chunks[i] if i < len(text_chunks) else seg.get("text", "")
            
            chunks.append({
                "start": cur,
                "end": actual_end,
                "text": chunk_text,
                "words": chunk_words if chunk_words else []
            })
            cur = actual_end
    else:
        # No words: split text smartly
        text_chunks = split_text_smart(seg.get("text", ""), n_chunks)
        for i in range(n_chunks):
            end = min(cur + chunk_size, en)
            chunks.append({
                "start": cur,
                "end": end,
                "text": text_chunks[i] if i < len(text_chunks) else seg.get("text", ""),
            })
            cur = end
    
    return [c for c in chunks if dur(c) >= 0.05]
