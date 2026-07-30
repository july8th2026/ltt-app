"""
W1 — Google credentials upload.

The property that matters: an OAuth-client JSON must be REJECTED. Accepting
one produces a config that looks valid and then hangs forever, because
`utils/sheet_client.py` falls back to `InstalledAppFlow.run_local_server()`
— a browser on the machine running the code, which a remote server does not
have (docs/WEB_PARITY_PLAN.md B-1).
"""
from __future__ import annotations

import json

import pytest

from server.services.credentials_service import (
    describe_stored,
    store_credentials,
    validate_service_account,
)

SERVICE_ACCOUNT = {
    "type": "service_account",
    "project_id": "demo-project",
    "private_key_id": "abc",
    # Not a real key — shape only.
    "private_key": "-----BEGIN " + "PRIVATE KEY-----\nfake\n-----END " + "PRIVATE KEY-----\n",
    "client_email": "bot@demo-project.iam.gserviceaccount.com",
    "client_id": "123",
    "token_uri": "https://oauth2.googleapis.com/token",
}

INSTALLED_CLIENT = {
    "installed": {
        "client_id": "123.apps.googleusercontent.com",
        "client_secret": "placeholder",
        "redirect_uris": ["http://localhost"],
    }
}

WEB_CLIENT = {"web": {"client_id": "x", "client_secret": "y"}}


def _raw(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


# ─── validation ────────────────────────────────────────────────────────────────

def test_service_account_is_accepted():
    r = validate_service_account(_raw(SERVICE_ACCOUNT))
    assert r["ok"] is True
    assert r["client_email"] == "bot@demo-project.iam.gserviceaccount.com"


def test_installed_oauth_client_is_rejected_with_the_reason():
    r = validate_service_account(_raw(INSTALLED_CLIENT))
    assert r["ok"] is False
    assert "SERVICE ACCOUNT" in r["error"]
    assert "trình duyệt" in r["error"]      # explains WHY, not just "invalid"


def test_web_oauth_client_is_rejected():
    assert validate_service_account(_raw(WEB_CLIENT))["ok"] is False


def test_empty_file_is_rejected():
    assert validate_service_account(b"")["ok"] is False
    assert validate_service_account(b"   ")["ok"] is False


def test_malformed_json_is_rejected_with_line_number():
    r = validate_service_account(b"{not json")
    assert r["ok"] is False
    assert "JSON" in r["error"]


def test_non_utf8_is_rejected():
    r = validate_service_account(b"\xff\xfe\x00binary")
    assert r["ok"] is False


def test_json_array_is_rejected():
    assert validate_service_account(b'[{"type":"service_account"}]')["ok"] is False


@pytest.mark.parametrize("missing", ["client_email", "private_key", "token_uri"])
def test_incomplete_service_account_is_rejected(missing):
    data = dict(SERVICE_ACCOUNT)
    data[missing] = ""
    r = validate_service_account(_raw(data))
    assert r["ok"] is False
    assert missing in r["error"]


# ─── storage ───────────────────────────────────────────────────────────────────

def test_store_writes_file_and_reports_email(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_SECRETS_DIR", str(tmp_path))
    ok, msg, info = store_credentials(_raw(SERVICE_ACCOUNT))

    assert ok is True
    assert info["client_email"] in msg
    # The share step is the one operators forget; it must be in the message.
    assert "Share" in msg or "chia sẻ" in msg.lower()

    written = tmp_path / "google_service_account.json"
    assert written.exists()
    assert json.loads(written.read_text(encoding="utf-8"))["type"] == "service_account"


def test_store_refuses_oauth_client_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_SECRETS_DIR", str(tmp_path))
    ok, msg, _ = store_credentials(_raw(INSTALLED_CLIENT))
    assert ok is False
    assert list(tmp_path.glob("*.json")) == []


def test_describe_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_SECRETS_DIR", str(tmp_path))
    assert describe_stored()["exists"] is False


def test_describe_stored_never_returns_the_private_key(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_SECRETS_DIR", str(tmp_path))
    store_credentials(_raw(SERVICE_ACCOUNT))

    info = describe_stored()
    blob = json.dumps(info, ensure_ascii=False)

    assert info["valid"] is True
    assert "PRIVATE KEY" not in blob
    assert "private_key" not in info
    # client_email IS shown on purpose — the operator must share the Sheet
    # with it or every read 403s.
    assert info["client_email"].endswith(".iam.gserviceaccount.com")


def test_describe_flags_a_wrong_type_already_on_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_SECRETS_DIR", str(tmp_path))
    (tmp_path / "google_service_account.json").write_text(
        json.dumps(INSTALLED_CLIENT), encoding="utf-8")
    info = describe_stored()
    assert info["exists"] is True
    assert info["valid"] is False
