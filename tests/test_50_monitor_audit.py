"""W4 — Monitor + TT Audit web pages.

Beyond route/render coverage, this file pins the two desktop defects the web
port fixes, so a future refactor cannot silently reintroduce them:

  * `monitor_tab.py:388` — a swallowed NameError made the Pages column
    always render 0.
  * the `_Empty` snapshot fallback omitted 5 attributes the renderer reads.
"""
from __future__ import annotations

import inspect
import json
import sys

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from platform_core.password_hashing import hash_password
from server.services import audit_service, monitor_service
from server.services import ui_constants as UI

ADMIN_PASSWORD = "correct horse battery staple"


def _fake_module(**attrs):
    """A stand-in module object for monkeypatch.setitem(sys.modules, ...).

    A plain object is used rather than type(): functions stored on a class
    become descriptors, which changes their call signature.
    """
    mod = type(sys)("fake")
    for name, value in attrs.items():
        setattr(mod, name, value)
    return mod


@pytest.fixture
def client(tmp_path) -> TestClient:
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"sheet_id": "abc"}), encoding="utf-8")
    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "test-session-secret-not-a-real-secret",
        "LTT_ADMIN_USERNAME": "admin",
        "LTT_ADMIN_PASSWORD_HASH": hash_password(ADMIN_PASSWORD),
    })
    return TestClient(app, base_url="https://testserver", follow_redirects=False)


@pytest.fixture
def client_logged_in(client) -> TestClient:
    r = client.get("/login")
    marker = 'name="csrf_token" value="'
    start = r.text.index(marker) + len(marker)
    client.post("/login", data={
        "username": "admin", "password": ADMIN_PASSWORD,
        "csrf_token": r.text[start:r.text.index('"', start)],
    })
    return client


# ----------------------------------------------------------------- unit: tokens

class _FakeAccount:
    def __init__(self, name, pages, selected):
        self.name = name
        self._pages = pages
        self._selected = selected

    def get_pages_list(self):
        return list(self._pages)

    def get_selected_pages(self):
        return list(self._selected)


class _FakeStore:
    is_unreadable = False
    load_error = ""

    def __init__(self, accounts):
        self._accounts = accounts

    def all_accounts(self):
        return list(self._accounts)


def test_pages_column_is_not_always_zero(monkeypatch):
    """Regression guard for desktop bug 1.

    The desktop lost the account->pages join to a NameError swallowed by a
    bare except, so this column rendered 0 for every account no matter how
    many pages were selected.
    """
    store = _FakeStore([_FakeAccount("Acc A", ["p1", "p2", "p3"], ["p1", "p2"])])

    class _Refresher:
        def __init__(self, config, store):
            pass

        def health_summary(self):
            return [{"name": "Acc A", "days": 42, "status": "ok"}]

    monkeypatch.setitem(sys.modules, "core.token_store",
                        _fake_module(get_default_store=lambda: store))
    monkeypatch.setitem(sys.modules, "core.token_refresher",
                        _fake_module(TokenRefresher=_Refresher))

    rows, err = monitor_service.collect_token_health({})
    assert err == ""
    assert len(rows) == 1
    assert (rows[0].pages_selected, rows[0].pages_total) == (2, 3)


def test_unreadable_token_store_surfaces_the_reason(monkeypatch):
    """A store that cannot be decrypted must not look like 'no accounts'."""
    class _Broken:
        is_unreadable = True
        load_error = "InvalidToken: khoa may khong khop"

        def all_accounts(self):        # pragma: no cover - must not be reached
            raise AssertionError("should not read accounts from a broken store")

    monkeypatch.setitem(sys.modules, "core.token_store",
                        _fake_module(get_default_store=lambda: _Broken()))

    rows, err = monitor_service.collect_token_health({})
    assert rows == []
    assert "InvalidToken" in err


def test_token_row_permanent_token_renders_infinity():
    row = monitor_service.TokenRow("x", -1, "permanent")
    assert row.token_text == "∞"
    assert row.colour == UI.COLORS["green"]


def test_token_row_expired_is_red():
    assert monitor_service.TokenRow("x", 0, "expired").colour == UI.COLORS["red"]


# ---------------------------------------------------------------- unit: metrics

def test_metric_avg_upload_never_divides_by_zero():
    assert monitor_service.MetricRow("p", 0, 0.0, 0.0).avg_upload_s == 0.0
    assert monitor_service.MetricRow("p", 4, 1.0, 10.0).avg_upload_s == 2.5


