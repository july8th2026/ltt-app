"""Intent classifier v2 — assigns editorial purpose to clip candidates.

Every clip gets classified into exactly ONE EditorialIntent:
  HOOK    — Strong opening, grabs attention in first 3s
  STORY   — Complete narrative arc (setup → development → resolution)
  PAYOFF  — Clear conclusion or resolution
  SHOCK   — Unexpected twist, dramatic surprise, viral/controversial moment
  INSIGHT — Dense information, key learning, unique perspective
  LOOP    — Self-contained moment ideal for infinite replay
  UNKNOWN — Unclassifiable (filtered from final output)

All thresholds sourced from T registry (cutclipshort.editorial.thresholds).
Vocabulary sourced from cutclipshort.editorial.vocabulary (multi-language).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# VOCABULARY (multi-language, loaded once)
# ══════════════════════════════════════════════════════════════════════

def _load_vocabulary() -> dict[str, frozenset[str]]:
    """Load intent vocabulary from language modules. Cached at module level."""
    sets: dict[str, frozenset[str]] = {
        "conflict": frozenset(), "debate": frozenset(),
        "insight": frozenset(), "loop": frozenset(),
    }
    try:
        from cutclipshort.editorial.vocabulary.en import (
            CONFLICT_WORDS, DEBATE_MARKERS, INSIGHT_MARKERS, LOOP_MARKERS,
        )
        sets["conflict"] = CONFLICT_WORDS
        sets["debate"] = DEBATE_MARKERS
        sets["insight"] = INSIGHT_MARKERS
        sets["loop"] = LOOP_MARKERS
    except ImportError:
        pass

    # Merge Vietnamese vocabulary
    try:
        from cutclipshort.editorial.vocabulary.vi import (
            CONFLICT_WORDS as VI_CONFLICT,
        )
        sets["conflict"] = sets["conflict"] | VI_CONFLICT
    except (ImportError, AttributeError):
        pass
    try:
        from cutclipshort.editorial.vocabulary.vi import (
            INSIGHT_MARKERS as VI_INSIGHT,
            LOOP_MARKERS as VI_LOOP,
            DEBATE_MARKERS as VI_DEBATE,
        )
        sets["insight"] = sets["insight"] | VI_INSIGHT
        sets["loop"] = sets["loop"] | VI_LOOP
        sets["debate"] = sets["debate"] | VI_DEBATE
    except (ImportError, AttributeError):
        pass

    return sets


_VOCAB: dict[str, frozenset[str]] | None = None


def _get_vocab() -> dict[str, frozenset[str]]:
    """Lazy-load vocabulary (cached after first call)."""
    global _VOCAB
    if _VOCAB is None:
        _VOCAB = _load_vocabulary()
    return _VOCAB


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def classify_intent(
    *,
    hook_score: float,
    payoff_score: float,
    coherence_resolution_found: bool,
    emotional_intensity: float,
    narrative_completeness: float,
    speech_text: str,
    genre_cue_score: float,
    pacing_score: float = 0.5,
    content_density: float = 0.5,
    audio_energy: float = 0.5,
    motion_intensity: float = 0.5,
) -> tuple[str, float, str, dict[str, float]]:
    """Classify clip intent from multi-signal analysis.

    Returns:
        (intent_value, confidence, reasoning, intent_features)
    """
    from cutclipshort.editorial.thresholds import T

    lower = speech_text.lower() if speech_text else ""
    vocab = _get_vocab()

    features = _extract_features(
        hook_score=hook_score, payoff_score=payoff_score,
        coherence_resolution_found=coherence_resolution_found,
        emotional_intensity=emotional_intensity,
        narrative_completeness=narrative_completeness,
        lower_text=lower, genre_cue_score=genre_cue_score,
        pacing_score=pacing_score, content_density=content_density,
        audio_energy=audio_energy, motion_intensity=motion_intensity,
        vocab=vocab,
    )

    scorers = [_score_hook, _score_story, _score_payoff,
               _score_shock, _score_insight, _score_loop]

    scores: dict[str, float] = {}
    reasons: dict[str, str] = {}
    for scorer in scorers:
        name, score, reason = scorer(features, T)
        scores[name] = score
        reasons[name] = reason

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    confidence = scores[best]

    if confidence < T.intent_min_confidence:
        reasoning = f"No strong signal (best={best} at {confidence:.2f} < {T.intent_min_confidence})"
        return "unknown", confidence, reasoning, features

    reasoning = f"{best}: {reasons[best]}"
    logger.debug("Intent: %s (%.2f) — %s", best, confidence, reasons[best])
    return best, round(confidence, 3), reasoning, features


# ══════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION
# ══════════════════════════════════════════════════════════════════════

def _extract_features(
    *, hook_score: float, payoff_score: float,
    coherence_resolution_found: bool, emotional_intensity: float,
    narrative_completeness: float, lower_text: str,
    genre_cue_score: float, pacing_score: float,
    content_density: float, audio_energy: float,
    motion_intensity: float, vocab: dict[str, frozenset[str]],
) -> dict[str, float]:
    """Extract all classifiable features into a flat dict."""
    excl = lower_text.count("!")
    ques = lower_text.count("?")
    padded = f" {lower_text} "
    conflict = sum(1 for w in vocab.get("conflict", ()) if f" {w} " in padded)
    debate = sum(1 for m in vocab.get("debate", ()) if m in lower_text)
    insight = sum(1 for m in vocab.get("insight", ()) if m in lower_text)
    loop = sum(1 for m in vocab.get("loop", ()) if m in lower_text)
    wc = len(lower_text.split()) if lower_text else 0

    return {
        "hook_score": hook_score, "payoff_score": payoff_score,
        "coherence_resolved": 1.0 if coherence_resolution_found else 0.0,
        "emotional_intensity": emotional_intensity,
        "narrative_completeness": narrative_completeness,
        "genre_cue_score": genre_cue_score,
        "pacing_score": pacing_score, "content_density": content_density,
        "audio_energy": audio_energy, "motion_intensity": motion_intensity,
        "exclamation_count": float(excl), "question_count": float(ques),
        "conflict_hits": float(conflict), "debate_hits": float(debate),
        "insight_hits": float(insight), "loop_hits": float(loop),
        "word_count": float(wc),
    }


# ══════════════════════════════════════════════════════════════════════
# INTENT SCORERS — all use T registry, zero magic numbers
# ══════════════════════════════════════════════════════════════════════

def _score_hook(f: dict[str, float], T: object) -> tuple[str, float, str]:
    """HOOK: Strong opening, weak/no conclusion."""
    score = 0.0
    parts: list[str] = []
    hs, ps = f["hook_score"], f["payoff_score"]

    if hs > T.intent_hook_strong and ps < T.intent_hook_payoff_weak:
        score = hs * 0.7
        parts.append(f"strong_open={hs:.2f}+weak_close={ps:.2f}")
    elif hs > T.intent_hook_very_strong:
        score = hs * 0.5
        parts.append(f"very_strong={hs:.2f}")

    if f["question_count"] >= T.intent_hook_question_min and hs > 0.5:
        score += 0.10
        parts.append(f"questions={int(f['question_count'])}")

    return "hook", min(1.0, score), " + ".join(parts) or "no hook signal"


def _score_story(f: dict[str, float], T: object) -> tuple[str, float, str]:
    """STORY: Complete narrative arc with development."""
    score = 0.0
    parts: list[str] = []
    nc = f["narrative_completeness"]

    if nc > T.intent_story_completeness:
        score = nc * 0.80
        parts.append(f"arc={nc:.2f}")

    if nc > T.intent_story_coherence_threshold and f["coherence_resolved"] > 0.5:
        score += 0.15
        parts.append("resolved")

    if f["pacing_score"] > T.intent_story_pacing_bonus:
        score += 0.05
        parts.append("pacing")

    return "story", min(1.0, score), " + ".join(parts) or "no arc"


def _score_payoff(f: dict[str, float], T: object) -> tuple[str, float, str]:
    """PAYOFF: Clear conclusion or resolution."""
    score = 0.0
    parts: list[str] = []
    ps = f["payoff_score"]

    if ps > T.intent_payoff_strong and f["coherence_resolved"] > 0.5:
        score = ps * 0.75
        parts.append(f"strong={ps:.2f}+resolved")
    elif ps > T.intent_payoff_decent:
        score = ps * 0.4
        parts.append(f"decent={ps:.2f}")

    return "payoff", min(1.0, score), " + ".join(parts) or "no payoff"


def _score_shock(f: dict[str, float], T: object) -> tuple[str, float, str]:
    """SHOCK: Surprise, drama, viral moment, controversial take."""
    score = 0.0
    parts: list[str] = []
    ei, ae, mi = f["emotional_intensity"], f["audio_energy"], f["motion_intensity"]

    if ei > T.intent_shock_emotion_high:
        score += 0.35
        parts.append(f"emotion={ei:.2f}")
    elif ei > T.intent_shock_emotion_med:
        score += 0.15

    if ae > T.intent_shock_audio_burst:
        score += 0.20
        parts.append(f"audio={ae:.2f}")

    if mi > T.intent_shock_motion_spike:
        score += 0.15
        parts.append(f"motion={mi:.2f}")

    if f["exclamation_count"] >= T.intent_shock_exclamation_min:
        score += 0.15
        parts.append(f"excl={int(f['exclamation_count'])}")

    if f["conflict_hits"] >= T.intent_shock_conflict_min:
        score += 0.20
        parts.append(f"conflict={int(f['conflict_hits'])}")

    if f["debate_hits"] >= T.intent_shock_debate_min:
        score += 0.10
        parts.append(f"debate={int(f['debate_hits'])}")

    if f["hook_score"] > T.intent_shock_hook_emotion_combo and ei > T.intent_shock_hook_emotion_combo:
        score += 0.10

    return "shock", min(1.0, score), " + ".join(parts) or "no shock"


def _score_insight(f: dict[str, float], T: object) -> tuple[str, float, str]:
    """INSIGHT: Dense info, key learning, unique perspective."""
    score = 0.0
    parts: list[str] = []
    cd, wc, ih = f["content_density"], f["word_count"], f["insight_hits"]

    if cd > T.intent_insight_density_high:
        score += 0.35
        parts.append(f"density={cd:.2f}")
    elif cd > T.intent_insight_density_med:
        score += 0.15

    if ih >= T.intent_insight_markers_strong:
        score += 0.30
        parts.append(f"markers={int(ih)}")
    elif ih >= T.intent_insight_markers_weak:
        score += 0.15
        parts.append(f"markers={int(ih)}")

    if wc > T.intent_insight_min_words:
        score += 0.10
        parts.append(f"words={int(wc)}")

    if T.intent_insight_pacing_min < f["pacing_score"] < T.intent_insight_pacing_max:
        score += 0.05

    if f["genre_cue_score"] > T.intent_insight_genre_density_combo and cd > T.intent_insight_genre_density_combo:
        score += 0.10
        parts.append("edu_cue")

    # Penalty: very high narrative = story, not insight
    if f["narrative_completeness"] > 0.6 and ih < 2:
        score *= 0.7
        parts.append("likely_story")

    return "insight", min(1.0, score), " + ".join(parts) or "no insight"


def _score_loop(f: dict[str, float], T: object) -> tuple[str, float, str]:
    """LOOP: Self-contained moment for infinite replay.

    Distinct from SHOCK: LOOP = visual/satisfying/mesmerizing, low speech.
    High emotion or high word count triggers penalties (→ SHOCK or INSIGHT instead).
    """
    score = 0.0
    parts: list[str] = []
    mi, wc, ei = f["motion_intensity"], f["word_count"], f["emotional_intensity"]
    lh = f["loop_hits"]

    if lh >= T.intent_loop_markers_strong:
        score += 0.25
        parts.append(f"markers={int(lh)}")
    elif lh >= T.intent_loop_markers_weak:
        score += 0.10

    # Core: high motion + low speech = visual loop
    if mi > T.intent_loop_motion_threshold and wc < T.intent_loop_max_words_visual:
        score += 0.30
        parts.append(f"visual(motion={mi:.2f},words={int(wc)})")
    elif mi > T.intent_loop_motion_threshold:
        score += 0.15
        parts.append(f"motion={mi:.2f}")

    # Satisfying: moderate emotion + visual
    if T.intent_loop_satisfying_emotion_min < ei < T.intent_loop_satisfying_emotion_max \
       and mi > T.intent_loop_satisfying_motion_min:
        score += 0.10
        parts.append("satisfying")

    # Penalty: too many words = not a loop
    if wc > T.intent_loop_wordy_penalty_words:
        score *= 0.5
        parts.append("wordy")

    # Penalty: very high emotion = shock, not loop
    if ei > T.intent_loop_emotional_penalty:
        score *= 0.6
        parts.append("emotional->shock")

    return "loop", min(1.0, score), " + ".join(parts) or "no loop"
