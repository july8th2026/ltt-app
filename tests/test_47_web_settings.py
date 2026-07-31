"""
Web Settings page — GUI parity phase 1.

The properties that matter most here are not cosmetic:

  * a secret must never be rendered into HTML;
  * submitting the form with a secret field left blank must NOT wipe the
    stored secret (a round-trip through the UI would otherwise silently
    destroy an App Secret);
  * invalid input must leave the on-disk config untouched — a bad column
    mapping silently stops the bot (docs/_luutru/AUDIT_REPORT.md B3), so a
    half-applied save is worse than a rejected one.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from core.config_defaults import DEFAULTS
from server.app import create_app
from server.auth.password_hashing import hash_password
from server.services.settings_schema import (
    GROUPS,
    all_field_keys,
    coverage_report,
    secret_keys,
)
from server.services.settings_service import apply_form, save_config, view_model

ADMIN_PASSWORD = "correct horse battery staple"
FAKE_SECRET = "s3cr3t" + "AppSecretValue" + "998877"


# ─── schema coverage ───────────────────────────────────────────────────────────

def test_every_default_key_is_reachable_from_the_ui():
    """A config key nobody can edit is a key that silently rots."""
    missing = coverage_report()["missing"]
    assert missing == [], f"these config keys have no UI field: {missing}"


def test_schema_has_no_invented_keys_outside_the_real_config():
    """Guards against typo'd field keys that would write junk into config."""
    unknown = set(coverage_report()["unknown"])
    # These two are real keys used by core/ but absent from DEFAULTS.
    allowed = {"fb_comment_enabled", "tiktok_redirect_uri"}
    assert unknown <= allowed, f"unexpected keys: {unknown - allowed}"


def test_group_ids_and_field_keys_are_unique():
    ids = [g.id for g in GROUPS]
    assert len(ids) == len(set(ids))
    keys = [f.key for g in GROUPS for f in g.fields]
    assert len(keys) == len(set(keys)), "a field key appears twice"


# ─── secrets never leave the server ────────────────────────────────────────────

def test_view_model_never_exposes_a_secret_value():
    cfg = dict(DEFAULTS)
    for k in secret_keys():
        cfg[k] = FAKE_SECRET

    vm = view_model(cfg)
    blob = json.dumps(vm, ensure_ascii=False, default=str)
    assert FAKE_SECRET not in blob

    for k in secret_keys():
        assert vm[k]["value"] == ""
        assert vm[k]["is_set"] is True


def test_view_model_marks_unset_secrets():
    cfg = dict(DEFAULTS)
    for k in secret_keys():
        cfg[k] = ""
    vm = view_model(cfg)
    for k in secret_keys():
        assert vm[k]["is_set"] is False


# ─── form merge semantics ──────────────────────────────────────────────────────

def test_blank_secret_submission_keeps_the_stored_value():
    """The dangerous case: user edits an unrelated field and saves."""
    cfg = dict(DEFAULTS)
    cfg["meta_app_secret"] = FAKE_SECRET

    new, errors = apply_form(cfg, {"meta_app_secret": "", "sheet_id": "abc"})

    assert errors == {}
    assert new["meta_app_secret"] == FAKE_SECRET      # preserved
    assert new["sheet_id"] == "abc"


def test_non_blank_secret_submission_replaces_it():
    cfg = dict(DEFAULTS)
    cfg["meta_app_secret"] = FAKE_SECRET
    new, _ = apply_form(cfg, {"meta_app_secret": "brand-new-value"})
    assert new["meta_app_secret"] == "brand-new-value"


def test_absent_checkbox_means_false():
    """Unchecked boxes are simply missing from an HTML form body."""
    cfg = dict(DEFAULTS)
    cfg["anti_spam_dedup"] = True
    new, _ = apply_form(cfg, {"sheet_id": "x"})     # checkbox not submitted
    assert new["anti_spam_dedup"] is False


def test_present_checkbox_means_true():
    cfg = dict(DEFAULTS)
    cfg["anti_spam_dedup"] = False
    new, _ = apply_form(cfg, {"anti_spam_dedup": "on"})
    assert new["anti_spam_dedup"] is True


def test_bad_number_is_reported_not_coerced():
    new, errors = apply_form(dict(DEFAULTS), {"job_delay_seconds": "ba mươi"})
    assert "job_delay_seconds" in errors


def test_bad_json_is_reported_with_a_useful_message():
    new, errors = apply_form(dict(DEFAULTS), {"sheets": "[{broken"})
    assert "sheets" in errors
    assert "JSON" in errors["sheets"]


