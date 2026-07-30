"""
oauth_service.py — provider OAuth on the web (W5).

The desktop flow could not work on a server: it opened a browser on the
machine running the bot and bound `localhost:8765` / `localhost:8766` to
catch the redirect (`core/auth_manager.py`, `core/tiktok/auth_manager.py`).
On a VPS there is no browser, and the operator's browser cannot reach the
server's localhost.

Here the provider redirects straight back to this app, so the callback is an
ordinary authenticated request. The Graph / TikTok work itself is NOT
reimplemented — it lives in `AuthManager.complete_oauth()` and
`TikTokAuthManager.complete_oauth()`, which the desktop transport also calls.
This module only owns what the web needs and the desktop got for free from a
closure variable:

  * a **server-side** store for `state` and the PKCE `code_verifier`, since
    they must survive the round trip between two separate HTTP requests;
  * **binding each flow to the browser session** that started it, via a
    nonce kept in the signed session cookie. Without it, anyone who learned
    a `state` value could complete a flow into this operator's token store;
  * **single-use** consumption and a TTL, so a leaked or replayed callback
    URL is worthless.

This also lets the TikTok relay go away entirely: the relay existed only
because there was no public callback endpoint to register.
"""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass

CALLBACK_PATHS = {
    "facebook": "/oauth/facebook/callback",
    "tiktok":   "/oauth/tiktok/callback",
}

FLOW_TTL_S = 600         # a login that takes >10 minutes has been abandoned
MAX_PENDING = 20         # bound the store; an operator has one browser
SESSION_NONCE_KEY = "oauth_nonce"


class OAuthError(Exception):
    """Anything that should be shown to the operator rather than logged."""


@dataclass
class PendingFlow:
    provider: str
    state: str
    redirect_uri: str
    session_nonce: str
    code_verifier: str = ""      # TikTok (PKCE) only
    created_at: float = 0.0

    def is_expired(self, now: float) -> bool:
        return (now - self.created_at) > FLOW_TTL_S


