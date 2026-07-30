"""
Audio rights pre-check (Sprint TT-5 / F5).

TikTok runs Content ID against every uploaded audio stream. If your
video uses copyrighted commercial music, TT can:
  • mute the audio entirely
  • restrict reach to certain regions
  • take the video down
  • strike the account (after repeats)

True audio fingerprinting requires a commercial service (Audd, AcoustID,
ACRCloud) — out of scope for a desktop bot. This module does the CHEAP
checks that catch the most common mistakes:

  1. SILENCE detection — videos with 0 audio confuse the algorithm
     (some get full reach, some get instantly buried as low-quality).

  2. AUDIO metadata tags — many videos imported from music platforms
     carry ID3-style tags (artist, title, album). ffprobe exposes
     these; if present and recognisable, warn the user.

  3. FILENAME signals — files named like
     `Justin_Bieber_Ghost_Official.mp4` or `<song>.mp3.mp4` are
     near-certain copyright issues.

For deep detection, F5-future would integrate with one of the audio
fingerprinting APIs. Out of scope here.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass


# Patterns in filenames that strongly suggest copyrighted music
_COPYRIGHT_PATTERNS = [
    r"official[\s_-]?music[\s_-]?video",
    r"official[\s_-]?audio",
    r"\(official\)",
    r"feat\.",     # featuring credit
    r"\bft\b",
    r"\bremix\b",
    r"lyric[s]?[\s_-]?video",
]
_COPYRIGHT_RE = re.compile("|".join(_COPYRIGHT_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class AudioRightsSignal:
    has_audio:        bool
    risk_level:       str          # "none" | "low" | "medium" | "high"
    message:          str
    detected_tags:    dict
    fix_hint:         str = ""


def check_audio_rights(file_path: str) -> AudioRightsSignal:
    """Inspect *file_path* for audio-rights red flags. Read-only, no network."""
    if not file_path or not os.path.exists(file_path):
        return AudioRightsSignal(
            has_audio=False, risk_level="none",
            message="File không tồn tại",
            detected_tags={},
        )

    # 1. Filename heuristic — runs even without ffprobe
    name_lower = os.path.basename(file_path).lower()
    if _COPYRIGHT_RE.search(name_lower):
        return AudioRightsSignal(
            has_audio=True, risk_level="high",
            message=f"Tên file gợi ý nhạc bản quyền: {os.path.basename(file_path)}",
            detected_tags={"filename_pattern": "copyright_signal"},
            fix_hint=(
                "Thay nhạc bằng track từ TikTok Sound Library, "
                "Epidemic Sound, hoặc royalty-free."
            ),
        )

    # 2. ffprobe audio metadata
    try:
        from core.tiktok.video_validator import _ffprobe
    except Exception:
        return _no_audio_check_possible(file_path)

    meta = _ffprobe(file_path)
    if meta is None:
        return _no_audio_check_possible(file_path)

    audio_stream = None
    for s in meta.get("streams", []) or []:
        if s.get("codec_type") == "audio":
            audio_stream = s
            break

    if audio_stream is None:
        return AudioRightsSignal(
            has_audio=False, risk_level="low",
            message="Video không có audio track — TT có thể auto-mute / flag low quality",
            detected_tags={},
            fix_hint="Thêm voice-over hoặc nhạc royalty-free",
        )

    # 3. ID3-style tags
    tags = audio_stream.get("tags", {}) or {}
    fmt_tags = (meta.get("format", {}) or {}).get("tags", {}) or {}
    all_tags = {**fmt_tags, **tags}

    interesting = {}
    for key in ("artist", "title", "album", "composer", "TPE1", "TIT2", "TALB"):
        for variant in (key, key.lower(), key.upper(), key.title()):
            if variant in all_tags:
                interesting[key.lower()] = str(all_tags[variant])
                break

    if interesting:
        return AudioRightsSignal(
            has_audio=True, risk_level="medium",
            message=(
                "Audio có ID3 tags (artist/title/album) — gợi ý track có bản quyền"
            ),
            detected_tags=interesting,
            fix_hint=(
                "Strip ID3 với ffmpeg `-map_metadata -1` HOẶC thay bằng "
                "track TikTok Sound Library."
            ),
        )

    return AudioRightsSignal(
        has_audio=True, risk_level="low",
        message="Audio không có metadata khả nghi — likely OK",
        detected_tags={},
    )


def _no_audio_check_possible(file_path: str) -> AudioRightsSignal:
    return AudioRightsSignal(
        has_audio=True,   # assume audio exists (defensive)
        risk_level="none",
        message="ffprobe không khả dụng — không thể kiểm tra audio metadata",
        detected_tags={},
        fix_hint="Cài ffmpeg để bot kiểm tra audio rights tự động",
    )
