"""Hook-Payoff coherence scorer — measures whether a clip's payoff resolves its hook.

A clip with a "How do I...?" hook should contain an answer.
A clip with a "The crazy thing is..." hook should contain a reveal.
A clip with setup → punchline should include the punchline.

Without coherence, clips feel incomplete even if hook and payoff scores are individually decent.

Coherence check logic:
1. Classify hook promise type (question → answer, claim → evidence, setup → punchline)
2. Scan payoff zone for matching resolution signals
3. Score match quality (0.0 = no resolution, 1.0 = clear resolution)
4. Apply distance penalty (payoff too far from hook = weaker coherence)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from cutclipshort.editorial.hook_detector import HookAnalysis
from cutclipshort.editorial.payoff_detector import PayoffAnalysis
from cutclipshort.types import TimeRange, TranscriptSegment

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoherenceResult:
    """Result of hook-payoff coherence analysis."""
    score: float           # 0.0-1.0
    hook_promise: str      # "question", "claim", "curiosity", "setup", "none"
    resolution_found: bool
    resolution_type: str   # "answer", "evidence", "reveal", "punchline", "none"
    distance_penalty: float  # 0.0-0.3 (how far payoff is from hook)
    reasoning: str


# Resolution patterns keyed by hook promise type
_RESOLUTION_PATTERNS: dict[str, list[str]] = {
    "question": [
        r"\b(the answer|because|the reason|it's because|that's why|so basically)\b",
        r"\b(you (can|should|need to|have to))\b",
        r"\b(here's (how|what|why))\b",
        r"\b(the (way|trick|secret|key) is)\b",
    ],
    "claim": [
        r"\b(for example|here's proof|the data shows|studies show)\b",
        r"\b(let me (show|explain|prove))\b",
        r"\b(and that's (why|how|what))\b",
        r"\b(so (that's|there you go|in conclusion))\b",
        # Narrative/descriptive resolution (v3)
        r"\b(look at|watch|see how|notice)\b",
        r"\b(satisfying|incredible|amazing|beautiful|perfect)\b",
        r"\b(the result|finally|complete|finished|done)\b",
        r"\b(before and after|transformation|clean|restored)\b",
    ],
    "curiosity": [
        r"\b(turns out|it was actually|the truth is|the answer is)\b",
        r"\b(what (happened|they found|we discovered))\b",
        r"\b(and (then|that's when))\b",
        # Visual payoff (v3)
        r"\b(look at (that|this)|watch (this|what)|see (the|how))\b",
        r"\b(satisfying|incredible|wow|unbelievable)\b",
    ],
    "setup": [
        r"\b(and then|but then|so)\b",
        r"\b(turns out|in the end|and that's)\b",
        # Process completion (v3)
        r"\b(finally|complete|done|finished|result)\b",
        r"\b(now (look|see|watch))\b",
    ],
}


def score_coherence(
    hook: HookAnalysis,
    payoff: PayoffAnalysis,
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
) -> CoherenceResult:
    """Score how well the payoff resolves the hook's promise.

    Args:
        hook: Hook analysis from hook_detector.
        payoff: Payoff analysis from payoff_detector.
        time_range: Full clip time range.
        transcript: All transcript segments for this clip.
    """
    # 1. Classify hook promise
    hook_promise = _classify_hook_promise(hook)

    if hook_promise == "none":
        # No clear promise → coherence doesn't apply → neutral score
        return CoherenceResult(
            score=0.5,
            hook_promise="none",
            resolution_found=False,
            resolution_type="none",
            distance_penalty=0.0,
            reasoning="No clear hook promise to resolve",
        )

    # 2. Get clip text (full)
    clip_text = _get_clip_text(time_range, transcript)
    # Get payoff zone text (last 40% of clip)
    payoff_start = time_range.start + time_range.duration * 0.6
    payoff_text = _get_clip_text(
        TimeRange(start=payoff_start, end=time_range.end), transcript,
    )

    # 3. Check for resolution in payoff zone
    resolution_found, resolution_type = _find_resolution(
        hook_promise, payoff_text, clip_text,
    )

    # 4. Distance penalty
    distance_penalty = _compute_distance_penalty(hook, payoff, time_range)

    # 5. Compute coherence score
    if resolution_found:
        base_score = 0.85
    elif payoff.sentence_complete > 0.5:
        # No explicit resolution but ends cleanly → partial credit
        base_score = 0.5
    else:
        base_score = 0.2

    score = max(0.0, min(1.0, base_score - distance_penalty))

    # Build reasoning
    parts = [f"hook_promise={hook_promise}"]
    if resolution_found:
        parts.append(f"resolution={resolution_type}")
    else:
        parts.append("NO resolution found")
    if distance_penalty > 0.05:
        parts.append(f"distance_penalty=-{distance_penalty:.2f}")

    return CoherenceResult(
        score=round(score, 3),
        hook_promise=hook_promise,
        resolution_found=resolution_found,
        resolution_type=resolution_type,
        distance_penalty=round(distance_penalty, 3),
        reasoning="; ".join(parts),
    )


def _classify_hook_promise(hook: HookAnalysis) -> str:
    """Determine what the hook promises the viewer."""
    if hook.hook_type == "question" or hook.question_score > 0:
        return "question"

    if hook.hook_type == "bold_statement" or hook.bold_score > 0:
        return "claim"

    text = hook.hook_text.lower()

    # Curiosity gap markers
    curiosity = (
        "the crazy thing", "you won't believe", "nobody tells",
        "the secret", "the truth", "what if", "imagine",
        "here's what", "did you know",
    )
    for c in curiosity:
        if c in text:
            return "curiosity"

    # Setup markers (comedy / story)
    setup = ("so", "okay so", "one day", "i was", "this happened")
    for s in setup:
        pattern = r'(?:^|\b)' + re.escape(s) + r'(?:\b|$)'
        if re.match(pattern, text):
            return "setup"

    if hook.keyword_score > 0.3:
        return "claim"  # Keyword hook = implicit claim

    return "none"


def _find_resolution(
    hook_promise: str,
    payoff_text: str,
    full_text: str,
) -> tuple[bool, str]:
    """Check if the clip contains a resolution for the hook promise.

    Three-tier resolution detection:
    1. Regex pattern matching in payoff zone (most reliable)
    2. Regex pattern matching in full text (fallback)
    3. Content structure matching (no regex, structural cues)
    """
    if not payoff_text:
        return False, "none"

    payoff_lower = payoff_text.lower()
    full_lower = full_text.lower()

    # Tier 1: Regex in payoff zone
    patterns = _RESOLUTION_PATTERNS.get(hook_promise, [])
    for pattern in patterns:
        if re.search(pattern, payoff_lower, re.IGNORECASE):
            return True, f"matched_{hook_promise}"

    # Tier 2: Regex in full text
    for pattern in patterns:
        if re.search(pattern, full_lower, re.IGNORECASE):
            return True, f"matched_{hook_promise}_mid"

    # Tier 3: Content structure detection (non-regex)
    found, rtype = _check_structural_resolution(hook_promise, payoff_lower, full_lower)
    if found:
        return True, rtype

    return False, "none"


def _check_structural_resolution(
    hook_promise: str,
    payoff_text: str,
    full_text: str,
) -> tuple[bool, str]:
    """Detect resolution through structural cues instead of keyword regex.

    For question hooks:  check if payoff contains declarative statements
    For claim hooks:     check if body has elaboration/examples
    For curiosity hooks: check for reveal structure (shorter sentence after buildup)
    For setup hooks:     check for punchline structure (pause/beat patterns)
    """
    if hook_promise == "question":
        # Declarative answer: payoff has statement with subject+verb, no question mark
        # More words in payoff than hook = elaboration = likely answer
        payoff_words = len(payoff_text.split())
        has_question_in_payoff = "?" in payoff_text
        if payoff_words > 15 and not has_question_in_payoff:
            return True, "structural_answer"

    elif hook_promise == "claim":
        # Claim evidence: full text has "because", "since", "for example"
        evidence_words = ("because", "since", "therefore", "as a result",
                          "for example", "for instance", "evidence", "proof")
        hits = sum(1 for w in evidence_words if w in full_text)
        if hits >= 2:
            return True, "structural_evidence"

    elif hook_promise == "curiosity":
        # Reveal: payoff contains factual/definitive language
        definitive = ("actually", "in fact", "the real", "what really",
                      "the truth", "it turns out", "in reality")
        if any(d in payoff_text for d in definitive):
            return True, "structural_reveal"

    elif hook_promise == "setup":
        # Punchline: short final sentence (< 8 words) after longer buildup
        sentences = [s.strip() for s in re.split(r'[.!?]+', payoff_text) if s.strip()]
        if len(sentences) >= 2:
            last_len = len(sentences[-1].split())
            prev_len = len(sentences[-2].split())
            if last_len <= 6 and prev_len >= 10:
                return True, "structural_punchline"

    return False, "none"


def _compute_distance_penalty(
    hook: HookAnalysis,
    payoff: PayoffAnalysis,
    time_range: TimeRange,
) -> float:
    """Penalty if the payoff is very far from the hook (long clip, weak middle)."""
    duration = time_range.duration
    if duration <= 30:
        return 0.0  # Short clips don't get penalized
    if duration <= 45:
        return 0.05
    if duration <= 60:
        return 0.10
    return 0.15  # Very long clips: harder to maintain coherence


def _get_clip_text(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
) -> str:
    """Extract transcript text within a time range."""
    matching = [s for s in transcript if s.time_range.overlaps(time_range)]
    return " ".join(s.text.strip() for s in matching)