class FlowStore:
    """In-memory, single-use, TTL-bounded pending-flow store.

    In-process is correct under ADR-005 (one orchestrator process). If the app
    is ever run with multiple workers this must move to shared storage, or a
    callback will land on a worker that never saw the flow.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._flows: dict[str, PendingFlow] = {}

    def put(self, flow: PendingFlow) -> None:
        with self._lock:
            self._prune(time.time())
            if len(self._flows) >= MAX_PENDING:
                # Drop the oldest rather than refusing — a fresh, deliberate
                # login attempt should never be blocked by stale entries.
                oldest = min(self._flows.values(), key=lambda f: f.created_at)
                self._flows.pop(oldest.state, None)
            self._flows[flow.state] = flow

    def take(self, state: str) -> PendingFlow | None:
        """Pop the flow for `state`. Single-use: a replayed callback finds
        nothing."""
        with self._lock:
            now = time.time()
            self._prune(now)
            flow = self._flows.pop(state, None)
            if flow is None or flow.is_expired(now):
                return None
            return flow

    def _prune(self, now: float) -> None:
        for state in [s for s, f in self._flows.items() if f.is_expired(now)]:
            self._flows.pop(state, None)

    # Test/diagnostic helpers.
    def pending_count(self) -> int:
        with self._lock:
            self._prune(time.time())
            return len(self._flows)

    def clear(self) -> None:
        with self._lock:
            self._flows.clear()


_store = FlowStore()


def store() -> FlowStore:
    return _store


# ── session binding ────────────────────────────────────────────────────────

def session_nonce(session: dict) -> str:
    """Stable per-session nonce, minted on first use.

    Kept in the signed session cookie, so a callback can prove it arrived in
    the same browser session that started the flow.
    """
    nonce = str(session.get(SESSION_NONCE_KEY, "") or "")
    if not nonce:
        nonce = secrets.token_urlsafe(24)
        session[SESSION_NONCE_KEY] = nonce
    return nonce


def callback_url(base_url: str, provider: str) -> str:
    """Absolute callback URL, which must match the provider registration
    byte-for-byte or the token exchange is rejected."""
    if provider not in CALLBACK_PATHS:
        raise OAuthError(f"Provider không hỗ trợ: {provider}")
    return base_url.rstrip("/") + CALLBACK_PATHS[provider]


# The redirect URI is read from the SAME config keys the bot already uses —
# `meta_redirect_uri` / `tiktok_redirect_uri`, the values registered at the
# Meta and TikTok developer portals. No new key is introduced: the operator
# repoints the existing ones from the old static bridge pages
# (https://lttstudios.com/auth/fb-callback.html,
#  https://lttstudios.com/legal/callback.html) to this app's own routes.
REDIRECT_CONFIG_KEY = {
    "facebook": "meta_redirect_uri",
    "tiktok":   "tiktok_redirect_uri",
}

_PORTAL = {
    "facebook": "Meta → App → Facebook Login → Valid OAuth Redirect URIs",
    "tiktok":   "TikTok Developer Portal → App → Login Kit → Redirect URI",
}


def resolve_redirect_uri(config: dict, provider: str, request_base: str) -> str:
    """The redirect URI to send, validated against what this app can serve.

    Deliberately strict. A redirect_uri mismatch surfaces at the provider as
    an opaque error long after the operator has left this app, so it is far
    cheaper to refuse up front and say exactly which value to change where.
    """
    key = REDIRECT_CONFIG_KEY[provider]
    configured = str(config.get(key, "") or "").strip()
    expected = callback_url(request_base, provider)

    if not configured:
        raise OAuthError(
            f"Chưa đặt `{key}`. Vào Cài đặt và điền:\n    {expected}\n"
            f"rồi khai báo đúng URL đó ở {_PORTAL[provider]}."
        )
    if not configured.startswith("https://"):
        raise OAuthError(
            f"`{key}` phải là HTTPS — {'Facebook' if provider == 'facebook' else 'TikTok'} "
            f"từ chối HTTP. Giá trị hiện tại: {configured}"
        )
    if not configured.rstrip("/").endswith(CALLBACK_PATHS[provider]):
        raise OAuthError(
            f"`{key}` đang trỏ tới {configured}\n"
            f"— đó là trang callback tĩnh của bản desktop cũ, không còn dùng.\n"
            f"Ứng dụng web nhận callback tại:\n    {expected}\n"
            f"Hãy sửa `{key}` thành URL đó, VÀ khai báo đúng nó ở "
            f"{_PORTAL[provider]}."
        )
    return configured


# ── Facebook ───────────────────────────────────────────────────────────────

def facebook_start(config: dict, request_base: str, session: dict) -> str:
    from core.auth_manager import AuthManager

    manager = AuthManager(config)
    if not manager.is_configured():
        raise OAuthError(
            "Chưa cấu hình Meta App ID / App Secret. Vào Cài đặt → "
            "'Meta App (Facebook Login)' để nhập trước khi kết nối."
        )

    redirect_uri = resolve_redirect_uri(config, "facebook", request_base)
    state = secrets.token_urlsafe(24)
    _store.put(PendingFlow(
        provider="facebook", state=state, redirect_uri=redirect_uri,
        session_nonce=session_nonce(session), created_at=time.time(),
    ))
    return manager.build_authorize_url(redirect_uri, state)


def facebook_finish(config: dict, state: str, code: str, session: dict):
    from core.auth_manager import AuthManager

    flow = _consume(state, session, "facebook")
    manager = AuthManager(config)
    return manager.complete_oauth(code, flow.redirect_uri)


# ── TikTok ─────────────────────────────────────────────────────────────────

def tiktok_start(config: dict, request_base: str, session: dict) -> str:
    from core.tiktok.auth_manager import TikTokAuthManager

    manager = TikTokAuthManager(config)
    if not manager.is_configured():
        raise OAuthError(
            "Chưa cấu hình TikTok Client Key / Client Secret. Vào Cài đặt → "
            "'TikTok App' để nhập trước khi kết nối."
        )

    redirect_uri = resolve_redirect_uri(config, "tiktok", request_base)
    state = secrets.token_urlsafe(24)
    code_verifier, code_challenge = manager.generate_pkce_pair()
    # The verifier must never leave the server: it is what proves this app
    # (not whoever intercepted the code) is redeeming the authorization code.
    _store.put(PendingFlow(
        provider="tiktok", state=state, redirect_uri=redirect_uri,
        session_nonce=session_nonce(session), code_verifier=code_verifier,
        created_at=time.time(),
    ))
    return manager.build_authorize_url(redirect_uri, state, code_challenge)


def tiktok_finish(config: dict, state: str, code: str, session: dict):
    from core.tiktok.auth_manager import TikTokAuthManager

    flow = _consume(state, session, "tiktok")
    manager = TikTokAuthManager(config)
    return manager.complete_oauth(code, flow.code_verifier, flow.redirect_uri)


def tiktok_scopes(config: dict) -> list[str]:
    """Scopes to show on the disclosure screen — the exact list that will be
    requested, read from config rather than restated here."""
    from core.tiktok.auth_manager import TikTokAuthManager

    raw = TikTokAuthManager(config).scopes
    return [s.strip() for s in str(raw).split(",") if s.strip()]


# ── shared ─────────────────────────────────────────────────────────────────

def _consume(state: str, session: dict, provider: str) -> PendingFlow:
    if not state:
        raise OAuthError("Thiếu tham số state — không thể xác thực callback.")

    flow = _store.take(state)
    if flow is None:
        raise OAuthError(
            "Phiên kết nối không còn hợp lệ (đã hết 10 phút, đã dùng rồi, "
            "hoặc máy chủ vừa khởi động lại). Hãy bấm kết nối lại."
        )
    if flow.provider != provider:
        raise OAuthError("Callback không khớp nền tảng đã yêu cầu.")

    expected = str(session.get(SESSION_NONCE_KEY, "") or "")
    if not expected or not secrets.compare_digest(expected, flow.session_nonce):
        raise OAuthError(
            "Callback đến từ một phiên trình duyệt khác — đã từ chối. "
            "Hãy đăng nhập lại rồi bấm kết nối từ đầu."
        )
    return flow


def provider_error_message(params: dict) -> str:
    """Human-readable text for a provider-side denial, if any."""
    for key in ("error_description", "error_message", "error_reason", "error"):
        value = str(params.get(key, "") or "").strip()
        if value:
            return value
    return ""
