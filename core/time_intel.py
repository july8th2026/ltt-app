"""
Time-of-day intelligence (Phase 3.3).

Why this exists:
  Posts at 3am don't just look bad to humans — FB also tracks publish-hour
  distribution. A real Page operator concentrates posts in waking hours
  (peaks at lunch/evening, valleys overnight). A bot that posts every 60
  minutes round the clock has a flat distribution → bot signature.

This module reads audit log success events, builds per-target hourly
histograms, and produces:
  • peak_hours()        — hours that historically work well (highest success / engagement)
  • optimal_distribution() — weighted random hour bias for upcoming posts
  • health_warnings()   — flags pages whose distribution looks "bot-flat"

Used by:
  • rate_tuner: feeds peak-hour insight into recommendations.
  • sheet_runner: optional "next-scheduled-time within active_hours window"
    helper that biases toward peak hours.
"""
from __future__ import annotations

import json
import os
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class HourlyDistribution:
    """Per-target distribution of successful posts across 24 hours."""
    target:       str
    histogram:    list[int] = field(default_factory=lambda: [0] * 24)  # index 0-23
    total:        int       = 0

    @property
    def is_significant(self) -> bool:
        """Need enough samples for stats to mean anything."""
        return self.total >= 20

    def peak_hours(self, n: int = 3) -> list[int]:
        """Return the *n* hours with the highest post-success count."""
        ranked = sorted(range(24), key=lambda h: self.histogram[h], reverse=True)
        return ranked[:n]

    def quiet_hours(self) -> list[int]:
        """Hours with zero posts — bot SHOULD avoid these unless they're nighttime."""
        return [h for h in range(24) if self.histogram[h] == 0]

    def stddev(self) -> float:
        """Standard deviation of the histogram. Higher = more concentrated.
        A flat distribution (stddev ≈ 0) looks bot-like."""
        if not self.total:
            return 0.0
        if len(self.histogram) < 2:
            return 0.0
        return statistics.pstdev(self.histogram)

    def is_bot_flat(self) -> bool:
        """Heuristic: 24-hour-uniform → flat → bot. Threshold tuned for
        ~50 sample histograms — needs more samples for reliable detection."""
        if self.total < 20:
            return False
        mean = self.total / 24.0
        # All bins close to mean → flat
        return self.stddev() < mean * 0.4


# ─── Build from audit log ─────────────────────────────────────────────────────

def build_distributions(
    log_path:     Optional[str] = None,   # None -> utils.audit_logger.default_log_path()
    within_days:  int = 30,
    *,
    timezone_offset_hours: int = 7,    # Asia/Ho_Chi_Minh default
) -> dict[str, HourlyDistribution]:
    """Walk the audit log and bucket each success event by hour-of-day
    (in the user's configured timezone).

    Returns {target → HourlyDistribution}. Empty dict on missing log.
    """
    out: dict[str, HourlyDistribution] = {}
    if log_path is None:
        # Phai la CHINH file ma utils/audit_logger.py ghi vao. Truoc day moi
        # ben tu viet "data/audit_log.jsonl" nen chi can doi thu muc du lieu
        # la ben doc va ben ghi tro vao hai file khac nhau — thong ke rong ma
        # khong co loi nao hien ra.
        from utils.audit_logger import default_log_path
        log_path = default_log_path()
    if not os.path.exists(log_path):
        return out

    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)
    tz_delta = timedelta(hours=timezone_offset_hours)

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
                event = str(rec.get("event", ""))
                if not (event == "facebook_publish_success"
                        or event == "tiktok_publish_success"):
                    continue
                ts_str = rec.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    continue
                if ts < cutoff:
                    continue
                target = str(rec.get("open_id", "") or rec.get("display_name", "") or "?")
                d = out.setdefault(target, HourlyDistribution(target=target))
                local_hour = (ts + tz_delta).hour
                d.histogram[local_hour] += 1
                d.total += 1
    except OSError:
        pass

    return out


# ─── Recommendations ─────────────────────────────────────────────────────────

def weighted_peak_hours(dist: HourlyDistribution) -> list[int]:
    """Return all hours where post count is ≥ mean + 0.5 × stddev — these
    are the "above-average" hours suitable for scheduling new posts."""
    if dist.total < 10:
        return list(range(8, 23))   # fallback: business hours
    mean = dist.total / 24.0
    threshold = mean + 0.5 * dist.stddev()
    return [h for h in range(24) if dist.histogram[h] >= threshold]


def pick_post_hour(
    dist: HourlyDistribution,
    *,
    active_hours: Optional[tuple[int, int]] = None,
    rng: Optional[random.Random] = None,
) -> int:
    """Pick a single hour for the next post.

    Strategy:
      • If we have a significant distribution → weighted random over the
        histogram (so peaks attract more posts but valleys aren't zero).
      • If not significant → uniform random over the active window
        (default 8-22).
    """
    rng = rng or random.Random()

    if active_hours is not None:
        start, end = active_hours
        # Build the list of allowed hours
        if start < end:
            allowed = list(range(start, end))
        elif start == end:
            allowed = list(range(24))
        else:
            allowed = list(range(start, 24)) + list(range(0, end))
    else:
        allowed = list(range(8, 22))

    if not allowed:
        allowed = list(range(24))

    if dist.is_significant:
        weights = [max(1, dist.histogram[h]) for h in allowed]
        return rng.choices(allowed, weights=weights, k=1)[0]
    return rng.choice(allowed)


def health_warnings(dists: dict[str, HourlyDistribution]) -> list[str]:
    """Return a list of human-readable warnings about post-time patterns."""
    out = []
    for target, d in dists.items():
        if d.is_bot_flat():
            out.append(
                f"🟠 '{target}': lịch post quá đều ({d.total} post, σ={d.stddev():.1f}) "
                f"— FB có thể phát hiện pattern. Xem xét tăng jitter."
            )
        # Posts trong khung 1h-5h sáng có vẻ đáng ngờ
        night_total = sum(d.histogram[h] for h in range(1, 6))
        if d.total >= 20 and night_total / d.total > 0.25:
            out.append(
                f"🟡 '{target}': {night_total}/{d.total} post trong khung 1-5h sáng "
                f"— nghi pattern automation."
            )
    return out
