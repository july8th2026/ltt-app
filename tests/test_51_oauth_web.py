"""W5 — provider OAuth in the web app.

The security properties are the point of these tests, not the happy path:
a callback endpoint that writes into the encrypted token store must not be
drivable by anyone who merely learns a `state` value, and a PKCE verifier
must never be replayable.
"""
from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from platform_core.password_hashing import hash_password
from server.services import oauth_service
from server.services.oauth_service import (
    CALLBACK_PATHS,
    FlowStore,
    OAuthError,
    PendingFlow,
    callback_url,
    resolve_redirect_uri,
    session_nonce,
)

ADMIN_PASSWORD = "correct horse battery staple"
FB_CALLBACK = "https://app.lttstudios.com/oauth/facebook/callback"
TT_CALLBACK = "https://app.lttstudios.com/oauth/tiktok/callback"


@pytest.fixture(autouse=True)
def _clean_store():
    oauth_service.store().clear()
    yield
    oauth_service.store().clear()


def _app_env(tmp_path, **config):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(config), encoding="utf-8")
    return {
        "LTT_ENV": "local-server-test",
        "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "test-session-secret-not-a-real-secret",
        "LTT_ADMIN_USERNAME": "admin",
        "LTT_ADMIN_PASSWORD_HASH": hash_password(ADMIN_PASSWORD),
    }


@pytest.fixture
def client(tmp_path) -> TestClient:
    app = create_app(env=_app_env(
        tmp_path,
        meta_app_id="123456789", meta_app_secret="fake-meta-secret-value",
        meta_redirect_uri=FB_CALLBACK,
        tiktok_client_key="fakeclientkey", tiktok_client_secret="fake-tt-secret",
        tiktok_redirect_uri=TT_CALLBACK,
        tiktok_scopes="user.info.basic,video.upload,video.publish",
    ))
    return TestClient(app, base_url="https://app.lttstudios.com",
                      follow_redirects=False)


def _login(c: TestClient) -> None:
    r = c.get("/login")
    marker = 'name="csrf_token" value="'
    start = r.text.index(marker) + len(marker)
    c.post("/login", data={"username": "admin", "password": ADMIN_PASSWORD,
                           "csrf_token": r.text[start:r.text.index('"', start)]})


def _csrf(html: str) -> str:
    marker = 'name="csrf_token" value="'
    start = html.index(marker) + len(marker)
    return html[start:html.index('"', start)]


@pytest.fixture
def logged_in(client) -> TestClient:
    _login(client)
    return client


# ── flow store ─────────────────────────────────────────────────────────────

def _flow(state="s1", nonce="n1", provider="facebook", age=0.0):
    return PendingFlow(provider=provider, state=state, redirect_uri=FB_CALLBACK,
                       session_nonce=nonce, created_at=time.time() - age)


def test_flow_is_single_use():
    store = FlowStore()
    store.put(_flow())
    assert store.take("s1") is not None
    assert store.take("s1") is None, "a replayed callback must find nothing"


def test_expired_flow_is_refused():
    store = FlowStore()
    store.put(_flow(age=oauth_service.FLOW_TTL_S + 1))
    assert store.take("s1") is None


def test_store_is_bounded():
    store = FlowStore()
    for i in range(oauth_service.MAX_PENDING + 10):
        store.put(_flow(state=f"s{i}"))
    assert store.pending_count() <= oauth_service.MAX_PENDING


def test_expired_flows_are_pruned_not_just_hidden():
    store = FlowStore()
    store.put(_flow(state="old", age=oauth_service.FLOW_TTL_S + 1))
    store.put(_flow(state="new"))
    assert store.pending_count() == 1


# ── session binding ────────────────────────────────────────────────────────

def test_session_nonce_is_minted_once_and_reused():
    session: dict = {}
    first = session_nonce(session)
    assert first and session_nonce(session) == first


def test_callback_from_a_different_session_is_refused():
    """The core reason the nonce exists: knowing `state` must not be enough."""
    oauth_service.store().put(_flow(state="st", nonce="browser-A"))
    with pytest.raises(OAuthError, match="phiên trình duyệt khác"):
        oauth_service._consume("st", {"oauth_nonce": "browser-B"}, "facebook")


def test_callback_with_no_session_nonce_is_refused():
    oauth_service.store().put(_flow(state="st", nonce="browser-A"))
    with pytest.raises(OAuthError, match="phiên trình duyệt khác"):
        oauth_service._consume("st", {}, "facebook")


def test_provider_cannot_be_crossed():
    """A TikTok callback must not redeem a Facebook flow."""
    oauth_service.store().put(_flow(state="st", nonce="n", provider="facebook"))
    with pytest.raises(OAuthError, match="không khớp nền tảng"):
        oauth_service._consume("st", {"oauth_nonce": "n"}, "tiktok")