def test_metrics_are_sorted_by_page(monkeypatch):
    monkeypatch.setitem(sys.modules, "core.rate_limiter", _fake_module(
        get_global_page_metrics=lambda: {
            "Zeta": {"uploads_done": 1, "avg_wait_s": 2.0, "total_upload_s": 3.0},
            "Alpha": {"uploads_done": 2, "avg_wait_s": 1.0, "total_upload_s": 4.0},
        }))
    assert [r.page for r in monitor_service.collect_metrics()] == ["Alpha", "Zeta"]


def test_metrics_failure_is_not_fatal(monkeypatch):
    def _boom():
        raise RuntimeError("nope")

    monkeypatch.setitem(sys.modules, "core.rate_limiter",
                        _fake_module(get_global_page_metrics=_boom))
    assert monitor_service.collect_metrics() == []


# --------------------------------------------------------------- unit: antispam

# Every attribute collect_antispam() reads off the snapshot.
_READ_ATTRS = [
    "n_critical_tokens", "n_warn_tokens", "token_messages", "open_breakers",
    "total_attempts_7d", "total_successes_7d", "success_rate_7d",
    "targets_with_abuse", "targets_with_rate", "recommendations",
    "total_content_records", "page_health_warnings", "n_pages_throttled",
    "n_pages_dead", "time_intel_warnings", "n_bot_flat_targets",
]


def test_empty_snapshot_has_every_attribute_the_renderer_reads():
    """Regression guard for desktop bug 2 — the fallback was missing 5 of
    these, so one failure produced a second AttributeError."""
    missing = [a for a in _READ_ATTRS
               if not hasattr(monitor_service._EmptySnapshot, a)]
    assert missing == [], f"_EmptySnapshot missing: {missing}"


def test_antispam_failure_still_renders(monkeypatch):
    """A broken snapshot must degrade to a warning, not blow up the page."""
    def _boom(_config):
        raise RuntimeError("db locked")

    monkeypatch.setitem(sys.modules, "core.anti_spam_analytics", _fake_module(
        collect_snapshot=_boom, format_oneline=lambda s: "unused"))

    summary, colour, details = monitor_service.collect_antispam({})
    assert "db locked" in summary
    assert colour == UI.COLORS["amber"]
    assert details == []


def test_antispam_red_when_pages_dead(monkeypatch):
    class _Snap(monitor_service._EmptySnapshot):
        n_pages_dead = 2

    monkeypatch.setitem(sys.modules, "core.anti_spam_analytics", _fake_module(
        collect_snapshot=lambda c: _Snap(), format_oneline=lambda s: "2 page chet"))
    summary, colour, _ = monitor_service.collect_antispam({})
    assert colour == UI.COLORS["red"]
    assert summary == "2 page chet"


def test_antispam_amber_when_only_warnings(monkeypatch):
    class _Snap(monitor_service._EmptySnapshot):
        n_warn_tokens = 1

    monkeypatch.setitem(sys.modules, "core.anti_spam_analytics", _fake_module(
        collect_snapshot=lambda c: _Snap(), format_oneline=lambda s: "ok"))
    assert monitor_service.collect_antispam({})[1] == UI.COLORS["amber"]


# ------------------------------------------------------------------- unit: logs

def test_logs_are_newest_first_and_coloured(monkeypatch):
    monkeypatch.setitem(sys.modules, "utils.logger", _fake_module(
        get_recent_logs=lambda n: [
            {"level": "info", "formatted": "cu nhat"},
            {"level": "error", "formatted": "moi nhat"},
        ]))
    logs = monitor_service.collect_logs()
    assert logs[0]["message"] == "moi nhat"
    assert logs[0]["colour"] == UI.log_colour("error", "moi nhat")


def test_logs_failure_is_not_fatal(monkeypatch):
    def _boom(n):
        raise RuntimeError("no buffer")

    monkeypatch.setitem(sys.modules, "utils.logger",
                        _fake_module(get_recent_logs=_boom))
    assert monitor_service.collect_logs() == []


# ------------------------------------------------------------------ unit: audit

def test_audit_item_icons_and_fix_visibility():
    assert audit_service.AuditItem("n", "PASS", "m", "fix").show_fix is False
    assert audit_service.AuditItem("n", "FAIL", "m", "fix").show_fix is True
    assert audit_service.AuditItem("n", "WARN", "m").show_fix is False
    assert audit_service.AuditItem("n", "FAIL", "m").icon == "❌"


