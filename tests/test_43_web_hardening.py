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


# ─── W1.2: handler 500 tổng ─────────────────────────────────────────────────────

def test_loi_chua_bat_tra_500_co_style_va_no_store(tmp_path):
    """Route raise Exception (không phải HTTPException) phải trả 500 CÓ style,
    no-store và correlation id — không phải 500 trần mất header (có thể bị cache)."""
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "job_delay_seconds": 30, "max_retries": 3, "tiktok_poll_interval_s": 5,
        "tiktok_upload_timeout_s": 60, "tiktok_request_timeout_s": 10,
        "sheet_id": "abc",
    }), encoding="utf-8")
    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "test-session-secret-not-a-real-secret",
        "LTT_ADMIN_USERNAME": "admin",
        "LTT_ADMIN_PASSWORD_HASH": hash_password(ADMIN_PASSWORD),
    })

    @app.get("/_noi_gian_test")
    def _boom():
        raise RuntimeError("no vo co chu dich de test handler 500")

    client = TestClient(app, base_url="https://testserver",
                        follow_redirects=False, raise_server_exceptions=False)
    r = client.get("/_noi_gian_test")
    assert r.status_code == 500
    assert "text/html" in r.headers["content-type"]          # trang có style
    assert r.headers.get("cache-control") == "no-store"      # không bị cache
    assert r.headers.get("X-Correlation-ID")                 # có mã tra cứu
    assert "LTT AI Studio" in r.text                         # base template áp dụng


def test_loi_chua_bat_o_health_van_tra_json(tmp_path):
    """Lỗi ở /health phải giữ JSON cho probe máy, không trả HTML."""
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "job_delay_seconds": 30, "max_retries": 3, "tiktok_poll_interval_s": 5,
        "tiktok_upload_timeout_s": 60, "tiktok_request_timeout_s": 10,
        "sheet_id": "abc",
    }), encoding="utf-8")
    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "test-session-secret-not-a-real-secret",
        "LTT_ADMIN_USERNAME": "admin",
        "LTT_ADMIN_PASSWORD_HASH": hash_password(ADMIN_PASSWORD),
    })

    @app.get("/health/_boom_test")
    def _boom():
        raise RuntimeError("boom")

    client = TestClient(app, base_url="https://testserver",
                        raise_server_exceptions=False)
    r = client.get("/health/_boom_test")
    assert r.status_code == 500
    assert "application/json" in r.headers["content-type"]


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
    # App video cần media-src (blob: đọc metadata client + R2 phát video presigned).
    assert "media-src 'self' blob:" in csp
    assert "r2.cloudflarestorage.com" in csp
    # connect-src cho upload thẳng browser→R2 (presigned PUT).
    assert "connect-src 'self' https://*.r2.cloudflarestorage.com" in csp
    assert "https://cloudflareinsights.com" in csp
    assert "https://static.cloudflareinsights.com" in csp
    # img-src cho ảnh output phục vụ qua R2 presigned (app chat AI, ảnh…).
    assert "img-src 'self' data: https://*.r2.cloudflarestorage.com" in csp


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


def test_favicon_ico_redirects_to_existing_static_asset(tmp_path):
    response = _client(tmp_path).get("/favicon.ico", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/favicon.svg"


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
