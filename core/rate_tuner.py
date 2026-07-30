"""
Adaptive rate tuner — analyses recent history and suggests config adjustments.

Sources:
  • audit_log.jsonl  → success/failure events with timestamps
  • content_history.db → per-target post counts
  • RateLimiter.all_metrics() → per-page wait time + concurrency stats

Goal:
  Read the last N days of activity per target/account and produce a
  recommendation report. Optionally (auto_apply=True) write the suggested
  config keys back; default is "show recommendation only".

Design philosophy:
  • Never silently tighten limits without user opt-in.
  • Loosening (faster) requires high confidence (≥95 % success rate, large
    sample). Tightening (slower) requires only 1-2 failure signals.
  • Operates within USER_DEFINED safety bounds (config keys with "_min" /
    "_max" suffix). The tuner never crosses those bounds.

This is "Phase 3" auto-improvement — the bot learns what works and adjusts.
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional


# ─── Default safety bounds (overridden by user config) ───────────────────────

_DEFAULT_BOUNDS = {
    # base_key: (min_value, max_value)
    "min_interval_per_page_s":         (30, 600),
    "min_inter_page_interval_s":       (0, 1800),
    "max_posts_per_page_per_day":      (1, 50),
    "max_posts_per_account_per_day":   (1, 200),
}


@dataclass
class TargetStats:
    """Per-target activity stats over the analysis window."""
    target:          str
    total_attempts:  int   = 0
    successes:       int   = 0
    failures:        int   = 0
    rate_limit_hits: int   = 0
    abuse_signals:   int   = 0
    timestamps:      list  = field(default_factory=list)  # ISO strings of success events

    @property
    def success_rate(self) -> float:
        return self.successes / self.total_attempts if self.total_attempts else 0.0

    @property
    def has_signal(self) -> bool:
        """True if there's any worrying signal in the window."""
        return self.rate_limit_hits > 0 or self.abuse_signals > 0


@dataclass
class TunerRecommendation:
    """Output of the tuner — what to change and why."""
    target:        str           # account / page name; or "global"
    metric:        str           # config key to adjust
    current_value: float
    suggested:     float
    reason:        str           # human-readable justification
    confidence:    str           # "low" | "medium" | "high"
    direction:     str           # "tighten" | "loosen" | "stay"


# ─── Analysis ────────────────────────────────────────────────────────────────

def parse_audit_log(
    log_path: Optional[str] = None,   # None -> utils.audit_logger.default_log_path()
    *,
    within_days: int = 7,
    platforms:   Iterable[str] = ("facebook", "tiktok"),
) -> dict[str, TargetStats]:
    """Walk the audit log and aggregate per-target stats.

    Returns dict mapping target_id → TargetStats. Empty when log is missing.
    """
    out: dict[str, TargetStats] = {}
    if log_path is None:
        # Cung ly do nhu core/time_intel.py: phai la CHINH file ma
        # utils/audit_logger.py ghi vao, khong phai mot chuoi tuong doi rieng.
        from utils.audit_logger import default_log_path
        log_path = default_log_path()
    if not os.path.exists(log_path):
        return out

    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)
    platforms_set = {p.lower() for p in platforms}

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
                # Only care about FB / TikTok publish-level events
                platform = "facebook" if event.startswith("facebook_") else (
                    "tiktok" if event.startswith("tiktok_") else "")
                if platform not in platforms_set:
                    continue

                ts_str = rec.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    continue
                if ts < cutoff:
                    continue

                target = str(rec.get("open_id", "") or rec.get("display_name", "") or "?")
                s = out.setdefault(target, TargetStats(target=target))

                if event.endswith("_publish_attempt"):
                    s.total_attempts += 1
                elif event.endswith("_publish_success"):
                    s.successes += 1
                    s.timestamps.append(ts_str)
                elif event.endswith("_publish_failure") or event.endswith("_publish_failed"):
                    s.failures += 1
                    err = str(rec.get("error_code", ""))
                    if err in ("4", "17", "32", "613"):
                        s.rate_limit_hits += 1
                    elif err in ("368", "322"):
                        s.abuse_signals += 1
    except OSError:
        pass

    return out


