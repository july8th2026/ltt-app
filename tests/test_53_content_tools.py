"""The three Content Vault actions from the desktop Settings tab.

These were found missing during W6: `gui/settings_tab.py` had Export Content
History, Cross-target duplicates, and Import CSV, and the web had no trace of
any of them. Config-key coverage was complete, which is exactly why the gap
went unnoticed — the buttons were not config.
"""
from __future__ import annotations

import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from platform_core.password_hashing import hash_password
from server.services import content_tools

ADMIN_PASSWORD = "correct horse battery staple"


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
def logged_in(client) -> TestClient:
    r = client.get("/login")
    marker = 'name="csrf_token" value="'
    start = r.text.index(marker) + len(marker)
    client.post("/login", data={"username": "admin", "password": ADMIN_PASSWORD,
                                "csrf_token": r.text[start:r.text.index('"', start)]})
    return client


def _csrf(html: str) -> str:
    marker = 'name="csrf_token" value="'
    start = html.index(marker) + len(marker)
    return html[start:html.index('"', start)]


# ── export ─────────────────────────────────────────────────────────────────

def test_export_filename_is_timestamped():
    name = content_tools.export_filename()
    assert name.startswith("content_history_")
    assert name.endswith(".csv")


def test_export_reuses_the_shared_writer(monkeypatch):
    """The column layout must come from core.content_vault, not be restated
    for the web — two writers would drift."""
    import inspect
    assert "from core.content_vault import export_to_csv" in \
        inspect.getsource(content_tools.export_history_csv)


def test_export_returns_text_and_count(monkeypatch):
    import core.content_vault as vault

    def fake_export(path):
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["video_hash", "target"])
            w.writerow(["abc123", "PageA"])
        return 1

    monkeypatch.setattr(vault, "export_to_csv", fake_export)
    text, count = content_tools.export_history_csv()
    assert count == 1
    assert "abc123" in text


def test_export_download_has_a_filename_and_bom(logged_in, monkeypatch):
    """A CSV without a BOM opens as mojibake in Excel, which is where an
    operator will actually open it."""
    import core.content_vault as vault
    monkeypatch.setattr(vault, "export_to_csv",
                        lambda path: (open(path, "w", encoding="utf-8")
                                      .write("video_hash\nTiệm truyện\n"), 1)[1])

    page = logged_in.get("/settings")
    r = logged_in.post("/settings/export-history",
                       data={"csrf_token": _csrf(page.text)})
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert "content_history_" in r.headers["content-disposition"]
    assert r.content.startswith(b"\xef\xbb\xbf"), "missing UTF-8 BOM"


def test_export_requires_csrf(logged_in):
    r = logged_in.post("/settings/export-history", data={"csrf_token": "forged"})
    assert r.status_code == 400
    assert "text/html" in r.headers["content-type"]


def test_export_requires_login(client):
    r = client.post("/settings/export-history", data={"csrf_token": "x"})
    assert r.status_code in (302, 303, 307, 401)


# ── cross-target duplicates ────────────────────────────────────────────────

class _Group:
    def __init__(self, h, count, targets):
        self.video_hash, self.count, self.targets = h, count, targets


def test_no_duplicates_reads_as_good_news(monkeypatch):
    """The desktop framed an empty result as a healthy setup rather than an
    error; an operator should not go hunting for a problem."""
    import core.content_vault as vault
    monkeypatch.setattr(vault, "find_cross_target_duplicates", lambda min_targets: [])
    report = content_tools.find_duplicates()
    assert report.total == 0
    assert "setup" in report.summary and "tốt" in report.summary


def test_duplicates_are_summarised_and_capped(monkeypatch):
    import core.content_vault as vault
    many = [_Group(f"hash{i:04d}" + "x" * 20, 2, ["A", "B"]) for i in range(40)]
    monkeypatch.setattr(vault, "find_cross_target_duplicates", lambda min_targets: many)

    report = content_tools.find_duplicates()
    assert report.total == 40
    assert len(report.groups) == content_tools.MAX_DUPLICATE_GROUPS
    assert report.groups[0].hash_short == "hash0000" + "xxxx"


def test_duplicate_targets_are_truncated_with_an_ellipsis(monkeypatch):
    import core.content_vault as vault
    group = _Group("h" * 20, 6, ["A", "B", "C", "D", "E", "F"])
    monkeypatch.setattr(vault, "find_cross_target_duplicates",
                        lambda min_targets: [group])
    text = content_tools.find_duplicates().groups[0].targets_text
    assert text.endswith("...")
    assert "E" not in text


