"""
Multi-Meta-App rotation (Sprint B1).

Why this exists:
  If your bot ships with ONE Meta App ID and that app gets banned
  (TOS violation, mistaken suspension, app review denied) your bot is
  100 % offline until you reconfigure. With multiple apps registered
  to YOUR account, the bot can rotate to a healthy fallback automatically.

Architecture:
  • Settings stores a LIST of (app_id, app_secret, redirect_uri) tuples.
  • Each FB account in TokenStore is tagged with which app_id its tokens
    were issued against (already set during OAuth).
  • For NEW OAuth, pick a healthy app from the pool using a round-robin
    or least-used policy.
  • If an app fails check_app_status() → mark it disabled in the pool;
    refuse to use it for new OAuth until a manual re-check.

This module ONLY manages the app pool. Token storage continues to live
in core/token_store.py — that schema already supports per-account app_id
recording via the AccountInfo.meta_app_id field (if not present, we'll
add it during the wiring step).
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class MetaAppRecord:
    """One Meta App in the rotation pool."""
    app_id:        str
    app_secret:    str
    redirect_uri:  str = ""
    name:          str = ""    # optional human-readable label
    disabled:      bool = False
    last_status:   str = "unknown"
    last_check_at: str = ""

    def to_dict(self) -> dict:
        return {
            "app_id":        self.app_id,
            "app_secret":    self.app_secret,
            "redirect_uri":  self.redirect_uri,
            "name":          self.name,
            "disabled":      self.disabled,
            "last_status":   self.last_status,
            "last_check_at": self.last_check_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MetaAppRecord":
        return cls(
            app_id        = str(d.get("app_id",       "")),
            app_secret    = str(d.get("app_secret",   "")),
            redirect_uri  = str(d.get("redirect_uri", "")),
            name          = str(d.get("name",         "")),
            disabled      = bool(d.get("disabled",    False)),
            last_status   = str(d.get("last_status",  "unknown")),
            last_check_at = str(d.get("last_check_at", "")),
        )


class MetaAppPool:
    """Manages a list of MetaAppRecords with round-robin selection."""

    def __init__(self, records: Optional[list[MetaAppRecord]] = None):
        self._records: list[MetaAppRecord] = list(records or [])
        self._lock = threading.Lock()
        self._rr_iter = None
        self._rebuild_iter()

    def _rebuild_iter(self):
        """Reset the round-robin iterator over enabled apps."""
        enabled = [r for r in self._records if not r.disabled and r.app_id and r.app_secret]
        self._rr_iter = itertools.cycle(enabled) if enabled else None

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def records(self) -> list[MetaAppRecord]:
        with self._lock:
            return list(self._records)

    def add(self, rec: MetaAppRecord) -> None:
        with self._lock:
            self._records.append(rec)
            self._rebuild_iter()

    def find(self, app_id: str) -> Optional[MetaAppRecord]:
        with self._lock:
            for r in self._records:
                if r.app_id == app_id:
                    return r
            return None

    def mark_disabled(self, app_id: str, reason: str = "") -> None:
        with self._lock:
            for r in self._records:
                if r.app_id == app_id:
                    r.disabled    = True
                    r.last_status = f"disabled: {reason}" if reason else "disabled"
                    r.last_check_at = datetime.now(timezone.utc).isoformat()
                    self._rebuild_iter()
                    return

    def mark_healthy(self, app_id: str) -> None:
        with self._lock:
            for r in self._records:
                if r.app_id == app_id:
                    r.disabled    = False
                    r.last_status = "ok"
                    r.last_check_at = datetime.now(timezone.utc).isoformat()
                    self._rebuild_iter()
                    return

    def next_healthy(self) -> Optional[MetaAppRecord]:
        """Return the next healthy app via round-robin. None if pool empty."""
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

    # ── Persistence ──────────────────────────────────────────────────────

    def to_list(self) -> list[dict]:
        return [r.to_dict() for r in self.records]

    @classmethod
    def from_config(cls, config: dict) -> "MetaAppPool":
        """Build pool from config["meta_app_pool"] (list of dicts)."""
        raw = config.get("meta_app_pool", [])
        if not isinstance(raw, list):
            raw = []
        # Backward compat: if pool is empty but legacy meta_app_id is set,
        # treat the legacy single-app config as a 1-element pool.
        if not raw:
            legacy_id = str(config.get("meta_app_id", "")).strip()
            legacy_secret = str(config.get("meta_app_secret", "")).strip()
            if legacy_id and legacy_secret:
                raw = [{
                    "app_id":     legacy_id,
                    "app_secret": legacy_secret,
                    "redirect_uri": str(config.get("meta_redirect_uri", "")),
                    "name":       "Legacy default app",
                }]
        return cls(records=[MetaAppRecord.from_dict(d) for d in raw])
