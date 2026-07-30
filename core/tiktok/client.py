"""
TikTokClient — HTTP wrapper for TikTok Content Posting API v2.

Base URL: https://open.tiktokapis.com
Auth:     Bearer {access_token}

All endpoints return JSON with shape:
    { "data": {...}, "error": { "code": "ok"|"...", "message": "..." } }

Raises TikTokError on API errors or non-2xx HTTP responses.
"""
from __future__ import annotations

import json
import time
from typing import Callable, Optional

import requests

# ─── Error class ──────────────────────────────────────────────────────────────

class TikTokError(RuntimeError):
    """
    Represents a TikTok API error.

    Attributes:
        error_code  — TikTok error code string, e.g. "access_token_invalid"
        http_status — HTTP status code (0 if network-level error)
    """

    #: Error codes that indicate an expired or invalid access_token
    _AUTH_CODES = frozenset({
        "access_token_invalid",
        "access_token_expired",
        "token_expired",
    })

    #: Error codes that indicate rate-limiting
    _RATE_CODES = frozenset({
        "rate_limit_exceeded",
        "spam_risk_too_many_pending_share",
    })

    def __init__(self, message: str, error_code: str = "", http_status: int = 0):
        super().__init__(message)
        self.error_code  = error_code
        self.http_status = http_status

    def is_auth_error(self) -> bool:
        return self.error_code in self._AUTH_CODES or self.http_status == 401

    def is_rate_limit(self) -> bool:
        return self.error_code in self._RATE_CODES or self.http_status == 429

    def is_server_error(self) -> bool:
        return self.http_status >= 500


# ─── Client ───────────────────────────────────────────────────────────────────

