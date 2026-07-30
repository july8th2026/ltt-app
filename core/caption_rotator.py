"""
Caption auto-rotation engine (Sprint A1).

Why this exists:
  Uploading the same video to 20 pages with identical captions = textbook
  page-farm signal. FB's text-similarity model flags duplicate captions
  even when videos differ slightly. The fix is content-side variation —
  generate a unique caption for each upload from a small template grammar.

Strategy: token-rotation grammar
  Each caption template is a string with {variable} placeholders. The
  rotator picks a value from the corresponding word-pool for each var,
  using a stable PRNG seeded on (target_id, video_hash, day) so reposts
  to the same target on the same day produce the SAME caption (idempotent),
  while different targets / different videos get different captions.

Example template:
    "{greeting} {emoji_open} Xem video mới {topic_phrase} {emoji_close}
     #{hashtag_main} #{hashtag_secondary}"

Pool entries are user-supplied via config or default pool.

This module is OFFLINE — no API calls. Safe to invoke from sheet_runner
right before publish.
"""
from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ─── Default pools ──────────────────────────────────────────────────────────
# Conservative, neutral Vietnamese-leaning pools. Power users override via
# config["caption_rotator_pools"] = {"greeting": [...], ...}.

_DEFAULT_POOLS: dict[str, list[str]] = {
    "greeting":     ["Chào bạn", "Hi cả nhà", "Xin chào",
                     "Hello mọi người", "Hôm nay rồi"],
    "emoji_open":   ["🌟", "✨", "🔥", "💫", "⭐", "🌸", "🎉", "👀"],
    "emoji_close":  ["💖", "🙌", "👇", "🎬", "📌", "✅", "💯"],
    "cta":          ["Đừng quên like + share nhé!", "Bấm theo dõi để xem nhiều hơn",
                     "Để lại 1 ❤ nếu bạn thích", "Chia sẻ cho bạn bè cùng xem",
                     "Comment ý kiến của bạn 👇"],
    "transition":   ["Đặc biệt là", "Đáng chú ý nhất", "Phải nói rằng",
                     "Thú vị nhất là", "Ấn tượng nhất"],
    "filler":       ["nhé", "nha", "ạ", "đó", "luôn"],
}


@dataclass
class CaptionRotationConfig:
    """Settings consumed by CaptionRotator."""
    pools:           dict[str, list[str]] = field(default_factory=dict)
    templates:       list[str] = field(default_factory=list)
    keep_original:   bool = True   # If True, original caption is one of the templates

    @classmethod
    def from_app_config(cls, config: dict) -> "CaptionRotationConfig":
        """Build from the global config dict."""
        return cls(
            pools         = dict(_DEFAULT_POOLS,
                                  **(config.get("caption_rotator_pools", {}) or {})),
            templates     = list(config.get("caption_rotator_templates", []) or []),
            keep_original = bool(config.get("caption_rotator_keep_original", True)),
        )


class CaptionRotator:
    """Produces deterministic per-(target,video,day) caption variants.

    Determinism matters: if a row is retried, we must produce the SAME
    caption — otherwise the second attempt looks like a new post even
    though it's a retry, and FB's dedup would flag it.
    """

    _VAR_PATTERN = re.compile(r"\{(\w+)\}")

    def __init__(self, cfg: Optional[CaptionRotationConfig] = None):
        self.cfg = cfg or CaptionRotationConfig(pools=dict(_DEFAULT_POOLS))

    def variant_for(
        self,
        original_caption: str,
        *,
        target_id:  str,
        video_hash: str = "",
        day_key:    str = "",
    ) -> str:
        """Return a varied caption for this (target, video, day) tuple.

        If no templates configured and keep_original=True → return original
        unchanged. If templates available → pick one deterministically and
        fill {var} placeholders from pools.
        """
        if day_key == "":
            day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Choose a template — if keep_original, the original itself is in
        # the pool of choices so unchanged-text is one of the possible outputs.
        candidates = list(self.cfg.templates or [])
        if self.cfg.keep_original and original_caption.strip():
            candidates.append(original_caption)
        if not candidates:
            return original_caption

        rng = self._rng_for(target_id, video_hash, day_key)
        template = rng.choice(candidates)

        # Fill placeholders with deterministic picks from pools.
        # Special placeholder: {body} → injects the user-provided original_caption.
        # This lets templates *wrap* the user's caption with rotating intro/cta/hashtags
        # rather than *replacing* it. Pool entry named "body" takes precedence if
        # explicitly configured (advanced override).
        def replace(match):
            name = match.group(1)
            if name == "body" and "body" not in self.cfg.pools:
                # Auto-inject the caller's original caption when template uses {body}
                return original_caption
            pool = self.cfg.pools.get(name, [])
            if not pool:
                return match.group(0)   # leave unfilled {var}
            # Sub-rng to keep variable picks stable across multiple {var}
            return rng.choice(pool)

        return self._VAR_PATTERN.sub(replace, template)

    def _rng_for(self, target_id: str, video_hash: str, day_key: str) -> random.Random:
        seed_str = f"{target_id}|{video_hash}|{day_key}"
        h = hashlib.sha256(seed_str.encode("utf-8")).digest()
        seed = int.from_bytes(h[:8], "big")
        return random.Random(seed)

    # ── Sanity: caption text similarity check (used for cross-target warn) ──

    @staticmethod
    def similarity(a: str, b: str) -> float:
        """Cheap Jaccard similarity on token sets (lower-case, alpha only).

        Returns a value in [0.0, 1.0]. 1.0 = identical, 0.0 = no overlap.
        Useful to flag captions that are "too similar across targets".
        """
        toks_a = set(re.findall(r"[a-zA-ZÀ-ỹ]+", (a or "").lower()))
        toks_b = set(re.findall(r"[a-zA-ZÀ-ỹ]+", (b or "").lower()))
        if not toks_a or not toks_b:
            return 0.0
        inter = toks_a & toks_b
        union = toks_a | toks_b
        return len(inter) / len(union)
