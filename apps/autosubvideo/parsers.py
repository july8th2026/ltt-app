"""
Transcript format parsers for autosubvideo.

Extracted from the original auto_sub_video API layer. Parses uploaded
transcript files (SRT / VTT / ASS / SSA / JSON) into a normalized list of
segment dicts shaped like:

    {"start": float, "end": float, "text": str, "type": "speech"}

Dispatch by file extension via `parse_transcript(filename, raw_bytes)`.
"""
from __future__ import annotations

import json
import re


# ── Timecode helpers ──────────────────────────────────────────────────────────

def _tc_to_sec(tc: str) -> float:
    """Convert SRT/VTT timecode 'HH:MM:SS,mmm' or 'HH:MM:SS.mmm' → seconds."""
    tc = tc.replace(",", ".")
    m = re.match(r"(\d+):(\d+):(\d+)[.](\d+)", tc)
    if not m:
        return 0.0
    return int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000


def _ass_tc_to_sec(tc: str) -> float:
    """Convert ASS timecode 'H:MM:SS.cc' → seconds."""
    m = re.match(r"(\d+):(\d+):(\d+)[.](\d+)", tc.strip())
    if not m:
        return 0.0
    return int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 100


# ── Format parsers ────────────────────────────────────────────────────────────

def _parse_srt(text: str) -> list[dict]:
    """Parse SRT subtitle → [{start, end, text, type}]."""
    blocks = text.strip().replace("\r\n", "\n").split("\n\n")
    result = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        ts_line = None
        for line in lines:
            if "-->" in line:
                ts_line = line
                break
        if not ts_line:
            continue
        m = re.match(
            r"(\d{2}:\d{2}:\d{2}[,.:]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.:]\d{3})",
            ts_line,
        )
        if not m:
            continue
        start = _tc_to_sec(m[1])
        end = _tc_to_sec(m[2])
        ts_idx = lines.index(ts_line)
        seg_text = "\n".join(lines[ts_idx + 1:]).strip()
        seg_text = re.sub(r"<[^>]+>", "", seg_text)  # strip HTML tags
        if seg_text and end > start:
            result.append({"start": start, "end": end, "text": seg_text, "type": "speech"})
    if not result:
        raise ValueError("Không tìm thấy segment nào trong file SRT")
    return result


def _parse_vtt(text: str) -> list[dict]:
    """Parse WebVTT → [{start, end, text, type}]."""
    # Remove WEBVTT header and NOTE blocks
    cleaned = re.sub(r"^WEBVTT.*?\n\n", "", text, count=1, flags=re.DOTALL)
    cleaned = re.sub(r"^NOTE[\s\S]*?\n\n", "", cleaned, flags=re.MULTILINE)
    result = _parse_srt(cleaned)
    if not result:
        raise ValueError("Không tìm thấy segment nào trong file VTT")
    return result


def _parse_ass(text: str) -> list[dict]:
    """Parse ASS/SSA subtitle → [{start, end, text, type}]."""
    result = []
    for line in text.split("\n"):
        line = line.strip()
        if not line.startswith("Dialogue:"):
            continue
        # Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
        # Use maxsplit=9 so commas inside Text field are preserved
        parts = line[10:].split(",", 9)
        if len(parts) < 10:
            continue
        start = _ass_tc_to_sec(parts[1])
        end = _ass_tc_to_sec(parts[2])
        raw_text = parts[9]
        # Strip ASS override tags {...} and convert \N to newline
        seg_text = re.sub(r"\{[^}]*\}", "", raw_text)
        seg_text = seg_text.replace("\\N", "\n").replace("\\n", "\n").strip()
        if seg_text and end > start:
            result.append({"start": start, "end": end, "text": seg_text, "type": "speech"})
    if not result:
        raise ValueError("Không tìm thấy Dialogue nào trong file ASS")
    return result


def _parse_json(text: str) -> list[dict]:
    """Parse JSON transcript → [{start, end, text, type}].

    The original API layer parsed JSON transcripts via json.loads() and
    validated that the result is a non-empty list. Here we additionally
    normalize each item into the canonical segment shape so callers get a
    consistent structure regardless of source format.
    """
    data = json.loads(text)
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Transcript JSON phải là array có ít nhất 1 segment")

    result: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        result.append({
            "start": float(item.get("start", 0) or 0),
            "end": float(item.get("end", 0) or 0),
            "text": str(item.get("text", "")),
            "type": str(item.get("type", "speech")),
        })
    if not result:
        raise ValueError("Không tìm thấy segment nào trong file JSON")
    return result


# ── Dispatch ──────────────────────────────────────────────────────────────────

def _get_ext(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def parse_transcript(filename: str, raw_bytes: bytes) -> list[dict]:
    """
    Parse a transcript file into a list of segment dicts.

    Dispatches by file extension (.srt / .vtt / .ass / .ssa / .json) and
    returns a list of dicts shaped like:
        {"start": float, "end": float, "text": str, "type": "speech"}

    Raises ValueError on unsupported extension or unparseable content.
    """
    ext = _get_ext(filename)
    text = raw_bytes.decode("utf-8", errors="replace")

    if ext == ".json":
        return _parse_json(text)
    if ext == ".srt":
        return _parse_srt(text)
    if ext == ".vtt":
        return _parse_vtt(text)
    if ext in {".ass", ".ssa"}:
        return _parse_ass(text)

    raise ValueError(
        f"Transcript không hỗ trợ: {ext}. "
        f"Chấp nhận: .ass, .json, .srt, .ssa, .vtt"
    )
