"""
P4/P5 (account modules) and P6 (worker control) web tests.

The security-critical assertion running through all of these: no token,
refresh token, or other credential material may reach the browser. The
service layer returns view dataclasses that simply do not carry those
fields, and the tests below prove it end-to-end through rendered HTML.
"""
from __future__ import annotations

import json
import threading

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from platform_core.password_hashing import hash_password
from server.services.accounts import list_facebook_accounts, list_tiktok_accounts
from server.services.worker_control import (
    NoWorkersConfiguredError,
    WorkerBusyError,
    WorkerController,
    reset_controller_for_tests,
)

ADMIN_PASSWORD = "correct horse battery staple"
FB_TOKEN   = "EAA" + "syntheticFixtureFbToken" + "998877"
TT_TOKEN   = "act." + "syntheticFixtureTtToken" + "554433"


@pytest.fixture(autouse=True)
def _isolate_controller():
    """The worker controller is process-wide by design (ADR-005); reset it
    between tests so a running worker cannot leak across cases."""
    reset_controller_for_tests()
    yield
    reset_controller_for_tests()


# ─── fakes ─────────────────────────────────────────────────────────────────────

class _FakePage:
    def __init__(self, pid, name):
        self.id, self.name = pid, name
        self.category, self.picture_url, self.selected = "Media", "", True


class _FakeFbAccount:
    fb_user_id = "u1"
    name = "Test Account"
    user_token = FB_TOKEN
    is_system_user = False

    def token_status_label(self):
        return "✅ Vĩnh viễn", "#4CAF50"

    def is_token_valid(self):
        return True

    def days_until_expiry(self):
        return -1

    def get_pages_list(self):
        return [_FakePage("p1", "My Page")]


class _FakeFbStore:
    is_unreadable = False
    load_error = None

    def all_accounts(self):
        return [_FakeFbAccount()]


class _UnreadableStore:
    is_unreadable = True
    load_error = "Không giải mã được data/tokens.enc bằng khoá của máy này."

    def all_accounts(self):
        return []


class _FakeTtAccount:
    open_id = "tt1"
    display_name = "TikTok User"
    access_token = TT_TOKEN
    refresh_token = TT_TOKEN

    def token_status_label(self):
        return "✅ Còn 3 ngày", "#4CAF50"

    def is_token_valid(self):
        return True

    def days_until_expiry(self):
        return 3


class _FakeTtStore:
    is_unreadable = False
    load_error = None

    def all_accounts(self):
        return [_FakeTtAccount()]


# ─── service layer ─────────────────────────────────────────────────────────────

def test_facebook_listing_strips_tokens():
    listing = list_facebook_accounts(store=_FakeFbStore())
    assert listing.accounts[0].name == "Test Account"
    assert listing.total_pages == 1
    assert FB_TOKEN not in json.dumps(listing.accounts[0].__dict__, default=str)
    assert not hasattr(listing.accounts[0], "user_token")


def test_tiktok_listing_strips_tokens():
    listing = list_tiktok_accounts(store=_FakeTtStore())
    assert listing.accounts[0].name == "TikTok User"
    assert TT_TOKEN not in json.dumps(listing.accounts[0].__dict__, default=str)


def test_unreadable_store_is_reported_not_shown_as_empty():
    """The audit's core failure mode: a broken store must never look like
    'no accounts connected'."""
    listing = list_facebook_accounts(store=_UnreadableStore())
    assert listing.is_unreadable is True
    assert listing.accounts == []
    assert "Không giải mã được" in listing.unreadable


# ─── worker controller ─────────────────────────────────────────────────────────

def test_controller_refuses_empty_worker_list():
    with pytest.raises(NoWorkersConfiguredError):
        WorkerController().start(workers=[], config={}, platform="facebook")


def test_controller_rejects_second_concurrent_run(monkeypatch):
    class _StubRunner:
        def __init__(self, *, stop_event=None, **kw):
            self.stop_event = stop_event or threading.Event()

        def run(self):
            self.stop_event.wait()

    monkeypatch.setattr("core.worker_app.SheetRunner", _StubRunner)

    controller = WorkerController()
    workers = [{"tab": "T", "account_id": "__test_ctl_busy__"}]
    controller.start(workers, {"anti_spam_session_lock_enabled": False}, "facebook")
    try:
        assert controller.snapshot().running is True
        with pytest.raises(WorkerBusyError):
            controller.start(workers, {"anti_spam_session_lock_enabled": False}, "facebook")
    finally:
        controller.stop()


def test_controller_snapshot_when_never_started():
    snap = WorkerController().snapshot()
    assert snap.running is False
    assert snap.workers == []


def test_controller_log_is_bounded():
    controller = WorkerController()
    for i in range(500):
        controller._on_log(f"line {i}", "info")
    assert len(controller.snapshot().log) <= 300


# ─── web routes ────────────────────────────────────────────────────────────────

def _client(tmp_path) -> TestClient:
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "job_delay_seconds": 30, "max_retries": 3,
        "tiktok_poll_interval_s": 5, "tiktok_upload_timeout_s": 60,
        "tiktok_request_timeout_s": 10, "sheet_id": "abc",
    }), encoding="utf-8")
    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "test-session-secret-not-a-real-secret",
        "LTT_ADMIN_USERNAME": "admin",
        "LTT_ADMIN_PASSWORD_HASH": hash_password(ADMIN_PASSWORD),
    })
    return TestClient(app, base_url="https://testserver", follow_redirects=False)


