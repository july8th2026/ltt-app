"""
Shared utilities for core modules.
Centralises patterns that would otherwise be copy-pasted across files.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Optional


# ─── Concurrency helpers ──────────────────────────────────────────────────────

def interruptible_sleep(stop_event: threading.Event, seconds: float):
    """Sleep that wakes early if stop_event fires. Raises InterruptedError."""
    end = time.time() + seconds
    while time.time() < end:
        if stop_event and stop_event.is_set():
            raise InterruptedError("Dừng bởi người dùng")
        time.sleep(min(0.3, max(0, end - time.time())))


def check_stop(stop_event: threading.Event):
    """Raise InterruptedError if stop_event is set."""
    if stop_event and stop_event.is_set():
        raise InterruptedError("Dừng bởi người dùng")


# ─── Facebook content helpers ─────────────────────────────────────────────────

def build_description(description: str, keywords: str) -> str:
    """Combine description text and comma/space-separated keywords into a single body."""
    parts = [description.strip()] if description.strip() else []
    if keywords.strip():
        tags = " ".join(
            f"#{w.strip().lstrip('#')}"
            for w in keywords.replace(",", " ").split()
            if w.strip()
        )
        if tags:
            parts.append(tags)
    return "\n\n".join(parts)


def parse_schedule(s: str) -> Optional[datetime]:
    """Parse a schedule datetime string in common formats. Returns None on failure."""
    s = s.strip()
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


# ─── Config helpers ───────────────────────────────────────────────────────────

def graph_api_version(config: dict) -> str:
    """Extract graph_api_version from config, defaulting to v21.0."""
    return str(config.get("graph_api_version", "v21.0")).strip() or "v21.0"


# Maps a "shared" config key → its TikTok-prefixed equivalent.
# Used by get_platform_config() so TikTok can have independent rate-limit
# settings while keeping back-compat: a missing/zero tt_* falls back to the
# shared key.
_TIKTOK_OVERRIDE_KEYS: dict[str, str] = {
    "min_interval_per_page_s":         "tt_min_interval_per_account_s",
    "min_inter_page_interval_s":       "tt_min_inter_account_interval_s",
    "jitter_s":                        "tt_jitter_s",
    "active_hours_start":              "tt_active_hours_start",
    "active_hours_end":                "tt_active_hours_end",
    "max_posts_per_page_per_day":      "tt_max_posts_per_account_per_day",
    "max_posts_per_account_per_day":   "tt_max_posts_per_account_per_day",
    "job_delay_seconds":               "tt_job_delay_seconds",
}


def get_platform_config(config: dict, platform: str, base_key: str, default=None):
    """Return the config value for *base_key* scoped to *platform*.

    For platform="tiktok": tries the matching tt_* override first; if empty
    or 0, falls back to the shared base_key value.
    For platform="facebook" (or anything else): returns the base_key value
    directly. This preserves backwards-compat: existing single-platform
    bots see no behaviour change.

    Empty-string ("") and 0 are treated as "unset" so the fallback triggers.
    Use this for rate-limit values where 0 means disabled but the user may
    want to inherit the FB-side setting instead.
    """
    p = (platform or "").strip().lower()
    if p == "tiktok":
        tt_key = _TIKTOK_OVERRIDE_KEYS.get(base_key)
        if tt_key:
            tt_val = config.get(tt_key)
            # Treat "" and 0 as "unset" → fall through to shared key
            if tt_val not in (None, "", 0, 0.0):
                return tt_val
    if default is not None:
        return config.get(base_key, default)
    return config.get(base_key)
