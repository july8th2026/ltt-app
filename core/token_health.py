"""
Token health monitor.

Tracks per-account token metadata so the bot can:
  • warn the user before a token expires (proactive reconnect)
  • flag accounts with abnormal refresh patterns (possible compromise)
  • feed the anti-spam dashboard with token status

Sources of truth:
  • FB: AccountInfo.token_expires_at (set during OAuth)
  • TikTok: TikTokAccount.expires_at + refresh_expires_at

This module is read-only against those stores; it does NOT modify tokens.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class TokenHealthLevel(Enum):
    HEALTHY     = "healthy"      # > 14 days remaining
    AGING       = "aging"        # 7-14 days
    WARN        = "warn"         # 2-7 days — user should plan to reconnect
    CRITICAL    = "critical"     # < 48 h — reconnect now
    EXPIRED     = "expired"      # already expired


@dataclass(frozen=True)
class TokenHealthReport:
    """Summary of one account's token state."""
    account_id:    str
    platform:      str           # "facebook" | "tiktok"
    expires_at:    Optional[datetime]
    days_remaining: float        # <0 means already expired
    level:         TokenHealthLevel
    message:       str           # human-readable Vietnamese summary


def assess_expiry(expires_at: Optional[datetime]) -> tuple[TokenHealthLevel, float]:
    """Translate an expiry timestamp into (level, days_remaining)."""
    if expires_at is None:
        return TokenHealthLevel.HEALTHY, 99999.0   # treat "no expiry" as healthy
    now = datetime.now(timezone.utc)
    delta = expires_at - now
    days = delta.total_seconds() / 86400.0
    if days < 0:
        return TokenHealthLevel.EXPIRED,  days
    if days < 2:
        return TokenHealthLevel.CRITICAL, days
    if days < 7:
        return TokenHealthLevel.WARN,     days
    if days < 14:
        return TokenHealthLevel.AGING,    days
    return TokenHealthLevel.HEALTHY,      days


def _parse_iso(s) -> Optional[datetime]:
    """Tolerant ISO-8601 parsing — handles both string and float (unix ts)."""
    if not s:
        return None
    if isinstance(s, (int, float)):
        try:
            return datetime.fromtimestamp(float(s), tz=timezone.utc)
        except (ValueError, OSError):
            return None
    try:
        # ISO with optional trailing Z
        s = str(s).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def report_facebook_account(account) -> TokenHealthReport:
    """Build a TokenHealthReport from a TokenStore AccountInfo."""
    expiry = _parse_iso(getattr(account, "token_expires_at", None))
    level, days = assess_expiry(expiry)
    return TokenHealthReport(
        account_id     = str(getattr(account, "fb_user_id", "") or ""),
        platform       = "facebook",
        expires_at     = expiry,
        days_remaining = round(days, 2),
        level          = level,
        message        = _summary_vi(getattr(account, "name", "?"), level, days),
    )


def report_tiktok_account(account) -> TokenHealthReport:
    """Build a TokenHealthReport from a TikTokAccount."""
    # TikTokAccount.expires_at can be unix timestamp (number) or ISO string
    expiry = _parse_iso(getattr(account, "expires_at", None))
    level, days = assess_expiry(expiry)
    return TokenHealthReport(
        account_id     = str(getattr(account, "open_id", "") or ""),
        platform       = "tiktok",
        expires_at     = expiry,
        days_remaining = round(days, 2),
        level          = level,
        message        = _summary_vi(
            getattr(account, "display_name", "") or getattr(account, "open_id", "?"),
            level, days,
        ),
    )


def _summary_vi(name: str, level: TokenHealthLevel, days: float) -> str:
    if level is TokenHealthLevel.EXPIRED:
        return f"❌ '{name}': token đã hết hạn {-days:.0f} ngày trước — kết nối lại NGAY"
    if level is TokenHealthLevel.CRITICAL:
        return f"🔴 '{name}': token còn {days*24:.0f} giờ — kết nối lại trong hôm nay"
    if level is TokenHealthLevel.WARN:
        return f"🟠 '{name}': token còn {days:.1f} ngày — sắp xếp kết nối lại tuần này"
    if level is TokenHealthLevel.AGING:
        return f"🟡 '{name}': token còn {days:.1f} ngày — bắt đầu để ý"
    return f"🟢 '{name}': token còn {days:.0f} ngày — khoẻ"


# ─── Public helpers used by the GUI / Monitor tab ────────────────────────────

def all_facebook_reports() -> list[TokenHealthReport]:
    """One report per stored FB account. Empty list if no token store."""
    try:
        from core.token_store import get_default_store
        return [report_facebook_account(a) for a in get_default_store().all_accounts()]
    except Exception:
        return []


def all_tiktok_reports() -> list[TokenHealthReport]:
    """One report per stored TikTok account."""
    try:
        from core.tiktok.token_store import TikTokTokenStore
        return [report_tiktok_account(a) for a in TikTokTokenStore().all_accounts()]
    except Exception:
        return []


def critical_or_worse() -> list[TokenHealthReport]:
    """All accounts whose token is at CRITICAL or EXPIRED level. Used by
    the dashboard / Telegram notifier to surface red alerts."""
    out = []
    for r in all_facebook_reports() + all_tiktok_reports():
        if r.level in (TokenHealthLevel.CRITICAL, TokenHealthLevel.EXPIRED):
            out.append(r)
    return out
