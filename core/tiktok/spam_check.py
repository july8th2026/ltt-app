"""
TikTok spam pre-flight checker.

Validates post content BEFORE upload to avoid:
- TikTok flagging the account/app as spam
- Wasted API quota on rejected posts
- App audit rejection due to spam-enabling behavior

H1 fix + M7 fix.

TikTok's spam signals (from their public guidelines):
- Empty captions or emoji-only captions
- Excessive hashtags (>30 is suspicious)
- Hashtag stuffing ("#fyp #foryou #viral #trending" generic spam)
- Duplicate captions across many posts
- Very short captions on commercial content
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


# Hashtag spam patterns
_SPAM_HASHTAGS = {
    "fyp", "foryou", "foryoupage", "viral", "trending", "viralvideo",
    "explore", "explorepage", "fy", "trend", "trendingnow",
    "popular", "subscribe", "follow", "followme", "likeforlike",
}
# Caption length limits
_MAX_CAPTION_LEN     = 2200    # TikTok max
_MIN_CAPTION_LEN     = 0       # 0 is allowed but warned
_RECOMMENDED_MIN_LEN = 10      # below this triggers warning
# Hashtag limits
_MAX_HASHTAGS        = 30      # hard limit
_RECOMMENDED_HASHTAGS = 5      # 3-5 is sweet spot per TikTok analytics


@dataclass
class SpamCheckResult:
    """Result of a spam pre-flight check."""
    is_blocked: bool          # True → must not upload (hard violation)
    warnings:   List[str]     # Soft issues — display to user but allow override
    blockers:   List[str]     # Hard issues — prevent upload


def check_post_content(
    *,
    caption: str,
    description: str = "",
    keywords: str = "",
    allow_empty_caption: bool = True,
) -> SpamCheckResult:
    """Validate post content before TikTok upload.

    Args:
        caption:    main video caption/title
        description: longer description (some platforms combine)
        keywords:   comma-separated hashtags (will be appended to caption)
        allow_empty_caption: if True, empty caption only triggers warning (not block)

    Returns:
        SpamCheckResult with warnings + blockers lists.
    """
    warnings: list[str] = []
    blockers: list[str] = []

    # Build full text as TikTok will see it
    full_text = " ".join(filter(None, [caption, description, keywords])).strip()

    # 1. Caption length
    if len(full_text) > _MAX_CAPTION_LEN:
        blockers.append(
            f"Caption quá dài ({len(full_text)} ký tự, tối đa {_MAX_CAPTION_LEN}). "
            "TikTok sẽ từ chối."
        )

    if not full_text.strip():
        msg = "Caption rỗng — TikTok có thể flag là low-quality content."
        if allow_empty_caption:
            warnings.append(msg)
        else:
            blockers.append(msg)
    elif len(full_text) < _RECOMMENDED_MIN_LEN:
        warnings.append(
            f"Caption quá ngắn ({len(full_text)} ký tự). Khuyến nghị tối thiểu "
            f"{_RECOMMENDED_MIN_LEN} ký tự để tăng engagement."
        )

    # 2. Emoji-only check
    text_no_spaces = re.sub(r"\s", "", full_text)
    if text_no_spaces and not re.search(r"[A-Za-zÀ-ỹ0-9]", text_no_spaces):
        warnings.append(
            "Caption chỉ chứa emoji/ký tự đặc biệt — TikTok có thể flag là spam."
        )

    # 3. Hashtag count
    hashtags = re.findall(r"#(\w+)", full_text)
    hashtag_count = len(hashtags)

    if hashtag_count > _MAX_HASHTAGS:
        blockers.append(
            f"Quá nhiều hashtag ({hashtag_count}). TikTok flag spam khi >30 hashtag. "
            f"Giảm xuống dưới {_MAX_HASHTAGS}."
        )
    elif hashtag_count > 15:
        warnings.append(
            f"Số hashtag ({hashtag_count}) khá cao. Khuyến nghị 3-5 hashtag liên quan "
            "để TikTok algorithm hoạt động tốt nhất."
        )

    # 4. Generic spam hashtags
    hashtag_lower = [h.lower() for h in hashtags]
    spam_count = sum(1 for h in hashtag_lower if h in _SPAM_HASHTAGS)
    if spam_count >= 3:
        warnings.append(
            f"Phát hiện {spam_count} hashtag chung chung (#fyp, #foryou, #viral...). "
            "TikTok algorithm coi đây là tín hiệu spam yếu. Dùng hashtag chuyên đề "
            "(niche) cụ thể hơn để tăng reach."
        )

    # 5. Excessive repetition (same word 5+ times)
    words = re.findall(r"\w+", full_text.lower())
    if words:
        word_counts: dict[str, int] = {}
        for w in words:
            if len(w) >= 3:   # ignore short words
                word_counts[w] = word_counts.get(w, 0) + 1
        max_repeat = max(word_counts.values()) if word_counts else 0
        if max_repeat >= 5:
            most_common = max(word_counts.items(), key=lambda x: x[1])
            warnings.append(
                f"Từ '{most_common[0]}' lặp lại {most_common[1]} lần. "
                "TikTok có thể flag là keyword stuffing."
            )

    return SpamCheckResult(
        is_blocked = len(blockers) > 0,
        warnings   = warnings,
        blockers   = blockers,
    )


def format_check_result(result: SpamCheckResult) -> str:
    """Format result as human-readable string for logs/dialogs."""
    parts = []
    if result.blockers:
        parts.append("❌ BLOCKED:")
        parts.extend(f"  • {b}" for b in result.blockers)
    if result.warnings:
        if parts:
            parts.append("")
        parts.append("⚠️ Cảnh báo (vẫn cho upload):")
        parts.extend(f"  • {w}" for w in result.warnings)
    if not parts:
        return "✅ Nội dung OK, không có cảnh báo spam."
    return "\n".join(parts)
