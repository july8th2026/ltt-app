"""
Adaptive backoff strategy mapped to Facebook Graph API error codes.

Why this exists:
  The existing chunk-retry in graph_uploader uses LINEAR backoff (5s, 10s,
  15s). That's fine for transient network errors but wrong for FB's deliberate
  throttling: when you get error 4/17 (rate limit), retrying every 5 s tells
  FB "this bot doesn't listen" → escalates to error 32 (page-suspended) →
  account-level limit. Each FB error code has a recommended cool-down range.

This module maps error → (cooldown_seconds, escalation_level) and exposes a
single helper, get_backoff_for_fb_error(), that the publisher pipeline can
consult to decide how long to wait before the next attempt.

Reference: https://developers.facebook.com/docs/graph-api/guides/error-handling
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class BackoffPolicy:
    """Result of consulting the FB error code map.

    cooldown_s   — recommended seconds to wait before retrying. Includes a
                   small random jitter to avoid synchronized retries across
                   parallel workers.
    severity     — "transient" | "rate" | "abuse" | "permanent"
    retryable    — False for permanent errors (token revoked etc.). Caller
                   must NOT retry these — escalate to the user.
    notify_user  — True when the user should be told (via Telegram / GUI).
    """
    cooldown_s:   float
    severity:     str
    retryable:    bool
    notify_user:  bool
    description:  str


# Error code → BackoffPolicy. Codes not in the map fall through to the default.
_BACKOFF_MAP: dict[int, BackoffPolicy] = {
    # ─── Permanent / non-retryable ─────────────────────────────────────────
    190: BackoffPolicy(0,    "permanent", False, True,
                       "Token expired/invalid — user must reconnect"),
    102: BackoffPolicy(0,    "permanent", False, True,
                       "Session expired — user must reconnect"),
    200: BackoffPolicy(0,    "permanent", False, True,
                       "Missing scope/permission — user re-grant during OAuth"),
    104: BackoffPolicy(0,    "permanent", False, True,
                       "Token missing"),
    10:  BackoffPolicy(0,    "permanent", False, True,
                       "App lacks the required permission"),
    230: BackoffPolicy(0,    "permanent", False, True,
                       "User blocked the app"),

    # ─── Rate-limit errors (retryable with significant cool-down) ──────────
    # FB rate limits reset every hour on the hour. Use 30 m cool-down so
    # we land safely in the next window with margin.
    4:   BackoffPolicy(1800,  "rate", True, False,
                       "App-level API rate limit (4)"),
    17:  BackoffPolicy(3600,  "rate", True, True,
                       "User-level rate limit (17) — > 1 h cool-down"),
    32:  BackoffPolicy(7200,  "rate", True, True,
                       "Page-level rate limit (32) — page throttled"),
    613: BackoffPolicy(3600,  "rate", True, True,
                       "App-level rate limit (613)"),

    # ─── Abuse / spam markers — long cool-down, alert user ─────────────────
    # 368 = "page suspended for spam". This is the FB signal that says
    # "stop posting to this page right now, we're watching". 24 h is the
    # conservative minimum cool-down recommended by FB community docs.
    368: BackoffPolicy(86400, "abuse", True, True,
                       "PAGE TEMPORARILY BLOCKED (368) — stop for 24 h"),
    322: BackoffPolicy(21600, "abuse", True, True,
                       "Content quality block (322) — 6 h cool-down"),

    # ─── Transient / connectivity (short backoff) ──────────────────────────
    1:   BackoffPolicy(30,    "transient", True, False,
                       "Unknown / transient error (1)"),
    2:   BackoffPolicy(60,    "transient", True, False,
                       "Temporary issue (2)"),
    # HTTP 5xx style — pass them through as transient
    500: BackoffPolicy(120,   "transient", True, False, "FB server error 500"),
    503: BackoffPolicy(180,   "transient", True, False, "FB unavailable 503"),

    # ─── Video-specific errors (mostly permanent — file is bad) ────────────
    100:   BackoffPolicy(0,    "permanent", False, True,
                         "Invalid parameter (100) — usually wrong video URL/format"),
    6000:  BackoffPolicy(0,    "permanent", False, True,
                         "Video format not supported (6000)"),
    6001:  BackoffPolicy(0,    "permanent", False, True,
                         "Video too large (6001)"),
    6002:  BackoffPolicy(0,    "permanent", False, True,
                         "Video corrupt (6002)"),
}


# Default policy used for any error code not explicitly listed.
_DEFAULT = BackoffPolicy(
    cooldown_s=60, severity="transient", retryable=True, notify_user=False,
    description="Unmapped error — default 60 s cool-down",
)


# ─── TikTok error code policies (string codes, not numeric) ─────────────────
# TikTok Content Posting API uses string error codes. Map → policy mirrors
# the FB layout. Used by TikTokPublisher / status_poller via get_backoff_for_tiktok_error.
#
# Reference: https://developers.tiktok.com/doc/content-posting-api-reference-errors

_TIKTOK_BACKOFF_MAP: dict[str, BackoffPolicy] = {
    # Permanent / non-retryable
    "access_token_invalid":     BackoffPolicy(0, "permanent", False, True,
                                              "Token TikTok hết hạn — reconnect"),
    "access_token_expired":     BackoffPolicy(0, "permanent", False, True,
                                              "Token TikTok expired"),
    "scope_not_authorized":     BackoffPolicy(0, "permanent", False, True,
                                              "Thiếu scope — reconnect với scope mới"),
    "invalid_param":            BackoffPolicy(0, "permanent", False, True,
                                              "Param sai — kiểm tra task"),
    "url_ownership_unverified": BackoffPolicy(0, "permanent", False, True,
                                              "Domain chưa verify trên TT portal"),
    "privacy_level_option_mismatch": BackoffPolicy(0, "permanent", False, True,
                                              "App chưa audit — phải dùng SELF_ONLY"),
    "video_pull_failed":        BackoffPolicy(0, "permanent", False, True,
                                              "TT không tải được video — check format"),
    "unaudited_client_can_only_post_to_private_accounts": BackoffPolicy(
                                              0, "permanent", False, True,
                                              "Acc privacy phải private trước khi audit"),
    "auto_cleanup_frame_rate":  BackoffPolicy(0, "permanent", False, True,
                                              "Frame rate không hỗ trợ"),
    "auto_cleanup_duration":    BackoffPolicy(0, "permanent", False, True,
                                              "Video duration không hỗ trợ"),
    "auto_cleanup_size":        BackoffPolicy(0, "permanent", False, True,
                                              "Video size không hỗ trợ"),

    # Rate-limit (long cooldown)
    "rate_limit_exceeded":      BackoffPolicy(3600, "rate", True, True,
                                              "TT rate limit — 1h cooldown"),
    "daily_publish_cap_exceeded": BackoffPolicy(86400, "rate", True, True,
                                              "Daily cap acc — 24h cooldown"),

    # Abuse / spam — long + notify
    "spam_risk_text":           BackoffPolicy(21600, "abuse", True, True,
                                              "Caption flagged spam — review content"),
    "spam_risk_user_banned_from_posting": BackoffPolicy(86400, "abuse", True, True,
                                              "User TẠM CẤM POST — 24h cooldown"),
    "spam_risk_too_many_posts": BackoffPolicy(86400, "abuse", True, True,
                                              "Quá nhiều post — 24h cooldown"),

    # Transient (short cooldown)
    "internal_error":           BackoffPolicy(120, "transient", True, False,
                                              "TT internal — short retry"),
    "network_error":            BackoffPolicy(60,  "transient", True, False,
                                              "Network blip"),
    "publish_id_not_found":     BackoffPolicy(60,  "transient", True, False,
                                              "Status poll race — short retry"),
}


def get_backoff_for_tiktok_error(code: str, *, jitter: bool = True) -> BackoffPolicy:
    """Return the backoff policy for a TikTok API error string code.

    Falls back to the default (60 s transient) when *code* isn't recognised.
    Mirrors get_backoff_for_fb_error() for FB so both platforms have parallel
    error-handling semantics.
    """
    key = (code or "").strip().lower()
    p = _TIKTOK_BACKOFF_MAP.get(key, _DEFAULT)
    if jitter and p.cooldown_s > 0:
        factor = random.uniform(0.85, 1.15)
        p = BackoffPolicy(
            cooldown_s   = round(p.cooldown_s * factor, 1),
            severity     = p.severity,
            retryable    = p.retryable,
            notify_user  = p.notify_user,
            description  = p.description,
        )
    return p


def is_tiktok_abuse_signal(code: str) -> bool:
    return get_backoff_for_tiktok_error(code, jitter=False).severity == "abuse"


def is_tiktok_permanent(code: str) -> bool:
    return not get_backoff_for_tiktok_error(code, jitter=False).retryable


def get_backoff_for_fb_error(code: int, *, subcode: int = 0, jitter: bool = True) -> BackoffPolicy:
    """Return the backoff policy for a Facebook Graph error code.

    Falls back to the default (60 s transient) when *code* is not in the map.
    If *jitter* is True (the default), the cooldown is multiplied by a
    random factor in [0.85, 1.15] — anti-synchronization for parallel workers.
    """
    # Subcode lookup first: some errors are disambiguated only via subcode
    # (e.g. 100 / 1366046 = malformed URL specifically). For now we only
    # look up by primary code.
    p = _BACKOFF_MAP.get(int(code), _DEFAULT)
    if jitter and p.cooldown_s > 0:
        factor = random.uniform(0.85, 1.15)
        p = BackoffPolicy(
            cooldown_s   = round(p.cooldown_s * factor, 1),
            severity     = p.severity,
            retryable    = p.retryable,
            notify_user  = p.notify_user,
            description  = p.description,
        )
    return p


def is_rate_limit_error(code: int) -> bool:
    """True if *code* is one of FB's rate-limit responses."""
    return get_backoff_for_fb_error(code, jitter=False).severity == "rate"


def is_abuse_signal(code: int) -> bool:
    """True if *code* indicates FB has flagged the account/page for abuse."""
    return get_backoff_for_fb_error(code, jitter=False).severity == "abuse"


def is_permanent(code: int) -> bool:
    """True if retrying *code* will keep failing without user action."""
    return not get_backoff_for_fb_error(code, jitter=False).retryable
