from __future__ import annotations

import json
from typing import Optional

from .nhat_ky import info, debug


def calculate_cumulative_silence(insertion_plan: list[dict], time_point: float) -> float:
    """
    Calculate total silence added before a given time point.
    
    Args:
        insertion_plan: List of insertion points (sorted by at_sec)
        time_point: Time point to check (in seconds)
    
    Returns:
        Total silence in seconds added before time_point
    """
    total_silence_ms = 0
    
    for item in insertion_plan:
        if item["at_sec"] <= time_point:
            total_silence_ms += item["pause_ms"]
        else:
            break
    
    return total_silence_ms / 1000.0  # Convert to seconds


def adjust_transcript_timestamps(
    original_transcript: dict,
    insertion_plan: list[dict],
) -> dict:
    """
    Recalculate transcript timestamps after silence insertion.
    
    Logic:
        For each word/segment:
            new_start = old_start + cumulative_silence_before(old_start)
            new_end = old_end + cumulative_silence_before(old_end)
    
    Args:
        original_transcript: Original transcript from STT
        insertion_plan: List of insertion points (must be sorted by at_sec)
    
    Returns:
        New transcript with adjusted timestamps
    """
    
    if not insertion_plan:
        debug("transcript_no_adjustment", reason="no insertion points")
        return original_transcript.copy()
    
    # Sort insertion plan by time (just in case)
    sorted_plan = sorted(insertion_plan, key=lambda x: x["at_sec"])
    
    # Deep copy original transcript
    new_transcript = {
        "text": original_transcript.get("text", ""),
        "language": original_transcript.get("language", ""),
        "duration": original_transcript.get("duration", 0),
        "segments": [],
    }
    
    # Adjust segment and word timestamps
    for seg in original_transcript.get("segments", []):
        old_start = seg["start"]
        old_end = seg["end"]
        
        # Calculate silence added before this segment
        silence_before_start = calculate_cumulative_silence(sorted_plan, old_start)
        silence_before_end = calculate_cumulative_silence(sorted_plan, old_end)
        
        new_seg = {
            "start": old_start + silence_before_start,
            "end": old_end + silence_before_end,
            "text": seg["text"],
        }
        
        # Adjust word timestamps if available
        if "words" in seg:
            new_words = []
            for w in seg["words"]:
                old_w_start = w["start"]
                old_w_end = w["end"]
                
                silence_before_w_start = calculate_cumulative_silence(sorted_plan, old_w_start)
                silence_before_w_end = calculate_cumulative_silence(sorted_plan, old_w_end)
                
                new_words.append({
                    "word": w["word"],
                    "start": old_w_start + silence_before_w_start,
                    "end": old_w_end + silence_before_w_end,
                })
            
            new_seg["words"] = new_words
        
        new_transcript["segments"].append(new_seg)
    
    # Update total duration
    total_silence_s = sum(item["pause_ms"] for item in sorted_plan) / 1000.0
    new_transcript["duration"] = original_transcript.get("duration", 0) + total_silence_s
    
    info(
        "transcript_adjusted",
        original_duration_s=round(original_transcript.get("duration", 0), 2),
        new_duration_s=round(new_transcript["duration"], 2),
        silence_added_s=round(total_silence_s, 2),
        segments=len(new_transcript["segments"]),
    )
    
    return new_transcript


def save_transcript(transcript: dict, output_path: str) -> str:
    """Save transcript to JSON file"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    
    debug("transcript_saved", path=output_path)
    return output_path


def load_transcript(json_path: str) -> dict:
    """Load transcript from JSON file"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)