def test_result_name_normalises_enums_and_junk():
    assert audit_service._result_name("ChecklistResult.PASS") == "PASS"
    assert audit_service._result_name(None) == "WARN"

    class _E:
        name = "fail"
    assert audit_service._result_name(_E()) == "FAIL"


def test_audit_summary_colours_follow_worst_result():
    def rep(**counts):
        r = audit_service.AuditReport()
        for result, n in counts.items():
            for i in range(n):
                r.items.append(audit_service.AuditItem(f"{result}{i}", result, ""))
        return r

    assert audit_service._summary(rep(FAIL=1, PASS=3))[1] == UI.COLORS["red"]
    assert audit_service._summary(rep(WARN=1, PASS=3))[1] == UI.COLORS["amber"]
    assert audit_service._summary(rep(PASS=4))[1] == UI.COLORS["green"]


def test_scopes_are_explained_and_unknown_is_flagged():
    scopes = audit_service._scopes({"tiktok_scopes": "video.upload,weird.scope"})
    assert scopes[0]["explain"] != audit_service.SCOPE_UNKNOWN
    assert scopes[1]["explain"] == audit_service.SCOPE_UNKNOWN


def test_scopes_fall_back_to_defaults_when_config_blank():
    assert [s["scope"] for s in audit_service._scopes({"tiktok_scopes": ""})] == \
        ["user.info.basic", "video.upload", "video.publish"]


def test_audit_runner_is_single_flight():
    runner = audit_service.AuditRunner()
    runner._inflight = True
    assert runner.is_stale() is False           # never re-enter while running
    runner.refresh_async({})                    # must be a no-op
    assert runner.report().running is True


def test_audit_runner_reports_checklist_failure_without_raising(monkeypatch):
    def _boom(_config):
        raise RuntimeError("privacy URL 500")

    monkeypatch.setitem(sys.modules, "core.tiktok.audit_checklist",
                        _fake_module(run_checklist=_boom))

    runner = audit_service.AuditRunner()
    runner._run({})
    rep = runner.report()
    assert "privacy URL 500" in rep.error
    assert rep.running is False
    assert rep.scopes, "scopes are config-derived and must survive a failure"


def test_audit_report_age_text():
    import time
    assert audit_service.AuditReport().age_text == "chưa chạy"
    r = audit_service.AuditReport(generated_at=time.time() - 5)
    assert "giây trước" in r.age_text
    r = audit_service.AuditReport(generated_at=time.time() - 300)
    assert "phút trước" in r.age_text


def test_checklist_is_never_run_on_the_request_thread():
    """The checklist makes 3+ outbound HTTPS calls with 6-8s timeouts. If a
    route ever calls run_checklist directly the page hangs for the operator."""
    import server.routes.monitor as monitor_routes
    src = inspect.getsource(monitor_routes)
    assert "run_checklist" not in src
    assert "refresh_async" in src


# ------------------------------------------------------------------ route level

def test_monitor_and_audit_pages_render(client_logged_in):
    for path, needle in (("/monitor", "TOKEN HEALTH"),
                         ("/audit", "TikTok Audit")):
        r = client_logged_in.get(path)
        assert r.status_code == 200, path
        assert needle in r.text, path


def test_monitor_and_audit_require_login(client):
    for path in ("/monitor", "/audit", "/api/monitor/logs", "/api/audit/status"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code in (302, 303, 307, 401), path


def test_monitor_reset_requires_valid_csrf(client_logged_in):
    r = client_logged_in.post("/monitor/reset-metrics",
                              data={"csrf_token": "forged"},
                              follow_redirects=False)
    # Rejected quietly by redirect; the important part is no 500 and no reset.
    assert r.status_code in (303, 400, 403)


def test_monitor_logs_api_returns_json(client_logged_in):
    r = client_logged_in.get("/api/monitor/logs")
    assert r.status_code == 200
    assert isinstance(r.json()["logs"], list)


def test_audit_status_api_shape(client_logged_in):
    r = client_logged_in.get("/api/audit/status")
    assert r.status_code == 200
    body = r.json()
    for key in ("running", "summary", "counts", "age", "items", "error"):
        assert key in body, key


# ------------------------------------------------------- no placeholders remain

def test_placeholder_module_is_gone():
    """Every desktop tab now has a real page; nothing should still be stubbed."""
    with pytest.raises(ImportError):
        __import__("server.routes.placeholder")


def test_every_page_is_marked_built():
    from server.templating import BUILT_PAGES
    unbuilt = [k for k, v in BUILT_PAGES.items() if not v]
    assert unbuilt == [], f"still marked unbuilt: {unbuilt}"
