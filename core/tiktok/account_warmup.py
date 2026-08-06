"""
TikTok account warm-up policy (Sprint TT-1.2).

Why this exists:
  Newly-created TikTok accounts go through a multi-week "trust building"
  phase. Posting at full quota in week 1 = strong page-farm signal and
  often triggers a shadow ban that lasts months. A real creator builds
  organically: 1 post the first day, a few the first week, etc.

Mirrors core/page_warmup.py architecture so the FB and TT pipelines stay
symmetric — same curve shape, different age source.

Data source:
  TikTok Login Kit `/v2/user/info/?fields=open_id,display_name,follower_count`
  doesn't expose account creation time directly. We approximate via the
  audit-log: first time we see this open_id in `tiktok_publish_*` events.
  This is conservative (under-estimates age for accounts that existed
  before the bot did) — but the safe direction.

Cache lifetime: 24h. New accounts age quickly so we re-check daily.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


# None = tu dong giai qua LTT_DATA_DIR luc dung. Dat duong dan cu the de ep buoc.
_CACHE_PATH: Optional[str] = None


def _cache_path() -> str:
    """Nơi lưu cache tuổi tài khoản TikTok, giải qua ranh giới đường dẫn P2."""
    if _CACHE_PATH:
        return _CACHE_PATH
    try:
        from platform_core.runtime_paths import data_path
        return data_path("tiktok_account_age_cache.json")
    except Exception:
        return os.path.join("data", "tiktok_account_age_cache.json")


def _audit_log_path() -> str:
    """Nhật ký kiểm toán — phải là chính file mà utils/audit_logger.py ghi."""
    from utils.audit_logger import default_log_path
    return default_log_path()

# Same warm-up curve shape as page_warmup, slightly stricter (TT shadow-bans
# faster). (max_age_days, recommended_posts_per_day)
_WARMUP_CURVE: list[tuple[int, int]] = [
    (   1, 1),
    (   3, 1),
    (   7, 2),
    (  14, 3),
    (  30, 4),
    (  60, 6),
    (  90, 10),
    (99999, 0),   # mature
]


@dataclass(frozen=True)
class TikTokWarmupAdvice:
    open_id:                 str
    age_days:                int
    recommended_max_per_day: int    # 0 → no warm-up (mature)
    note:                    str


def recommended_cap_for_age(age_days: int) -> int:
    """Return the recommended max-posts-per-day for an account of *age_days*."""
    age_days = max(0, int(age_days))
    for max_age, cap in _WARMUP_CURVE:
        if age_days <= max_age:
            return cap
    return 0


_cache_lock = threading.Lock()
_cache: Optional[dict] = None


def _load_cache() -> dict:
    global _cache
    with _cache_lock:
        if _cache is not None:
            return _cache
        path = _cache_path()
        if not os.path.exists(path):
            _cache = {}
            return _cache
        try:
            with open(path, encoding="utf-8") as f:
                _cache = json.load(f)
                if not isinstance(_cache, dict):
                    _cache = {}
        except (OSError, ValueError):
            _cache = {}
        return _cache


def _save_cache() -> None:
    with _cache_lock:
        if _cache is None:
            return
        path = _cache_path()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(_cache, f, ensure_ascii=False, indent=2)
        except OSError:
            pass


def clear_cache() -> None:
    """Test helper — reset both in-memory and on-disk cache."""
    global _cache
    with _cache_lock:
        _cache = {}
    try:
        path = _cache_path()
        if os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass


def _first_seen_at(open_id: str, log_path: Optional[str] = None) -> Optional[datetime]:
    """Find the earliest timestamp the audit log mentions *open_id*.

    Returns None when the log is missing or the open_id never appeared.
    """
    if log_path is None:
        log_path = _audit_log_path()
    if not os.path.exists(log_path) or not open_id:
        return None
    earliest: Optional[datetime] = None
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (ValueError, json.JSONDecodeError):
                    continue
                if str(rec.get("open_id", "")) != open_id:
                    continue
                ts_str = rec.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    continue
                if earliest is None or ts < earliest:
                    earliest = ts
    except OSError:
        return None
    return earliest


def get_warmup_advice(
    open_id:       str,
    *,
    force_refresh: bool = False,
    audit_log_path: Optional[str] = None,   # None -> audit_logger.default_log_path()
) -> TikTokWarmupAdvice:
    """Return warm-up advice for *open_id*.

    Uses 24h cache; refreshes from audit log when stale.
    """
    cache = _load_cache()
    now = datetime.now(timezone.utc)
    entry = cache.get(open_id)

    if entry and not force_refresh:
        try:
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if (now - cached_at) < timedelta(hours=24):
                first_seen_iso = entry.get("first_seen_at")
                if first_seen_iso:
                    first_seen = datetime.fromisoformat(first_seen_iso)
                    return _build_advice(open_id, first_seen, now)
        except (KeyError, ValueError):
            pass

    first_seen = _first_seen_at(open_id, audit_log_path)
    if first_seen is None:
        # No history → treat as brand-new (conservative)
        return TikTokWarmupAdvice(
            open_id=open_id, age_days=0,
            recommended_max_per_day=recommended_cap_for_age(0),
            note=f"Acc TT '{open_id}' chưa có lịch sử — coi như mới (cap 1/day)",
        )

    cache[open_id] = {
        "first_seen_at": first_seen.isoformat(),
        "cached_at":     now.isoformat(),
    }
    _save_cache()
    return _build_advice(open_id, first_seen, now)


def _build_advice(open_id: str, first_seen: datetime, now: datetime) -> TikTokWarmupAdvice:
    age_days = max(0, (now - first_seen).days)
    cap = recommended_cap_for_age(age_days)
    if cap == 0:
        return TikTokWarmupAdvice(
            open_id=open_id, age_days=age_days,
            recommended_max_per_day=0,
            note=f"Acc TT '{open_id}' {age_days}d tuổi — đã mature",
        )
    return TikTokWarmupAdvice(
        open_id=open_id, age_days=age_days,
        recommended_max_per_day=cap,
        note=f"Acc TT '{open_id}' {age_days}d tuổi → khuyến nghị ≤{cap}/day",
    )


def effective_daily_cap(advice: TikTokWarmupAdvice, user_cap: int) -> int:
    """Combine warm-up advice with user-configured cap (lower wins)."""
    if advice.recommended_max_per_day > 0 and user_cap > 0:
        return min(user_cap, advice.recommended_max_per_day)
    if advice.recommended_max_per_day > 0:
        return advice.recommended_max_per_day
    return user_cap
