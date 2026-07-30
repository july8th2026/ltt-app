"""
TikTok client-credentials pool (Sprint TT-1.4).

Mirrors core/multi_app.py (MetaAppPool) so the FB and TT pipelines have
parallel multi-app resilience: when the user's primary TikTok app gets
audit-rejected or suspended, the bot rotates to a healthy fallback app
configured in `tiktok_client_pool`.

A "TT client" here = (client_key, client_secret, redirect_uri) tuple
registered on developers.tiktok.com. Each gets its own audit pipeline,
so this is the legitimate recommended way to scale up production usage.

Schema (in config["tiktok_client_pool"]):
    [{"client_key": "...", "client_secret": "...", "redirect_uri": "...",
      "name": "Primary", "disabled": false, "last_status": "ok",
      "last_check_at": ""}, ...]

Empty pool → fall back to legacy single-client keys (tiktok_client_key /
tiktok_client_secret). Same backward-compat contract as MetaAppPool.
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class TikTokClientRecord:
    """One TikTok app in the rotation pool."""
    client_key:    str
    client_secret: str
    redirect_uri:  str = ""
    name:          str = ""
    disabled:      bool = False
    last_status:   str = "unknown"
    last_check_at: str = ""

    def to_dict(self) -> dict:
        return {
            "client_key":    self.client_key,
            "client_secret": self.client_secret,
            "redirect_uri":  self.redirect_uri,
            "name":          self.name,
            "disabled":      self.disabled,
            "last_status":   self.last_status,
            "last_check_at": self.last_check_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TikTokClientRecord":
        return cls(
            client_key    = str(d.get("client_key",    "")),
            client_secret = str(d.get("client_secret", "")),
            redirect_uri  = str(d.get("redirect_uri",  "")),
            name          = str(d.get("name",          "")),
            disabled      = bool(d.get("disabled",     False)),
            last_status   = str(d.get("last_status",   "unknown")),
            last_check_at = str(d.get("last_check_at", "")),
        )


class TikTokClientPool:
    """Round-robin pool of TikTokClientRecords."""

    def __init__(self, records: Optional[list[TikTokClientRecord]] = None):
        self._records: list[TikTokClientRecord] = list(records or [])
        self._lock = threading.Lock()
        self._rr_iter = None
        self._rebuild_iter()

    def _rebuild_iter(self):
        enabled = [r for r in self._records
                   if not r.disabled and r.client_key and r.client_secret]
        self._rr_iter = itertools.cycle(enabled) if enabled else None

    # ── Public API ──────────────────────────────────────────────────────────

    @property
    def records(self) -> list[TikTokClientRecord]:
        with self._lock:
            return list(self._records)

    def add(self, rec: TikTokClientRecord) -> None:
        with self._lock:
            self._records.append(rec)
            self._rebuild_iter()

    def find(self, client_key: str) -> Optional[TikTokClientRecord]:
        with self._lock:
            for r in self._records:
                if r.client_key == client_key:
                    return r
            return None

    def mark_disabled(self, client_key: str, reason: str = "") -> None:
        with self._lock:
            for r in self._records:
                if r.client_key == client_key:
                    r.disabled    = True
                    r.last_status = f"disabled: {reason}" if reason else "disabled"
                    r.last_check_at = datetime.now(timezone.utc).isoformat()
                    self._rebuild_iter()
                    return

    def mark_healthy(self, client_key: str) -> None:
        with self._lock:
            for r in self._records:
                if r.client_key == client_key:
                    r.disabled    = False
                    r.last_status = "ok"
                    r.last_check_at = datetime.now(timezone.utc).isoformat()
                    self._rebuild_iter()
                    return

    def next_healthy(self) -> Optional[TikTokClientRecord]:
        with self._lock:
            if self._rr_iter is None:
                return None
            try:
                return next(self._rr_iter)
            except StopIteration:
                return None

    def healthy_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._records if not r.disabled)

    # ── Persistence ─────────────────────────────────────────────────────────

    def to_list(self) -> list[dict]:
        return [r.to_dict() for r in self.records]

    @classmethod
    def from_config(cls, config: dict) -> "TikTokClientPool":
        raw = config.get("tiktok_client_pool", [])
        if not isinstance(raw, list):
            raw = []
        # Backward compat: legacy single-client config → 1-element pool.
        if not raw:
            legacy_key = str(config.get("tiktok_client_key", "")).strip()
            legacy_secret = str(config.get("tiktok_client_secret", "")).strip()
            if legacy_key and legacy_secret:
                raw = [{
                    "client_key":    legacy_key,
                    "client_secret": legacy_secret,
                    "redirect_uri":  str(config.get("tiktok_redirect_uri", "")),
                    "name":          "Legacy default TT app",
                }]
        return cls(records=[TikTokClientRecord.from_dict(d) for d in raw])