def test_missing_state_is_refused():
    with pytest.raises(OAuthError, match="Thiếu tham số state"):
        oauth_service._consume("", {"oauth_nonce": "n"}, "facebook")


def test_unknown_state_message_explains_the_likely_causes():
    with pytest.raises(OAuthError, match="không còn hợp lệ"):
        oauth_service._consume("never-issued", {"oauth_nonce": "n"}, "facebook")


# ── redirect URI resolution ────────────────────────────────────────────────

BASE = "https://app.lttstudios.com"


def test_callback_url_shape():
    assert callback_url(BASE, "facebook") == FB_CALLBACK
    assert callback_url(BASE + "/", "tiktok") == TT_CALLBACK


def test_unknown_provider_is_refused():
    with pytest.raises(OAuthError):
        callback_url(BASE, "instagram")


def test_missing_redirect_uri_names_the_config_key_and_the_portal():
    with pytest.raises(OAuthError) as exc:
        resolve_redirect_uri({}, "facebook", BASE)
    text = str(exc.value)
    assert "meta_redirect_uri" in text
    assert FB_CALLBACK in text
    assert "Valid OAuth Redirect URIs" in text


def test_http_redirect_uri_is_refused():
    with pytest.raises(OAuthError, match="phải là HTTPS"):
        resolve_redirect_uri(
            {"tiktok_redirect_uri": "http://app.lttstudios.com/oauth/tiktok/callback"},
            "tiktok", BASE)


def test_stale_desktop_bridge_page_is_diagnosed():
    """The real config still points at the desktop's static bridge page. That
    must produce an actionable message, not an opaque provider error later."""
    with pytest.raises(OAuthError) as exc:
        resolve_redirect_uri(
            {"tiktok_redirect_uri": "https://lttstudios.com/legal/callback.html"},
            "tiktok", BASE)
    text = str(exc.value)
    assert "callback.html" in text
    assert TT_CALLBACK in text
    assert "Redirect URI" in text


def test_correct_redirect_uri_is_accepted():
    assert resolve_redirect_uri(
        {"meta_redirect_uri": FB_CALLBACK}, "facebook", BASE) == FB_CALLBACK


# ── start: authorize URL ───────────────────────────────────────────────────

def test_facebook_start_builds_a_urlencoded_authorize_url():
    session: dict = {}
    url = oauth_service.facebook_start(
        {"meta_app_id": "123", "meta_app_secret": "shh",
         "meta_redirect_uri": FB_CALLBACK, "graph_api_version": "v21.0"},
        BASE, session)

    assert url.startswith("https://www.facebook.com/v21.0/dialog/oauth?")
    # The desktop interpolated raw, which would have broken on any URI with a
    # query string. Everything must be percent-encoded now.
    assert "redirect_uri=https%3A%2F%2Fapp.lttstudios.com" in url
    assert "response_type=code" in url
    assert oauth_service.store().pending_count() == 1
    assert session["oauth_nonce"]


def test_tiktok_start_sends_s256_challenge_and_keeps_verifier_server_side():
    session: dict = {}
    url = oauth_service.tiktok_start(
        {"tiktok_client_key": "ck", "tiktok_client_secret": "cs",
         "tiktok_redirect_uri": TT_CALLBACK,
         "tiktok_scopes": "user.info.basic,video.upload"}, BASE, session)

    assert url.startswith("https://www.tiktok.com/v2/auth/authorize/?")
    assert "code_challenge_method=S256" in url
    assert "code_challenge=" in url

    flow = oauth_service.store().take(_state_from(url))
    assert flow.code_verifier, "verifier must be stored for the exchange"
    # The verifier is the secret half of PKCE — it must never be in the URL
    # the operator's browser (or TikTok) sees.
    assert flow.code_verifier not in url


def _state_from(url: str) -> str:
    from urllib.parse import parse_qs, urlparse
    return parse_qs(urlparse(url).query)["state"][0]


def test_pkce_challenge_is_base64url_sha256_of_the_verifier():
    import base64
    import hashlib

    from core.tiktok.auth_manager import TikTokAuthManager
    verifier, challenge = TikTokAuthManager.generate_pkce_pair()
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    assert challenge == expected
    assert "=" not in challenge


def test_unconfigured_app_is_refused_before_any_redirect():
    with pytest.raises(OAuthError, match="Meta App ID"):
        oauth_service.facebook_start({"meta_redirect_uri": FB_CALLBACK}, BASE, {})
    with pytest.raises(OAuthError, match="TikTok Client Key"):
        oauth_service.tiktok_start({"tiktok_redirect_uri": TT_CALLBACK}, BASE, {})


def test_start_failure_leaves_no_pending_flow():
    with pytest.raises(OAuthError):
        oauth_service.facebook_start({}, BASE, {})
    assert oauth_service.store().pending_count() == 0


# ── provider-side denial ───────────────────────────────────────────────────