class TikTokClient:
    """
    Thin HTTP client for TikTok Content Posting API v2.

    One instance per request or per worker — stateless except for the token.
    """

    BASE_URL  = "https://open.tiktokapis.com"
    USER_INFO_FIELDS = "open_id,display_name,avatar_url"

    def __init__(
        self,
        access_token: str,
        on_log: Optional[Callable] = None,
        timeout: int = 60,
        *,
        account_id: str = "",
        config:     Optional[dict] = None,
    ):
        self._token   = access_token
        self._log     = on_log or (lambda msg, lvl: None)
        self._timeout = timeout
        self._session = requests.Session()

        # Sprint TT-1.3: per-account network identity (UA + proxy).
        # Mirrors core/graph_client.py wiring for FB. Identity stays stable
        # per account_id so FB doesn't see UA rotate mid-session.
        self._identity_ua: str = ""
        self._identity_proxy: str = ""
        if account_id and config is not None and config.get("network_identity_enabled", False):
            try:
                from core.network_identity import NetworkIdentityProvider
                ident = NetworkIdentityProvider(config).identity_for(account_id)
                self._identity_ua    = ident.user_agent
                self._identity_proxy = ident.proxy
            except Exception:
                pass

        # The Authorization + Content-Type headers live on the shared session
        # so every request reuses them automatically.
        self._session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json; charset=UTF-8",
        })

    def _apply_identity(self, headers: dict, kwargs: dict) -> None:
        """Merge identity UA + proxy into per-request headers/kwargs (Sprint TT-1.3)."""
        if self._identity_ua:
            headers["User-Agent"] = self._identity_ua
        if self._identity_proxy:
            kwargs["proxies"] = {"http": self._identity_proxy, "https": self._identity_proxy}

    def _url(self, path: str) -> str:
        return f"{self.BASE_URL}/{path.lstrip('/')}"

    # ── Core HTTP methods ──────────────────────────────────────────────────

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        """GET request; returns parsed data dict. Raises TikTokError on failure."""
        return self._request_with_retry("GET", path, params=params)

    def post(self, path: str, payload: dict) -> dict:
        """POST JSON; returns parsed data dict. Raises TikTokError on failure."""
        return self._request_with_retry("POST", path, payload=payload)

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        payload: Optional[dict] = None,
        max_retries: int = 3,
    ) -> dict:
        """H2 fix: Auto-retry on 429 (Retry-After) and 5xx errors.

        TikTok requires apps to respect Retry-After. Apps that hammer through
        429s get app-level penalties.
        """
        url = self._url(path)
        for attempt in range(max_retries + 1):
            self._log(f"[TikTok] {method} {url}", "debug")
            # Sprint TT-1.3: apply network identity (UA + proxy) per request
            _headers: dict = {}
            _req_kw:  dict = {"timeout": self._timeout}
            self._apply_identity(_headers, _req_kw)
            try:
                if method == "GET":
                    resp = self._session.get(
                        url, params=params, headers=_headers, **_req_kw,
                    )
                else:
                    resp = self._session.post(
                        url,
                        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                        headers=_headers, **_req_kw,
                    )
            except requests.RequestException as exc:
                raise TikTokError(f"Lỗi mạng khi {method} {path}: {exc}") from exc

            # Respect Retry-After on 429 / 503
            if resp.status_code in (429, 503) and attempt < max_retries:
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait_s = int(retry_after) if retry_after else (2 ** attempt) * 5
                except ValueError:
                    wait_s = (2 ** attempt) * 5
                wait_s = min(max(wait_s, 5), 120)   # clamp [5s, 120s]
                self._log(
                    f"[TikTok] HTTP {resp.status_code} — chờ {wait_s}s rồi retry "
                    f"(attempt {attempt + 1}/{max_retries})",
                    "warning",
                )
                time.sleep(wait_s)
                continue

            # 5xx → exponential backoff retry
            if 500 <= resp.status_code < 600 and attempt < max_retries:
                wait_s = min((2 ** attempt) * 3, 30)
                self._log(
                    f"[TikTok] HTTP {resp.status_code} (server error) — "
                    f"chờ {wait_s}s rồi retry (attempt {attempt + 1}/{max_retries})",
                    "warning",
                )
                time.sleep(wait_s)
                continue

            return self._parse(resp, path)

        # Exhausted retries
        raise TikTokError(
            f"Hết số lần thử {method} {path} (HTTP {resp.status_code})",
            http_status=resp.status_code,
        )

    def put_binary(
        self,
        url: str,
        data: bytes,
        content_type: str = "video/mp4",
        content_range: Optional[str] = None,
    ) -> int:
        """
        PUT raw bytes to a pre-signed upload URL.
        Returns HTTP status code.
        Raises TikTokError on non-2xx.
        """
        headers = {"Content-Type": content_type}
        if content_range:
            headers["Content-Range"] = content_range
        self._log(
            f"[TikTok] PUT binary {len(data):,} bytes → {url[:60]}...", "debug"
        )
        try:
            resp = requests.put(
                url, data=data, headers=headers, timeout=self._timeout
            )
        except requests.RequestException as exc:
            raise TikTokError(f"Lỗi mạng khi PUT binary: {exc}") from exc
        if not resp.ok:
            raise TikTokError(
                f"PUT binary thất bại: HTTP {resp.status_code} — {resp.text[:200]}",
                http_status=resp.status_code,
            )
        return resp.status_code

    # ── High-level helpers ─────────────────────────────────────────────────

    def get_user_info(self) -> dict:
        """
        Return basic user info dict with keys:
            open_id, display_name, avatar_url
        """
        resp = self.get(
            "/v2/user/info/",
            params={"fields": self.USER_INFO_FIELDS},
        )
        # TikTok wraps the user object under resp["data"]["user"]
        return resp.get("user", resp)

    # ── Internal response parsing ──────────────────────────────────────────

    @staticmethod
    def _parse(resp: requests.Response, path: str = "") -> dict:
        """
        Parse a TikTok API response.

        TikTok always returns 200 even for logical errors; the real status
        lives in body["error"]["code"].  Returns body["data"] on success.
        """
        try:
            body = resp.json()
        except ValueError:
            if not resp.ok:
                raise TikTokError(
                    f"HTTP {resp.status_code} {path} — không phải JSON: {resp.text[:200]}",
                    http_status=resp.status_code,
                )
            return {}

        err = body.get("error", {})
        code = str(err.get("code", "ok")).lower()
        if code not in ("ok", "success", ""):
            # Never dump full body — may include tokens or signed URLs.
            if err.get("message"):
                raw_msg = str(err.get("message"))
            else:
                from utils.logger import safe_response_repr
                raw_msg = safe_response_repr(body)
            # H3 fix: translate error code to friendly Vietnamese message
            from core.tiktok.error_codes import get_friendly_message
            friendly = get_friendly_message(code, fallback=raw_msg)
            raise TikTokError(
                friendly,
                error_code=code,
                http_status=resp.status_code,
            )

        if not resp.ok:
            raise TikTokError(
                f"HTTP {resp.status_code} {path}",
                http_status=resp.status_code,
            )

        return body.get("data", body)
