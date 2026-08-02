"""Editorial threshold registry — single source of truth for all tunable constants.

Replaces 90+ magic numbers scattered across candidate_generator, clip_ranker,
hook_detector, payoff_detector, intent_classifier, coherence, segment_scorer.

All values are loaded from AppConfig if available, falling back to defaults.
This enables:
1. User tuning via YAML config or env vars
2. Quality-tier-aware threshold adjustment
3. Zero magic numbers in business logic

Usage:
    from cutclipshort.editorial.thresholds import T
    if spike.intensity < T.EMOTIONAL_SPIKE_MIN_INTENSITY: ...
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EditorialThresholds:
    """All editorial threshold values in one place."""

    # ── Candidate generation ──────────────────────────────────────
    emotional_spike_min_intensity: float = 0.35
    temporal_overlap_max: float = 0.40
    semantic_overlap_max: float = 0.60
    coverage_gap_min_ratio: float = 0.15  # 15% = zone needs at least 1 proposal
    speech_ratio_min_for_gap_fill: float = 0.30

    # ── Hook detection ────────────────────────────────────────────
    hook_keyword_threshold: float = 0.30
    hook_energy_strong: float = 0.60
    hook_silence_penalty_threshold: float = 0.10
    hook_strong_score: float = 0.70
    hook_decent_score: float = 0.50
    hook_weak_score: float = 0.30
    hook_bold_energy_threshold: float = 0.70

    # ── Payoff detection ──────────────────────────────────────────
    payoff_keyword_threshold: float = 0.30
    payoff_sentence_complete_threshold: float = 0.50
    payoff_strong_score: float = 0.70
    payoff_decent_score: float = 0.60
    payoff_weak_score: float = 0.40
    payoff_energy_drop_threshold: float = 0.50
    payoff_trailing_pause_threshold: float = 0.30
    payoff_trailing_pause_close: float = 0.30

    # ── Segment scoring ───────────────────────────────────────────
    semantic_score_bonus_threshold: float = 0.60
    semantic_hook_bonus_threshold: float = 0.50
    filler_heavy_threshold: float = 0.15
    filler_moderate_threshold: float = 0.10
    hook_weak_penalty: float = 0.20
    hook_moderate_penalty: float = 0.30
    genre_cue_bonus_threshold: float = 0.10
    semantic_bonus_threshold: float = 0.01
    concept_coverage_threshold: float = 0.50
    concept_overlap_threshold: float = 0.30

    # ── Clip ranking ──────────────────────────────────────────────
    rank_viable_min_score: float = 0.20
    rank_hook_type_dominance_max: float = 0.50
    rank_zone_coverage_low: float = 0.10
    rank_zone_coverage_med: float = 0.50
    rank_visual_person_threshold: float = 0.60
    rank_speech_presence_threshold: float = 0.10

    # ── Ranking boost thresholds ──────────────────────────────────
    boost_hook_strong: float = 0.60
    boost_pacing_good: float = 0.70
    boost_silence_low: float = 0.05
    boost_genre_match: float = 0.50
    boost_payoff_strong: float = 0.60
    boost_payoff_very_strong: float = 0.70
    boost_density_high: float = 0.70
    boost_speech_heavy: float = 0.70

    # ── Tag thresholds ────────────────────────────────────────────
    tag_hook_strong: float = 0.70
    tag_hook_decent: float = 0.50
    tag_payoff_strong: float = 0.70
    tag_pacing_good: float = 0.70
    tag_density_rich: float = 0.70
    tag_speech_heavy: float = 0.80
    tag_genre_match: float = 0.50

    # ── Explain/risk thresholds ───────────────────────────────────
    explain_hook_strong: float = 0.70
    explain_hook_decent: float = 0.40
    explain_payoff_strong: float = 0.70
    explain_genre_match: float = 0.50
    explain_pacing_good: float = 0.70
    explain_hook_weak: float = 0.30
    explain_payoff_weak: float = 0.40
    explain_speech_low: float = 0.30
    explain_visual_poor: float = 0.30
    explain_audio_poor: float = 0.40
    explain_silence_penalty: float = 0.15
    explain_coherence_poor: float = 0.30

    # ── Intent classification ─────────────────────────────────────
    intent_min_confidence: float = 0.25

    # Hook intent
    intent_hook_strong: float = 0.60
    intent_hook_very_strong: float = 0.70
    intent_hook_payoff_weak: float = 0.40
    intent_hook_question_min: int = 2

    # Story intent
    intent_story_completeness: float = 0.50
    intent_story_coherence_threshold: float = 0.40
    intent_story_pacing_bonus: float = 0.70

    # Payoff intent
    intent_payoff_strong: float = 0.70
    intent_payoff_decent: float = 0.50

    # Shock intent
    intent_shock_emotion_high: float = 0.70
    intent_shock_emotion_med: float = 0.50
    intent_shock_audio_burst: float = 0.70
    intent_shock_motion_spike: float = 0.70
    intent_shock_exclamation_min: int = 3
    intent_shock_conflict_min: int = 2
    intent_shock_debate_min: int = 2
    intent_shock_hook_emotion_combo: float = 0.60

    # Insight intent
    intent_insight_density_high: float = 0.70
    intent_insight_density_med: float = 0.50
    intent_insight_markers_strong: int = 3
    intent_insight_markers_weak: int = 1
    intent_insight_min_words: int = 50
    intent_insight_pacing_min: float = 0.50
    intent_insight_pacing_max: float = 0.85
    intent_insight_genre_density_combo: float = 0.50

    # Loop intent
    intent_loop_markers_strong: int = 2
    intent_loop_markers_weak: int = 1
    intent_loop_motion_threshold: float = 0.60
    intent_loop_max_words_visual: int = 25
    intent_loop_satisfying_emotion_min: float = 0.30
    intent_loop_satisfying_emotion_max: float = 0.70
    intent_loop_satisfying_motion_min: float = 0.50
    intent_loop_wordy_penalty_words: int = 50
    intent_loop_emotional_penalty: float = 0.70

    # ── Coherence ─────────────────────────────────────────────────
    coherence_keyword_threshold: float = 0.30
    coherence_distance_penalty_threshold: float = 0.05
    coherence_sentence_complete_for_payoff: float = 0.50

    # ── Emotion mapper ────────────────────────────────────────────
    emotion_text_energy_threshold: float = 0.30

    # ── Semantic scorer ───────────────────────────────────────────
    semantic_filler_heavy: float = 0.15
    semantic_info_density_bonus: float = 0.70
    semantic_emotional_bonus: float = 0.50
    semantic_filler_moderate: float = 0.10

    # ── Narrative segmenter ───────────────────────────────────────
    narrative_min_completeness: float = 0.40
    narrative_min_peak_intensity: float = 0.30
    narrative_intro_threshold: float = 0.50
    narrative_resolution_threshold: float = 0.50
    narrative_stage_min: float = 0.20

    # ── Genre cues ────────────────────────────────────────────────
    genre_cue_primary_threshold: float = 0.50
    genre_cue_secondary_threshold: float = 0.30
    genre_cue_energy_threshold: float = 0.60


# ── Singleton instance ────────────────────────────────────────────────
T = EditorialThresholds()


def load_thresholds_from_config(config: dict) -> None:
    """Update thresholds from editorial config section.

    Called once during pipeline setup. Any key in the config dict that
    matches a threshold field name will override the default.
    """
    global T
    for key, val in config.items():
        if hasattr(T, key) and isinstance(val, (int, float)):
            object.__setattr__(T, key, float(val))


def reset_thresholds() -> None:
    """Reset all thresholds to defaults (useful for tests)."""
    global T
    T = EditorialThresholds()