def _login(client: TestClient) -> None:
    resp = client.get("/login")
    marker = 'name="csrf_token" value="'
    start = resp.text.index(marker) + len(marker)
    token = resp.text[start:resp.text.index('"', start)]
    client.post("/login", data={
        "username": "admin", "password": ADMIN_PASSWORD, "csrf_token": token,
    })


def _csrf_from(html: str) -> str:
    marker = 'name="csrf_token" value="'
    start = html.index(marker) + len(marker)
    return html[start:html.index('"', start)]


@pytest.mark.parametrize("path", ["/facebook", "/tiktok", "/workers", "/api/workers/status"])
def test_new_routes_require_login(tmp_path, path):
    resp = _client(tmp_path).get(path)
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/login")


def test_facebook_page_renders_account_without_leaking_token(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "server.services.accounts.list_facebook_accounts",
        lambda store=None: list_facebook_accounts(store=_FakeFbStore()),
    )
    monkeypatch.setattr(
        "server.routes.accounts.list_facebook_accounts",
        lambda: list_facebook_accounts(store=_FakeFbStore()),
    )
    client = _client(tmp_path)
    _login(client)

    resp = client.get("/facebook")
    assert resp.status_code == 200
    assert "Test Account" in resp.text
    assert "My Page" in resp.text
    assert FB_TOKEN not in resp.text          # the whole point


def test_facebook_page_shows_unreadable_store_loudly(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "server.routes.accounts.list_facebook_accounts",
        lambda: list_facebook_accounts(store=_UnreadableStore()),
    )
    client = _client(tmp_path)
    _login(client)

    resp = client.get("/facebook")
    assert resp.status_code == 200
    assert "Không đọc được kho token" in resp.text
    # The actionable step must be one the operator can actually take on the
    # web. It used to say "open the desktop app", which is wrong now that
    # the desktop is retired — System-User token import is the path that
    # works without a browser OAuth round-trip.
    assert "System User" in resp.text


def test_tiktok_page_renders_without_leaking_token(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "server.routes.accounts.list_tiktok_accounts",
        lambda: list_tiktok_accounts(store=_FakeTtStore()),
    )
    client = _client(tmp_path)
    _login(client)

    resp = client.get("/tiktok")
    assert resp.status_code == 200
    assert "TikTok User" in resp.text
    assert TT_TOKEN not in resp.text


def test_workers_page_reports_no_configured_workers(tmp_path, monkeypatch):
    monkeypatch.setattr("server.routes.workers._stored_workers", lambda p: [])
    client = _client(tmp_path)
    _login(client)

    resp = client.get("/workers")
    assert resp.status_code == 200
    assert "Chưa có worker nào" in resp.text


def test_start_without_workers_returns_conflict_not_crash(tmp_path, monkeypatch):
    monkeypatch.setattr("server.routes.workers._stored_workers", lambda p: [])
    client = _client(tmp_path)
    _login(client)

    page = client.get("/workers")
    resp = client.post("/workers/start", data={
        "csrf_token": _csrf_from(page.text), "platform": "facebook",
    })
    assert resp.status_code == 409
    assert "Chưa có worker" in resp.text


def test_start_requires_valid_csrf(tmp_path, monkeypatch):
    monkeypatch.setattr("server.routes.workers._stored_workers", lambda p: [])
    client = _client(tmp_path)
    _login(client)

    resp = client.post("/workers/start", data={
        "csrf_token": "forged", "platform": "facebook",
    })
    assert resp.status_code == 400


def test_stop_requires_valid_csrf(tmp_path):
    client = _client(tmp_path)
    _login(client)
    resp = client.post("/workers/stop", data={"csrf_token": "forged"})
    assert resp.status_code == 400


def test_start_then_status_api_then_stop(tmp_path, monkeypatch):
    """The end-to-end control-plane loop: web starts the worker, the JSON
    status endpoint reflects it, web stops it."""
    class _StubRunner:
        def __init__(self, *, stop_event=None, **kw):
            self.stop_event = stop_event or threading.Event()

        def run(self):
            self.stop_event.wait()

    monkeypatch.setattr("core.worker_app.SheetRunner", _StubRunner)
    monkeypatch.setattr(
        "server.routes.workers._stored_workers",
        lambda p: [{"tab": "T1", "page": "P1", "account_id": "__test_web_loop__"}],
    )

    client = _client(tmp_path)
    _login(client)

    page = client.get("/workers")
    csrf = _csrf_from(page.text)

    started = client.post("/workers/start", data={
        "csrf_token": csrf, "platform": "facebook",
    })
    assert started.status_code == 303

    status = client.get("/api/workers/status")
    assert status.status_code == 200
    assert status.json()["running"] is True

    stopped = client.post("/workers/stop", data={"csrf_token": csrf})
    assert stopped.status_code == 303

    from server.services.worker_control import get_controller
    assert get_controller().snapshot() is not None


def test_dashboard_surfaces_blockers(tmp_path, monkeypatch):
    """H6.6: blocker doctor KHONG con la banner toan cuc. No gan vao dung the
    app so huu (khop manifest.blocker_titles), hien badge 'can thiet lap'."""
    from tools import doctor

    def _fake_run(check_sheet_flag=False, env=None):
        r = doctor.Report()
        r.add("Tài khoản Facebook", doctor.BLOCK, "unreadable", "reconnect")
        return r

    monkeypatch.setattr(doctor, "run", _fake_run)

    client = _client(tmp_path)
    _login(client)
    resp = client.get("/")
    assert resp.status_code == 200
    # Badge tren the app (socialbot khai blocker_titles co "Tai khoan Facebook").
    assert "cần thiết lập" in resp.text
    assert "Tài khoản Facebook" in resp.text
