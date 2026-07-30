"""
P3 — web platform foundation tests.

Verifies:
  - server.app never imports customtkinter or gui.*
  - /health/live and /health/ready behave correctly
  - anonymous users cannot reach the dashboard (redirected to /login)
  - CSRF protection rejects a login POST without a valid token
  - login rate limiting kicks in after repeated failures
  - a successful login grants access; logout revokes it
  - cookies are marked secure/httponly outside development
  - password hashing round-trips and fails closed on malformed input
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.auth.password_hashing import hash_password, verify_password
from server.auth.rate_limit import RateLimiter
from server.settings import MissingServerSecretError, load_server_settings


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── No-GUI import boundary ───────────────────────────────────────────────────

def test_server_app_does_not_import_gui_or_customtkinter():
    script = (
        "import sys\n"
        "import server.app\n"
        "bad = [m for m in sys.modules if m == 'customtkinter' or m.startswith('gui.') or m == 'gui']\n"
        "assert not bad, bad\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_project_root(), capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


# ─── test app factory ──────────────────────────────────────────────────────────

ADMIN_PASSWORD = "correct horse battery staple"


def _test_env(tmp_path, **overrides) -> dict:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({
        "job_delay_seconds": 30, "max_retries": 3,
        "tiktok_poll_interval_s": 5, "tiktok_upload_timeout_s": 60,
        "tiktok_request_timeout_s": 10, "sheet_id": "abc",
    }), encoding="utf-8")
    env = {
        "LTT_ENV": "local-server-test",
        "LTT_CONFIG_PATH": str(cfg_path),
        "LTT_SESSION_SECRET": "test-session-secret-not-a-real-secret",
        "LTT_ADMIN_USERNAME": "admin",
        "LTT_ADMIN_PASSWORD_HASH": hash_password(ADMIN_PASSWORD),
    }
    env.update(overrides)
    return env


def _client(tmp_path, **overrides) -> TestClient:
    env = _test_env(tmp_path, **overrides)
    app = create_app(env=env)
    # base_url must be https:// — the session cookie is marked Secure
    # (secure_cookies=True for local-server-test/production), and httpx's
    # cookie jar correctly refuses to resend a Secure cookie over plain
    # http, which the default "http://testserver" base_url would be. This
    # mirrors real deployment: the browser always talks HTTPS to Caddy,
    # even though Caddy->uvicorn is a plain-HTTP loopback hop.
    return TestClient(app, base_url="https://testserver", follow_redirects=False)


# ─── health ────────────────────────────────────────────────────────────────────

def test_health_live_always_ok(tmp_path):
    client = _client(tmp_path)
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_ready_ok_when_config_loads(tmp_path):
    client = _client(tmp_path)
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_health_ready_503_when_config_missing(tmp_path):
    env = _test_env(tmp_path, LTT_CONFIG_PATH=str(tmp_path / "does_not_exist.json"))
    app = create_app(env=env)
    client = TestClient(app, follow_redirects=False)
    resp = client.get("/health/ready")
    assert resp.status_code == 503


# ─── authorization boundary ────────────────────────────────────────────────────

def test_anonymous_dashboard_access_redirects_to_login(tmp_path):
    client = _client(tmp_path)
    resp = client.get("/")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_login_page_reachable_anonymously(tmp_path):
    client = _client(tmp_path)
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "csrf_token" in resp.text or "name=\"csrf_token\"" in resp.text


# ─── CSRF ──────────────────────────────────────────────────────────────────────

def test_login_post_without_csrf_token_is_rejected(tmp_path):
    client = _client(tmp_path)
    client.get("/login")  # establishes a session with a csrf token, unused below
    resp = client.post("/login", data={
        "username": "admin", "password": ADMIN_PASSWORD, "csrf_token": "wrong-token",
    })
    assert resp.status_code == 400


# ─── login / logout flow ───────────────────────────────────────────────────────

def _get_csrf_token(client: TestClient) -> str:
    resp = client.get("/login")
    # crude extraction — good enough for a test, avoids adding an HTML parser dep
    marker = 'name="csrf_token" value="'
    start = resp.text.index(marker) + len(marker)
    end = resp.text.index('"', start)
    return resp.text[start:end]


def test_login_wrong_password_returns_401(tmp_path):
    client = _client(tmp_path)
    token = _get_csrf_token(client)
    resp = client.post("/login", data={
        "username": "admin", "password": "wrong-password", "csrf_token": token,
    })
    assert resp.status_code == 401


def test_login_success_then_dashboard_then_logout(tmp_path):
    client = _client(tmp_path)
    token = _get_csrf_token(client)
    resp = client.post("/login", data={
        "username": "admin", "password": ADMIN_PASSWORD, "csrf_token": token,
    })
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"

    dash = client.get("/")
    assert dash.status_code == 200
    assert "admin" in dash.text

    logout_resp = client.post("/logout")
    assert logout_resp.status_code == 303
    assert logout_resp.headers["location"] == "/login"

    dash_after = client.get("/")
    assert dash_after.status_code == 303
    assert dash_after.headers["location"] == "/login"


# ─── rate limiting ──────────────────────────────────────────────────────────────

def test_login_rate_limited_after_repeated_failures(tmp_path):
    client = _client(tmp_path)
    for _ in range(5):
        token = _get_csrf_token(client)
        resp = client.post("/login", data={
            "username": "admin", "password": "wrong", "csrf_token": token,
        })
        assert resp.status_code == 401

    token = _get_csrf_token(client)
    resp = client.post("/login", data={
        "username": "admin", "password": "wrong", "csrf_token": token,
    })
    assert resp.status_code == 429


def test_rate_limiter_unit_allows_then_blocks_then_resets():
    limiter = RateLimiter(max_attempts=2, window_seconds=60.0)
    assert limiter.allow("k") is True
    assert limiter.allow("k") is True
    assert limiter.allow("k") is False
    limiter.reset("k")
    assert limiter.allow("k") is True


# ─── secure cookie configuration ────────────────────────────────────────────────

def test_secure_cookie_flag_set_outside_development(tmp_path):
    client = _client(tmp_path)  # local-server-test -> secure_cookies=True
    token = _get_csrf_token(client)
    resp = client.post("/login", data={
        "username": "admin", "password": ADMIN_PASSWORD, "csrf_token": token,
    })
    set_cookie = resp.headers.get("set-cookie", "")
    assert "httponly" in set_cookie.lower()
    assert "secure" in set_cookie.lower()


def test_development_env_does_not_require_explicit_secrets(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({
        "job_delay_seconds": 30, "max_retries": 3,
        "tiktok_poll_interval_s": 5, "tiktok_upload_timeout_s": 60,
        "tiktok_request_timeout_s": 10, "sheet_id": "abc",
    }), encoding="utf-8")
    settings = load_server_settings(env={
        "LTT_ENV": "development", "LTT_CONFIG_PATH": str(cfg_path),
    })
    assert settings.session_secret  # auto-generated
    assert settings.secure_cookies is False


def test_production_env_requires_explicit_secrets(tmp_path):
    with pytest.raises(MissingServerSecretError):
        load_server_settings(env={"LTT_ENV": "production"})


# ─── password hashing ───────────────────────────────────────────────────────────

def test_password_hash_roundtrip():
    h = hash_password("some-strong-password")
    assert verify_password("some-strong-password", h) is True
    assert verify_password("wrong-password", h) is False


def test_password_hash_never_contains_plaintext():
    h = hash_password("super-secret-value-123")
    assert "super-secret-value-123" not in h


@pytest.mark.parametrize("bad_hash", ["", "not-a-valid-hash", "pbkdf2_sha256$abc$x$y", "md5$1$a$b"])
def test_verify_password_fails_closed_on_malformed_hash(bad_hash):
    assert verify_password("anything", bad_hash) is False


# ─── PB-1: styled error pages ──────────────────────────────────────────────────

def test_unknown_page_renders_styled_html_not_json(tmp_path):
    client = _client(tmp_path)
    resp = client.get("/no-such-page")
    assert resp.status_code == 404
    assert "text/html" in resp.headers["content-type"]
    assert "LTT AI Studio" in resp.text          # base template applied
    assert "Không tìm thấy" in resp.text


def test_health_errors_stay_json_for_machine_probes(tmp_path):
    """The reverse proxy / service manager probes /health — those callers
    must keep getting JSON even though HTML pages exist now."""
    client = _client(tmp_path)
    resp = client.get("/health/nope")
    assert resp.status_code == 404
    assert "application/json" in resp.headers["content-type"]


def test_error_page_includes_correlation_id(tmp_path):
    client = _client(tmp_path)
    resp = client.get("/no-such-page")
    assert resp.headers.get("X-Correlation-ID")
    assert "Mã tra cứu" in resp.text


def test_anonymous_redirect_still_works_with_error_handler(tmp_path):
    """require_login raises an HTTPException carrying a redirect; the new
    error handler must let it through instead of rendering an error page."""
    client = _client(tmp_path)
    resp = client.get("/")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


# ─── PB-2: /status page ────────────────────────────────────────────────────────

def test_status_page_requires_login(tmp_path):
    client = _client(tmp_path)
    resp = client.get("/status")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_status_page_renders_doctor_report_for_logged_in_user(tmp_path):
    client = _client(tmp_path)
    token = _get_csrf_token(client)
    client.post("/login", data={
        "username": "admin", "password": ADMIN_PASSWORD, "csrf_token": token,
    })

    resp = client.get("/status")
    assert resp.status_code == 200
    assert "Tình trạng hệ thống" in resp.text
    # The doctor always reports at least the environment + config checks.
    assert "Môi trường" in resp.text


def test_status_page_does_not_hit_sheet_api_by_default(tmp_path, monkeypatch):
    """Sheet checks cost a network round trip; they must be opt-in."""
    from tools import doctor

    called = {"sheet": False}

    def _spy(report, config, workers):
        called["sheet"] = True

    monkeypatch.setattr(doctor, "check_sheet", _spy)

    client = _client(tmp_path)
    token = _get_csrf_token(client)
    client.post("/login", data={
        "username": "admin", "password": ADMIN_PASSWORD, "csrf_token": token,
    })
    client.get("/status")

    assert called["sheet"] is False