def test_valid_json_list_is_parsed():
    new, errors = apply_form(dict(DEFAULTS), {"sheets": '[{"id":"a","alias":"b"}]'})
    assert errors == {}
    assert new["sheets"] == [{"id": "a", "alias": "b"}]


# ─── saving never corrupts a working config ────────────────────────────────────

def test_invalid_config_is_not_written(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    good = {"job_delay_seconds": 30, "max_retries": 3, "tiktok_poll_interval_s": 5,
            "tiktok_upload_timeout_s": 60, "tiktok_request_timeout_s": 10}
    cfg_file.write_text(json.dumps(good), encoding="utf-8")
    monkeypatch.setenv("LTT_CONFIG_PATH", str(cfg_file))

    bad = dict(good)
    bad["job_delay_seconds"] = -99          # violates the validator

    saved, errors, _ = save_config(bad)

    assert saved is False
    assert errors
    assert json.loads(cfg_file.read_text(encoding="utf-8")) == good   # untouched


def test_valid_save_writes_and_makes_a_backup(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    good = {"job_delay_seconds": 30, "max_retries": 3, "tiktok_poll_interval_s": 5,
            "tiktok_upload_timeout_s": 60, "tiktok_request_timeout_s": 10}
    cfg_file.write_text(json.dumps(good), encoding="utf-8")
    monkeypatch.setenv("LTT_CONFIG_PATH", str(cfg_file))

    updated = dict(good, sheet_id="new-sheet")
    saved, errors, _ = save_config(updated)

    assert saved is True, errors
    assert json.loads(cfg_file.read_text(encoding="utf-8"))["sheet_id"] == "new-sheet"
    backups = list(tmp_path.glob("config.backup_*.json"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8")) == good


# ─── the page itself ───────────────────────────────────────────────────────────

def _client(tmp_path) -> TestClient:
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "job_delay_seconds": 30, "max_retries": 3, "tiktok_poll_interval_s": 5,
        "tiktok_upload_timeout_s": 60, "tiktok_request_timeout_s": 10,
        "sheet_id": "abc", "meta_app_secret": FAKE_SECRET,
    }), encoding="utf-8")
    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "test-session-secret-not-a-real-secret",
        "LTT_ADMIN_USERNAME": "admin",
        "LTT_ADMIN_PASSWORD_HASH": hash_password(ADMIN_PASSWORD),
    })
    return TestClient(app, base_url="https://testserver", follow_redirects=False)


def _login(c: TestClient) -> None:
    r = c.get("/login")
    m = 'name="csrf_token" value="'
    s = r.text.index(m) + len(m)
    c.post("/login", data={"username": "admin", "password": ADMIN_PASSWORD,
                           "csrf_token": r.text[s:r.text.index('"', s)]})


def _csrf(html: str) -> str:
    m = 'name="csrf_token" value="'
    s = html.index(m) + len(m)
    return html[s:html.index('"', s)]


def test_settings_requires_login(tmp_path):
    r = _client(tmp_path).get("/settings")
    assert r.status_code == 303
    assert r.headers["location"].startswith("/login")


def test_settings_page_renders_all_groups(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_CONFIG_PATH", str(tmp_path / "config.json"))
    c = _client(tmp_path)
    _login(c)
    r = c.get("/settings")
    assert r.status_code == 200
    for g in GROUPS:
        assert g.title in r.text, f"group missing from page: {g.title}"


def test_rendered_page_contains_no_secret_value(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_CONFIG_PATH", str(tmp_path / "config.json"))
    c = _client(tmp_path)
    _login(c)
    r = c.get("/settings")
    assert FAKE_SECRET not in r.text


def test_save_requires_csrf(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_CONFIG_PATH", str(tmp_path / "config.json"))
    c = _client(tmp_path)
    _login(c)
    r = c.post("/settings", data={"csrf_token": "forged", "sheet_id": "x"})
    assert r.status_code == 400


def test_save_roundtrip_updates_config(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    monkeypatch.setenv("LTT_CONFIG_PATH", str(cfg_file))
    c = _client(tmp_path)
    _login(c)

    page = c.get("/settings")
    r = c.post("/settings", data={
        "csrf_token": _csrf(page.text),
        "sheet_id": "sheet-from-web",
        "job_delay_seconds": "45",
        "meta_app_secret": "",          # blank => keep
    })
    assert r.status_code == 200
    on_disk = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert on_disk["sheet_id"] == "sheet-from-web"
    assert on_disk["job_delay_seconds"] == 45
    assert on_disk["meta_app_secret"] == FAKE_SECRET      # not wiped
