"""
Top-level aggregator used by the GUI dashboard (P4.1).

Gathers data from:
  • RateLimiter.get_global_page_metrics()  — per-page upload counts
  • core.circuit_breaker._default          — breaker state per target
  • core.token_health                      — expiry alerts
  • core.rate_tuner.parse_audit_log        — recent activity
  • core.content_history.get_default_store — total recorded posts

Returns a single dataclass that the Monitor tab renders as a card.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AntiSpamSnapshot:
    """Snapshot of every anti-spam signal for the GUI."""
    # Token health
    n_critical_tokens:   int   = 0
    n_warn_tokens:       int   = 0
    token_messages:      list  = field(default_factory=list)

    # Circuit breaker
    open_breakers:       list  = field(default_factory=list)   # [(target, seconds_remaining)]
    halfopen_breakers:   list  = field(default_factory=list)

    # Activity (last 7 days from audit log)
    total_attempts_7d:   int   = 0
    total_successes_7d:  int   = 0
    success_rate_7d:     float = 0.0
    targets_with_abuse:  list  = field(default_factory=list)
    targets_with_rate:   list  = field(default_factory=list)

    # Content history
    total_content_records: int = 0

    # Recommendations
    recommendations:     list  = field(default_factory=list)   # list of TunerRecommendation

    # GAP-5: Page health (reach throttle detection)
    page_health_warnings: list = field(default_factory=list)   # list[PageHealthReport.message]
    n_pages_throttled:    int  = 0
    n_pages_dead:         int  = 0

    # GAP-5: Time-of-day intelligence
    time_intel_warnings:  list = field(default_factory=list)
    n_bot_flat_targets:   int  = 0

    # Round 2.2 — Phase 5 signals
    meta_app_status:        str  = ""    # "ok" | "disabled" | "suspended" | "unknown"
    meta_app_message:       str  = ""
    meta_app_pool_healthy:  int  = 0    # number of healthy apps in rotation
    meta_app_pool_total:    int  = 0

    # Sprint TT-2.3 — TikTok signals (parallel to FB)
    tiktok_app_status:        str = ""
    tiktok_app_message:       str = ""
    tiktok_client_pool_healthy: int = 0
    tiktok_client_pool_total:   int = 0


def collect_snapshot(current_config: dict) -> AntiSpamSnapshot:
    """Build a fresh AntiSpamSnapshot — safe to call from the GUI thread.
    All sub-systems return empty defaults on failure rather than raising."""
    snap = AntiSpamSnapshot()

    # ── Token health ──────────────────────────────────────────────────────────
    try:
        from core.token_health import (
            TokenHealthLevel,
            all_facebook_reports, all_tiktok_reports,
        )
        for r in all_facebook_reports() + all_tiktok_reports():
            if r.level in (TokenHealthLevel.CRITICAL, TokenHealthLevel.EXPIRED):
                snap.n_critical_tokens += 1
                snap.token_messages.append(r.message)
            elif r.level is TokenHealthLevel.WARN:
                snap.n_warn_tokens += 1
                snap.token_messages.append(r.message)
    except Exception:
        pass

    # ── Circuit breaker ──────────────────────────────────────────────────────
    try:
        from core.circuit_breaker import _default as _cb_singleton
        if _cb_singleton is not None:
            for key, s in _cb_singleton._by_key.items():
                if s.state.value == "open":
                    snap.open_breakers.append(
                        (key, _cb_singleton.seconds_until_allowed(key))
                    )
                elif s.state.value == "half_open":
                    snap.halfopen_breakers.append(key)
    except Exception:
        pass

    # ── Activity (last 7 days) ───────────────────────────────────────────────
    try:
        from core.rate_tuner import (
            health_summary, parse_audit_log, recommend_adjustments,
        )
        stats = parse_audit_log(within_days=7)
        sm = health_summary(stats)
        snap.total_attempts_7d  = sm["total_attempts"]
        snap.total_successes_7d = sm["successes"]
        snap.success_rate_7d    = sm["success_rate"]
        snap.targets_with_abuse = sm["targets_with_abuse_signal"]
        snap.targets_with_rate  = sm["targets_with_rate_limit_hit"]
        # Adjustments
        snap.recommendations = recommend_adjustments(stats, current_config)
    except Exception:
        pass

    # ── Content history total ────────────────────────────────────────────────
    try:
        from core.content_history import get_default_store
        snap.total_content_records = get_default_store().total_count()
    except Exception:
        pass

    # ── Page health (GAP-5) ──────────────────────────────────────────────────
    # Iterates pages in the FB token store and asks page_health for each.
    # Silent on absence: empty list when no token store / no reach samples.
    try:
        from core.page_health import all_page_reports, PageHealthLevel
        for r in all_page_reports():
            if r.level is PageHealthLevel.THROTTLED:
                snap.n_pages_throttled += 1
                snap.page_health_warnings.append(r.message)
            elif r.level is PageHealthLevel.DEAD:
                snap.n_pages_dead += 1
                snap.page_health_warnings.append(r.message)
            elif r.level is PageHealthLevel.SUSPECTED:
                snap.page_health_warnings.append(r.message)
    except Exception:
        pass

    # ── Meta App status + pool health (Round 2.2) ───────────────────────────
    try:
        from core.app_status import check_app_status, AppStatus
        report = check_app_status(current_config)
        snap.meta_app_status  = report.status.value
        snap.meta_app_message = report.message
    except Exception:
        pass
    try:
        from core.multi_app import MetaAppPool
        pool = MetaAppPool.from_config(current_config)
        snap.meta_app_pool_total   = len(pool.records)
        snap.meta_app_pool_healthy = pool.healthy_count()
    except Exception:
        pass

    # Sprint TT-2.3 — TikTok app status + client pool
    try:
        from core.app_status import check_tiktok_app_status
        tt_report = check_tiktok_app_status(current_config)
        snap.tiktok_app_status  = tt_report.status.value
        snap.tiktok_app_message = tt_report.message
    except Exception:
        pass
    try:
        from core.tiktok.multi_client import TikTokClientPool
        tt_pool = TikTokClientPool.from_config(current_config)
        snap.tiktok_client_pool_total   = len(tt_pool.records)
        snap.tiktok_client_pool_healthy = tt_pool.healthy_count()
    except Exception:
        pass

    # ── Time-of-day intelligence (GAP-3) ─────────────────────────────────────
    try:
        from core.time_intel import build_distributions, health_warnings
        tz_offset = 7
        try:
            from zoneinfo import ZoneInfo
            from datetime import datetime as _dt
            tz_offset = int(_dt.now(ZoneInfo(
                current_config.get("timezone", "Asia/Ho_Chi_Minh")
            )).utcoffset().total_seconds() / 3600)
        except Exception:
            pass
        dists = build_distributions(within_days=30, timezone_offset_hours=tz_offset)
        warns = health_warnings(dists)
        snap.time_intel_warnings = warns
        snap.n_bot_flat_targets  = sum(
            1 for d in dists.values() if d.is_bot_flat()
        )
    except Exception:
        pass

    return snap


def format_oneline(snap: AntiSpamSnapshot) -> str:
    """Single-line status for the Monitor header."""
    parts = []
    if snap.meta_app_status in ("disabled", "suspended"):
        parts.append(f"☠️ Meta App {snap.meta_app_status.upper()}")
    if snap.n_critical_tokens > 0:
        parts.append(f"🔴 {snap.n_critical_tokens} token critical")
    if snap.n_pages_dead > 0:
        parts.append(f"☠️ {snap.n_pages_dead} page DEAD")
    if snap.n_pages_throttled > 0:
        parts.append(f"🔻 {snap.n_pages_throttled} page throttled")
    if snap.open_breakers:
        parts.append(f"⏸ {len(snap.open_breakers)} breaker OPEN")
    if snap.targets_with_abuse:
        parts.append(f"🚨 {len(snap.targets_with_abuse)} abuse signal")
    if snap.n_bot_flat_targets > 0:
        parts.append(f"🤖 {snap.n_bot_flat_targets} bot-flat pattern")
    if snap.meta_app_pool_total > 1 and snap.meta_app_pool_healthy == 0:
        parts.append("🚫 multi-app pool: 0 healthy")
    if snap.tiktok_app_status in ("disabled", "suspended"):
        parts.append(f"☠️ TT App {snap.tiktok_app_status.upper()}")
    if snap.tiktok_client_pool_total > 1 and snap.tiktok_client_pool_healthy == 0:
        parts.append("🚫 TT client pool: 0 healthy")
    if not parts:
        return f"✅ Anti-Spam OK ({snap.success_rate_7d*100:.0f}% success last 7d)"
    return " · ".join(parts)
