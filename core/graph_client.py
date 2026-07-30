"""
Thin HTTP client for Meta Graph API.
Handles: base URL routing, retry with exponential backoff, error parsing.
"""
from __future__ import annotations

import time
from typing import Optional

import requests

GRAPH_BASE = "https://graph.facebook.com"
GRAPH_VIDEO_BASE = "https://graph-video.facebook.com"
DEFAULT_VERSION = "v21.0"

_RETRY_CODES = {1, 2, 4, 17, 341}          # transient Graph errors
_RATE_LIMIT_CODES = {17, 32, 613}           # rate-limit error codes

# ─── Shared session pool ──────────────────────────────────────────────────────
# One requests.Session per API version — reuses TCP connections across uploads.
import threading as _threading
_sessions: dict[str, requests.Session] = {}
_sessions_lock = _threading.Lock()   # BUG-03 fix: guard TOCTOU race in _get_session


def _get_session(version: str) -> requests.Session:
    # BUG-03 fix: check-then-act must be atomic to prevent duplicate session creation
    with _sessions_lock:
        if version not in _sessions:
            s = requests.Session()
            s.headers["User-Agent"] = "LTTStudio/1.0"   # HV-07 fix: consistent UA
            _sessions[version] = s
        return _sessions[version]


# ─── Error class ──────────────────────────────────────────────────────────────

class GraphError(Exception):
    """Represents a Meta Graph API error response."""

    def __init__(
        self,
        message: str,
        code: int = 0,
        subcode: int = 0,
        fbtrace_id: str = "",
        raw: dict = None,
    ):
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.fbtrace_id = fbtrace_id
        self.raw = raw or {}

    def is_token_error(self) -> bool:
        """Token expired or invalid."""
        return self.code in (190, 102) or self.subcode in (463, 467, 458)

    def is_permission_error(self) -> bool:
        """Missing permission / app review required."""
        return self.code in (100, 200, 273, 299)

    def is_rate_limit(self) -> bool:
        return self.code in _RATE_LIMIT_CODES

    def is_page_restricted(self) -> bool:
        """Page is restricted / restricted from posting."""
        return self.code == 368 or self.subcode in (1404006, 1404030, 1893002)

    def is_retryable(self) -> bool:
        return self.code in _RETRY_CODES or self.is_rate_limit()

    def __str__(self) -> str:
        parts = [self.args[0]]
        if self.code:
            parts.append(f"code={self.code}")
        if self.subcode:
            parts.append(f"subcode={self.subcode}")
        if self.fbtrace_id:
            parts.append(f"trace={self.fbtrace_id}")
        return " | ".join(parts)


def _raise_if_error(resp_json: dict):
    err = resp_json.get("error")
    if not err:
        return
    raise GraphError(
        message=err.get("message", "Unknown Graph error"),
        code=int(err.get("code", 0)),
        subcode=int(err.get("error_subcode", 0)),
        fbtrace_id=err.get("fbtrace_id", ""),
        raw=err,
    )


# ─── Client ───────────────────────────────────────────────────────────────────