def test_duplicate_lookup_failure_is_reported_not_raised(monkeypatch):
    import core.content_vault as vault

    def boom(min_targets):
        raise RuntimeError("db locked")

    monkeypatch.setattr(vault, "find_cross_target_duplicates", boom)
    report = content_tools.find_duplicates()
    assert "db locked" in report.error
    assert "db locked" in report.summary


def test_duplicates_page_renders(logged_in, monkeypatch):
    import core.content_vault as vault
    monkeypatch.setattr(vault, "find_cross_target_duplicates", lambda min_targets: [])
    page = logged_in.get("/settings")
    r = logged_in.post("/settings/duplicates", data={"csrf_token": _csrf(page.text)})
    assert r.status_code == 200
    assert "mỗi page có content riêng" in r.text


# ── calendar CSV import ────────────────────────────────────────────────────

def test_import_rejects_a_missing_file():
    assert "Chưa chọn file" in content_tools.import_calendar_csv("", b"").fatal


def test_import_rejects_a_non_csv():
    assert "Chỉ nhận file .csv" in \
        content_tools.import_calendar_csv("video.mp4", b"data").fatal


def test_import_rejects_an_empty_file():
    assert "rỗng" in content_tools.import_calendar_csv("plan.csv", b"").fatal


def test_import_rejects_an_oversized_file():
    """A content calendar is text. A huge upload means the wrong file was
    picked, and saying so beats a parser error."""
    big = b"x" * (content_tools.MAX_IMPORT_BYTES + 1)
    report = content_tools.import_calendar_csv("plan.csv", big)
    assert "vượt giới hạn" in report.fatal
    assert "chọn nhầm file" in report.fatal


class _Row:
    def __init__(self, platform, target_page, title):
        self.platform, self.target_page, self.title = platform, target_page, title


class _Result:
    def __init__(self, rows, errors):
        self.rows, self.errors = rows, errors


def test_import_previews_rows_and_counts_overflow(monkeypatch):
    import core.content_calendar as cal
    rows = [_Row("facebook", f"Page{i}", f"Video {i}") for i in range(9)]
    monkeypatch.setattr(cal, "import_csv", lambda path: _Result(rows, []))

    report = content_tools.import_calendar_csv("plan.csv", b"a,b\n1,2\n")
    assert report.ok_rows == 9
    assert len(report.preview) == content_tools.PREVIEW_ROWS
    assert report.row_overflow == 9 - content_tools.PREVIEW_ROWS
    assert "facebook/Page0" in report.preview[0]


def test_import_reports_row_errors_and_caps_them(monkeypatch):
    import core.content_calendar as cal
    errors = [f"dòng {i}: thiếu title" for i in range(25)]
    monkeypatch.setattr(cal, "import_csv", lambda path: _Result([], errors))

    report = content_tools.import_calendar_csv("plan.csv", b"a\n")
    assert len(report.errors) == content_tools.MAX_ERROR_LINES
    assert report.error_overflow == 25 - content_tools.MAX_ERROR_LINES


def test_import_parse_failure_is_reported_not_raised(monkeypatch):
    import core.content_calendar as cal

    def boom(path):
        raise ValueError("bad delimiter")

    monkeypatch.setattr(cal, "import_csv", boom)
    assert "bad delimiter" in \
        content_tools.import_calendar_csv("plan.csv", b"x").fatal


def test_import_page_says_it_does_not_write_to_the_sheet(logged_in, monkeypatch):
    """The desktop parsed and previewed only — the Sheet writer was never
    built. Claiming otherwise would silently drop the operator's rows."""
    import core.content_calendar as cal
    monkeypatch.setattr(cal, "import_csv",
                        lambda path: _Result([_Row("facebook", "P", "T")], []))

    page = logged_in.get("/settings")
    r = logged_in.post(
        "/settings/import-calendar",
        data={"csrf_token": _csrf(page.text)},
        files={"csv_file": ("plan.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")},
    )
    assert r.status_code == 200
    assert "chưa ghi vào Google" in r.text.replace("\n", " ")


def test_import_temp_file_is_always_cleaned_up(monkeypatch, tmp_path):
    """An upload path that leaks temp files fills the server's disk over time."""
    import glob
    import tempfile

    import core.content_calendar as cal
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(cal, "import_csv", lambda path: _Result([], []))

    content_tools.import_calendar_csv("plan.csv", b"a\n")
    assert glob.glob(str(tmp_path / "ltt_import_*")) == []


def test_all_three_actions_are_reachable_from_the_settings_page(logged_in):
    html = logged_in.get("/settings").text
    for action in ("/settings/export-history", "/settings/duplicates",
                   "/settings/import-calendar"):
        assert action in html, f"{action} not reachable from /settings"
