"""Semantic scorer — NLP-enhanced scoring for editorial intelligence.

Provides semantic analysis capabilities that go beyond keyword matching:

1. **Sentence structure analysis**: Detects rhetorical devices, narrative arcs
2. **Information density scoring**: Measures unique concepts per sentence
3. **Emotional intensity mapping**: Detects sentiment shifts and emphasis
4. **Topic coherence**: Measures whether text stays on-topic or rambles
5. **Narrative completeness**: Detects setup-development-resolution structure
6. **Hook sophistication**: Classifies hooks beyond keyword matching

All analysis is pure Python — no external ML models required.
Uses lexical analysis, sentence structure, and statistical text features.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Vocabulary system (multi-language) ────────────────────────────────
# Default to English; use set_language() or pass language to analyze_text()

# ── Vocabulary (English defaults, importable by other modules) ────────
# Other modules import these directly: from semantic_scorer import _EMOTION_HIGH
from cutclipshort.editorial.vocabulary.en import (
    EMOTION_HIGH as _EMOTION_HIGH,
    EMOTION_MEDIUM as _EMOTION_MEDIUM,
    EMOTION_MILD as _EMOTION_MILD,
    SETUP_MARKERS as _SETUP_MARKERS,
    DEVELOPMENT_MARKERS as _DEVELOPMENT_MARKERS,
    RESOLUTION_MARKERS as _RESOLUTION_MARKERS,
    FILLER_WORDS as _FILLER_WORDS,
    STOP_WORDS as _STOP_WORDS,
)


def _get_vocab(language: str = "en"):
    """Get vocabulary module for a specific language."""
    from cutclipshort.editorial.vocabulary import get_vocabulary
    return get_vocabulary(language)

# Rhetorical devices (language-neutral)
_CONTRAST_PAIRS = [
    ("not", "but"), ("isn't", "is"), ("don't", "do"),
    ("before", "after"), ("without", "with"), ("never", "always"),
    ("wrong", "right"), ("old", "new"), ("bad", "good"),
]

# NOTE: _FILLER_WORDS and _STOP_WORDS now imported from vocabulary.en above
# Other modules (emotion_mapper, narrative_segmenter) import them from here


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SemanticAnalysis:
    """Result of semantic analysis on a text segment."""
    # Scores (0.0-1.0)
    information_density: float    # Unique concepts per sentence
    emotional_intensity: float    # Emotional word density
    narrative_completeness: float # Has setup + development + resolution
    topic_coherence: float        # How focused/on-topic the text is
    rhetorical_strength: float    # Rhetorical devices detected

    # Composite
    semantic_score: float         # Weighted combination

    # Diagnostics
    unique_concepts: int          # Number of unique meaningful words
    sentence_count: int           # Number of sentences
    filler_ratio: float           # Fraction of filler words
    narrative_stages_found: list[str]  # Which stages detected
    rhetorical_devices: list[str]     # Which devices detected
    reasoning: str


def analyze_text(text: str) -> SemanticAnalysis:
    """Perform semantic analysis on a text segment.

    This is the main entry point for semantic scoring.
    Pure Python — no external models required.
    """
    if not text or len(text.strip()) < 10:
        return SemanticAnalysis(
            information_density=0.0, emotional_intensity=0.0,
            narrative_completeness=0.0, topic_coherence=0.5,
            rhetorical_strength=0.0, semantic_score=0.1,
            unique_concepts=0, sentence_count=0, filler_ratio=0.0,
            narrative_stages_found=[], rhetorical_devices=[],
            reasoning="Text too short for analysis",
        )

    lower = text.lower()
    words = _tokenize(lower)
    sentences = _split_sentences(text)

    # 1. Information density
    info_density, unique_concepts = _score_information_density(words, sentences)

    # 2. Emotional intensity
    emotional = _score_emotional_intensity(words)

    # 3. Narrative completeness
    narrative, stages = _score_narrative_completeness(lower, sentences)

    # 4. Topic coherence
    coherence = _score_topic_coherence(words, sentences)

    # 5. Rhetorical strength
    rhetorical, devices = _score_rhetorical_strength(lower, sentences)

    # 6. Filler ratio
    filler_ratio = _compute_filler_ratio(lower, words)

    # Composite score
    semantic_score = (
        info_density * 0.25
        + emotional * 0.15
        + narrative * 0.25
        + coherence * 0.20
        + rhetorical * 0.15
    )

    # Filler penalty
    if filler_ratio > 0.15:
        semantic_score *= max(0.5, 1.0 - filler_ratio)

    semantic_score = min(1.0, max(0.0, semantic_score))

    # Build reasoning
    parts = []
    if info_density > 0.7:
        parts.append(f"info_dense({unique_concepts} concepts)")
    if emotional > 0.5:
        parts.append(f"emotional({emotional:.2f})")
    if stages:
        parts.append(f"narrative({'+'.join(stages)})")
    if devices:
        parts.append(f"rhetoric({','.join(devices[:3])})")
    if filler_ratio > 0.1:
        parts.append(f"filler({filler_ratio:.0%})")

    return SemanticAnalysis(
        information_density=round(info_density, 3),
        emotional_intensity=round(emotional, 3),
        narrative_completeness=round(narrative, 3),
        topic_coherence=round(coherence, 3),
        rhetorical_strength=round(rhetorical, 3),
        semantic_score=round(semantic_score, 3),
        unique_concepts=unique_concepts,
        sentence_count=len(sentences),
        filler_ratio=round(filler_ratio, 3),
        narrative_stages_found=stages,
        rhetorical_devices=devices,
        reasoning=" | ".join(parts) if parts else "neutral",
    )


def score_hook_semantic(hook_text: str) -> float:
    """Score hook text using semantic analysis.

    Returns 0.0-1.0 score based on:
    - Opening sentence structure (question, command, statement)
    - Emotional intensity of first words
    - Information promise (will viewer learn something?)
    - Specificity (numbers, names, concrete details)
    """
    if not hook_text or len(hook_text.strip()) < 5:
        return 0.1

    lower = hook_text.lower().strip()
    words = lower.split()
    score = 0.0

    # 1. Specificity: numbers and concrete details
    numbers = re.findall(r'\b\d+\b', lower)
    if numbers:
        score += 0.20

    # 2. Direct address: "you" in first 5 words
    if "you" in words[:5] or "your" in words[:5]:
        score += 0.15

    # 3. Contrast/tension: "but", "however", "not X but Y"
    if any(w in words[:10] for w in ["but", "however", "yet", "except", "instead"]):
        score += 0.15

    # 4. Emotional intensity
    emotion_hits = sum(1 for w in words[:10] if w in _EMOTION_HIGH)
    if emotion_hits:
        score += 0.20
    elif sum(1 for w in words[:10] if w in _EMOTION_MEDIUM):
        score += 0.10

    # 5. Information promise: "how to", "X ways", "the secret", etc.
    promise_patterns = [
        r'\b\d+\s+(ways?|tips?|steps?|reasons?|things?|mistakes?)\b',
        r'\bhow to\b', r'\bwhy\b.*\bmatters?\b', r'\bthe (secret|truth|key)\b',
        r'\beverything you need\b', r'\bguide to\b',
    ]
    for pat in promise_patterns:
        if re.search(pat, lower):
            score += 0.15
            break

    # 6. Sentence structure: short, punchy opening = better hook
    first_sentence = _split_sentences(hook_text)[0] if _split_sentences(hook_text) else hook_text
    word_count = len(first_sentence.split())
    if word_count <= 8:
        score += 0.10  # Short and punchy
    elif word_count >= 20:
        score -= 0.05  # Too long for a hook

    return min(1.0, max(0.0, score))


def score_coherence_semantic(
    hook_text: str, full_text: str, payoff_text: str,
) -> float:
    """Score hook-payoff coherence using semantic similarity.

    Uses vocabulary overlap between hook and payoff to measure
    whether the payoff addresses the hook's topic.
    """
    if not hook_text or not payoff_text:
        return 0.3

    hook_concepts = _extract_concepts(hook_text.lower())
    payoff_concepts = _extract_concepts(payoff_text.lower())
    full_concepts = _extract_concepts(full_text.lower())

    if not hook_concepts:
        return 0.5

    # Concept overlap: what fraction of hook concepts appear in payoff?
    direct_overlap = len(hook_concepts & payoff_concepts) / len(hook_concepts)

    # Full text overlap (less strict)
    full_overlap = len(hook_concepts & full_concepts) / len(hook_concepts)

    # Combined score
    score = direct_overlap * 0.6 + full_overlap * 0.4

    # Bonus for development: payoff has NEW concepts (not just echo)
    new_in_payoff = len(payoff_concepts - hook_concepts)
    if new_in_payoff > 3:
        score = min(1.0, score + 0.15)  # Developed the topic

    return min(1.0, max(0.0, score))


# ══════════════════════════════════════════════════════════════════════════
# INTERNAL ANALYSIS FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════

def _tokenize(text: str) -> list[str]:
    """Simple word tokenization."""
    return re.findall(r'\b[a-z]+\b', text.lower())


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]


def _extract_concepts(text: str) -> set[str]:
    """Extract meaningful concept words (non-stop, non-filler)."""
    words = _tokenize(text)
    return {w for w in words if w not in _STOP_WORDS and w not in _FILLER_WORDS and len(w) > 2}


def _score_information_density(
    words: list[str], sentences: list[str],
) -> tuple[float, int]:
    """Score how information-dense the text is.

    High density = many unique meaningful words per sentence.
    """
    concepts = _extract_concepts(" ".join(words))
    unique_count = len(concepts)

    if not sentences:
        return 0.0, 0

    concepts_per_sentence = unique_count / len(sentences)

    # Ideal: 5-10 unique concepts per sentence
    if 5 <= concepts_per_sentence <= 10:
        score = 1.0
    elif concepts_per_sentence > 10:
        score = 0.85  # Very dense (might be too fast)
    elif concepts_per_sentence >= 3:
        score = concepts_per_sentence / 5.0
    else:
        score = max(0.1, concepts_per_sentence / 3.0)

    return min(1.0, score), unique_count


def _score_emotional_intensity(words: list[str]) -> float:
    """Score emotional intensity based on word choice."""
    if not words:
        return 0.0

    high_count = sum(1 for w in words if w in _EMOTION_HIGH)
    med_count = sum(1 for w in words if w in _EMOTION_MEDIUM)
    mild_count = sum(1 for w in words if w in _EMOTION_MILD)

    weighted = high_count * 3 + med_count * 2 + mild_count * 1
    total_words = len(words)

    # Normalize: expect ~5% emotional words in engaging content
    ratio = weighted / total_words if total_words > 0 else 0
    score = min(1.0, ratio / 0.05)

    return score


def _score_narrative_completeness(
    lower_text: str, sentences: list[str],
) -> tuple[float, list[str]]:
    """Score narrative structure: setup → development → resolution."""
    stages: list[str] = []

    # Check for setup markers
    for marker in _SETUP_MARKERS:
        if marker in lower_text[:100]:  # Setup should be near start
            stages.append("setup")
            break

    # Check for development markers
    for marker in _DEVELOPMENT_MARKERS:
        if marker in lower_text:
            stages.append("development")
            break

    # Check for resolution markers
    for marker in _RESOLUTION_MARKERS:
        # Resolution should be in last 40% of text
        cutoff = len(lower_text) * 6 // 10
        if marker in lower_text[cutoff:]:
            stages.append("resolution")
            break

    # Score based on stages present
    stage_count = len(stages)
    if stage_count == 3:
        score = 1.0
    elif stage_count == 2:
        score = 0.7
    elif stage_count == 1:
        score = 0.4
    else:
        # Fallback: if text has multiple sentences, it at least has structure
        if len(sentences) >= 3:
            score = 0.3
        else:
            score = 0.1

    return score, stages


def _score_topic_coherence(
    words: list[str], sentences: list[str],
) -> float:
    """Score how focused the text is on a single topic.

    Uses vocabulary overlap between sentences as a proxy for coherence.
    """
    if len(sentences) < 2:
        return 0.7  # Single sentence = trivially coherent

    # Extract concept sets per sentence
    sentence_concepts = [
        _extract_concepts(s) for s in sentences
    ]

    # Measure pairwise overlap between consecutive sentences
    overlaps = []
    for i in range(len(sentence_concepts) - 1):
        s1 = sentence_concepts[i]
        s2 = sentence_concepts[i + 1]
        if s1 and s2:
            overlap = len(s1 & s2) / min(len(s1), len(s2))
            overlaps.append(overlap)

    if not overlaps:
        return 0.5

    avg_overlap = sum(overlaps) / len(overlaps)

    # Also measure overall vocabulary concentration
    all_concepts = set()
    for sc in sentence_concepts:
        all_concepts |= sc

    if all_concepts:
        # How many concepts appear in multiple sentences?
        multi_appear = sum(
            1 for c in all_concepts
            if sum(1 for sc in sentence_concepts if c in sc) >= 2
        )
        concentration = multi_appear / len(all_concepts)
    else:
        concentration = 0.0

    score = avg_overlap * 0.6 + concentration * 0.4
    return min(1.0, score)


def _score_rhetorical_strength(
    lower_text: str, sentences: list[str],
) -> tuple[float, list[str]]:
    """Detect rhetorical devices: contrast, repetition, tricolon, etc."""
    devices: list[str] = []

    # 1. Contrast pairs
    for a, b in _CONTRAST_PAIRS:
        if a in lower_text and b in lower_text:
            devices.append("contrast")
            break

    # 2. Repetition (same word 3+ times = emphasis)
    words = _tokenize(lower_text)
    word_freq: dict[str, int] = {}
    for w in words:
        if w not in _STOP_WORDS and len(w) > 3:
            word_freq[w] = word_freq.get(w, 0) + 1
    repeated = [w for w, c in word_freq.items() if c >= 3]
    if repeated:
        devices.append("repetition")

    # 3. Tricolon (3 items in a list)
    tricolon_pattern = r'\b\w+,\s*\w+,?\s*(and|or)\s*\w+\b'
    if re.search(tricolon_pattern, lower_text):
        devices.append("tricolon")

    # 4. Rhetorical question
    questions = [s for s in sentences if s.strip().endswith("?")]
    if questions and len(sentences) > 1:
        # Question followed by answer = rhetorical
        for i, s in enumerate(sentences):
            if s.strip().endswith("?") and i < len(sentences) - 1:
                devices.append("rhetorical_question")
                break

    # 5. Anaphora (repeated sentence starters)
    if len(sentences) >= 3:
        starters = [s.split()[:2] if s.split() else [] for s in sentences]
        starter_strs = [" ".join(s) for s in starters if s]
        starter_freq: dict[str, int] = {}
        for s in starter_strs:
            starter_freq[s] = starter_freq.get(s, 0) + 1
        if any(c >= 2 for c in starter_freq.values()):
            devices.append("anaphora")

    score = min(1.0, len(devices) * 0.25)
    return score, devices


def _compute_filler_ratio(lower_text: str, words: list[str]) -> float:
    """Compute ratio of filler words in text."""
    if not words:
        return 0.0

    filler_count = 0
    for filler in _FILLER_WORDS:
        if " " in filler:
            filler_count += lower_text.count(filler)
        else:
            filler_count += sum(1 for w in words if w == filler)

    return filler_count / len(words) if words else 0.0
