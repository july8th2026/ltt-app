"""Smart clip title generator — SEO-optimized, platform-safe.

Generates meaningful titles from clip content analysis:
- display_title: Human-readable Vietnamese title for GUI
- seo_slug: URL-safe slug for export filenames
- suggested_hashtags: 3-5 relevant hashtags
- seo_description: Short description for platform upload

Design principles:
- No clickbait (fake promises, "shocking", "you won't believe")
- No ALL CAPS full title
- No sexual/violent/misleading language
- Natural questions encouraged (high engagement)
- Emoji sparingly (max 1-2)
- Platform limits respected (TikTok 150, YouTube 70, Reels 2200)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class TitleResult:
    """Generated title package for a clip."""
    display_title: str           # Vietnamese GUI title (5-12 words)
    seo_slug: str                # URL-safe filename slug
    suggested_hashtags: list[str] = field(default_factory=list)
    seo_description: str = ""    # Platform upload description


# ── Banned words (violate platform policies) ────────────────────────────
BANNED_WORDS = {
    # English clickbait / policy violations
    "shocking", "exposed", "you won't believe", "watch before deleted",
    "secret revealed", "doctors hate", "they don't want you to know",
    "link in bio", "follow for more", "dm for", "dm me",
    "free money", "get rich", "guaranteed",
    # Vietnamese equivalents
}

# ── Genre → hashtag pools ───────────────────────────────────────────────
GENRE_HASHTAGS: dict[str, list[str]] = {
    "storytelling": ["#storytelling", "#story", "#viral", "#foryou", "#fyp"],
    "nature": ["#nature", "#wildlife", "#amazing", "#beautiful", "#fyp"],
    "history": ["#history", "#facts", "#didyouknow", "#education", "#fyp"],
    "action": ["#action", "#epic", "#amazing", "#viral", "#fyp"],
    "kids_music": ["#kidsmusic", "#children", "#fun", "#cute", "#fyp"],
    "animation": ["#animation", "#cartoon", "#funny", "#viral", "#fyp"],
    "comedy": ["#comedy", "#funny", "#humor", "#viral", "#fyp"],
    "review": ["#review", "#satisfying", "#asmr", "#oddlysatisfying", "#fyp"],
    "highlight_reel": ["#highlights", "#bestmoments", "#compilation", "#viral", "#fyp"],
    "talking_head": ["#tips", "#advice", "#viral", "#foryou", "#fyp"],
    "podcast": ["#podcast", "#conversation", "#insight", "#viral", "#fyp"],
    "interview": ["#interview", "#conversation", "#insight", "#viral", "#fyp"],
    "education": ["#education", "#learn", "#didyouknow", "#facts", "#fyp"],
    "news_commentary": ["#news", "#commentary", "#opinion", "#viral", "#fyp"],
}

# ── Hook type → title strategy ──────────────────────────────────────────
HOOK_EMOJI: dict[str, str] = {
    "question": "\u2753",      # ❓
    "curiosity": "\U0001f440",  # 👀
    "conflict": "\u26a0\ufe0f",  # ⚠️
    "surprise": "\U0001f631",   # 😱
    "emotional": "\U0001f622",  # 😢
    "authority": "\U0001f4a1",  # 💡
    "reaction": "\U0001f525",   # 🔥
    "organic": "\u2728",        # ✨
}


def generate_titles(
    hook_text: str,
    speech_preview: str,
    hook_type: str,
    tags: list[str],
    genre: str,
    score: float,
    candidate_id: str,
    duration: float = 0.0,
) -> TitleResult:
    """Generate smart titles from clip analysis data.

    Args:
        hook_text: Opening sentence/phrase from first 3 seconds
        speech_preview: First ~120 chars of transcript
        hook_type: Hook classification (question, curiosity, etc.)
        tags: Semantic tags from scoring
        genre: Content genre
        score: Overall score (0-1.0)
        candidate_id: Clip ID (c001, c002...)
        duration: Clip duration in seconds

    Returns:
        TitleResult with display_title, seo_slug, hashtags, description
    """
    # Step 1: Extract best title text
    raw_title = _extract_title_text(hook_text, speech_preview, hook_type)

    # Step 2: Clean and format
    display_title = _format_display_title(raw_title, hook_type)

    # Step 3: Apply safety filter
    display_title = _safety_filter(display_title)

    # Step 4: Truncate to platform limits
    display_title = _truncate_title(display_title, max_chars=65)

    # Step 5: Generate URL-safe slug
    seo_slug = _to_slug(display_title, candidate_id)

    # Step 6: Generate hashtags
    hashtags = _generate_hashtags(tags, genre, hook_type)

    # Step 7: Generate description
    description = _generate_description(
        display_title, speech_preview, genre, duration
    )

    return TitleResult(
        display_title=display_title,
        seo_slug=seo_slug,
        suggested_hashtags=hashtags,
        seo_description=description,
    )


# ═══════════════════════════════════════════════════════════════════════
# INTERNAL FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _extract_title_text(
    hook_text: str, speech_preview: str, hook_type: str
) -> str:
    """Extract the best title text from available content."""
    # Priority 1: hook_text (first sentence)
    if hook_text and len(hook_text.strip()) > 10:
        text = hook_text.strip()
        # Take first sentence only
        for sep in [".", "!", "?", "\n"]:
            if sep in text:
                first = text.split(sep)[0].strip()
                if len(first) > 10:
                    # Keep the punctuation for questions/exclamations
                    if sep in ("?", "!"):
                        return first + sep
                    return first
        # If no sentence break, take first 60 chars at word boundary
        if len(text) > 60:
            cut = text[:60].rsplit(" ", 1)[0]
            return cut.strip()
        return text

    # Priority 2: speech_preview (first meaningful sentence)
    if speech_preview and len(speech_preview.strip()) > 10:
        text = speech_preview.strip()
        for sep in [".", "!", "?"]:
            if sep in text:
                first = text.split(sep)[0].strip()
                if len(first) > 8:
                    if sep in ("?", "!"):
                        return first + sep
                    return first
        return text[:60].rsplit(" ", 1)[0].strip()

    # Priority 3: Generic based on hook type
    fallback = {
        "question": "What happens next?",
        "curiosity": "Look at this closely",
        "conflict": "This changes everything",
        "surprise": "Wait for it",
        "emotional": "This moment",
        "authority": "Here's what you need to know",
        "reaction": "Watch this",
        "organic": "Check this out",
    }
    return fallback.get(hook_type, "Watch this")


def _format_display_title(raw_title: str, hook_type: str) -> str:
    """Format raw text into a display-ready title."""
    title = raw_title.strip()

    # Remove trailing incomplete words/fragments
    if title and title[-1] not in ".!?":
        # Check if last word looks cut off (very short)
        words = title.split()
        if words and len(words[-1]) <= 2 and len(words) > 3:
            title = " ".join(words[:-1])

    # Capitalize first letter
    if title and title[0].islower():
        title = title[0].upper() + title[1:]

    # Add contextual emoji (just 1, at start)
    emoji = HOOK_EMOJI.get(hook_type, "")
    if emoji and not any(c in title for c in "\U0001f600\U0001f64f\U0001f300\U0001f5ff"):
        title = f"{emoji} {title}"

    return title


def _safety_filter(title: str) -> str:
    """Remove policy-violating language."""
    lower = title.lower()

    # Check banned phrases
    for banned in BANNED_WORDS:
        if banned in lower:
            # Replace with neutral alternative
            title = re.sub(re.escape(banned), "", title, flags=re.IGNORECASE).strip()

    # Remove ALL CAPS words (keep if short like "AI", "CEO")
    words = title.split()
    cleaned = []
    for w in words:
        # Skip emoji
        if len(w) <= 1 or not w.isascii():
            cleaned.append(w)
            continue
        # Allow short acronyms (2-3 chars)
        if w.isupper() and len(w) > 3:
            cleaned.append(w.capitalize())
        else:
            cleaned.append(w)

    return " ".join(cleaned)


def _truncate_title(title: str, max_chars: int = 65) -> str:
    """Truncate title to platform limit at word boundary."""
    if len(title) <= max_chars:
        return title

    # Cut at word boundary
    truncated = title[:max_chars].rsplit(" ", 1)[0]

    # Don't end with punctuation fragments
    truncated = truncated.rstrip(",;:-")

    return truncated.strip()


def _to_slug(title: str, candidate_id: str) -> str:
    """Convert title to URL-safe filename slug.

    Result: "c001_nhin-ky-khe-phim-nay"
    """
    # Remove emoji and special chars
    text = ""
    for c in title:
        if unicodedata.category(c).startswith(("L", "N", "Z")):
            text += c

    # Vietnamese diacritics → ASCII
    slug = _remove_diacritics(text.lower().strip())

    # Replace spaces/special with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    # Limit length
    if len(slug) > 40:
        slug = slug[:40].rsplit("-", 1)[0]

    # Prefix with candidate_id for sorting
    if slug:
        return f"{candidate_id}_{slug}"
    return candidate_id


def _remove_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics: ắ→a, ờ→o, etc."""
    # Vietnamese-specific replacements
    vn_map = {
        "\u0111": "d", "\u0110": "d",  # đ/Đ
    }
    for src, dst in vn_map.items():
        text = text.replace(src, dst)

    # NFD decomposition strips combining marks
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _generate_hashtags(
    tags: list[str], genre: str, hook_type: str
) -> list[str]:
    """Generate 3-5 relevant hashtags."""
    result: list[str] = []

    # Genre-specific hashtags (pick 2-3)
    genre_tags = GENRE_HASHTAGS.get(genre, GENRE_HASHTAGS["talking_head"])
    result.extend(genre_tags[:3])

    # Tag-based hashtags
    tag_map = {
        "strong_hook": "#mustsee",
        "high_energy": "#energy",
        "decent_hook": "#interesting",
        "good_pacing": "#smooth",
        "has_person": "#people",
        "question": "#question",
        "emotional": "#emotional",
    }
    for tag in tags:
        if tag in tag_map and len(result) < 5:
            result.append(tag_map[tag])

    # Hook type bonus
    hook_tags = {
        "question": "#didyouknow",
        "surprise": "#waitforit",
        "reaction": "#reaction",
        "emotional": "#emotional",
        "curiosity": "#lookcloser",
    }
    if hook_type in hook_tags and len(result) < 5:
        result.append(hook_tags[hook_type])

    # Always include #fyp if not already
    if "#fyp" not in result:
        result.append("#fyp")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for h in result:
        if h not in seen:
            seen.add(h)
            unique.append(h)

    return unique[:5]


def _generate_description(
    title: str, speech_preview: str, genre: str, duration: float
) -> str:
    """Generate short SEO description for platform upload."""
    # Remove emoji from title for description
    clean_title = re.sub(
        r"[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff"
        r"\u2600-\u26ff\u2700-\u27bf\u2753\u2728]+",
        "", title
    ).strip()

    parts = [clean_title]

    # Add context from speech if different from title
    if speech_preview and len(speech_preview) > len(clean_title) + 20:
        # Take first sentence from preview that's not the title
        extra = speech_preview[len(clean_title):].strip()
        for sep in [".", "!", "?"]:
            if sep in extra:
                sentence = extra.split(sep)[0].strip()
                if len(sentence) > 15:
                    parts.append(sentence + sep)
                    break

    # Duration context
    if duration > 0:
        dur_sec = int(duration)
        parts.append(f"({dur_sec}s)")

    desc = " ".join(parts)

    # Platform limit (Instagram Reels allows 2200, but keep concise)
    return desc[:200].strip()
