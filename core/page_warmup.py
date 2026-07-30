"""
Page warm-up policy (Phase 3.2).

Why this exists:
  Brand-new Facebook pages (< 30 days old) attract much heavier spam
  scrutiny. Posting at full daily quota immediately after page creation
  is one of the strongest "page-farm" signals — FB has documented this
  in their abuse-prevention research. A real growing page ramps up
  gradually: a few posts the first week, more the second, etc.

This module:
  • Tells the caller the recommended daily cap for a page based on its age.
  • Caches page creation_time so we don't hit the API every check.
  • Caller (sheet_runner / rate_limiter) clamps user-config max_posts_per_page_per_day
    by min(user_value, warmup_recommended) when the page is new.

Cache lifetime: 24 h. Page creation_time never changes so we could cache
forever, but a 24 h refresh covers the edge case of pages that get re-created
under the same ID.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


# ─── Warm-up curve ────────────────────────────────────────────────────────────
# Recommended max posts/day at each age bracket. Approximated from the
# "ramp like a real human" model used by major social-media schedulers.

_WARMUP_CURVE: list[tuple[int, int]] = [
    # (max_age_days, recommended_posts_per_day)
    (   1,  1),    # Day 0:        1 post
    (   3,  1),    # Day 1-3:      1 post/day
    (   7,  2),    # Day 4-7:      2 posts/day
    (  14,  3),    # Day 8-14:     3 posts/day
    (  30,  5),    # Day 15-30:    5 posts/day
    (  60,  8),    # Day 31-60:    8 posts/day
    (  90, 12),    # Day 61-90:   12 posts/day
    (99999, 0),    # > 90 days:    no warm-up cap (use user config)
]


@dataclass(frozen=True)
class WarmupAdvice:
    page_id:                 str
    age_days:                int
    recommended_max_per_day: int    # 0 → no warm-up needed (page is mature)
    note:                    str


# ─── Cache (in-memory + JSON file) ───────────────────────────────────────────

_CACHE_PATH = os.path.join("data", "page_warmup_cache.json")
_cache_lock = threading.Lock()
_cache: Optional[dict] = None


def _load_cache() -> dict:
    """Read the JSON cache file. Returns {} on missing/corrupt."""
    global _cache
    with _cache_lock:
        if _cache is not None:
            return _cache
        if not os.path.exists(_CACHE_PATH):
            _cache = {}
            return _cache
        try:
            with open(_CACHE_PATH, encoding="utf-8") as f:
                _cache = json.load(f)
                if not isinstance(_cache, dict):
                    _cache = {}
        except (OSError, ValueError):
            _cache = {}
        return _cache


def _save_cache():
    with _cache_lock:
        if _cache is None:
            return
        os.makedirs(os.path.dirname(_CACHE_PATH) or ".", exist_ok=True)
        try:
            with open(_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(_cache, f, ensure_ascii=False, indent=2)
        except OSError:
            pass


def clear_cache():
    """Reset both in-memory and on-disk cache. Used by tests."""
    global _cache
    with _cache_lock:
        _cache = {}
    try:
        if os.path.exists(_CACHE_PATH):
            os.unlink(_CACHE_PATH)
    except OSError:
        pass


# ─── Public API ──────────────────────────────────────────────────────────────

def recommended_cap_for_age(age_days: int) -> int:
    """Return the recommended max-posts-per-day for a page of *age_days* age.

    Returns 0 once the page is past the warm-up window — caller should use
    user-configured cap instead.
    """
    age_days = max(0, int(age_days))
    for max_age, cap in _WARMUP_CURVE:
        if age_days <= max_age:
            return cap
    return 0


def _fetch_created_time(graph_client, page_id: str, page_access_token: str) -> Optional[datetime]:
    """Hit Graph API for /{page_id}?fields=created_time. Returns None on fail."""
    try:
        resp = graph_client.get(
            page_id,
            params={"fields": "created_time"},
            token=page_access_token,
        )
        ct = resp.get("created_time", "")
        if not ct:
            return None
        # Graph API returns ISO 8601 with timezone offset
        return datetime.fromisoformat(ct.replace("Z", "+00:00"))
    except Exception:
        return None


def get_warmup_advice(
    page_id:           str,
    *,
    graph_client       = None,
    page_access_token: str = "",
    force_refresh:     bool = False,
) -> WarmupAdvice:
    """Return WarmupAdvice for *page_id*.

    Uses cached page-creation timestamp when available; refreshes from
    Graph API at most once per 24 h. If the API call fails, falls back to
    "0 days old, recommended_max=1" — safest default for an unknown page.

    Caller flow:
        advice = get_warmup_advice(page_id, graph_client=gc, page_access_token=tok)
        user_cap = config.get("max_posts_per_page_per_day", 0)
        effective_cap = (
            min(user_cap, advice.recommended_max_per_day)
            if advice.recommended_max_per_day > 0 and user_cap > 0
            else (user_cap or advice.recommended_max_per_day)
        )
    """
    cache = _load_cache()
    entry = cache.get(page_id)
    now = datetime.now(timezone.utc)

    if entry and not force_refresh:
        cached_at = datetime.fromisoformat(entry.get("cached_at", ""))
        if (now - cached_at) < timedelta(hours=24):
            ct_str = entry.get("created_time")
            if ct_str:
                ct = datetime.fromisoformat(ct_str)
                return _build_advice(page_id, ct, now)

    # Cache miss / stale → fetch
    if graph_client is not None and page_access_token:
        ct = _fetch_created_time(graph_client, page_id, page_access_token)
        if ct is not None:
            cache[page_id] = {
                "created_time": ct.isoformat(),
                "cached_at":    now.isoformat(),
            }
            _save_cache()
            return _build_advice(page_id, ct, now)

    # No client / no data → treat as fully-warm so we don't accidentally
    # block users who don't have read_insights permission. Conservative
    # alternative: assume new page. Choose conservative-but-not-blocking:
    return WarmupAdvice(
        page_id=page_id, age_days=999,
        recommended_max_per_day=0,
        note="No age data available — using user-configured cap",
    )


def _build_advice(page_id: str, created_at: datetime, now: datetime) -> WarmupAdvice:
    age_days = max(0, (now - created_at).days)
    cap = recommended_cap_for_age(age_days)
    if cap == 0:
        return WarmupAdvice(
            page_id=page_id, age_days=age_days,
            recommended_max_per_day=0,
            note=f"Page {age_days} ngày tuổi — đã hết giai đoạn warm-up",
        )
    return WarmupAdvice(
        page_id=page_id, age_days=age_days,
        recommended_max_per_day=cap,
        note=f"Page {age_days} ngày tuổi → khuyến nghị ≤ {cap} post/ngày",
    )


def effective_daily_cap(advice: WarmupAdvice, user_cap: int) -> int:
    """Combine warm-up advice with the user-configured cap.

    Rules:
      • If warm-up gives a cap (>0), the effective cap is min(user_cap, warmup_cap)
        — never weaker than the warm-up recommendation.
      • If warm-up advises "no cap" (0) → use user_cap as-is.
      • If user_cap is 0 (unlimited) but warm-up gives a cap → use warm-up cap.
    """
    if advice.recommended_max_per_day > 0 and user_cap > 0:
        return min(user_cap, advice.recommended_max_per_day)
    if advice.recommended_max_per_day > 0:
        return advice.recommended_max_per_day
    return user_cap