def recommend_adjustments(
    stats:         dict[str, TargetStats],
    current_config: dict,
    *,
    bounds: Optional[dict] = None,
) -> list[TunerRecommendation]:
    """Produce a list of recommendations from per-target stats.

    Rules:
      • abuse_signals > 0 → tighten max_posts_per_page_per_day by 50 % (cap at bound)
      • rate_limit_hits > 0 → tighten min_inter_page_interval_s by +50 %
      • success_rate ≥ 0.97 AND total_attempts ≥ 30 → loosen interval by -10 %
      • Otherwise → stay
    """
    bounds = {**_DEFAULT_BOUNDS, **(bounds or {})}
    recs: list[TunerRecommendation] = []

    def _clamp(key: str, value: float) -> float:
        lo, hi = bounds.get(key, (None, None))
        if lo is not None:
            value = max(lo, value)
        if hi is not None:
            value = min(hi, value)
        return value

    cur_interval     = float(current_config.get("min_inter_page_interval_s", 0) or 0)
    cur_max_per_page = float(current_config.get("max_posts_per_page_per_day", 0) or 0)

    for target, s in stats.items():
        if s.abuse_signals > 0 and cur_max_per_page > 0:
            new = _clamp("max_posts_per_page_per_day", round(cur_max_per_page * 0.5))
            if new < cur_max_per_page:
                recs.append(TunerRecommendation(
                    target=target,
                    metric="max_posts_per_page_per_day",
                    current_value=cur_max_per_page,
                    suggested=new,
                    reason=f"{s.abuse_signals} abuse signal(s) in last window — TIGHTEN",
                    confidence="high",
                    direction="tighten",
                ))

        if s.rate_limit_hits > 0:
            new = _clamp("min_inter_page_interval_s", round(cur_interval * 1.5) or 180)
            if new > cur_interval:
                recs.append(TunerRecommendation(
                    target=target,
                    metric="min_inter_page_interval_s",
                    current_value=cur_interval,
                    suggested=new,
                    reason=f"{s.rate_limit_hits} rate-limit hit(s) — slow down",
                    confidence="medium",
                    direction="tighten",
                ))

        # Loosening: only after 30+ samples with ≥97% success
        if s.total_attempts >= 30 and s.success_rate >= 0.97:
            if cur_interval > bounds["min_inter_page_interval_s"][0]:
                new = _clamp("min_inter_page_interval_s", round(cur_interval * 0.9))
                if new < cur_interval:
                    recs.append(TunerRecommendation(
                        target=target,
                        metric="min_inter_page_interval_s",
                        current_value=cur_interval,
                        suggested=new,
                        reason=f"{s.total_attempts} attempts at {s.success_rate*100:.0f}% — can speed up slightly",
                        confidence="low",
                        direction="loosen",
                    ))

    return recs


def health_summary(stats: dict[str, TargetStats]) -> dict:
    """Aggregate cross-target totals for a one-line health summary."""
    total = sum(s.total_attempts for s in stats.values())
    succ  = sum(s.successes for s in stats.values())
    fail  = sum(s.failures for s in stats.values())
    rate  = (succ / total) if total else 0.0
    abuse_targets = [s.target for s in stats.values() if s.abuse_signals > 0]
    rate_targets  = [s.target for s in stats.values() if s.rate_limit_hits > 0]
    return {
        "total_attempts":   total,
        "successes":        succ,
        "failures":         fail,
        "success_rate":     round(rate, 3),
        "targets_with_abuse_signal":     abuse_targets,
        "targets_with_rate_limit_hit":   rate_targets,
        "n_targets":        len(stats),
    }
