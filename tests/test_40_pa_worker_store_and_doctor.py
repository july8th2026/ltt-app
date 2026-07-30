"""
PA-4 / PA-5 — worker-list persistence and the doctor health report.

Guards docs/_luutru/AUDIT_REPORT.md finding D3 (worker list existed only in GUI
memory, so no headless run could reproduce the operator's real setup, and
worker_main's legacy guess targeted the wrong tab).
"""
from __future__ import annotations

import json

import pytest

import worker_main
from core.worker_store import (
    WORKERS_SCHEMA_VERSION,
    WorkerStoreError,
    load_workers,
    save_workers,
)


# ─── worker_store ──────────────────────────────────────────────────────────────

def test_roundtrip(tmp_path):
    p = str(tmp_path / "workers.json")
    save_workers([{"tab": "T1", "page": "P1", "sheet_id": "S1"}], path=p)
    got = load_workers(path=p)
    assert len(got) == 1
    assert got[0]["tab"] == "T1"
    assert got[0]["page"] == "P1"


def test_missing_file_is_empty_not_an_error(tmp_path):
    assert load_workers(path=str(tmp_path / "nope.json")) == []


def test_platforms_do_not_overwrite_each_other(tmp_path):
    """The desktop app has a Sheet-FB tab and a Sheet-TikTok tab; saving
    one must not wipe the other's list."""
    p = str(tmp_path / "workers.json")
    save_workers([{"tab": "FB-Tab"}], platform="facebook", path=p)
    save_workers([{"tab": "TT-Tab"}], platform="tiktok", path=p)

    assert [w["tab"] for w in load_workers(platform="facebook", path=p)] == ["FB-Tab"]
    assert [w["tab"] for w in load_workers(platform="tiktok", path=p)] == ["TT-Tab"]
    assert len(load_workers(path=p)) == 2      # platform=None -> everything


def test_empty_platform_is_stored_as_facebook(tmp_path):
    p = str(tmp_path / "workers.json")
    save_workers([{"tab": "T"}], platform="", path=p)
    assert len(load_workers(platform="facebook", path=p)) == 1


def test_resave_replaces_only_that_platform(tmp_path):
    p = str(tmp_path / "workers.json")
    save_workers([{"tab": "A"}, {"tab": "B"}], platform="facebook", path=p)
    save_workers([{"tab": "C"}], platform="facebook", path=p)
    assert [w["tab"] for w in load_workers(platform="facebook", path=p)] == ["C"]


def test_display_only_fields_are_not_persisted(tmp_path):
    """account_name is a cached label; persisting it would let stale
    display data outlive the account it described."""
    p = str(tmp_path / "workers.json")
    save_workers([{"tab": "T", "account_name": "Stale Cached Name"}], path=p)
    assert "account_name" not in load_workers(path=p)[0]


def test_rows_without_tab_are_dropped(tmp_path):
    p = str(tmp_path / "workers.json")
    save_workers([{"tab": "Good"}, {"tab": ""}], path=p)
    assert [w["tab"] for w in load_workers(path=p)] == ["Good"]


def test_newer_schema_version_is_rejected(tmp_path):
    p = tmp_path / "workers.json"
    p.write_text(json.dumps({
        "_schema_version": WORKERS_SCHEMA_VERSION + 1, "workers": [{"tab": "T"}],
    }), encoding="utf-8")
    with pytest.raises(WorkerStoreError):
        load_workers(path=str(p))


def test_corrupt_file_raises_rather_than_silently_empty(tmp_path):
    p = tmp_path / "workers.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(WorkerStoreError):
        load_workers(path=str(p))


def test_wrong_toplevel_shape_is_rejected(tmp_path):
    p = tmp_path / "workers.json"
    p.write_text(json.dumps([{"tab": "T"}]), encoding="utf-8")  # array, not object
    with pytest.raises(WorkerStoreError):
        load_workers(path=str(p))


# ─── worker_main worker resolution ─────────────────────────────────────────────

def test_explicit_workers_file_takes_precedence(tmp_path, monkeypatch):
    wf = tmp_path / "explicit.json"
    wf.write_text(json.dumps([{"tab": "Explicit"}]), encoding="utf-8")
    got = worker_main.resolve_workers(str(wf), "facebook")
    assert got[0]["tab"] == "Explicit"


def test_falls_back_to_stored_workers(tmp_path, monkeypatch):
    store = str(tmp_path / "workers.json")
    save_workers([{"tab": "FromStore"}], platform="facebook", path=store)
    monkeypatch.setattr("core.worker_store.default_path", lambda env=None: store)

    got = worker_main.resolve_workers(None, "facebook")
    assert got[0]["tab"] == "FromStore"


def test_no_workers_anywhere_raises_instead_of_guessing(tmp_path, monkeypatch):
    """The audit proved the old legacy-config guess ran the WRONG tab.
    Failing loudly is the required behavior."""
    monkeypatch.setattr(
        "core.worker_store.default_path", lambda env=None: str(tmp_path / "absent.json"),
    )
    with pytest.raises(worker_main.NoWorkersError):
        worker_main.resolve_workers(None, "facebook")


def test_main_returns_exit_code_3_when_no_workers(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"sheet_tab": "X", "sheet_id": "Y"}), encoding="utf-8")
    monkeypatch.setattr(
        "core.worker_store.default_path", lambda env=None: str(tmp_path / "absent.json"),
    )
    assert worker_main.main(["--config", str(cfg)]) == 3


# ─── doctor ────────────────────────────────────────────────────────────────────

def test_doctor_reports_blocker_for_unreadable_tokens(tmp_path, monkeypatch):
    import base64
    import hashlib

    from cryptography.fernet import Fernet

    from tools import doctor

    foreign = base64.urlsafe_b64encode(hashlib.sha256(b"other-machine").digest())
    tok = tmp_path / "tokens.enc"
    tok.write_bytes(Fernet(foreign).encrypt(b'[{"fb_user_id":"u1"}]'))

    import core.token_store as ts
    monkeypatch.setattr(ts, "TOKEN_FILE", str(tok))

    report = doctor.Report()
    doctor.check_tokens(report)

    fb = [s for s in report.sections if "Facebook" in s["check"]][0]
    assert fb["status"] == doctor.BLOCK
    assert fb["fix"]                       # must be actionable
    assert report.has_blocker is True


def test_doctor_output_contains_no_token_material(tmp_path, monkeypatch):
    import base64
    import hashlib

    from cryptography.fernet import Fernet

    from tools import doctor

    # Assembled at runtime so this fixture does not trip the repo's own
    # source secret scanner (same convention as test_33_secret_scanner).
    secret = "EAA" + "syntheticFixtureMustNotLeak" + "123456"
    foreign = base64.urlsafe_b64encode(hashlib.sha256(b"other-machine").digest())
    tok = tmp_path / "tokens.enc"
    tok.write_bytes(Fernet(foreign).encrypt(
        json.dumps([{"fb_user_id": "u1", "user_token": secret}]).encode()
    ))

    import core.token_store as ts
    monkeypatch.setattr(ts, "TOKEN_FILE", str(tok))

    report = doctor.Report()
    doctor.check_tokens(report)
    assert secret not in report.to_text()


def test_doctor_exit_code_zero_when_healthy(monkeypatch):
    from tools import doctor

    report = doctor.Report()
    report.add("Everything", doctor.OK, "fine")
    assert report.has_blocker is False


def test_doctor_warning_alone_does_not_block(monkeypatch):
    from tools import doctor

    report = doctor.Report()
    report.add("Something", doctor.WARN, "not ideal")
    assert report.has_blocker is False
    assert "cảnh báo" in report.to_text()
