"""
Web hardening checks found while auditing the dashboard's features before
putting it on a public domain (app.lttstudios.com).

Two real gaps this guards:
  1. FastAPI's /docs, /redoc and /openapi.json were reachable without
     authentication — free reconnaissance of every route and parameter.
  2. No security response headers at all (clickjacking, MIME sniffing,
     no HSTS on a domain that will be HTTPS-only).
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.auth.password_hashing import hash_password

ADMIN_PASSWORD = "correct horse battery staple"


def _client(tmp_path, environment: str = "local-server-test") -> TestClient:
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "job_delay_seconds": 30, "max_retries": 3,
        "tiktok_poll_interval_s": 5, "tiktok_upload_timeout_s": 60,
        "tiktok_request_timeout_s": 10, "sheet_id": "abc",
    }), encoding="utf-8")
    env = {
        "LTT_ENV": environment,
        "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "test-session-secret-not-a-real-secret",
        "LTT_ADMIN_USERNAME": "admin",
        "LTT_ADMIN_PASSWORD_HASH": hash_password(ADMIN_PASSWORD),
    }
    return TestClient(create_app(env=env), base_url="https://testserver",
                      follow_redirects=False)


# ─── API docs exposure ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
@pytest.mark.parametrize("environment", ["local-server-test", "production"])
def test_api_docs_are_not_exposed_outside_development(tmp_path, path, environment):
    resp = _client(tmp_path, environment).get(path)
    assert resp.status_code == 404, f"{path} must not be reachable in {environment}"


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_api_docs_remain_available_in_development(tmp_path, path):
    """Developer convenience is kept — the risk only exists on a public host."""
    resp = _client(tmp_path, "development").get(path)
    assert resp.status_code == 200


# ─── security headers ──────────────────────────────────────────────────────────

def test_security_headers_present_on_pages(tmp_path):
    resp = _client(tmp_path).get("/login")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "same-origin"
    csp = resp.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in csp
    assert "default-src 'self'" in csp
    assert "form-action 'self'" in csp


def test_dynamic_responses_are_not_cacheable(tmp_path):
    """Response ĐỘNG (ngoài /static/) phải `no-store` để CDN/proxy không cache.

    Khoá lỗi thật ở H5: ảnh output per-user phục vụ ở URL `.png` bị Cloudflare
    cache theo đuôi file rồi trả cho người KHÔNG đăng nhập (bỏ qua auth ở origin).
    """
    c = _client(tmp_path)
    assert c.get("/login").headers.get("Cache-Control") == "no-store"
    assert c.get("/health/ready").headers.get("Cache-Control") == "no-store"
    # /static/ là asset công khai — KHÔNG bị ép no-store (được phép cache).
    st = c.get("/static/htmx.min.js")
    if st.status_code == 200:
        assert st.headers.get("Cache-Control") != "no-store"


def test_hsts_sent_outside_development(tmp_path):
    resp = _client(tmp_path, "production").get("/health/live")
    assert "max-age=" in resp.headers["Strict-Transport-Security"]


def test_hsts_not_sent_in_development(tmp_path):
    """A cached HSTS entry for localhost is painful to undo, and dev runs
    plain HTTP."""
    resp = _client(tmp_path, "development").get("/health/live")
    assert "Strict-Transport-Security" not in resp.headers


def test_security_headers_present_on_error_pages(tmp_path):
    resp = _client(tmp_path).get("/definitely-not-a-page")
    assert resp.status_code == 404
    assert resp.headers["X-Frame-Options"] == "DENY"


def test_correlation_id_still_emitted(tmp_path):
    resp = _client(tmp_path).get("/login")
    assert resp.headers.get("X-Correlation-ID")


# ─── session cookie flags (regression guard) ───────────────────────────────────

def test_session_cookie_flags_outside_development(tmp_path):
    client = _client(tmp_path)
    resp = client.get("/login")
    cookie = resp.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
