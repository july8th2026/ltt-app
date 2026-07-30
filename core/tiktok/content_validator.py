"""
TikTok caption + hashtag policy enforcer (Sprint TT-5 / F6).

Validates the text side of a TikTok post BEFORE upload:
  • Caption ≤ 2200 chars (TT hard limit)
  • Hashtag count: 0-30 allowed; 1-10 is sweet spot for organic reach
  • No banned hashtags (small built-in blacklist; user can extend via config)
  • No URL link in caption (TT auto-strips them; mark visually as warning)
  • No emoji-only caption (TT flags low-quality)
  • No CAPSLOCK-only caption (also low-quality flag)

Returns ContentReport so the GUI / compliance guard can decide fail/warn.

Keep this module pure-Python, no API calls — it runs offline before any
upload attempt and is fully unit-testable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


# TT documented caption max — 2200 chars including spaces, hashtags, mentions.
_MAX_CAPTION_CHARS = 2200
# TT documented hashtag limit (not strictly enforced but flagged by their
# spam detector). Going > 30 hashtags is the strongest "tag stuffing" signal.
_MAX_HASHTAGS      = 30
_RECOMMENDED_HASHTAG_RANGE = (1, 10)

# Built-in blacklist of hashtags TT bans / shadow-bans (rotating list, growing).
# Source: community-maintained — user can extend via config["tiktok_banned_hashtags"].
_BUILTIN_BANNED_HASHTAGS = {
    # generic spam / NSFW / scam
    "fyp",     # ironic: too generic to help; also viewed as begging-for-reach
    "foryou",  # same
    "viral",
    "f4f", "follow4follow", "followforfollow",
    "sub4sub",
    "freemoney", "easymoney",
    "weightloss",   # often flagged in health-related contexts
    "diet",         # likewise
    # well-known TT bans
    "tagcloud",
    "couplegoals",   # often-banned for unspecified reasons
}

_HASHTAG_RE = re.compile(r"#([\w\-_À-ỹ]+)", re.UNICODE)
_URL_RE     = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


class CheckResult(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ContentCheckItem:
    name:     str
    result:   CheckResult
    message:  str
    fix_hint: str = ""


@dataclass
class ContentReport:
    caption:        str
    char_count:     int = 0
    hashtag_count:  int = 0
    hashtags:       list = field(default_factory=list)
    items:          list[ContentCheckItem] = field(default_factory=list)

    @property
    def fail_count(self) -> int:
        return sum(1 for i in self.items if i.result is CheckResult.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for i in self.items if i.result is CheckResult.WARN)

    @property
    def ready_to_upload(self) -> bool:
        return self.fail_count == 0

    def summary(self) -> str:
        if self.ready_to_upload and self.warn_count == 0:
            return "✅ Caption OK"
        if self.ready_to_upload:
            return f"🟡 {self.warn_count} warning(s) — không block upload"
        return f"❌ {self.fail_count} blocking — sửa caption trước upload"


# ─── Public API ──────────────────────────────────────────────────────────────

def validate_content(
    caption:     str,
    *,
    extra_banned: set = None,
) -> ContentReport:
    """Validate a TikTok caption string. Returns ContentReport."""
    caption = (caption or "").strip()
    rep = ContentReport(caption=caption, char_count=len(caption))

    # Build the effective banlist
    banned = set(_BUILTIN_BANNED_HASHTAGS)
    if extra_banned:
        banned |= {h.lower().lstrip("#") for h in extra_banned}

    # Hashtag extraction (case-insensitive comparison)
    hashtags = [h.lower() for h in _HASHTAG_RE.findall(caption)]
    rep.hashtags = hashtags
    rep.hashtag_count = len(hashtags)

    # ── Check 1: caption length ──────────────────────────────────────────
    if rep.char_count == 0:
        rep.items.append(ContentCheckItem(
            "Length", CheckResult.WARN,
            "Caption rỗng — TT flag low-quality",
            "Thêm caption mô tả nội dung",
        ))
    elif rep.char_count > _MAX_CAPTION_CHARS:
        rep.items.append(ContentCheckItem(
            "Length", CheckResult.FAIL,
            f"Caption {rep.char_count} chars > {_MAX_CAPTION_CHARS} max",
            f"Rút gọn xuống ≤ {_MAX_CAPTION_CHARS} chars",
        ))
    else:
        rep.items.append(ContentCheckItem(
            "Length", CheckResult.PASS,
            f"{rep.char_count}/{_MAX_CAPTION_CHARS} chars", "",
        ))

    # ── Check 2: hashtag count ───────────────────────────────────────────
    if rep.hashtag_count > _MAX_HASHTAGS:
        rep.items.append(ContentCheckItem(
            "Hashtags", CheckResult.FAIL,
            f"{rep.hashtag_count} hashtags > {_MAX_HASHTAGS} max — TT flag tag stuffing",
            "Giảm số hashtag",
        ))
    elif rep.hashtag_count == 0:
        rep.items.append(ContentCheckItem(
            "Hashtags", CheckResult.WARN,
            "Không có hashtag — giảm discovery",
            "Thêm 1-5 hashtag phù hợp nội dung",
        ))
    elif rep.hashtag_count > _RECOMMENDED_HASHTAG_RANGE[1]:
        rep.items.append(ContentCheckItem(
            "Hashtags", CheckResult.WARN,
            f"{rep.hashtag_count} hashtags — recommend ≤ "
            f"{_RECOMMENDED_HASHTAG_RANGE[1]} để tối ưu",
            "Giữ 1-10 hashtag chất lượng",
        ))
    else:
        rep.items.append(ContentCheckItem(
            "Hashtags", CheckResult.PASS,
            f"{rep.hashtag_count} hashtags (range tối ưu)", "",
        ))

    # ── Check 3: banned hashtags ─────────────────────────────────────────
    flagged = [h for h in hashtags if h in banned]
    if flagged:
        rep.items.append(ContentCheckItem(
            "Banned hashtags", CheckResult.FAIL,
            f"Hashtag bị TT shadow-ban / flag: {', '.join('#' + h for h in flagged[:5])}",
            "Xoá hoặc thay hashtag khác",
        ))
    else:
        rep.items.append(ContentCheckItem(
            "Banned hashtags", CheckResult.PASS,
            "Không có hashtag trong banlist", "",
        ))

    # ── Check 4: URL in caption ──────────────────────────────────────────
    urls = _URL_RE.findall(caption)
    if urls:
        rep.items.append(ContentCheckItem(
            "URL in caption", CheckResult.WARN,
            f"{len(urls)} URL trong caption — TT thường auto-strip / giảm reach",
            "Move link xuống bio thay vì caption",
        ))
    else:
        rep.items.append(ContentCheckItem(
            "URL in caption", CheckResult.PASS, "Không có URL", "",
        ))

    # ── Check 5: emoji-only / CAPSLOCK ──────────────────────────────────
    stripped = _HASHTAG_RE.sub("", caption)
    stripped = _URL_RE.sub("", stripped)
    letters = sum(1 for c in stripped if c.isalpha())
    if rep.char_count > 0 and letters == 0:
        rep.items.append(ContentCheckItem(
            "Text content", CheckResult.WARN,
            "Caption không có chữ (emoji-only) — TT flag low-quality",
            "Thêm ≥1 câu mô tả",
        ))
    elif letters > 0 and stripped.replace(" ", "").isupper():
        rep.items.append(ContentCheckItem(
            "Text content", CheckResult.WARN,
            "Caption ALL CAPS — TT giảm reach",
            "Dùng case bình thường, viết hoa chữ đầu câu",
        ))
    else:
        if rep.char_count > 0:
            rep.items.append(ContentCheckItem(
                "Text content", CheckResult.PASS,
                f"{letters} ký tự chữ", "",
            ))

    return rep
