"""Auto-detect content genre from analysis data.

Analyzes transcript, visual, and audio patterns to suggest the best
genre profile for the editorial brain. This helps when user selects
wrong genre (e.g., "talking_head" for a keyboard cleaning video).

Returns ranked list of genre suggestions with confidence scores.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from cutclipshort.types import AnalysisResult

logger = logging.getLogger(__name__)


def _count_words(text: str, words: tuple[str, ...]) -> int:
    """Count word occurrences using word-boundary matching.

    Prevents substring false positives: 'chiến' won't match 'chiến lược'.
    For multi-word phrases, uses simple 'in' check (safe for phrases).
    """
    count = 0
    for w in words:
        if " " in w:
            # Multi-word phrase: substring match is safe
            if w in text:
                count += 1
        else:
            # Single word: use word boundary
            if re.search(r'(?:^|\s)' + re.escape(w) + r'(?:\s|$)', text):
                count += 1
    return count


def suggest_genre(analysis: AnalysisResult) -> list[dict[str, Any]]:
    """Analyze content and suggest best genre(s).

    Returns:
        List of {genre: str, confidence: float, reason: str}, sorted by confidence desc.
    """
    scores: dict[str, tuple[float, str]] = {}

    # Signal 1: Person presence
    has_person_segs = sum(1 for v in analysis.visual_segments if v.has_person)
    person_ratio = has_person_segs / max(1, len(analysis.visual_segments))

    # Signal 2: Speech density
    total_speech = sum(s.end - s.start for s in analysis.transcript)
    duration = analysis.source.duration_sec
    speech_ratio = total_speech / max(1, duration)

    # Signal 3: Transcript analysis
    all_text = " ".join(s.text.lower() for s in analysis.transcript)
    word_count = len(all_text.split())

    # Signal 4: Scene count density (scenes per minute)
    scenes_per_min = len(analysis.scenes) / max(1, duration / 60)

    # ── Score each genre ──

    # Talking Head: high person presence + high speech + low scene density
    th_score = person_ratio * 0.4 + speech_ratio * 0.3 + (1.0 if scenes_per_min < 10 else 0.3) * 0.3
    scores["talking_head"] = (th_score, f"person={person_ratio:.0%} speech={speech_ratio:.0%}")

    # Podcast: high speech + low person + low scene density
    pod_score = (1 - person_ratio) * 0.2 + speech_ratio * 0.5 + (1.0 if scenes_per_min < 8 else 0.3) * 0.3
    scores["podcast"] = (pod_score, f"speech={speech_ratio:.0%} no_person={1-person_ratio:.0%}")

    # Review/Showcase: high scene density + moderate speech + descriptive language
    descriptive_words = _count_words(all_text, ("look", "watch", "see", "satisfying", "clean", "beautiful", "amazing"))
    review_score = (min(1.0, scenes_per_min / 15) * 0.3
                    + speech_ratio * 0.3
                    + min(1.0, descriptive_words / 3) * 0.4)
    scores["review"] = (review_score, f"scenes/min={scenes_per_min:.0f} descriptive={descriptive_words}")

    # Education: instructional language
    edu_words = _count_words(all_text, ("step", "first", "next", "learn", "how to", "method", "technique"))
    edu_score = speech_ratio * 0.3 + min(1.0, edu_words / 3) * 0.4 + person_ratio * 0.3
    scores["education"] = (edu_score, f"instructional={edu_words} speech={speech_ratio:.0%}")

    # Storytelling: narrative language
    story_words = _count_words(all_text, ("then", "suddenly", "one day", "remember", "happened", "turned out"))
    story_score = speech_ratio * 0.3 + min(1.0, story_words / 3) * 0.4 + (1 - min(1.0, scenes_per_min / 20)) * 0.3
    scores["storytelling"] = (story_score, f"narrative={story_words} speech={speech_ratio:.0%}")

    # Comedy: short sentences + high variance + comedy vocab
    comedy_words = _count_words(all_text, ("literally", "bro", "dude", "funny", "hilarious", "joke", "laugh"))
    comedy_score = min(1.0, comedy_words / 3) * 0.5 + speech_ratio * 0.3 + person_ratio * 0.2
    scores["comedy"] = (comedy_score, f"comedy_vocab={comedy_words}")

    # News Commentary: opinion + urgency
    news_words = _count_words(all_text, ("think", "opinion", "breaking", "happened", "apparently", "controversy"))
    news_score = min(1.0, news_words / 3) * 0.5 + speech_ratio * 0.3 + person_ratio * 0.2
    scores["news_commentary"] = (news_score, f"opinion={news_words}")

    # Interview: Q&A patterns
    question_count = sum(1 for s in analysis.transcript if "?" in s.text)
    interview_score = min(1.0, question_count / 5) * 0.4 + speech_ratio * 0.3 + person_ratio * 0.3
    scores["interview"] = (interview_score, f"questions={question_count}")

    # Nature: low speech + low person + high scene density (visual content)
    nature_words = _count_words(all_text, (
        "beautiful", "amazing", "nature", "wild", "ocean", "forest",
        "đẹp", "thiên nhiên", "hoang dã", "biển", "rừng", "ngoạn mục",
    ))
    nature_score = ((1 - speech_ratio) * 0.3
                    + (1 - person_ratio) * 0.2
                    + min(1.0, scenes_per_min / 15) * 0.2
                    + min(1.0, nature_words / 3) * 0.3)
    scores["nature"] = (nature_score, f"visual_heavy speech={speech_ratio:.0%} nature_vocab={nature_words}")

    # History: temporal markers + high speech + narrative
    history_words = _count_words(all_text, (
        "history", "century", "ancient", "war", "kingdom", "dynasty",
        "lịch sử", "thế kỷ", "cổ đại", "chiến tranh", "triều đại", "thời kỳ",
    ))
    year_hits = len(re.findall(r'\b(1[0-9]{3}|20[0-2][0-9])\b', all_text))
    history_score = (speech_ratio * 0.2
                     + min(1.0, (history_words + year_hits) / 4) * 0.5
                     + (1 - min(1.0, scenes_per_min / 20)) * 0.3)
    scores["history"] = (history_score, f"history_vocab={history_words} years={year_hits}")

    # Action: low speech + high scene density + action vocab
    action_words = _count_words(all_text, (
        "fight", "run", "attack", "battle", "win", "score", "goal",
        "đánh", "chạy", "tấn công", "chiến đấu", "thắng", "bàn thắng",
    ))
    action_score = ((1 - speech_ratio) * 0.3
                    + min(1.0, scenes_per_min / 20) * 0.3
                    + min(1.0, action_words / 3) * 0.4)
    scores["action"] = (action_score, f"action_vocab={action_words} scenes/min={scenes_per_min:.0f}")

    # Kids Music: low person + music/kids vocab + repetition
    kids_words = _count_words(all_text, (
        "sing", "dance", "song", "baby", "kids", "together",
        "hát", "nhảy", "bài hát", "bé", "các bạn nhỏ", "cùng nhau",
    ))
    kids_score = ((1 - person_ratio) * 0.2
                  + min(1.0, kids_words / 3) * 0.5
                  + (1 - speech_ratio) * 0.3)
    scores["kids_music"] = (kids_score, f"kids_vocab={kids_words}")

    # Animation: exclamations + action/emotion vocab + moderate speech
    anim_words = _count_words(all_text, (
        "hero", "villain", "magic", "power", "adventure", "monster",
        "anh hùng", "phép thuật", "sức mạnh", "phiêu lưu", "quái vật",
    ))
    excl_ratio = all_text.count("!") / max(1, word_count) * 100
    anim_score = (min(1.0, anim_words / 3) * 0.4
                  + min(1.0, excl_ratio / 5) * 0.3
                  + (1 - person_ratio) * 0.3)
    scores["animation"] = (anim_score, f"anim_vocab={anim_words} excl={excl_ratio:.0f}%")

    # Sort by confidence
    results = [
        {"genre": genre, "confidence": round(conf, 3), "reason": reason}
        for genre, (conf, reason) in sorted(scores.items(), key=lambda x: -x[1][0])
    ]

    logger.info(
        "Genre suggestion: top=%s (%.0f%%), person=%.0f%%, speech=%.0f%%, scenes/min=%.0f",
        results[0]["genre"], results[0]["confidence"] * 100,
        person_ratio * 100, speech_ratio * 100, scenes_per_min,
    )

    return results
