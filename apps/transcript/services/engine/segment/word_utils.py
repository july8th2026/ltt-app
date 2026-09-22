"""
Word-level Timestamp Utilities
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .constants import STRONG_PUNCT, MED_PUNCT, W_PUNCT, W_PAUSE, W_LEN
from .text_utils import clean_text


def extract_words_from_segment(segment: Dict) -> List[Dict]:
    """
    Extract word-level timestamps from a Whisper segment.
    Returns list of {word: str, start: float, end: float}
    """
    words = segment.get("words", [])
    if not words:
        return []

    result = []
    for w in words:
        # `word` = legacy dump, `text` = platform_core.stt.service (see flatten_words)
        word_text = clean_text(w.get("word") or w.get("text") or "")
        if not word_text:
            continue
        try:
            start = float(w.get("start", 0.0))
            end = float(w.get("end", 0.0))
            if end > start:
                result.append({"word": word_text, "start": start, "end": end})
        except (ValueError, TypeError):
            continue
    return result


def detect_natural_pauses(words: List[Dict], min_pause: float = 0.3) -> List[Tuple[float, float]]:
    """Detect natural pauses between words"""
    pauses = []
    for i in range(len(words) - 1):
        gap = words[i + 1]["start"] - words[i]["end"]
        if gap >= min_pause:
            pauses.append((words[i]["end"], words[i + 1]["start"]))
    return pauses


def punct_strength(word_text: str) -> float:
    """
    Calculate punctuation strength of a word
    Returns: 1.0 for strong, 0.6 for medium, 0.0 for none
    """
    w = (word_text or "").strip()
    if not w:
        return 0.0
    if w.endswith(STRONG_PUNCT):
        return 1.0
    if w.endswith(MED_PUNCT):
        return 0.6
    return 0.0


def find_closest_word_boundary(
    words: List[Dict],
    target_time: float,
    tolerance: float = 0.3,
) -> Optional[float]:
    """
    Find word boundary closest to target_time
    Used for emergency split
    """
    if not words:
        return None
    
    best_boundary = None
    best_dist = tolerance + 1.0
    
    for w in words:
        boundary = float(w["end"])
        dist = abs(boundary - target_time)
        if dist < best_dist and dist <= tolerance:
            best_dist = dist
            best_boundary = boundary
    
    return best_boundary


def choose_word_cut_index(
    words: List[Dict],
    *,
    seg_start: float,
    seg_end: float,
    max_s: float,
    min_chunk1: float,
    min_chunk2: float,
    target: float = 5.6,
) -> Optional[int]:
    """
    Choose optimal word index to cut segment
    
    Scoring based on:
    - Punctuation strength (W_PUNCT)
    - Pause/gap duration (W_PAUSE)  
    - Deviation from target length (W_LEN penalty)
    
    Returns: index i where cut should happen after word[i]
    """
    if not words or len(words) < 2:
        return None

    best_i = None
    best_score = -1e18

    # Precompute gaps
    gaps: List[float] = [0.0] * (len(words) - 1)
    for i in range(len(words) - 1):
        gap = float(words[i + 1]["start"]) - float(words[i]["end"])
        gaps[i] = gap

    for i in range(len(words) - 1):
        cut_t = float(words[i]["end"])
        next_start = float(words[i + 1]["start"])

        chunk1_d = cut_t - seg_start
        chunk2_d = seg_end - next_start

        # Check constraints
        if chunk1_d < min_chunk1 - 1e-6:
            continue
        if chunk1_d > max_s + 1e-6:
            continue
        if chunk2_d < min_chunk2 - 1e-6:
            continue

        # Calculate scores
        punct = punct_strength(words[i]["word"])
        gap = gaps[i]
        
        pause = 0.0
        if gap >= 0.50:
            pause = 1.0
        elif gap >= 0.35:
            pause = 0.7
        elif gap >= 0.25:
            pause = 0.4

        len_pen = abs(chunk1_d - target)

        # Penalty for cutting after short/function words (bad scene ending)
        _CONNECTORS = {
            # English function words
            "a","an","the","and","or","but","so","with","from","to","of","in","on","at","for",
            "is","are","was","were","be","been","am",
            "it","he","she","we","they","I","my","his","her","its","our","their","your",
            "if","as","by","up","no","not","do","did","has","had","have","will","can","may",
            "this","that","these","those","into","onto","upon","than","who","which","what",
            # Vietnamese function words
            "và","va","hay","hoặc","nhưng","mà","với","của","từ","cho","về","trong",
            "là","có","được","bị","một","các","những","này","đó","thì","cũng","đã","sẽ",
            "để","vì","nên","như","khi","nếu","tại","bởi","theo",
        }
        last_w = words[i]["word"].lower().rstrip(".,!?;:")
        connector_pen = 5.0 if last_w in _CONNECTORS else 0.0
        # Heavy penalty for very short end-words (1-2 chars) without punctuation
        # These create truncated-looking sentences ("into an", "of a", "is")
        if len(last_w) <= 2 and punct == 0:
            connector_pen += 10.0
        elif len(last_w) <= 3 and last_w in _CONNECTORS and punct == 0:
            connector_pen += 6.0

        score = (W_PUNCT * punct) + (W_PAUSE * pause) - (W_LEN * len_pen) - connector_pen

        if score > best_score:
            best_score = score
            best_i = i

    return best_i
