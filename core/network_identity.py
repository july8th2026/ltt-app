"""
Network identity diversity (Sprint C).

Why this exists:
  Every HTTP request the bot makes leaks an identity:
    • User-Agent string (default `python-requests/X.Y` is a CLEAR bot signal)
    • TLS fingerprint (Python's ssl module has a stable JA3)
    • Source IP (single residential/datacenter IP per machine)

  Real Facebook traffic is dominated by mobile apps (Android/iOS) using
  recent Chrome/Webview versions. Sending `python-requests/2.31` while
  pretending to be a regular user is a free signal we can fix.

This module provides:
  1. A rotating pool of mobile-ish User-Agents per account.
  2. Optional HTTPS proxy injection (user-supplied list — bot doesn't
     bundle proxies).
  3. Wrappers that GraphClient consumes when constructing requests.

What this module DOES NOT do:
  • Spoof TLS fingerprint — that requires a non-standard HTTP library
    (curl_cffi) which adds a binary dependency. Documented as a future
    upgrade in HANDOFF.md.
  • Spoof browser fingerprint (canvas / WebGL) — N/A for API-only bot.

Default behaviour is OPT-IN: with no config, the module is a no-op so
existing users see zero change.
"""
from __future__ import annotations

import hashlib
import random
import threading
from dataclasses import dataclass
from typing import Optional


# ─── Realistic mobile UAs (sampled from 2025 traffic) ────────────────────────

_MOBILE_UAS: list[str] = [
    # iPhone Safari + FB embedded webview shapes
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    # Android Chrome — Pixel + Samsung
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S928U) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Mobile Safari/537.36",
    # Desktop Chrome (some FB users are desktop)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36",
]


@dataclass(frozen=True)
class NetworkIdentity:
    """The HTTP-layer identity assigned to one account's requests.

    user_agent: the User-Agent header to send.
    proxy:      optional "http://user:pass@host:port" — applied to all HTTP/HTTPS.
    """
    user_agent: str
    proxy:      str = ""


class NetworkIdentityProvider:
    """Returns a deterministic NetworkIdentity per account_id.

    Determinism is important — we don't want the bot to rotate UAs mid-
    session because that itself is a fingerprint. One UA per account,
    stable across restarts.
    """

    def __init__(self, config: dict):
        self._config = config
        self._lock   = threading.Lock()
        self._cache: dict[str, NetworkIdentity] = {}

    def identity_for(self, account_id: str) -> NetworkIdentity:
        if not self._is_enabled():
            return self._noop_identity()
        with self._lock:
            cached = self._cache.get(account_id)
            if cached is not None:
                return cached
            ident = self._build(account_id)
            self._cache[account_id] = ident
            return ident

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    # ── Internals ────────────────────────────────────────────────────────

    def _is_enabled(self) -> bool:
        return bool(self._config.get("network_identity_enabled", False))

    def _noop_identity(self) -> NetworkIdentity:
        return NetworkIdentity(user_agent="", proxy="")

    def _build(self, account_id: str) -> NetworkIdentity:
        # Custom pool from config wins; otherwise use built-in defaults.
        uas = self._config.get("network_user_agents") or _MOBILE_UAS
        proxies = self._config.get("network_proxies") or []

        seed = int.from_bytes(hashlib.sha256(account_id.encode("utf-8")).digest()[:8], "big")
        rng = random.Random(seed)
        ua = rng.choice(uas) if uas else ""
        proxy = rng.choice(proxies) if proxies else ""
        return NetworkIdentity(user_agent=ua, proxy=proxy)


# ─── Singleton accessor ──────────────────────────────────────────────────────

_default_provider: Optional[NetworkIdentityProvider] = None
_default_lock     = threading.Lock()


def get_default_provider(config: Optional[dict] = None) -> NetworkIdentityProvider:
    """Process-wide singleton. Pass config on first call to initialise."""
    global _default_provider
    with _default_lock:
        if _default_provider is None:
            _default_provider = NetworkIdentityProvider(config or {})
        return _default_provider


def reset_default_provider() -> None:
    """Test helper — force the singleton to rebuild on next access."""
    global _default_provider
    with _default_lock:
        _default_provider = None
