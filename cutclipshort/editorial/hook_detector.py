"""Hook detector — scores the opening strength of a candidate segment.

A "hook" is the first 2-5 seconds of a clip. Strong hooks keep viewers
from scrolling. This module scores hook potential using:

1. **Keyword matching**: Does the opening sentence use attention-grabbing words?
2. **Question detection**: Questions create curiosity gaps.
3. **Speech energy**: Confident, energetic delivery signals importance.
4. **Silence avoidance**: Dead air in the first 2s kills retention.
5. **Bold statement detection**: Numbers, superlatives, contrarian claims.

Scoring range: 0.0 (weak/no hook) to 1.0 (extremely strong hook).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.editorial.thresholds import T as _T
from cutclipshort.types import (
    AudioSegment,
    TimeRange,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)

# ── Hook window ──────────────────────────────────────────────────────────
HOOK_WINDOW_SEC = 3.0  # First N seconds define the hook


@dataclass(frozen=True)
class HookAnalysis:
    """Detailed hook analysis result."""
    score: float              # 0.0-1.0 composite
    hook_text: str            # The opening words (≤ first 2 sentences)
    hook_type: str            # "question", "bold_statement", "keyword", "organic"
    keyword_score: float      # 0.0-1.0
    question_score: float     # 0.0 or bonus
    energy_score: float       # 0.0-1.0
    silence_penalty: float    # 0.0-0.3 (subtracted)
    bold_score: float         # 0.0 or bonus
    reasoning: str            # Human-readable explanation


def score_hook(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
    profile: GenreProfile,
) -> HookAnalysis:
    """Score the hook potential of a segment's opening.

    Args:
        time_range: The full candidate time range.
        transcript: All transcript segments (will filter to hook window).
        audio_segments: All audio segments (will filter to hook window).
        profile: Genre profile with keyword lists and weights.

    Returns:
        HookAnalysis with composite score and breakdown.
    """
    hook_end = time_range.start + HOOK_WINDOW_SEC
    hook_range = TimeRange(start=time_range.start, end=min(hook_end, time_range.end))

    # Extract opening text from transcript
    hook_text, hook_segments = _extract_hook_text(hook_range, transcript)
    hook_lower = hook_text.lower().strip()

    # 1. Keyword matching
    keyword_score = _score_keywords(hook_lower, profile)

    # 2. Question detection
    question_score = _score_question(hook_lower, profile)

    # 3. Bold statement detection (numbers, superlatives)
    bold_score = _score_bold_statement(hook_lower, profile)

    # 4. Speech energy in hook window
    energy_score = _score_energy(hook_range, audio_segments)

    # 5. Silence penalty (dead air at start)
    silence_penalty = _compute_silence_penalty(hook_range, audio_segments)

    # Content engagement score — detects engaging language that isn't keyword/question/bold
    engagement_score = _score_content_engagement(hook_lower)

    # Composite: genre-aware weighting
    q_bonus = profile.question_bonus
    b_bonus = profile.bold_statement_bonus

    # Best text signal: keyword, question, bold, or engagement
    best_text_signal = max(keyword_score, question_score + q_bonus, bold_score + b_bonus, engagement_score)

    raw = (
        energy_score * 0.25
        + best_text_signal * 0.35           # Strongest text signal dominates
        + engagement_score * 0.15           # Base engagement always contributes
        + (0.15 if hook_text else 0.0)      # Having speech at all
        - silence_penalty
    )
    score = max(0.0, min(1.0, raw))

    # Classify hook type — expanded taxonomy (v2.1)
    hook_type = _classify_hook_type(
        hook_lower, keyword_score, question_score, bold_score, energy_score,
    )

    # Build reasoning
    reasons = []
    if keyword_score > _T.hook_keyword_threshold:
        reasons.append(f"strong keyword match ({keyword_score:.2f})")
    if question_score > 0:
        reasons.append("opens with question")
    if bold_score > 0:
        reasons.append("bold/numeric claim")
    if energy_score > _T.hook_energy_strong:
        reasons.append(f"high speech energy ({energy_score:.2f})")
    if silence_penalty > _T.hook_silence_penalty_threshold:
        reasons.append(f"dead air penalty (-{silence_penalty:.2f})")
    if not hook_text:
        reasons.append("no speech in hook window")

    reasoning = "; ".join(reasons) if reasons else "average organic opening"

    # Confidence level for the hook type classification
    hook_confidence = max(keyword_score, question_score, bold_score, energy_score * 0.5)

    return HookAnalysis(
        score=round(score, 3),
        hook_text=hook_text[:150],
        hook_type=hook_type,
        keyword_score=round(keyword_score, 3),
        question_score=round(question_score, 3),
        energy_score=round(energy_score, 3),
        silence_penalty=round(silence_penalty, 3),
        bold_score=round(bold_score, 3),
        reasoning=reasoning,
    )


# ── Hook type taxonomy (v2.1) ────────────────────────────────────────────

# 7 hook types:
#   question    — "How do you...?", "Why does...?"
#   curiosity   — "The crazy thing is...", "Nobody tells you..."
#   conflict    — "Stop doing this", "The problem with...", "Wrong"
#   surprise    — "I couldn't believe...", "Plot twist", numbers/stats
#   emotional   — "I remember when...", "The hardest part..."
#   authority   — "As a doctor...", "After 10 years of..."
#   reaction    — "Wait what?", "No way", energy spike (prosody)

_CURIOSITY_PATTERNS = (
    "the crazy thing", "you won't believe", "nobody tells you",
    "the secret", "what if", "imagine", "little known",
    "most people don't", "here's what", "did you know",
    # Descriptive/imperative hooks (v3) — "Look at this!" style
    "look at", "look closely", "watch this", "watch what",
    "see how", "see this", "check this", "notice how",
    "before us", "can you see", "can you hear",
)

_IMPERATIVE_PATTERNS = (
    "look at", "look closely", "watch this", "watch what",
    "see how", "listen to", "check this out", "notice",
    "feel the", "smell the", "touch the",
)

_CONFLICT_PATTERNS = (
    "stop", "wrong", "don't", "the problem", "myth",
    "lie", "truth is", "unpopular opinion", "hot take",
    "i disagree", "actually no",
)

_EMOTIONAL_PATTERNS = (
    "i remember", "the hardest", "i'll never forget",
    "it broke my heart", "the moment i", "i was devastated",
    "i couldn't stop", "it changed my life",
)

_AUTHORITY_PATTERNS = (
    r"as a \w+", r"after \d+ years", r"with \d+ years",
    r"in my \d+ years", "as someone who", "having worked",
    "as an expert", "professionally",
)


def _classify_hook_type(
    text: str,
    keyword_score: float,
    question_score: float,
    bold_score: float,
    energy_score: float,
) -> str:
    """Classify hook into one of 7 types based on text and signal scores."""
    if not text:
        return "organic"

    # Priority order: most specific first

    # 1. Question (explicit ?)
    if question_score > 0:
        return "question"

    # 2. Authority (credibility-based hook)
    for pat in _AUTHORITY_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "authority"

    # 3. Emotional (personal/vulnerable)
    for pat in _EMOTIONAL_PATTERNS:
        if pat in text:
            return "emotional"

    # 4. Imperative/descriptive (v3 — "Look at this!")
    for pat in _IMPERATIVE_PATTERNS:
        if pat in text:
            return "curiosity"  # Imperative hooks create curiosity

    # 5. Conflict (contrarian/problem)
    for pat in _CONFLICT_PATTERNS:
        if pat in text:
            return "conflict"

    # 6. Surprise (numbers, bold claims)
    if bold_score > 0:
        return "surprise"

    # 7. Curiosity (gap/tease)
    for pat in _CURIOSITY_PATTERNS:
        if pat in text:
            return "curiosity"

    # 7. Reaction (energy spike, exclamation)
    if energy_score > _T.hook_bold_energy_threshold and "!" in text:
        return "reaction"

    # Fallback
    if keyword_score > _T.hook_keyword_threshold:
        return "curiosity"  # Keyword hooks usually create curiosity

    return "organic"


# ── Content engagement scoring ───────────────────────────────────────────

# Words/phrases that signal engaging content even without being a "hook keyword"
_ENGAGEMENT_WORDS = (
    # Sensory/descriptive (review, showcase, ASMR)
    "satisfying", "incredible", "amazing", "beautiful", "horrifying",
    "mesmerizing", "disgusting", "fascinating", "stunning", "terrifying",
    # Action/process (tutorial, cleaning, cooking)
    "watch", "look", "see", "notice", "listen", "feel",
    "transform", "clean", "remove", "reveal", "restore",
    # Intensity markers
    "extremely", "absolutely", "completely", "totally", "incredibly",
    "massive", "tiny", "enormous", "worst", "best",
    # Narrative engagement
    "before", "after", "finally", "suddenly", "first", "next",
    "challenge", "battle", "fight", "struggle", "resist",
)


def _score_content_engagement(text: str) -> float:
    """Score how engaging the opening text is, regardless of hook type.

    Catches narration/descriptive content that doesn't match hook patterns
    but is still attention-grabbing. Supports both EN and VI.
    """
    if not text:
        return 0.0

    hits = sum(1 for word in _ENGAGEMENT_WORDS if word in text)
    hits += sum(1 for word in _ENGAGEMENT_WORDS_VI if word in text)

    if hits >= 4:
        return 0.8
    elif hits >= 3:
        return 0.65
    elif hits >= 2:
        return 0.5
    elif hits >= 1:
        return 0.35
    return 0.1  # Base: some speech exists but not engaging


# ── Internal scoring functions ───────────────────────────────────────────

def _extract_hook_text(
    hook_range: TimeRange,
    transcript: list[TranscriptSegment],
) -> tuple[str, list[TranscriptSegment]]:
    """Get transcript text within the hook window."""
    matching = [
        seg for seg in transcript
        if seg.time_range.overlaps(hook_range)
    ]
    if not matching:
        return "", []

    # Take text from segments that start within or overlap the hook window
    # Limit to first ~2 sentences
    text_parts = []
    for seg in matching[:3]:  # At most 3 segments
        text_parts.append(seg.text.strip())

    full = " ".join(text_parts)
    # Truncate to roughly 2 sentences
    sentences = re.split(r'(?<=[.!?])\s+', full)
    hook_text = " ".join(sentences[:2])

    return hook_text, matching


def _score_keywords(text: str, profile: GenreProfile) -> float:
    """Score based on genre-specific hook keywords (EN + VI) with word-boundary matching."""
    if not text:
        return 0.0

    score = 0.0

    # Check English keyword list with word-boundary regex
    for kw in profile.hook_keywords:
        pattern = r'(?:^|\b)' + re.escape(kw) + r'(?:\b|$)'
        if re.search(pattern, text, re.IGNORECASE):
            score = max(score, 0.5)
            if re.match(r'^' + re.escape(kw) + r'\b', text, re.IGNORECASE):
                score = max(score, 0.8)
            break

    # Check Vietnamese keywords (substring match — VI doesn't have word boundaries like EN)
    for kw in profile.hook_keywords_vi:
        if kw in text:
            score = max(score, 0.5)
            if text.startswith(kw):
                score = max(score, 0.8)
            break

    # Check English regex patterns
    for pat in profile.hook_patterns:
        if re.search(pat, text, re.IGNORECASE):
            score = max(score, 0.7)
            break

    # Check Vietnamese regex patterns
    for pat in profile.hook_patterns_vi:
        if re.search(pat, text, re.IGNORECASE):
            score = max(score, 0.7)
            break

    # v3: Imperative/descriptive hook detection (universal — all genres)
    if score < 0.5:
        for imp in _IMPERATIVE_PATTERNS:
            if imp in text.lower():
                score = max(score, 0.6)
                break

    return min(1.0, score)


def _score_question(text: str, profile: GenreProfile) -> float:
    """Detect if hook opens with a question (EN + VI)."""
    if not text:
        return 0.0

    # Check for question mark in first sentence
    first_sentence = re.split(r'(?<=[.!?])\s+', text)[0]
    if "?" in first_sentence:
        return profile.question_bonus

    # English question words at start
    question_starters_en = (
        "how", "why", "what", "when", "where", "who",
        "did you", "have you", "do you", "can you",
        "is it", "are you", "would you",
    )
    for starter in question_starters_en:
        if text.startswith(starter):
            return profile.question_bonus * 0.8

    # Vietnamese question words at start
    question_starters_vi = (
        "tại sao", "vì sao", "làm sao", "như thế nào",
        "bao giờ", "ở đâu", "ai là", "cái gì",
        "bạn có", "bạn đã", "có phải", "liệu",
        "sao lại", "thế nào", "bao nhiêu",
    )
    for starter in question_starters_vi:
        if text.startswith(starter):
            return profile.question_bonus * 0.8

    return 0.0


# Modern Vietnamese TikTok hook markers — used in _score_content_engagement
_ENGAGEMENT_WORDS_VI = (
    # Sensory/reaction (3+ chars, distinctive)
    "choáng", "sốc luôn", "điên thật", "ghê quá", "kinh quá", "xỉu luôn",
    "đỉnh quá", "cháy quá", "mê luôn", "cực kỳ",
    # Conversational engagement (multi-word)
    "biết không", "xem coi", "coi nè", "nghe nè",
    "kiểu như", "cái này hay", "như kiểu",
    "bạn thấy không", "nhìn nè", "thử xem",
    # Modern slang (3+ chars)
    "slay", "vibe", "flex",
    "gắt quá", "đỉnh kout", "xịn quá", "chất quá", "phết đấy",
    # Intensity (3+ chars)
    "quá trời", "cực kỳ", "siêu đỉnh", "khủng khiếp",
    "tuyệt vời", "không thể tin", "đẳng cấp",
    # Narrative engagement
    "bất ngờ", "không ngờ", "thật không", "tin được không",
)


def _score_bold_statement(text: str, profile: GenreProfile) -> float:
    """Detect bold claims: numbers, superlatives, contrarian statements."""
    if not text:
        return 0.0

    score = 0.0

    # Numbers/statistics in opening ("3 things", "90% of people")
    if re.search(r'\b\d+\s*(ways|things|reasons|tips|mistakes|percent|%)', text):
        score = max(score, profile.bold_statement_bonus)

    # Superlatives
    superlatives = ("best", "worst", "biggest", "most important",
                    "number one", "#1", "only", "never", "always",
                    "nobody", "everyone", "everything")
    for sup in superlatives:
        if sup in text:
            score = max(score, profile.bold_statement_bonus * 0.8)
            break

    # Contrarian markers
    contrarian = ("actually", "wrong", "stop", "don't", "myth",
                  "lie", "truth is", "unpopular opinion")
    for c in contrarian:
        if c in text:
            score = max(score, profile.bold_statement_bonus)
            break

    return min(1.0, score)


def _score_energy(
    hook_range: TimeRange,
    audio_segments: list[AudioSegment],
) -> float:
    """Score speech energy in the hook window."""
    relevant = [
        seg for seg in audio_segments
        if seg.time_range.overlaps(hook_range)
    ]
    if not relevant:
        return 0.3  # No data = neutral

    # Average energy, weighted toward segments with speech
    total_energy = 0.0
    total_weight = 0.0
    for seg in relevant:
        w = 1.5 if seg.has_speech else 0.5
        total_energy += seg.energy_avg * w
        total_weight += w

    avg_energy = total_energy / total_weight if total_weight > 0 else 0.0

    # Normalize: energy 0.3+ is considered strong for speech
    return min(1.0, avg_energy / 0.4)


def _compute_silence_penalty(
    hook_range: TimeRange,
    audio_segments: list[AudioSegment],
) -> float:
    """Penalize silence at the very start of the clip (first 2 seconds)."""
    start_window = TimeRange(
        start=hook_range.start,
        end=min(hook_range.start + 2.0, hook_range.end),
    )

    relevant = [
        seg for seg in audio_segments
        if seg.time_range.overlaps(start_window) and seg.has_silence
    ]

    if not relevant:
        return 0.0

    # Calculate silence ratio in the opening 2 seconds
    silence_sec = sum(
        seg.time_range.overlap_duration(start_window)
        for seg in relevant
    )
    ratio = silence_sec / start_window.duration if start_window.duration > 0 else 0.0

    # Up to 0.3 penalty for full silence at start
    return min(0.3, ratio * 0.3)
