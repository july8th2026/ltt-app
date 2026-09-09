"""
Text Processing Utilities
"""
from __future__ import annotations

import math
from typing import Dict, List

from .constants import WS_RE, PUNCT_ONLY_RE, SENT_SPLIT_RE


def clean_text(t: str) -> str:
    """Clean and normalize text"""
    return WS_RE.sub(" ", (t or "").strip())


def is_junk_text(t: str) -> bool:
    """Check if text is junk (empty, too short, or only punctuation)"""
    tt = clean_text(t)
    if not tt:
        return True
    if len(tt) < 2:
        return True
    if PUNCT_ONLY_RE.match(tt) is not None:
        return True
    return False


def split_text_by_sentence(txt: str) -> List[str]:
    """Split text into sentences"""
    parts = [p.strip() for p in SENT_SPLIT_RE.split(clean_text(txt)) if p.strip()]
    return parts if parts else [txt.strip()]


def split_text_smart(text: str, n_chunks: int) -> List[str]:
    """
    Split text thành n chunks, tránh duplicate
    Used for emergency split when no word boundaries available
    """
    text = clean_text(text)
    if not text:
        return [""] * n_chunks
    
    # Try split by sentence first
    sentences = split_text_by_sentence(text)
    if len(sentences) >= n_chunks:
        # Chia đều sentences
        chunk_size = len(sentences) // n_chunks
        chunks = []
        for i in range(n_chunks):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < n_chunks - 1 else len(sentences)
            chunk_text = " ".join(sentences[start_idx:end_idx]).strip()
            chunks.append(chunk_text if chunk_text else text)
        return chunks
    
    # Fallback: split by words
    words = text.split()
    if len(words) >= n_chunks:
        chunk_size = len(words) // n_chunks
        chunks = []
        for i in range(n_chunks):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < n_chunks - 1 else len(words)
            chunk_text = " ".join(words[start_idx:end_idx]).strip()
            chunks.append(chunk_text if chunk_text else text)
        return chunks
    
    # Last resort: add suffix to differentiate
    return [f"{text} [{i+1}/{n_chunks}]" for i in range(n_chunks)]


def normalize_text_for_comparison(t: str) -> str:
    """
    Normalize text for duplicate detection
    Removes suffixes like [1/2], [2/2]
    """
    import re
    t = clean_text(t)
    # Remove suffix pattern [N/M]
    t = re.sub(r'\s*\[\d+/\d+\]\s*$', '', t)
    return t.lower().strip()


def dur(s: Dict) -> float:
    """Calculate duration of a segment"""
    return float(s["end"]) - float(s["start"])
