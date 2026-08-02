"""Pre-export quality checker — validates candidates BEFORE rendering.

Unlike the post-render evaluators (audio_evaluator, visual_evaluator, etc.)
which score the rendered output file, this checker validates the ClipSpec
and candidate data at plan time. It catches issues before wasting render time.

Checks performed:
1. Opening strength (hook text present, not weak filler)
2. Subtitle readability (line length, estimated text density)
3. Crop safety (zoom not excessive, person data available)
4. Clip completeness (sentence boundaries, duration sanity)
5. Duration sanity (within platform constraints)

Returns a PreExportReport with per-check pass/fail and human-readable issues.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from cutclipshort.types import (
    CandidateClip,
    ClipSpec,
    EditConstraints,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckResult:
    """Result of a single quality check."""
    name: str           # "opening_strength", "subtitle_readability", etc.
    passed: bool
    score: float        # 0.0-1.0
    message: str        # Human-readable explanation
    severity: str       # "error", "warning", "info"


@dataclass(frozen=True)
class PreExportReport:
    """Aggregated quality report for a candidate clip."""
    candidate_id: str
    checks: list[CheckResult]
    overall_passed: bool
    overall_score: float   # 0.0-100.0
    issues: list[str]      # Human-readable issue list
    suggestions: list[str] # Actionable improvement suggestions


def check_candidate(
    candidate: CandidateClip,
    clip_spec: ClipSpec | None = None,
    constraints: EditConstraints | None = None,
) -> PreExportReport:
    """Run all pre-export quality checks on a candidate.

    Args:
        candidate: The candidate clip to check.
        clip_spec: Optional ClipSpec for render-specific checks.
        constraints: Platform constraints for duration validation.

    Returns:
        PreExportReport with all check results.
    """
    checks: list[CheckResult] = []

    checks.append(_check_opening_strength(candidate))
    checks.append(_check_subtitle_readability(candidate, clip_spec))
    checks.append(_check_subtitle_burst(candidate))
    checks.append(_check_crop_safety(candidate, clip_spec))
    checks.append(_check_completeness(candidate))
    checks.append(_check_dead_tail(candidate))
    checks.append(_check_outro_cta(candidate))
    checks.append(_check_duration(candidate, constraints))
    checks.append(_check_coherence(candidate))
    checks.append(_check_risk_flags(candidate))

    # Aggregate
    overall_passed = all(c.passed for c in checks if c.severity == "error")
    scores = [c.score for c in checks]
    overall_score = round((sum(scores) / len(scores)) * 100, 1) if scores else 0.0

    issues = [c.message for c in checks if not c.passed]
    suggestions = _generate_suggestions(checks, candidate)

    return PreExportReport(
        candidate_id=candidate.candidate_id,
        checks=checks,
        overall_passed=overall_passed,
        overall_score=overall_score,
        issues=issues,
        suggestions=suggestions,
    )


def check_batch(
    candidates: list[CandidateClip],
    clip_specs: list[ClipSpec] | None = None,
    constraints: EditConstraints | None = None,
) -> list[PreExportReport]:
    """Check multiple candidates. Returns one report per candidate."""
    specs = clip_specs or [None] * len(candidates)
    return [
        check_candidate(c, s, constraints)
        for c, s in zip(candidates, specs)
    ]


# ══════════════════════════════════════════════════════════════════════════
# INDIVIDUAL CHECKS
# ══════════════════════════════════════════════════════════════════════════

def _check_opening_strength(candidate: CandidateClip) -> CheckResult:
    """Check 1: Does the clip start with a strong hook?"""
    hook = candidate.hook_text.strip().lower() if candidate.hook_text else ""

    if not hook:
        return CheckResult(
            name="opening_strength",
            passed=False,
            score=0.2,
            message="No hook text detected — clip may start without speech.",
            severity="warning",
        )

    # Check for filler/weak openings (EN + VI)
    filler_starts = (
        "um", "uh", "so um", "like", "yeah so", "okay um",
        "à", "ừm", "thì", "nói chung là", "ờ", "vâng thì",
    )
    for filler in filler_starts:
        if hook.startswith(filler):
            return CheckResult(
                name="opening_strength",
                passed=True,  # Not a blocker, just a warning
                score=0.4,
                message=f"Hook starts with filler word: '{filler}'",
                severity="warning",
            )

    # Check hook score from candidate
    hook_score = candidate.score.hook_strength
    if hook_score >= 0.6:
        return CheckResult(
            name="opening_strength",
            passed=True,
            score=hook_score,
            message="Strong opening hook detected.",
            severity="info",
        )
    elif hook_score >= 0.3:
        return CheckResult(
            name="opening_strength",
            passed=True,
            score=hook_score,
            message="Moderate opening — could be stronger.",
            severity="info",
        )
    else:
        return CheckResult(
            name="opening_strength",
            passed=True,
            score=max(0.2, hook_score),
            message="Weak opening — consider trimming start to a stronger sentence.",
            severity="warning",
        )


def _check_subtitle_readability(
    candidate: CandidateClip,
    clip_spec: ClipSpec | None,
) -> CheckResult:
    """Check 2: Will subtitles be readable?"""
    text = candidate.speech_text_preview or ""

    if not text:
        # No speech = no subtitles needed
        return CheckResult(
            name="subtitle_readability",
            passed=True,
            score=0.7,
            message="No speech content — subtitles not applicable.",
            severity="info",
        )

    # Estimate words per second
    duration = candidate.time_range.duration
    word_count = len(text.split())
    wps = word_count / duration if duration > 0 else 0

    if wps > 4.0:
        return CheckResult(
            name="subtitle_readability",
            passed=False,
            score=0.3,
            message=f"Very fast speech ({wps:.1f} words/sec) — subtitles may be hard to read.",
            severity="warning",
        )
    elif wps > 3.0:
        return CheckResult(
            name="subtitle_readability",
            passed=True,
            score=0.6,
            message=f"Fast speech ({wps:.1f} words/sec) — consider larger font or fewer words per line.",
            severity="info",
        )
    else:
        return CheckResult(
            name="subtitle_readability",
            passed=True,
            score=0.9,
            message=f"Speech pace ({wps:.1f} words/sec) suitable for subtitles.",
            severity="info",
        )


def _check_crop_safety(
    candidate: CandidateClip,
    clip_spec: ClipSpec | None,
) -> CheckResult:
    """Check 3: Is the crop/framing safe?"""
    if clip_spec and clip_spec.primary_framing:
        framing = clip_spec.primary_framing
        zoom = framing.zoom_start

        if zoom > 1.8:
            return CheckResult(
                name="crop_safety",
                passed=False,
                score=0.3,
                message=f"Zoom {zoom:.1f}x is very aggressive — may crop important content.",
                severity="warning",
            )
        elif zoom > 1.5:
            return CheckResult(
                name="crop_safety",
                passed=True,
                score=0.6,
                message=f"Zoom {zoom:.1f}x is moderately tight.",
                severity="info",
            )

    if candidate.has_person:
        return CheckResult(
            name="crop_safety",
            passed=True,
            score=0.9,
            message="Person detected — auto-crop has tracking data.",
            severity="info",
        )
    else:
        return CheckResult(
            name="crop_safety",
            passed=True,
            score=0.5,
            message="No person detected — using center crop fallback.",
            severity="warning",
        )


def _check_completeness(candidate: CandidateClip) -> CheckResult:
    """Check 4: Does the clip feel complete (not cut mid-sentence)?"""
    completeness = candidate.score.completeness

    if completeness >= 0.7:
        return CheckResult(
            name="completeness",
            passed=True,
            score=completeness,
            message="Clip has clear beginning and ending.",
            severity="info",
        )
    elif completeness >= 0.4:
        return CheckResult(
            name="completeness",
            passed=True,
            score=completeness,
            message="Clip ending may feel abrupt — consider extending by 1-2 seconds.",
            severity="warning",
        )
    else:
        return CheckResult(
            name="completeness",
            passed=False,
            score=completeness,
            message="Clip appears to cut mid-thought — likely needs trim adjustment.",
            severity="error",
        )


def _check_duration(
    candidate: CandidateClip,
    constraints: EditConstraints | None,
) -> CheckResult:
    """Check 5: Is the duration within platform constraints?"""
    duration = candidate.time_range.duration

    if duration < 5.0:
        return CheckResult(
            name="duration",
            passed=False,
            score=0.1,
            message=f"Clip is only {duration:.1f}s — too short for any platform.",
            severity="error",
        )

    if constraints:
        if duration < constraints.min_clip_duration_sec:
            return CheckResult(
                name="duration",
                passed=False,
                score=0.3,
                message=f"Duration {duration:.1f}s below minimum {constraints.min_clip_duration_sec}s.",
                severity="error",
            )
        if duration > constraints.max_clip_duration_sec:
            return CheckResult(
                name="duration",
                passed=False,
                score=0.3,
                message=f"Duration {duration:.1f}s exceeds maximum {constraints.max_clip_duration_sec}s.",
                severity="error",
            )

    if 15.0 <= duration <= 60.0:
        return CheckResult(
            name="duration",
            passed=True,
            score=0.9,
            message=f"Duration {duration:.1f}s is within optimal range.",
            severity="info",
        )
    else:
        return CheckResult(
            name="duration",
            passed=True,
            score=0.6,
            message=f"Duration {duration:.1f}s is acceptable but outside sweet spot (15-60s).",
            severity="info",
        )


def _check_subtitle_burst(candidate: CandidateClip) -> CheckResult:
    """Check: Subtitle text density — will viewer be overwhelmed?

    Detects: long unbroken speech runs, very dense text that floods the screen.
    """
    text = candidate.speech_text_preview or ""
    if not text:
        return CheckResult(
            name="subtitle_burst", passed=True, score=0.8,
            message="No speech — subtitle burst N/A.", severity="info",
        )

    duration = candidate.time_range.duration
    words = text.split()
    word_count = len(words)

    # Check average word length (long technical words harder to read)
    avg_word_len = sum(len(w) for w in words) / max(1, word_count)

    # Characters per second (>15 CPS = too fast for most viewers)
    cps = len(text) / max(1, duration)

    if cps > 18:
        return CheckResult(
            name="subtitle_burst", passed=False, score=0.2,
            message=f"Extreme text density ({cps:.0f} chars/sec) — subtitles will be unreadable.",
            severity="error",
        )
    elif cps > 14:
        return CheckResult(
            name="subtitle_burst", passed=True, score=0.4,
            message=f"High text density ({cps:.0f} chars/sec) — consider reducing caption speed.",
            severity="warning",
        )
    elif avg_word_len > 7:
        return CheckResult(
            name="subtitle_burst", passed=True, score=0.6,
            message=f"Long average word length ({avg_word_len:.1f} chars) — may slow reading.",
            severity="info",
        )
    else:
        return CheckResult(
            name="subtitle_burst", passed=True, score=0.9,
            message=f"Text density OK ({cps:.0f} chars/sec).",
            severity="info",
        )


def _check_dead_tail(candidate: CandidateClip) -> CheckResult:
    """Check: Does the clip end with dead silence or meaningless filler?

    Detects trailing silence, fading audio, or empty visual at the end.
    """
    completeness = candidate.score.completeness
    text = (candidate.speech_text_preview or "").strip().lower()

    # Check for trailing filler phrases
    trailing_fillers = (
        "um", "uh", "so yeah", "anyway", "you know", "alright",
        "okay", "so", "yeah", "right",
        # Vietnamese
        "vậy đó", "thôi", "à", "ừm", "nha", "nhé", "thế thôi",
    )

    # Get last few words
    words = text.split()
    last_words = " ".join(words[-4:]) if len(words) >= 4 else text

    for filler in trailing_fillers:
        if last_words.endswith(filler):
            return CheckResult(
                name="dead_tail", passed=True, score=0.4,
                message=f"Clip ends with filler: '...{filler}' — consider trimming end.",
                severity="warning",
            )

    # Very low completeness = likely dead tail
    if completeness < 0.3:
        return CheckResult(
            name="dead_tail", passed=True, score=0.3,
            message="Clip ending feels unfinished — may have dead silence at the end.",
            severity="warning",
        )

    return CheckResult(
        name="dead_tail", passed=True, score=0.9,
        message="Ending is clean — no dead tail detected.",
        severity="info",
    )


def _check_outro_cta(candidate: CandidateClip) -> CheckResult:
    """Check: Is this clip actually an outro/CTA rather than content?

    Detects: "Thank you for watching", "Subscribe", "Like and share",
    "See you next time", "Follow me" — these are NOT good standalone clips.
    """
    text = (candidate.hook_text or "").lower()
    full_text = (candidate.speech_text_preview or "").lower()

    # CTA/outro patterns — if these dominate, clip is an outro (EN + VI)
    outro_patterns = (
        "thank you for watching", "thanks for watching",
        "if you enjoyed", "subscribe", "like and",
        "see you next time", "see you in the next",
        "follow me", "check out", "link in",
        "leave a comment", "let me know in the comments",
        "hit the bell", "notification",
        "don't forget to", "make sure to",
        # Vietnamese
        "cảm ơn các bạn đã xem", "cám ơn đã theo dõi",
        "đăng ký kênh", "nhấn like", "bấm chuông",
        "hẹn gặp lại", "đừng quên", "chia sẻ video",
        "bình luận bên dưới", "link ở phần mô tả",
    )

    outro_hits = sum(1 for p in outro_patterns if p in full_text)

    if outro_hits >= 3:
        return CheckResult(
            name="outro_cta", passed=False, score=0.1,
            message=f"Clip is an outro/CTA ({outro_hits} CTA phrases) — not standalone content.",
            severity="error",
        )
    elif outro_hits >= 2:
        return CheckResult(
            name="outro_cta", passed=True, score=0.3,
            message=f"Clip contains {outro_hits} CTA phrases — likely an outro section.",
            severity="warning",
        )
    elif outro_hits == 1:
        return CheckResult(
            name="outro_cta", passed=True, score=0.7,
            message="Clip has minor CTA content — acceptable.",
            severity="info",
        )
    else:
        return CheckResult(
            name="outro_cta", passed=True, score=1.0,
            message="No CTA/outro content detected — clip is standalone content.",
            severity="info",
        )


def _check_coherence(candidate: CandidateClip) -> CheckResult:
    """Check 6: Does the clip have hook-payoff coherence?"""
    hook_promise = getattr(candidate, 'hook_promise', '') or ''
    payoff_res = getattr(candidate, 'payoff_resolution', '') or ''

    if not hook_promise or hook_promise == "none":
        return CheckResult(
            name="coherence",
            passed=True,
            score=0.6,
            message="No specific hook promise — coherence N/A.",
            severity="info",
        )

    if payoff_res and payoff_res != "none":
        return CheckResult(
            name="coherence",
            passed=True,
            score=0.9,
            message=f"Hook ({hook_promise}) resolved by {payoff_res}.",
            severity="info",
        )
    else:
        return CheckResult(
            name="coherence",
            passed=True,  # Not a blocker, but a warning
            score=0.3,
            message=f"Hook ({hook_promise}) has no clear resolution — clip may feel incomplete.",
            severity="warning",
        )


def _check_risk_flags(candidate: CandidateClip) -> CheckResult:
    """Check 7: Are there critical risk flags?"""
    flags = getattr(candidate, 'risk_flags', []) or []

    critical_flags = {"incomplete_ending", "weak_hook", "low_coherence", "dead_air_start"}
    critical_found = [f for f in flags if f in critical_flags]

    if not flags:
        return CheckResult(
            name="risk_flags",
            passed=True,
            score=1.0,
            message="No risk flags.",
            severity="info",
        )
    elif critical_found:
        return CheckResult(
            name="risk_flags",
            passed=True,  # Warning, not blocker
            score=max(0.2, 1.0 - len(critical_found) * 0.25),
            message=f"Risk flags: {', '.join(critical_found)}",
            severity="warning",
        )
    else:
        return CheckResult(
            name="risk_flags",
            passed=True,
            score=max(0.5, 1.0 - len(flags) * 0.1),
            message=f"Minor flags: {', '.join(flags)}",
            severity="info",
        )


# ══════════════════════════════════════════════════════════════════════════
# SUGGESTION GENERATOR
# ══════════════════════════════════════════════════════════════════════════

def _generate_suggestions(
    checks: list[CheckResult],
    candidate: CandidateClip,
) -> list[str]:
    """Generate actionable improvement suggestions from check results."""
    suggestions: list[str] = []

    for check in checks:
        if check.passed and check.severity == "info":
            continue

        if check.name == "opening_strength" and check.score < 0.5:
            suggestions.append("Trim the first 1-2 seconds to start at a stronger sentence.")

        elif check.name == "subtitle_readability" and check.score < 0.5:
            suggestions.append("Use a simpler caption style or increase font size for fast speech.")

        elif check.name == "crop_safety" and check.score < 0.5:
            suggestions.append("Reduce zoom level or switch to center crop mode.")

        elif check.name == "completeness" and check.score < 0.5:
            suggestions.append("Extend the clip end by 1-3 seconds to capture the full thought.")

        elif check.name == "duration" and not check.passed:
            dur = candidate.time_range.duration
            if dur < 15:
                suggestions.append(f"Extend clip to at least 15 seconds (currently {dur:.0f}s).")
            else:
                suggestions.append(f"Shorten clip to under 60 seconds (currently {dur:.0f}s).")

        elif check.name == "coherence" and check.score < 0.5:
            hp = getattr(candidate, 'hook_promise', '')
            suggestions.append(
                f"This clip opens with a {hp} but doesn't clearly resolve it. "
                "Consider extending to include the answer/payoff."
            )

        elif check.name == "risk_flags" and check.score < 0.5:
            suggestions.append("Multiple risk flags detected — review clip carefully before publishing.")

        elif check.name == "subtitle_burst" and check.score < 0.5:
            suggestions.append("Text is very dense — use a slower caption style or increase line breaks.")

        elif check.name == "dead_tail" and check.score < 0.5:
            suggestions.append("Trim the last 1-3 seconds to remove trailing silence or filler.")

        elif check.name == "outro_cta" and check.score < 0.3:
            suggestions.append("This clip is an outro/CTA section — consider removing it from export.")

    return suggestions
