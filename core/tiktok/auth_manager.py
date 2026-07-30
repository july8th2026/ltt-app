"""
core/tiktok/auth_manager.py — TikTok OAuth2 (PKCE) + token lifecycle.

Split so the web app can drive the flow across two HTTP requests:

    generate_pkce_pair()                                   -> (verifier, challenge)
    build_authorize_url(redirect_uri, state, challenge)    -> where to send them
    complete_oauth(code, verifier, redirect_uri)           -> saved TikTokAccount

TikTok redirects back to the app itself (`/oauth/tiktok/callback`, see
server/routes/oauth.py). Two mechanisms the desktop build needed are gone:

  * the local callback server on localhost:8766 — impossible on a server, and
    unnecessary once the app has a public HTTPS callback;
  * the cross-machine OAuth relay (lttstudios.com/api/oauth-relay/*), which
    only ever existed to work around the missing public callback. Keeping it
    would leave a second, weaker path into the token store.

`state`, the PKCE verifier, TTL and single-use enforcement live in
server/services/oauth_service.py — the verifier never leaves this server.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from typing import Callable, Optional
from urllib.parse import urlencode

import requests

from core.tiktok.token_store import TikTokAccount, TikTokTokenStore

# ─── OAuth endpoints ──────────────────────────────────────────────────────────

_AUTH_URL     = "https://www.tiktok.com/v2/auth/authorize/"
_TOKEN_URL    = "https://open.tiktokapis.com/v2/oauth/token/"
_REVOKE_URL   = "https://open.tiktokapis.com/v2/oauth/revoke/"
_USER_URL     = "https://open.tiktokapis.com/v2/user/info/"
_USER_FIELDS  = "open_id,display_name,avatar_url"

_DEFAULT_SCOPES   = "user.info.basic,video.upload,video.publish"

def _generate_pkce_pair() -> tuple[str, str]:
    """
    Returns (code_verifier, code_challenge).
    code_verifier: 86-char URL-safe random string (within PKCE [43, 128]).
    code_challenge: base64url(SHA-256(code_verifier)) without padding.
    """
    code_verifier = secrets.token_urlsafe(64)   # 64 random bytes → 86-char b64url
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


# ─── Auth manager ─────────────────────────────────────────────────────────────

class TikTokAuthManager:
    """
    Manages TikTok OAuth2 PKCE flow and token lifecycle.
    Cheap to construct; the web app makes one per request.
    """

    def __init__(
        self,
        config: dict,
        token_store: Optional[TikTokTokenStore] = None,
    ):
        self._config      = config
        # Sprint TT-1.4: pool-aware client selection. Falls back to legacy
        # single-client keys when tiktok_client_pool is empty.
        try:
            from core.tiktok.multi_client import TikTokClientPool
            self._client_pool = TikTokClientPool.from_config(config)
            chosen = self._client_pool.next_healthy()
        except Exception:
            self._client_pool = None
            chosen = None

        if chosen is not None:
            self.client_key    = chosen.client_key
            self.client_secret = chosen.client_secret
            self.redirect_uri  = chosen.redirect_uri or str(config.get("tiktok_redirect_uri", "")).strip()
        else:
            self.client_key   = str(config.get("tiktok_client_key", "")).strip()
            self.client_secret= str(config.get("tiktok_client_secret", "")).strip()
            self.redirect_uri = str(config.get("tiktok_redirect_uri", "")).strip()
        self.scopes       = str(config.get("tiktok_scopes", _DEFAULT_SCOPES)).strip()
        self.token_store  = token_store or TikTokTokenStore()

    # ── Configuration ──────────────────────────────────────────────────────

    def update_config(self, config: dict) -> None:
        """Hot-reload credentials without recreating the object."""
        self._config       = config
        self.client_key    = str(config.get("tiktok_client_key", "")).strip()
        self.client_secret = str(config.get("tiktok_client_secret", "")).strip()
        self.scopes        = str(config.get("tiktok_scopes", _DEFAULT_SCOPES)).strip()
        self.redirect_uri  = str(config.get("tiktok_redirect_uri", "")).strip()

    def is_configured(self) -> bool:
        """True if both client_key and client_secret are set."""
        return bool(self.client_key and self.client_secret)

    # ── OAuth2 PKCE flow ───────────────────────────────────────────────────
    #
    # Same split as the Facebook manager: build the URL, then finish the flow
    # from the returned code. Neither half binds a port nor opens a browser.
    # PKCE forces the caller to hold `code_verifier` alongside `state` between
    # the two calls, which on the web means a server-side store — a closure
    # variable does not survive a request boundary.

    def build_authorize_url(
        self, redirect_uri: str, state: str, code_challenge: str,
    ) -> str:
        if not self.is_configured():
            raise ValueError(
                "Chưa cấu hình TikTok Client Key / Client Secret.\n"
                "Vào Cài đặt → mục 'TikTok App' để nhập."
            )
        params = {
            "client_key":            self.client_key,
            "scope":                 self.scopes,
            "response_type":         "code",
            "redirect_uri":          redirect_uri,
            "state":                 state,
            "code_challenge":        code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    def generate_pkce_pair() -> tuple[str, str]:
        """(code_verifier, code_challenge) — public wrapper for callers that
        must persist the verifier themselves."""
        return _generate_pkce_pair()

    def complete_oauth(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        on_status: Callable[[str], None] = None,
    ) -> TikTokAccount:
        """Code -> tokens -> user info -> saved TikTokAccount."""
        log = on_status or (lambda m: None)

        # ── Exchange code → tokens ─────────────────────────────────────────
        log("Đang lấy Access Token từ TikTok...")
        token_resp = self._exchange_code(code, code_verifier, redirect_uri)

        access_token       = token_resp["access_token"]
        refresh_token      = token_resp["refresh_token"]
        expires_in         = int(token_resp.get("expires_in", 86400))
        refresh_expires_in = int(token_resp.get("refresh_expires_in", 31536000))
        open_id            = token_resp["open_id"]
        granted_scopes     = str(token_resp.get("scope", self.scopes)).split(",")

        now = time.time()
        expires_at         = now + expires_in
        refresh_expires_at = now + refresh_expires_in

        # ── Fetch user info ────────────────────────────────────────────────
        log("Đang lấy thông tin tài khoản TikTok...")
        from core.tiktok.client import TikTokClient
        client    = TikTokClient(access_token)
        user_info = client.get_user_info()

        display_name = str(user_info.get("display_name", "TikTok User"))
        avatar_url   = str(user_info.get("avatar_url", ""))

        # ── Build & persist TikTokAccount ──────────────────────────────────
        account = TikTokAccount(
            open_id            = open_id,
            display_name       = display_name,
            avatar_url         = avatar_url,
            access_token       = access_token,
            refresh_token      = refresh_token,
            expires_at         = expires_at,
            refresh_expires_at = refresh_expires_at,
            scopes             = [s.strip() for s in granted_scopes if s.strip()],
            connected_at       = datetime.now().isoformat(),
        )
        self.token_store.upsert_account(account)

        log(f"✅ Kết nối TikTok thành công: {display_name}")
        return account

    # ── Token refresh ──────────────────────────────────────────────────────

    def refresh_access_token(self, account: TikTokAccount) -> TikTokAccount:
        """
        Exchange refresh_token → new access_token.
        Saves updated account to token store.
        Raises RuntimeError if refresh_token is expired or API fails.
        """
        if not account.is_refresh_valid():
            raise RuntimeError(
                f"Refresh token của {account.display_name} đã hết hạn.\n"
                "Vui lòng kết nối lại tài khoản TikTok."
            )

        payload = {
            "client_key":    self.client_key,
            "client_secret": self.client_secret,
            "grant_type":    "refresh_token",
            "refresh_token": account.refresh_token,
        }
        try:
            resp = requests.post(_TOKEN_URL, data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise RuntimeError(f"Không thể làm mới token TikTok: {exc}") from exc

        if "error" in data and data["error"] not in ("ok", "success", ""):
            # Only surface safe, non-sensitive fields (never raw token values)
            _safe_err = data.get("error_description") or data.get("error") or "lỗi không xác định"
            raise RuntimeError(f"TikTok từ chối làm mới token: {_safe_err}")

        now = time.time()
        updated = TikTokAccount(
            open_id            = data.get("open_id", account.open_id),
            display_name       = account.display_name,
            avatar_url         = account.avatar_url,
            access_token       = data["access_token"],
            refresh_token      = data.get("refresh_token", account.refresh_token),
            expires_at         = now + int(data.get("expires_in", 86400)),
            refresh_expires_at = now + int(data.get("refresh_expires_in", 31536000)),
            scopes             = account.scopes,
            connected_at       = account.connected_at,
        )
        self.token_store.upsert_account(updated)
        return updated

    # ── Revoke ─────────────────────────────────────────────────────────────

    def revoke_account(self, open_id: str) -> None:
        """Remove account from local store (best-effort API revocation)."""
        account = self.token_store.get_account(open_id)
        if account:
            try:
                requests.post(_REVOKE_URL, data={
                    "client_key":    self.client_key,
                    "client_secret": self.client_secret,
                    "token":         account.access_token,
                }, timeout=15)
            except Exception:
                pass   # local removal always succeeds
        self.token_store.remove_account(open_id)

    # ── Internal ───────────────────────────────────────────────────────────

    def _exchange_code(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> dict:
        """POST to TikTok token endpoint; returns raw JSON body."""
        payload = {
            "client_key":    self.client_key,
            "client_secret": self.client_secret,
            "code":          code,
            "grant_type":    "authorization_code",
            "redirect_uri":  redirect_uri,
            "code_verifier": code_verifier,
        }
        try:
            resp = requests.post(_TOKEN_URL, data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise RuntimeError(f"Lỗi trao đổi mã OAuth TikTok: {exc}") from exc

        if "access_token" not in data:
            # Log only non-sensitive keys — never dump token values
            _safe_keys = {k: v for k, v in data.items()
                          if k not in ("access_token", "refresh_token", "open_id")}
            raise RuntimeError(
                f"TikTok không trả về access_token: {json.dumps(_safe_keys, ensure_ascii=False)[:300]}"
            )
        return data


# ─── Port binding helper (same pattern as FB auth_manager) ───────────────────