class GraphClient:
    """
    HTTP wrapper for Meta Graph API.
    Auto-retries transient/rate-limit errors (exponential back-off).
    """

    def __init__(
        self,
        version: str = DEFAULT_VERSION,
        timeout: int = 30,
        max_retries: int = 3,
        *,
        account_id: str = "",
        config:     Optional[dict] = None,
    ):
        self.version = version
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = _get_session(version)

        # Round 1.4 — Network identity (Sprint C).
        # When account_id is supplied AND network_identity_enabled is true in
        # config, override the session's User-Agent and configure proxy for
        # this account's requests. account_id="" → no-op (legacy behaviour).
        self._identity_ua: str = ""
        self._identity_proxy: str = ""
        if account_id and config is not None and config.get("network_identity_enabled", False):
            try:
                from core.network_identity import NetworkIdentityProvider
                # Use a non-singleton provider here so callers can pass per-config
                # without leaking state across tests.
                ident = NetworkIdentityProvider(config).identity_for(account_id)
                self._identity_ua    = ident.user_agent
                self._identity_proxy = ident.proxy
            except Exception:
                pass

    def _request_kwargs(self) -> dict:
        """Build per-request kwargs honoring the network identity override."""
        kw: dict = {"timeout": self.timeout}
        if self._identity_proxy:
            kw["proxies"] = {"http": self._identity_proxy, "https": self._identity_proxy}
        return kw

    def _request_headers(self, base: Optional[dict] = None) -> dict:
        h = dict(base or {})
        if self._identity_ua:
            h["User-Agent"] = self._identity_ua
        return h

    # ── Public GET / POST ──────────────────────────────────────────────────

    def get(self, path: str, params: dict = None, token: str = None) -> dict:
        """GET graph.facebook.com/{version}/{path}"""
        url = f"{GRAPH_BASE}/{self.version}/{path.lstrip('/')}"
        p = dict(params or {})
        if token:
            p["access_token"] = token
        return self._request("GET", url, params=p)

    def post(
        self,
        path: str,
        data: dict = None,
        token: str = None,
        video_endpoint: bool = False,
    ) -> dict:
        """POST graph[-video].facebook.com/{version}/{path}"""
        base = GRAPH_VIDEO_BASE if video_endpoint else GRAPH_BASE
        url = f"{base}/{self.version}/{path.lstrip('/')}"
        d = dict(data or {})
        if token:
            d["access_token"] = token
        return self._request("POST", url, data=d)

    def post_multipart(
        self,
        path: str,
        data: dict,
        files: dict,
        token: str = None,
        video_endpoint: bool = False,
    ) -> dict:
        """
        POST multipart/form-data.
        files = {"field_name": (filename, bytes_or_fileobj, mime_type)}
        Used for: resumable transfer phase (video_file_chunk) and thumbnail upload.
        """
        base = GRAPH_VIDEO_BASE if video_endpoint else GRAPH_BASE
        url = f"{base}/{self.version}/{path.lstrip('/')}"
        d = dict(data)
        if token:
            d["access_token"] = token
        return self._request("POST", url, data=d, files=files)

    # ── Token helpers ──────────────────────────────────────────────────────

    def exchange_short_for_long(
        self, app_id: str, app_secret: str, short_token: str
    ) -> tuple[str, int]:
        """
        Exchange short-lived user token → long-lived (60 days).
        Returns (long_token, expires_in_seconds).
        """
        resp = self.get("oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        })
        token = resp.get("access_token", "")
        expires = int(resp.get("expires_in", 5183944))  # ~60 days default
        if not token:
            raise GraphError("No access_token in long-lived token response")
        return token, expires

    def get_video_insights(self, video_id: str, token: str) -> dict:
        """
        K-7: Fetch video insights after processing (typically available after 24h).

        Returns flat dict:
            views, reach, reactions, comments_count, shares, minutes_viewed
        Calls two endpoints:
          1. /{video_id}?fields=reactions.summary(true),comments.summary(true),shares
          2. /{video_id}/video_insights?metric=post_impressions_unique,...
        """
        # Endpoint 1: engagement metrics
        try:
            eng = self.get(
                video_id,
                params={
                    "fields": (
                        "reactions.summary(true).limit(0),"
                        "comments.summary(true).limit(0),"
                        "shares"
                    )
                },
                token=token,
            )
        except Exception:
            eng = {}

        reactions     = eng.get("reactions", {}).get("summary", {}).get("total_count", 0)
        comments_count = eng.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares        = eng.get("shares", {}).get("count", 0)

        # Endpoint 2: video-specific metrics (reach, views)
        try:
            ins = self.get(
                f"{video_id}/video_insights",
                params={
                    "metric": (
                        "post_impressions_unique,"  # reach
                        "post_video_views,"          # views (≥3s)
                        "post_video_view_time"       # minutes viewed
                    ),
                    "period": "lifetime",
                },
                token=token,
            )
            metrics_raw = {
                item["name"]: item.get("values", [{}])[-1].get("value", 0)
                for item in ins.get("data", [])
            }
        except Exception:
            metrics_raw = {}

        return {
            "views":          int(metrics_raw.get("post_video_views", 0)),
            "reach":          int(metrics_raw.get("post_impressions_unique", 0)),
            "reactions":      int(reactions),
            "comments_count": int(comments_count),
            "shares":         int(shares),
            "minutes_viewed": round(
                float(metrics_raw.get("post_video_view_time", 0)) / 60, 1
            ),
        }

    def get_user_info(self, token: str) -> dict:
        """GET /me?fields=id,name — returns {id, name}."""
        return self.get("me", params={"fields": "id,name"}, token=token)

    def get_pages(self, token: str) -> list[dict]:
        """GET /me/accounts (paginated) — returns list of page dicts with access_token.

        Follows Graph cursor paging so Business Managers / System Users with
        more pages than one page-size still return every page. A safety cap of
        50 round-trips (≈5000 pages) guards against a runaway cursor loop.
        """
        pages: list[dict] = []
        params = {
            "fields": "id,name,access_token,category,picture",
            "limit": 100,
        }
        for _ in range(50):
            resp = self.get("me/accounts", params=params, token=token)
            pages.extend(resp.get("data", []))
            paging = resp.get("paging", {}) or {}
            after = (paging.get("cursors", {}) or {}).get("after", "")
            if not paging.get("next") or not after:
                break
            params = dict(params, after=after)
        return pages

    # ── Low-level ──────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        url: str,
        params: dict = None,
        data: dict = None,
        files: dict = None,
        raw_body: bytes = None,
        extra_headers: dict = None,
    ) -> dict:
        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                # Round 1.4: merge network-identity headers (UA override) + proxy
                headers = self._request_headers(extra_headers)
                req_kw  = self._request_kwargs()

                if files is not None:
                    resp = self._session.request(
                        method, url,
                        params=params, data=data, files=files,
                        headers=headers, **req_kw,
                    )
                elif raw_body is not None:
                    resp = self._session.request(
                        method, url,
                        params=params, data=raw_body,
                        headers=headers, **req_kw,
                    )
                elif data:
                    resp = self._session.request(
                        method, url,
                        params=params, data=data,
                        headers=headers, **req_kw,
                    )
                else:
                    resp = self._session.request(
                        method, url,
                        params=params,
                        headers=headers, **req_kw,
                    )

                # Parse JSON
                try:
                    resp_json = resp.json()
                except Exception:
                    resp.raise_for_status()
                    return {}

                # Raise GraphError if API returned an error
                try:
                    _raise_if_error(resp_json)
                except GraphError as ge:
                    if ge.is_retryable() and attempt < self.max_retries - 1:
                        wait = 2 ** (attempt + 1)
                        if ge.is_rate_limit():
                            wait = max(wait, 60)
                        time.sleep(wait)
                        last_exc = ge
                        continue
                    raise

                return resp_json

            except GraphError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        raise last_exc or RuntimeError("Request failed after retries")
