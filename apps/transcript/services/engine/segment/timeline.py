"""
Timeline Helper Functions
"""
from __future__ import annotations

from typing import Any, Dict, List

from .text_utils import clean_text, is_junk_text, dur


def safe_float(x: Any, default: float = 0.0) -> float:
    """Safely convert to float"""
    try:
        return float(x)
    except Exception:
        return float(default)


def normalize_type(t: Any) -> str:
    """Normalize segment type to 'speech' or 'silence'"""
    tt = str(t or "").strip().lower()
    if tt == "silence":
        return "silence"
    return "speech"


def coerce_raw(raw_segments: List[Dict]) -> List[Dict]:
    """
    Normalize raw segments
    
    - Drop junk text
    - Float times
    - Enforce non-decreasing order
    - Clamp overlaps
    - Preserve word-level data
    """
    out: List[Dict] = []
    last_end = 0.0
    
    for s in raw_segments or []:
        try:
            st = float(s.get("start", 0.0))
            en = float(s.get("end", 0.0))
        except Exception:
            continue
        
        if en < st:
            st, en = en, st
        
        txt = clean_text(s.get("text", ""))
        if is_junk_text(txt):
            continue

        # Clamp overlaps only
        if st < last_end:
            st = last_end
        if en < st:
            en = st
        if (en - st) < 0.05:
            continue

        seg_copy = {"start": st, "end": en, "text": txt}
        if "words" in s:
            seg_copy["words"] = s["words"]

        out.append(seg_copy)
        last_end = en
    
    return out


def round_ts(x: float, decimals: int = 2) -> float:
    """Round timestamp to decimals"""
    return round(float(x), decimals)


def round_timeline(tl: List[Dict], decimals: int = 2) -> List[Dict]:
    """Round all timestamps in timeline"""
    for s in tl:
        s["start"] = round_ts(s["start"], decimals)
        s["end"] = round_ts(s["end"], decimals)
    return tl


def export_clean_timeline(
    timeline: List[Dict],
    *,
    round_decimals: int = 2,
) -> List[Dict]:
    """
    Export clean timeline with strict schema
    
    Output: JSON array with exactly 6 keys per item:
    {
        "start": float,
        "end": float,
        "text": str,
        "type": "speech" | "silence",
        "scene_id": str,
        "index": int
    }
    """
    out: List[Dict] = []
    
    for s in (timeline or []):
        if not isinstance(s, dict) or not s:
            continue

        st = safe_float(s.get("start", 0.0), 0.0)
        en = safe_float(s.get("end", 0.0), 0.0)
        
        if en < st:
            st, en = en, st
        if (en - st) < 0.05:
            continue

        seg_type = normalize_type(s.get("type", "speech"))
        text = clean_text(s.get("text", ""))

        # Drop speech with junk text
        if seg_type == "speech" and is_junk_text(text):
            continue

        item = {
            "start": round(st, round_decimals),
            "end": round(en, round_decimals),
            "text": text,
            "type": seg_type,
            "scene_id": str(s.get("scene_id", "") or "").strip(),
            "index": int(s.get("index", 0) or 0),
        }

        out.append(item)

    # Re-assign scene_id and index sequentially
    for i, x in enumerate(out, start=1):
        x["index"] = i
        x["scene_id"] = f"S{i:04d}"

    return out


def analyze_segment_quality(segment: Dict) -> Dict[str, Any]:
    """
    Analyze quality metrics of a segment
    Kept for compatibility
    """
    from .word_utils import extract_words_from_segment, detect_natural_pauses
    
    words = extract_words_from_segment(segment) if "words" in segment else []
    metrics = {
        "has_words": len(words) > 0,
        "word_count": len(words),
        "duration": dur(segment),
    }
    
    if words:
        metrics["word_density"] = len(words) / dur(segment) if dur(segment) > 0 else 0
        pauses = detect_natural_pauses(words, min_pause=0.2)
        metrics["pause_count"] = len(pauses)
        metrics["pauses"] = pauses
        word_durs = [w["end"] - w["start"] for w in words]
        metrics["avg_word_duration"] = sum(word_durs) / len(word_durs) if word_durs else 0
    
    return metrics


def get_timeline_statistics(timeline: List[Dict]) -> Dict[str, Any]:
    """
    Get statistics about timeline
    Kept for compatibility
    """
    speech_segs = [s for s in timeline if s.get("type") == "speech"]
    silence_segs = [s for s in timeline if s.get("type") == "silence"]

    total_duration = max(float(s["end"]) for s in timeline) if timeline else 0
    speech_duration = sum(dur(s) for s in speech_segs)
    silence_duration = sum(dur(s) for s in silence_segs)

    return {
        "total_segments": len(timeline),
        "speech_segments": len(speech_segs),
        "silence_segments": len(silence_segs),
        "total_duration": total_duration,
        "speech_duration": speech_duration,
        "silence_duration": silence_duration,
        "speech_ratio": speech_duration / total_duration if total_duration > 0 else 0,
    }
