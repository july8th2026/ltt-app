"""Genre-specific content cue detectors.

Each detector analyzes transcript/audio/visual data for content patterns
specific to a genre. They return a float score (0.0-1.0) plus diagnostic
details. The segment_scorer uses these as bonus signals on top of the
base hook/payoff/pacing scores.

Detectors:
- comedy_cues:     Setup-punchline pattern, laughter pauses, rapid delivery
- education_cues:  Information density, step/list structure, key concept markers
- story_cues:      Tension arc, character references, temporal markers
- news_cues:       Opinion markers, reaction intensity, hot-take patterns
- review_cues:     Verdict markers, comparison language, pros/cons structure

All detectors are ADDITIVE — they don't replace base scoring, they provide
bonus signals that genre profiles can weight.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass

from cutclipshort.types import (
    AudioSegment,
    TimeRange,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenreCueResult:
    """Result from a genre-specific cue detector."""
    genre: str          # Which genre this detects for
    score: float        # 0.0-1.0 (how well it matches this genre pattern)
    signals: dict       # Diagnostic breakdown {signal_name: value}
    reasoning: str      # Human-readable explanation


# ══════════════════════════════════════════════════════════════════════════
# COMEDY CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_comedy_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect setup-punchline patterns and comedic delivery cues.

    Comedy patterns:
    1. Setup → Pause → Punchline (energy drop then spike or silence)
    2. Rapid-fire delivery (high WPM) followed by pause
    3. Short punchy sentences mixed with longer setups
    4. Comedic keywords ("literally", "bro", "I swear")
    5. Post-punchline silence (audience reaction / beat)
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    if not segs:
        return GenreCueResult("comedy", 0.0, {}, "no speech")

    # Signal 1: Setup-punchline pattern (long sentence → short sentence)
    setup_punchline = _detect_setup_punchline(segs)

    # Signal 2: Post-statement pause (silence after a sentence = beat)
    pause_score = _detect_comedic_pauses(segs, audio)

    # Signal 3: Comedic vocabulary
    vocab_score = _score_vocab(segs, _COMEDY_VOCAB)

    # Signal 4: Sentence length variance (comedy mixes long/short)
    variance_score = _sentence_length_variance(segs)

    # Signal 5: High energy spikes (delivery emphasis)
    energy_spike = _detect_energy_spikes(audio)

    composite = (
        setup_punchline * 0.30
        + pause_score * 0.25
        + vocab_score * 0.15
        + variance_score * 0.15
        + energy_spike * 0.15
    )

    signals = {
        "setup_punchline": round(setup_punchline, 3),
        "comedic_pauses": round(pause_score, 3),
        "comedy_vocab": round(vocab_score, 3),
        "sentence_variance": round(variance_score, 3),
        "energy_spikes": round(energy_spike, 3),
    }

    reasons = []
    if setup_punchline > 0.5:
        reasons.append("setup-punchline pattern detected")
    if pause_score > 0.5:
        reasons.append("comedic timing pauses")
    if vocab_score > 0.3:
        reasons.append("comedic vocabulary")

    return GenreCueResult(
        "comedy", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong comedy signals",
    )


_COMEDY_VOCAB = (
    "literally", "bro", "dude", "bruh", "lol", "lmao",
    "hilarious", "joke", "funny", "laugh", "punchline",
    "i swear", "no way", "dead", "dying", "i can't",
    "roast", "savage", "epic", "fail", "cringe",
)


# ══════════════════════════════════════════════════════════════════════════
# EDUCATION CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_education_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect educational content patterns.

    Education patterns:
    1. Step/list structure ("first", "second", "step one")
    2. Definition markers ("means", "defined as", "is called")
    3. Instructional language ("you need to", "let me show", "here's how")
    4. Key concept density (technical terms, specific nouns)
    5. Steady pacing (consistent WPM, not erratic)
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    if not segs:
        return GenreCueResult("education", 0.0, {}, "no speech")

    text = " ".join(s.text.lower() for s in segs)

    # Signal 1: List/step structure
    list_score = _detect_list_structure(text)

    # Signal 2: Definition markers
    def_score = _score_vocab(segs, _EDUCATION_DEFINITIONS)

    # Signal 3: Instructional language
    instruct_score = _score_vocab(segs, _EDUCATION_INSTRUCTIONAL)

    # Signal 4: Information density (unique words / total words)
    info_density = _information_density(text)

    # Signal 5: Steady pacing (low energy variance = consistent delivery)
    steady = _pacing_consistency(audio)

    composite = (
        list_score * 0.25
        + def_score * 0.20
        + instruct_score * 0.20
        + info_density * 0.20
        + steady * 0.15
    )

    signals = {
        "list_structure": round(list_score, 3),
        "definitions": round(def_score, 3),
        "instructional": round(instruct_score, 3),
        "info_density": round(info_density, 3),
        "steady_pacing": round(steady, 3),
    }

    reasons = []
    if list_score > 0.5:
        reasons.append("step/list structure")
    if instruct_score > 0.3:
        reasons.append("instructional language")
    if info_density > 0.6:
        reasons.append("high information density")

    return GenreCueResult(
        "education", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong education signals",
    )


_EDUCATION_DEFINITIONS = (
    "means", "defined as", "is called", "refers to",
    "in other words", "for example", "such as", "the concept",
    "the principle", "the key", "the difference",
)

_EDUCATION_INSTRUCTIONAL = (
    "you need to", "let me show", "here's how", "the trick is",
    "step one", "step two", "first thing", "next step",
    "make sure", "don't forget", "important to",
    "let me explain", "i'll teach", "pay attention",
)


# ══════════════════════════════════════════════════════════════════════════
# STORY ARC CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_story_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect narrative/storytelling patterns.

    Story patterns:
    1. Temporal markers ("one day", "then", "suddenly", "and then")
    2. Character references ("he", "she", "they", "my friend")
    3. Emotional arc (energy rises then falls = tension → resolution)
    4. First-person narrative ("I was", "I remember", "I couldn't believe")
    5. Cliffhanger language ("but then", "little did I know", "turns out")
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    if not segs:
        return GenreCueResult("storytelling", 0.0, {}, "no speech")

    text = " ".join(s.text.lower() for s in segs)

    # Signal 1: Temporal markers
    temporal_score = _count_pattern_density(text, _STORY_TEMPORAL)

    # Signal 2: Character/pronoun references
    char_score = _count_pattern_density(text, _STORY_CHARACTERS)

    # Signal 3: Emotional energy arc (rising then falling)
    arc_score = _detect_energy_arc(audio)

    # Signal 4: First-person narrative
    narrative_score = _count_pattern_density(text, _STORY_FIRST_PERSON)

    # Signal 5: Tension/cliffhanger language
    tension_score = _score_vocab(segs, _STORY_TENSION)

    composite = (
        temporal_score * 0.20
        + char_score * 0.15
        + arc_score * 0.25
        + narrative_score * 0.20
        + tension_score * 0.20
    )

    signals = {
        "temporal_markers": round(temporal_score, 3),
        "characters": round(char_score, 3),
        "energy_arc": round(arc_score, 3),
        "first_person": round(narrative_score, 3),
        "tension": round(tension_score, 3),
    }

    reasons = []
    if arc_score > 0.5:
        reasons.append("narrative energy arc")
    if temporal_score > 0.4:
        reasons.append("temporal storytelling markers")
    if tension_score > 0.3:
        reasons.append("tension/cliffhanger language")

    return GenreCueResult(
        "storytelling", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong story signals",
    )


_STORY_TEMPORAL = (
    "one day", "then", "suddenly", "and then", "next thing",
    "after that", "at that point", "by the time", "eventually",
    "finally", "in the end", "later", "moments later",
)

_STORY_CHARACTERS = (
    r"\bhe\b", r"\bshe\b", r"\bthey\b", r"\bmy friend\b",
    r"\bmy (mom|dad|brother|sister|boss|teacher)\b",
    r"\bthis (guy|girl|person|man|woman|kid)\b",
)

_STORY_FIRST_PERSON = (
    "i was", "i remember", "i couldn't", "i didn't",
    "i thought", "i realized", "i knew", "i felt",
    "i decided", "i walked", "i looked", "i said",
)

_STORY_TENSION = (
    "but then", "little did", "turns out", "plot twist",
    "out of nowhere", "i couldn't believe", "the craziest",
    "nobody expected", "what happened next", "and that's when",
)


# ══════════════════════════════════════════════════════════════════════════
# NEWS/COMMENTARY CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_news_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect news commentary and hot-take patterns.

    News patterns:
    1. Opinion markers ("I think", "in my opinion", "hot take")
    2. Current event references ("just happened", "breaking", "today")
    3. Rhetorical questions
    4. High energy / passionate delivery
    5. Call-to-action language ("what do you think", "let me know")
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    if not segs:
        return GenreCueResult("news_commentary", 0.0, {}, "no speech")

    text = " ".join(s.text.lower() for s in segs)

    opinion_score = _score_vocab(segs, _NEWS_OPINION)
    urgency_score = _score_vocab(segs, _NEWS_URGENCY)
    rhetorical_q = _count_questions(segs) * 0.15
    energy_level = _average_energy(audio)
    cta_score = _score_vocab(segs, _NEWS_CTA)

    composite = (
        opinion_score * 0.25
        + urgency_score * 0.25
        + min(1.0, rhetorical_q) * 0.15
        + energy_level * 0.20
        + cta_score * 0.15
    )

    signals = {
        "opinion_markers": round(opinion_score, 3),
        "urgency": round(urgency_score, 3),
        "rhetorical_questions": round(min(1.0, rhetorical_q), 3),
        "energy_level": round(energy_level, 3),
        "call_to_action": round(cta_score, 3),
    }

    reasons = []
    if opinion_score > 0.4:
        reasons.append("strong opinion markers")
    if urgency_score > 0.4:
        reasons.append("urgency/current-event language")
    if energy_level > 0.6:
        reasons.append("high-energy delivery")

    return GenreCueResult(
        "news_commentary", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong news signals",
    )


_NEWS_OPINION = (
    "i think", "in my opinion", "hot take", "unpopular opinion",
    "here's the thing", "the truth is", "let me be honest",
    "people don't realize", "what people miss", "my take",
    "controversial", "disagree", "ridiculous", "insane",
)

_NEWS_URGENCY = (
    "just happened", "breaking", "today", "this week",
    "can you believe", "they just", "apparently",
    "just announced", "developing", "update",
)

_NEWS_CTA = (
    "what do you think", "let me know", "comment below",
    "drop your", "thoughts", "agree or disagree",
)


# ══════════════════════════════════════════════════════════════════════════
# REVIEW CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_review_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect product/topic review patterns.

    Review patterns:
    1. Verdict language ("worth it", "buy it", "skip it", "recommend")
    2. Comparison markers ("compared to", "versus", "better than")
    3. Pros/cons structure ("the good", "the bad", "downside")
    4. Feature/benefit language ("feature", "performance", "quality")
    5. Rating/scoring language ("out of 10", "rating", "score")
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    if not segs:
        return GenreCueResult("review", 0.0, {}, "no speech")

    verdict_score = _score_vocab(segs, _REVIEW_VERDICT)
    comparison_score = _score_vocab(segs, _REVIEW_COMPARISON)
    proscons_score = _score_vocab(segs, _REVIEW_PROSCONS)
    feature_score = _score_vocab(segs, _REVIEW_FEATURES)
    rating_score = _score_vocab(segs, _REVIEW_RATING)

    composite = (
        verdict_score * 0.30
        + comparison_score * 0.20
        + proscons_score * 0.20
        + feature_score * 0.15
        + rating_score * 0.15
    )

    signals = {
        "verdict": round(verdict_score, 3),
        "comparison": round(comparison_score, 3),
        "pros_cons": round(proscons_score, 3),
        "features": round(feature_score, 3),
        "rating": round(rating_score, 3),
    }

    reasons = []
    if verdict_score > 0.4:
        reasons.append("verdict/recommendation language")
    if comparison_score > 0.3:
        reasons.append("comparison markers")
    if proscons_score > 0.3:
        reasons.append("pros/cons structure")

    return GenreCueResult(
        "review", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong review signals",
    )


_REVIEW_VERDICT = (
    "worth it", "buy it", "skip it", "recommend", "don't buy",
    "verdict", "final thoughts", "bottom line", "overall",
    "would i recommend", "should you buy", "is it worth",
)

_REVIEW_COMPARISON = (
    "compared to", "versus", "vs", "better than", "worse than",
    "alternative", "competitor", "similar to", "the difference",
)

_REVIEW_PROSCONS = (
    "the good", "the bad", "the ugly", "downside", "upside",
    "pros", "cons", "advantage", "disadvantage", "deal breaker",
    "one thing i love", "one thing i hate", "my biggest complaint",
)

_REVIEW_FEATURES = (
    "feature", "performance", "quality", "build quality",
    "battery", "screen", "camera", "design", "price",
    "value", "specification", "spec",
)

_REVIEW_RATING = (
    "out of 10", "out of ten", "out of 5", "rating", "score",
    "stars", "thumbs up", "thumbs down", "grade",
)


# ══════════════════════════════════════════════════════════════════════════
# TALKING HEAD CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_talking_head_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect talking head / solo presenter patterns.

    Patterns:
    1. Single continuous speaker (no turn-taking gaps)
    2. Direct address language ("you", "I want to tell you")
    3. Personal opinion / experience markers
    4. Consistent energy (not erratic)
    5. Moderate-to-high speech ratio (lots of talking)
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    if not segs:
        return GenreCueResult("talking_head", 0.0, {}, "no speech")

    text = " ".join(s.text.lower() for s in segs)

    # Signal 1: Direct address ("you", "your", "you need")
    direct_score = _count_pattern_density(text, _TH_DIRECT_ADDRESS)

    # Signal 2: Personal voice ("I think", "in my experience")
    personal_score = _score_vocab(segs, _TH_PERSONAL)

    # Signal 3: Consistent energy (low variance = single speaker style)
    consistency = _pacing_consistency(audio)

    # Signal 4: High speech ratio
    speech_segs = [s for s in audio if s.has_speech]
    speech_ratio = len(speech_segs) / max(1, len(audio))
    speech_score = min(1.0, speech_ratio / 0.7)

    # Signal 5: Instructional / advice language
    advice_score = _score_vocab(segs, _TH_ADVICE)

    composite = (
        direct_score * 0.25
        + personal_score * 0.20
        + consistency * 0.20
        + speech_score * 0.15
        + advice_score * 0.20
    )

    signals = {
        "direct_address": round(direct_score, 3),
        "personal_voice": round(personal_score, 3),
        "energy_consistency": round(consistency, 3),
        "speech_ratio": round(speech_score, 3),
        "advice_language": round(advice_score, 3),
    }

    reasons = []
    if direct_score > 0.4:
        reasons.append("direct address to viewer")
    if personal_score > 0.3:
        reasons.append("personal voice/opinion")
    if advice_score > 0.3:
        reasons.append("advice/instructional tone")

    return GenreCueResult(
        "talking_head", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong talking head signals",
    )


_TH_DIRECT_ADDRESS = (
    r"\byou\b", r"\byour\b", r"\byou're\b", r"\byou've\b",
    r"\byou need\b", r"\byou should\b", r"\byou can\b",
)

_TH_PERSONAL = (
    "i think", "in my opinion", "in my experience",
    "i believe", "i've found", "i realized", "i learned",
    "my take", "my advice", "personally",
)

_TH_ADVICE = (
    "you need to", "you should", "make sure", "don't forget",
    "the key is", "here's what", "the trick", "pro tip",
    "my recommendation", "i suggest", "the best way",
)


# ══════════════════════════════════════════════════════════════════════════
# PODCAST CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_podcast_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect podcast / conversation patterns.

    Patterns:
    1. Turn-taking: gaps between speech segments (two speakers)
    2. Agreement/disagreement markers ("yeah", "exactly", "I disagree")
    3. Elaboration language ("to add to that", "building on")
    4. Long-form density (higher word count, longer segments)
    5. Conversational fillers (casual speech markers)
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    if not segs:
        return GenreCueResult("podcast", 0.0, {}, "no speech")

    text = " ".join(s.text.lower() for s in segs)

    # Signal 1: Turn-taking (gaps between segments suggesting speaker changes)
    turn_score = _detect_turn_taking(segs)

    # Signal 2: Agreement/disagreement markers
    agree_score = _score_vocab(segs, _PODCAST_AGREE)

    # Signal 3: Elaboration language
    elaboration_score = _score_vocab(segs, _PODCAST_ELABORATE)

    # Signal 4: Long-form density (many words, dense content)
    word_count = len(text.split())
    duration = time_range.duration
    wps = word_count / max(1, duration)
    density_score = min(1.0, wps / 2.5) if wps > 1.5 else wps / 1.5

    # Signal 5: Conversational tone
    casual_score = _score_vocab(segs, _PODCAST_CASUAL)

    composite = (
        turn_score * 0.25
        + agree_score * 0.20
        + elaboration_score * 0.20
        + density_score * 0.15
        + casual_score * 0.20
    )

    signals = {
        "turn_taking": round(turn_score, 3),
        "agreement": round(agree_score, 3),
        "elaboration": round(elaboration_score, 3),
        "content_density": round(density_score, 3),
        "casual_tone": round(casual_score, 3),
    }

    reasons = []
    if turn_score > 0.4:
        reasons.append("turn-taking detected")
    if agree_score > 0.3:
        reasons.append("agreement/disagreement markers")
    if casual_score > 0.3:
        reasons.append("conversational tone")

    return GenreCueResult(
        "podcast", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong podcast signals",
    )


_PODCAST_AGREE = (
    "yeah", "exactly", "right", "absolutely", "i agree",
    "i disagree", "that's a good point", "interesting",
    "for sure", "totally", "100%", "fair enough",
)

_PODCAST_ELABORATE = (
    "to add to that", "building on", "and also", "on top of that",
    "the other thing", "what's interesting", "let me push back",
    "i'd say", "the way i see it",
)

_PODCAST_CASUAL = (
    "you know", "like", "i mean", "right", "kind of",
    "sort of", "basically", "honestly", "literally",
    "okay so", "wait", "hold on",
)


# ══════════════════════════════════════════════════════════════════════════
# INTERVIEW CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_interview_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect interview patterns (Q&A format).

    Patterns:
    1. Question-answer structure (? followed by long answer)
    2. Personal story markers from interviewee
    3. Reflection language ("looking back", "the turning point")
    4. Clear turn-taking with asymmetric lengths
    5. Interview prompts ("tell me about", "how did you")
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    if not segs:
        return GenreCueResult("interview", 0.0, {}, "no speech")

    text = " ".join(s.text.lower() for s in segs)

    # Signal 1: Q&A pattern (short question segment → long answer segment)
    qa_score = _detect_qa_pattern(segs)

    # Signal 2: Personal story / experience
    story_score = _score_vocab(segs, _INTERVIEW_STORY)

    # Signal 3: Reflection language
    reflect_score = _score_vocab(segs, _INTERVIEW_REFLECT)

    # Signal 4: Interview prompt language
    prompt_score = _score_vocab(segs, _INTERVIEW_PROMPT)

    # Signal 5: Asymmetric turn lengths (short Q, long A)
    asymmetry = _detect_length_asymmetry(segs)

    composite = (
        qa_score * 0.25
        + story_score * 0.20
        + reflect_score * 0.20
        + prompt_score * 0.15
        + asymmetry * 0.20
    )

    signals = {
        "qa_pattern": round(qa_score, 3),
        "personal_story": round(story_score, 3),
        "reflection": round(reflect_score, 3),
        "interview_prompts": round(prompt_score, 3),
        "length_asymmetry": round(asymmetry, 3),
    }

    reasons = []
    if qa_score > 0.4:
        reasons.append("Q&A pattern detected")
    if story_score > 0.3:
        reasons.append("personal story/experience")
    if reflect_score > 0.3:
        reasons.append("reflective language")

    return GenreCueResult(
        "interview", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong interview signals",
    )


_INTERVIEW_STORY = (
    "i remember", "when i was", "at that time", "my first",
    "the moment i", "i couldn't believe", "i realized",
    "the experience", "what happened was",
)

_INTERVIEW_REFLECT = (
    "looking back", "the turning point", "if i could",
    "what i learned", "the biggest lesson", "in hindsight",
    "that changed everything", "that was the moment",
)

_INTERVIEW_PROMPT = (
    "tell me about", "how did you", "what was it like",
    "can you describe", "what happened", "walk me through",
    "how do you", "what advice",
)


def _detect_turn_taking(segments: list[TranscriptSegment]) -> float:
    """Detect speaker turns via gaps between segments."""
    if len(segments) < 3:
        return 0.0
    turn_gaps = 0
    for i in range(1, len(segments)):
        gap = segments[i].start - segments[i - 1].end
        if 0.3 <= gap <= 2.0:  # Natural turn-taking gap
            turn_gaps += 1
    return min(1.0, turn_gaps / 3.0)


def _detect_qa_pattern(segments: list[TranscriptSegment]) -> float:
    """Detect question followed by longer answer."""
    if len(segments) < 2:
        return 0.0
    qa_count = 0
    for i in range(len(segments) - 1):
        if "?" in segments[i].text:
            q_words = len(segments[i].text.split())
            a_words = len(segments[i + 1].text.split())
            if a_words > q_words * 1.5:
                qa_count += 1
    return min(1.0, qa_count / 2.0)


def _detect_length_asymmetry(segments: list[TranscriptSegment]) -> float:
    """Detect alternating short/long segments (interviewer/interviewee)."""
    if len(segments) < 4:
        return 0.0
    lengths = [len(s.text.split()) for s in segments]
    alternating = 0
    for i in range(1, len(lengths)):
        ratio = max(lengths[i], lengths[i - 1]) / max(1, min(lengths[i], lengths[i - 1]))
        if ratio > 2.0:
            alternating += 1
    return min(1.0, alternating / 3.0)


# ══════════════════════════════════════════════════════════════════════════
# NATURE CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_nature_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect nature/wildlife content patterns.

    Nature patterns:
    1. Low speech ratio (mostly ambient/music)
    2. Visual vocabulary (beautiful, amazing, incredible)
    3. Descriptive/imperative language (look at, watch, see)
    4. Low energy variance (calm narration)
    5. Nature-specific vocabulary
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    # Signal 1: Speech ratio sweet spot (nature = mostly visual, some narration OK)
    speech_audio = [s for s in audio if s.has_speech]
    total_dur = time_range.duration if time_range.duration > 0 else 1.0
    speech_dur = sum(s.time_range.duration for s in speech_audio)
    speech_ratio = speech_dur / total_dur
    # Nature ideal: 0-30% speech. >50% = too talky for nature.
    # 0-10% = pure visual (0.9), 10-30% = light narration (1.0), 30-50% = OK (0.6), >50% = not nature (0.2)
    if speech_ratio <= 0.10:
        low_speech_score = 0.9  # Pure visual — great for nature
    elif speech_ratio <= 0.30:
        low_speech_score = 1.0  # Light narration — ideal
    elif speech_ratio <= 0.50:
        low_speech_score = 0.6  # Moderate narration — acceptable
    else:
        low_speech_score = 0.2  # Too speech-heavy for nature

    # Signal 2: Nature vocabulary (EN + VI)
    nature_vocab = _score_vocab(segs, _NATURE_VOCAB)

    # Signal 3: Descriptive/imperative language
    imperative_vocab = _score_vocab(segs, _NATURE_IMPERATIVE)

    # Signal 4: Calm energy (low variance)
    calm_score = _pacing_consistency(audio) if audio else 0.5

    # Signal 5: Ambient audio (silence without speech = nature sounds)
    silence_segs = [s for s in audio if s.has_silence]
    silence_dur = sum(s.time_range.duration for s in silence_segs)
    ambient_score = min(1.0, silence_dur / total_dur * 3.0) if total_dur > 0 else 0.0

    composite = (
        low_speech_score * 0.25
        + nature_vocab * 0.25
        + imperative_vocab * 0.15
        + calm_score * 0.15
        + ambient_score * 0.20
    )

    signals = {
        "low_speech": round(low_speech_score, 3),
        "nature_vocab": round(nature_vocab, 3),
        "imperative": round(imperative_vocab, 3),
        "calm_energy": round(calm_score, 3),
        "ambient_audio": round(ambient_score, 3),
    }

    reasons = []
    if low_speech_score > 0.5:
        reasons.append("low speech ratio (visual-heavy)")
    if nature_vocab > 0.3:
        reasons.append("nature vocabulary")
    if ambient_score > 0.5:
        reasons.append("ambient/environmental audio")

    return GenreCueResult(
        "nature", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong nature signals",
    )


_NATURE_VOCAB = (
    "beautiful", "amazing", "incredible", "stunning", "breathtaking",
    "majestic", "wild", "nature", "animal", "wildlife", "ocean",
    "forest", "mountain", "river", "rare", "species",
    # Vietnamese
    "đẹp", "tuyệt đẹp", "kỳ vĩ", "hoang dã", "thiên nhiên",
    "động vật", "biển", "rừng", "núi", "sông", "hiếm",
    "ngoạn mục", "choáng ngợp", "thần kỳ",
)

_NATURE_IMPERATIVE = (
    "look at", "watch", "see", "notice", "observe",
    # Vietnamese
    "nhìn kìa", "xem này", "nhìn xem", "quan sát",
)


# ══════════════════════════════════════════════════════════════════════════
# HISTORY CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_history_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect historical/documentary content patterns.

    History patterns:
    1. Temporal markers (years, centuries, eras)
    2. Historical vocabulary (kingdom, empire, battle, revolution)
    3. Narrative arc with factual density
    4. Steady pacing (documentary narration)
    5. Past tense / historical references
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    if not segs:
        return GenreCueResult("history", 0.0, {}, "no speech")

    text = " ".join(s.text.lower() for s in segs)

    # Signal 1: Temporal markers (years, dates, centuries)
    # Historical years (before 1980) count full; recent years (1980+) count half
    old_year_hits = len(re.findall(r'\b(1[0-8][0-9]{2}|19[0-7][0-9])\b', text))
    recent_year_hits = len(re.findall(r'\b(19[89][0-9]|20[0-2][0-9])\b', text))
    year_hits = old_year_hits + recent_year_hits * 0.3  # Recent years weight less
    temporal_hits = len(re.findall(
        r'\b(century|decade|era|ancient|medieval|years ago|thế kỷ|thời kỳ|triều đại|năm trước|cổ đại)\b',
        text, re.IGNORECASE,
    ))
    temporal_score = min(1.0, (year_hits + temporal_hits) / 3.0)

    # Signal 2: Historical vocabulary
    history_vocab = _score_vocab(segs, _HISTORY_VOCAB)

    # Signal 3: Information density (history = fact-dense)
    density = _information_density(text)

    # Signal 4: Steady narration pacing
    pacing = _pacing_consistency(audio) if audio else 0.5

    # Signal 5: Narrative energy arc (storytelling-like for documentary)
    arc = _detect_energy_arc(audio) if len(audio) >= 4 else 0.3

    composite = (
        temporal_score * 0.30
        + history_vocab * 0.25
        + density * 0.15
        + pacing * 0.15
        + arc * 0.15
    )

    signals = {
        "temporal_markers": round(temporal_score, 3),
        "history_vocab": round(history_vocab, 3),
        "info_density": round(density, 3),
        "steady_pacing": round(pacing, 3),
        "narrative_arc": round(arc, 3),
    }

    reasons = []
    if temporal_score > 0.3:
        reasons.append(f"temporal markers ({year_hits} years, {temporal_hits} eras)")
    if history_vocab > 0.3:
        reasons.append("historical vocabulary")
    if density > 0.6:
        reasons.append("high information density")

    return GenreCueResult(
        "history", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong history signals",
    )


_HISTORY_VOCAB = (
    "history", "kingdom", "empire", "battle", "revolution", "dynasty",
    "conquer", "civilization", "ancient", "legend", "war", "treaty",
    "colony", "independence", "discovery", "explorer",
    # Vietnamese
    "lịch sử", "vương quốc", "đế chế", "trận chiến", "cách mạng",
    "triều đại", "chinh phục", "văn minh", "cổ đại", "truyền thuyết",
    "chiến tranh", "hiệp ước", "thuộc địa", "độc lập", "khám phá",
)


# ══════════════════════════════════════════════════════════════════════════
# ACTION CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_action_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect action/sports/gaming content patterns.

    Action patterns:
    1. High energy audio (intense moments)
    2. Energy spikes (sudden bursts)
    3. Very low speech ratio (visual-heavy)
    4. Short exclamations (not long narration)
    5. Action vocabulary
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    # Signal 1: High average energy
    avg_energy = _average_energy(audio) if audio else 0.3

    # Signal 2: Energy spikes (action = bursts of intensity)
    energy_spikes = _detect_energy_spikes(audio) if len(audio) >= 2 else 0.0

    # Signal 3: Low speech ratio
    speech_audio = [s for s in audio if s.has_speech]
    total_dur = time_range.duration if time_range.duration > 0 else 1.0
    speech_dur = sum(s.time_range.duration for s in speech_audio)
    speech_ratio = speech_dur / total_dur
    low_speech = max(0.0, 1.0 - speech_ratio * 2.0) if speech_ratio < 0.4 else 0.1

    # Signal 4: Short exclamations (action = brief shouts, not sentences)
    short_excl = 0.0
    if segs:
        short_count = sum(1 for s in segs if len(s.text.split()) <= 4)
        short_excl = min(1.0, short_count / max(1, len(segs)))

    # Signal 5: Action vocabulary
    action_vocab = _score_vocab(segs, _ACTION_VOCAB)

    composite = (
        avg_energy * 0.25
        + energy_spikes * 0.25
        + low_speech * 0.20
        + short_excl * 0.15
        + action_vocab * 0.15
    )

    signals = {
        "high_energy": round(avg_energy, 3),
        "energy_spikes": round(energy_spikes, 3),
        "low_speech": round(low_speech, 3),
        "short_exclamations": round(short_excl, 3),
        "action_vocab": round(action_vocab, 3),
    }

    reasons = []
    if avg_energy > 0.6:
        reasons.append("high average energy")
    if energy_spikes > 0.5:
        reasons.append("energy burst patterns")
    if low_speech > 0.5:
        reasons.append("minimal speech (visual-heavy)")

    return GenreCueResult(
        "action", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong action signals",
    )


_ACTION_VOCAB = (
    "go", "run", "attack", "fight", "shoot", "jump", "dodge",
    "hit", "kill", "win", "lose", "score", "goal", "battle",
    "fast", "quick", "intense", "epic", "insane", "clutch",
    # Vietnamese
    "chạy", "tấn công", "đánh", "bắn", "nhảy", "né",
    "đấm", "thắng", "thua", "bàn thắng", "chiến", "nhanh",
    "kịch tính", "điên rồ", "cứu", "nguy hiểm",
)


# ══════════════════════════════════════════════════════════════════════════
# KIDS MUSIC CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_kids_music_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect children's music/song content patterns.

    Kids music patterns:
    1. Repetitive phrases (chorus/refrain)
    2. Simple vocabulary (short words)
    3. Consistent rhythm/pacing
    4. Low silence (continuous audio/music)
    5. Music vocabulary
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    # Signal 1: Repetition (same phrases appear multiple times)
    repetition = 0.0
    if segs:
        phrases = [s.text.lower().strip() for s in segs]
        unique = len(set(phrases))
        total = len(phrases)
        if total >= 3:
            repetition = max(0.0, 1.0 - unique / total) * 2.0
            repetition = min(1.0, repetition)

    # Signal 2: Simple vocabulary (short average word length)
    simple_vocab = 0.0
    if segs:
        text = " ".join(s.text for s in segs)
        words = text.split()
        if words:
            avg_word_len = sum(len(w) for w in words) / len(words)
            # Kids music: average word < 4 chars
            simple_vocab = max(0.0, 1.0 - (avg_word_len - 3.0) / 4.0)
            simple_vocab = min(1.0, simple_vocab)

    # Signal 3: Consistent rhythm
    rhythm = _pacing_consistency(audio) if audio else 0.5

    # Signal 4: Low silence (music = continuous sound)
    silence_segs = [s for s in audio if s.has_silence]
    total_dur = time_range.duration if time_range.duration > 0 else 1.0
    silence_dur = sum(s.time_range.duration for s in silence_segs)
    silence_ratio = silence_dur / total_dur
    low_silence = max(0.0, 1.0 - silence_ratio * 5.0)

    # Signal 5: Kids/music vocabulary
    kids_vocab = _score_vocab(segs, _KIDS_MUSIC_VOCAB)

    composite = (
        repetition * 0.25
        + simple_vocab * 0.20
        + rhythm * 0.20
        + low_silence * 0.15
        + kids_vocab * 0.20
    )

    signals = {
        "repetition": round(repetition, 3),
        "simple_vocab": round(simple_vocab, 3),
        "rhythm_consistency": round(rhythm, 3),
        "continuous_audio": round(low_silence, 3),
        "kids_vocab": round(kids_vocab, 3),
    }

    reasons = []
    if repetition > 0.3:
        reasons.append("repetitive phrases (chorus pattern)")
    if simple_vocab > 0.5:
        reasons.append("simple vocabulary")
    if kids_vocab > 0.3:
        reasons.append("music/kids vocabulary")

    return GenreCueResult(
        "kids_music", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong kids music signals",
    )


_KIDS_MUSIC_VOCAB = (
    "sing", "song", "dance", "clap", "jump", "twinkle",
    "la la", "baby", "kids", "together", "happy", "play",
    "come on", "let's go", "yay", "hooray",
    # Vietnamese
    "hát", "bài hát", "nhảy", "vỗ tay", "nhảy múa",
    "la la", "bé", "các bạn nhỏ", "cùng nhau", "vui",
    "chơi", "nào nào", "hoan hô", "múa",
)


# ══════════════════════════════════════════════════════════════════════════
# ANIMATION CUE DETECTOR
# ══════════════════════════════════════════════════════════════════════════

def detect_animation_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> GenreCueResult:
    """Detect animated content patterns.

    Animation differs from action by:
    - Character dialogue (multi-speaker dramatic lines, not shouts)
    - Narrative structure (story arc with plot, not energy bursts)
    - Moderate speech (characters talk, unlike silent action)
    - Fantasy/character vocabulary (hero, magic, quest — not fight, score, goal)
    """
    segs = _filter_transcript(time_range, transcript)
    audio = _filter_audio(time_range, audio_segments)

    # Signal 1: Character dialogue — moderate speech with varied speakers
    # Animation has more speech than action but less than talking head
    speech_audio = [s for s in audio if s.has_speech]
    total_dur = time_range.duration if time_range.duration > 0 else 1.0
    speech_dur = sum(s.time_range.duration for s in speech_audio)
    speech_ratio = speech_dur / total_dur
    # Animation sweet spot: 20-60% speech (characters talking)
    if 0.2 <= speech_ratio <= 0.6:
        dialogue_score = 0.9
    elif speech_ratio < 0.2:
        dialogue_score = 0.4  # Too silent for animation with dialogue
    else:
        dialogue_score = 0.5  # Too talky — more like talking head

    # Signal 2: Narrative arc (animation = episodic story structure)
    arc = _detect_energy_arc(audio) if len(audio) >= 4 else 0.3

    # Signal 3: Animation/character vocabulary (NOT action vocab)
    anim_vocab = _score_vocab(segs, _ANIMATION_VOCAB)

    # Signal 4: Plot structure markers (meanwhile, but then, suddenly)
    plot_markers = 0.0
    if segs:
        text = " ".join(s.text.lower() for s in segs)
        plot_hits = sum(1 for p in _ANIMATION_PLOT_MARKERS if p in text)
        plot_markers = min(1.0, plot_hits / 2.0)

    # Signal 5: Sentence length variety (animation = mix of short exclamations + longer narration)
    len_variance = _sentence_length_variance(segs) if segs else 0.0

    composite = (
        dialogue_score * 0.25
        + arc * 0.25
        + anim_vocab * 0.25
        + plot_markers * 0.15
        + len_variance * 0.10
    )

    signals = {
        "character_dialogue": round(dialogue_score, 3),
        "story_arc": round(arc, 3),
        "animation_vocab": round(anim_vocab, 3),
        "plot_structure": round(plot_markers, 3),
        "dialogue_variety": round(len_variance, 3),
    }

    reasons = []
    if dialogue_score > 0.7:
        reasons.append("character dialogue pattern")
    if arc > 0.5:
        reasons.append("narrative story arc")
    if anim_vocab > 0.3:
        reasons.append("animation/character vocabulary")
    if plot_markers > 0.3:
        reasons.append("plot structure markers")

    return GenreCueResult(
        "animation", round(composite, 3), signals,
        "; ".join(reasons) if reasons else "no strong animation signals",
    )


_ANIMATION_VOCAB = (
    "hero", "villain", "magic", "power", "transform", "save", "rescue",
    "adventure", "quest", "dragon", "princess", "monster", "kingdom",
    "spell", "shield", "sword", "warrior", "evil", "destiny", "chosen",
    # Vietnamese
    "anh hùng", "phản diện", "phép thuật", "sức mạnh", "biến hình",
    "phiêu lưu", "nhiệm vụ", "rồng", "công chúa", "quái vật",
    "vương quốc", "chiến binh", "bảo vệ", "số phận", "truyền thuyết",
)

_ANIMATION_PLOT_MARKERS = (
    "meanwhile", "but then", "suddenly", "little did", "and so",
    "the next day", "later that", "back at", "in the end",
    # Vietnamese
    "trong khi đó", "nhưng rồi", "bất ngờ", "không ngờ", "và thế là",
    "ngày hôm sau", "sau đó", "trở về", "cuối cùng",
    "thì ra", "hóa ra", "lúc đó", "khi ấy",
)


# ══════════════════════════════════════════════════════════════════════════
# UNIFIED GENRE CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════

def classify_segment_genre(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> dict[str, GenreCueResult]:
    """Run all genre cue detectors and return scores for each genre.

    Returns dict mapping genre name to cue result. The highest-scoring
    genre is the most likely classification for this segment.
    """
    return {
        "talking_head": detect_talking_head_cues(time_range, transcript, audio_segments),
        "podcast": detect_podcast_cues(time_range, transcript, audio_segments),
        "interview": detect_interview_cues(time_range, transcript, audio_segments),
        "comedy": detect_comedy_cues(time_range, transcript, audio_segments),
        "education": detect_education_cues(time_range, transcript, audio_segments),
        "storytelling": detect_story_cues(time_range, transcript, audio_segments),
        "news_commentary": detect_news_cues(time_range, transcript, audio_segments),
        "review": detect_review_cues(time_range, transcript, audio_segments),
        "nature": detect_nature_cues(time_range, transcript, audio_segments),
        "history": detect_history_cues(time_range, transcript, audio_segments),
        "action": detect_action_cues(time_range, transcript, audio_segments),
        "kids_music": detect_kids_music_cues(time_range, transcript, audio_segments),
        "animation": detect_animation_cues(time_range, transcript, audio_segments),
    }


# ══════════════════════════════════════════════════════════════════════════
# SHARED UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════

def _filter_transcript(
    tr: TimeRange, segments: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    return [s for s in segments if s.time_range.overlaps(tr)]


def _filter_audio(
    tr: TimeRange, segments: list[AudioSegment],
) -> list[AudioSegment]:
    return [s for s in segments if s.time_range.overlaps(tr)]


def _score_vocab(
    segments: list[TranscriptSegment], vocab: tuple[str, ...],
) -> float:
    """Score how many vocab terms appear in the transcript (0.0-1.0)."""
    if not segments:
        return 0.0
    text = " ".join(s.text.lower() for s in segments)
    hits = sum(1 for term in vocab if term in text)
    # Normalize: 3+ hits = max score
    return min(1.0, hits / 3.0)


def _count_pattern_density(text: str, patterns: tuple[str, ...]) -> float:
    """Count pattern hits normalized to text length."""
    if not text:
        return 0.0
    hits = 0
    for p in patterns:
        if p.startswith(r"\b"):
            hits += len(re.findall(p, text, re.IGNORECASE))
        elif p in text:
            hits += 1
    word_count = len(text.split())
    if word_count == 0:
        return 0.0
    # Normalize: ~1 hit per 20 words = strong signal
    density = hits / (word_count / 20.0)
    return min(1.0, density)


def _detect_setup_punchline(segments: list[TranscriptSegment]) -> float:
    """Detect long-sentence → short-sentence patterns (setup → punchline)."""
    if len(segments) < 2:
        return 0.0
    lengths = [len(s.text.split()) for s in segments]
    patterns_found = 0
    for i in range(len(lengths) - 1):
        if lengths[i] >= 8 and lengths[i + 1] <= 5:
            patterns_found += 1
    return min(1.0, patterns_found / 2.0)


def _detect_comedic_pauses(
    segments: list[TranscriptSegment],
    audio: list[AudioSegment],
) -> float:
    """Detect silence after short statements (comedic timing beats)."""
    if len(segments) < 2:
        return 0.0
    pause_count = 0
    for i in range(len(segments) - 1):
        gap = segments[i + 1].start - segments[i].end
        words = len(segments[i].text.split())
        if gap >= 0.8 and words <= 6:
            pause_count += 1
    return min(1.0, pause_count / 2.0)


def _sentence_length_variance(segments: list[TranscriptSegment]) -> float:
    """High variance in sentence lengths = comedic rhythm."""
    if len(segments) < 3:
        return 0.0
    lengths = [len(s.text.split()) for s in segments]
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    # Normalize: variance > 20 = high
    return min(1.0, variance / 25.0)


def _detect_energy_spikes(audio: list[AudioSegment]) -> float:
    """Detect sudden energy spikes (emphasis moments)."""
    if len(audio) < 2:
        return 0.0
    spike_count = 0
    for i in range(1, len(audio)):
        if audio[i].energy_avg > audio[i - 1].energy_avg * 1.5:
            spike_count += 1
    return min(1.0, spike_count / 3.0)


def _detect_list_structure(text: str) -> float:
    """Detect numbered lists or step sequences."""
    patterns = [
        r"\b(first|second|third|fourth|fifth)\b",
        r"\b(step (one|two|three|1|2|3))\b",
        r"\b(number (one|two|three|1|2|3))\b",
        r"\b(tip #?\d)\b",
        r"\b(reason #?\d)\b",
    ]
    hits = sum(len(re.findall(p, text, re.IGNORECASE)) for p in patterns)
    return min(1.0, hits / 2.0)


def _information_density(text: str) -> float:
    """Ratio of unique words to total words (higher = more informative)."""
    words = text.split()
    if len(words) < 10:
        return 0.3
    unique = len(set(words))
    ratio = unique / len(words)
    # Typical speech: 0.4-0.6 ratio; dense info: > 0.6
    return min(1.0, ratio / 0.65)


def _pacing_consistency(audio: list[AudioSegment]) -> float:
    """Low energy variance = consistent delivery (educational style)."""
    if len(audio) < 2:
        return 0.5
    energies = [s.energy_avg for s in audio if s.has_speech]
    if len(energies) < 2:
        return 0.5
    mean = sum(energies) / len(energies)
    variance = sum((e - mean) ** 2 for e in energies) / len(energies)
    # Low variance = consistent = good for education
    return max(0.0, 1.0 - variance * 15)


def _detect_energy_arc(audio: list[AudioSegment]) -> float:
    """Detect rising-then-falling energy pattern (narrative tension arc)."""
    if len(audio) < 4:
        return 0.3
    energies = [s.energy_avg for s in audio]
    n = len(energies)
    first_half = energies[:n // 2]
    second_half = energies[n // 2:]

    if not first_half or not second_half:
        return 0.3

    # Look for rising in first half, peak in middle, falling in second half
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    peak = max(energies)
    peak_pos = energies.index(peak) / n

    # Ideal: peak at 40-70% through the segment
    if 0.3 <= peak_pos <= 0.75 and peak > avg_first * 1.2:
        return 0.8
    elif avg_second < avg_first:
        return 0.5  # Falling energy = partial arc
    return 0.3


def _count_questions(segments: list[TranscriptSegment]) -> int:
    """Count question marks in transcript."""
    return sum(s.text.count("?") for s in segments)


def _average_energy(audio: list[AudioSegment]) -> float:
    """Average speech energy (0.0-1.0)."""
    speech = [s for s in audio if s.has_speech]
    if not speech:
        return 0.3
    avg = sum(s.energy_avg for s in speech) / len(speech)
    return min(1.0, avg / 0.35)
