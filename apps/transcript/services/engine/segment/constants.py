"""
Segment Constants & Patterns
"""
from __future__ import annotations

import re

# ============================================================
# REGEX PATTERNS
# ============================================================

WS_RE = re.compile(r"\s+")
PUNCT_ONLY_RE = re.compile(r'^[\s\.,!\?;\:\-—…""\'()\[\]\{\}]+$')
SENT_SPLIT_RE = re.compile(r"(?<=[\.\!\?…。！？])\s+")
CUT_HINT_RE = re.compile(r"[,\.\!\?\;\:…]+$")

# ============================================================
# PUNCTUATION CATEGORIES
# ============================================================

STRONG_PUNCT = (".", "!", "?", "…", ";", ":", "。", "！", "？")
MED_PUNCT = (",", "—", "–", "-", "，")

# ============================================================
# HARD BOUNDARIES (NON-NEGOTIABLE)
# ============================================================

HARD_MIN = 2.0  # Minimum speech duration
HARD_MAX = 6.0  # Maximum speech duration

SOFT_MIN = 2.5  # For gentle methods only
SOFT_MAX = 6.5  # For gentle methods only (rarely used)

# ============================================================
# SCORING WEIGHTS (for word boundary selection)
# ============================================================

W_PUNCT = 3.0   # Weight for punctuation strength
W_PAUSE = 3.0   # Weight for pause/gap
W_LEN = 1.0     # Penalty for deviation from target length