def test_provider_error_prefers_the_most_descriptive_field():
    assert oauth_service.provider_error_message(
        {"error": "access_denied", "error_description": "User denied"}
    ) == "User denied"
    assert oauth_service.provider_error_message({"error": "access_denied"}) \
        == "access_denied"
    assert oauth_service.provider_error_message({}) == ""


# ── routes ─────────────────────────────────────────────────────────────────

def test_all_oauth_routes_require_login(client):
    for path in ("/oauth/facebook/callback", "/oauth/tiktok/callback",
                 "/oauth/tiktok/disclosure"):
        r = client.get(path)
        assert r.status_code in (302, 303, 307, 401), path
    for path in ("/oauth/facebook/start", "/oauth/tiktok/start"):
        r = client.post(path, data={"csrf_token": "x"})
        assert r.status_code in (302, 303, 307, 401), path


def test_facebook_start_redirects_to_facebook(logged_in):
    page = logged_in.get("/facebook")
    r = logged_in.post("/oauth/facebook/start",
                       data={"csrf_token": _csrf(page.text)})
    assert r.status_code == 303
    assert r.headers["location"].startswith("https://www.facebook.com/")


def test_facebook_start_needs_csrf(logged_in):
    r = logged_in.post("/oauth/facebook/start", data={"csrf_token": "forged"})
    assert r.status_code == 303
    assert r.headers["location"] == "/facebook"
    assert oauth_service.store().pending_count() == 0


def test_tiktok_disclosure_lists_the_exact_scopes_requested(logged_in):
    r = logged_in.get("/oauth/tiktok/disclosure")
    assert r.status_code == 200
    for scope in ("user.info.basic", "video.upload", "video.publish"):
        assert scope in r.text
    assert "video.upload" in r.text


def test_tiktok_start_refuses_without_consent(logged_in):
    """TikTok audit requires disclosure before redirect. No consent, no
    redirect — and no pending flow left behind."""
    page = logged_in.get("/oauth/tiktok/disclosure")
    r = logged_in.post("/oauth/tiktok/start", data={"csrf_token": _csrf(page.text)})
    assert r.status_code == 400
    assert "Chưa xác nhận" in r.text
    assert oauth_service.store().pending_count() == 0


def test_tiktok_start_redirects_only_with_consent(logged_in):
    page = logged_in.get("/oauth/tiktok/disclosure")
    r = logged_in.post("/oauth/tiktok/start",
                       data={"csrf_token": _csrf(page.text), "consent": "yes"})
    assert r.status_code == 303
    assert r.headers["location"].startswith("https://www.tiktok.com/v2/auth/authorize/")


def test_disclosure_is_the_only_path_to_start(logged_in):
    """There must be no GET route that skips the consent screen."""
    assert logged_in.get("/oauth/tiktok/start").status_code == 405


def test_callback_with_unknown_state_shows_an_explanation(logged_in):
    r = logged_in.get("/oauth/facebook/callback?state=bogus&code=abc")
    assert r.status_code == 400
    assert "không còn hợp lệ" in r.text


def test_callback_reports_user_denial_without_touching_the_store(logged_in):
    r = logged_in.get("/oauth/tiktok/callback"
                      "?error=access_denied&error_description=User+cancelled")
    assert r.status_code == 400
    assert "User cancelled" in r.text


def test_accounts_page_shows_the_real_callback_uri(logged_in):
    """The page used to explain why OAuth was impossible. It must now tell the
    operator the exact URL to register."""
    fb = logged_in.get("/facebook").text
    assert "/oauth/facebook/callback" in fb
    assert "meta_redirect_uri" in fb
    tt = logged_in.get("/tiktok").text
    assert "/oauth/tiktok/callback" in tt
    assert "tiktok_redirect_uri" in tt


def test_blocked_reason_text_is_gone():
    """A stale 'OAuth chưa dùng được' message would be an outright lie now."""
    import server.services.accounts_actions as actions
    assert not hasattr(actions, "OAUTH_BLOCKED_REASON")


def test_callback_paths_match_the_routes(client):
    """The registered paths and the advertised paths must not drift.

    Probed over HTTP rather than by walking ``app.routes``. Introspecting the
    router is version-fragile: Starlette 1.x wraps included routers in an
    ``_IncludedRouter`` that exposes no ``.path``, so the old assertion started
    failing on a library upgrade while every callback still worked. An HTTP
    probe is also the stronger check — it proves the path is *reachable*, not
    merely that an object with a matching attribute exists somewhere.

    404 is the only failing answer. Anonymous requests legitimately answer 303
    (bounce to /login) and a callback missing its OAuth parameters legitimately
    answers 4xx; both prove the route is registered.
    """
    for path in CALLBACK_PATHS.values():
        response = client.get(path, follow_redirects=False)
        assert response.status_code != 404, (
            f"{path} khong duoc dang ky - callback URL da khai bao o "
            f"Meta/TikTok Portal se tra 404"
        )
