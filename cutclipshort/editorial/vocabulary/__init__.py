"""Multi-language vocabulary system for editorial intelligence.

Auto-detects language from transcript and returns appropriate vocabulary sets.
Falls back to English if language not supported.

Usage:
    from cutclipshort.editorial.vocabulary import get_vocabulary
    vocab = get_vocabulary("vi")  # or "en", or "auto" with transcript
    vocab.EMOTION_HIGH  # frozenset of high-emotion words
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_vocabulary(language: str = "en"):
    """Get vocabulary module for a language.

    Args:
        language: ISO 639-1 code ("en", "vi") or "auto" for detection.

    Returns:
        Vocabulary module with all word sets.
    """
    if language == "vi":
        from cutclipshort.editorial.vocabulary import vi
        return vi
    # Default: English
    from cutclipshort.editorial.vocabulary import en
    return en


def detect_language(transcript_text: str) -> str:
    """Simple language detection from transcript text.

    Checks for Vietnamese diacritics. Falls back to "en".
    """
    if not transcript_text:
        return "en"

    # Vietnamese has unique diacritical marks
    vi_chars = set("\u00e0\u00e1\u1ea3\u00e3\u1ea1\u0103\u1eaf\u1eb1\u1eb3\u1eb5\u1eb7\u00e2\u1ea5\u1ea7\u1ea9\u1eab\u1ead\u00e8\u00e9\u1ebb\u1ebd\u1eb9\u00ea\u1ebf\u1ec1\u1ec3\u1ec5\u1ec7\u00ec\u00ed\u1ec9\u0129\u1ecb\u00f2\u00f3\u1ecf\u00f5\u1ecd\u00f4\u1ed1\u1ed3\u1ed5\u1ed7\u1ed9\u01a1\u1edb\u1edd\u1edf\u1ee1\u1ee3\u00f9\u00fa\u1ee7\u0169\u1ee5\u01b0\u1ee9\u1eeb\u1eed\u1eef\u1ef1\u1ef3\u00fd\u1ef7\u1ef9\u1ef5\u0111")
    text_lower = transcript_text.lower()
    vi_count = sum(1 for c in text_lower if c in vi_chars)

    # Check 1: Diacritics (most reliable for real Whisper output)
    if len(text_lower) > 20 and vi_count / len(text_lower) > 0.02:
        return "vi"

    # Check 2: Common Vietnamese words without diacritics (fallback)
    vi_words = {"cac", "ban", "chung", "ta", "nay", "thi", "voi", "cho",
                "cua", "nhu", "nhung", "khong", "duoc", "rat", "cung",
                "biet", "lam", "xin", "moi", "nguoi", "hay", "noi"}
    words = set(text_lower.split())
    vi_word_hits = len(words & vi_words)
    if vi_word_hits >= 3:
        return "vi"

    return "en"
