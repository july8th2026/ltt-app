"""
PA-1 — token store must distinguish "no accounts" from "unreadable file".

Regression guard for docs/_luutru/AUDIT_REPORT.md finding D2: an undecryptable
token file used to be silently collapsed into "0 accounts", making a real
credential outage look identical to a fresh install. The live audit hit
exactly this — 27KB of real Facebook tokens reported as "no accounts
connected".
"""
from __future__ import annotations

import base64
import hashlib
import json

import pytest
from cryptography.fernet import Fernet

from core.tiktok.token_store import TikTokTokenStore
from core.token_store import AccountInfo, TokenStore


def _foreign_key() -> bytes:
    """A valid Fernet key that is NOT this machine's derived key —
    simulates a token file encrypted on a different host."""
    return base64.urlsafe_b64encode(hashlib.sha256(b"some-other-machine").digest())


# ─── state 1: file absent -> quiet "no accounts" ──────────────────────────────

def test_absent_file_is_not_an_error(tmp_path):
    store = TokenStore(path=str(tmp_path / "nope.enc"))
    assert store.count() == 0
    assert store.is_unreadable is False
    assert store.load_error is None


def test_empty_file_is_not_an_error(tmp_path):
    p = tmp_path / "tokens.enc"
    p.write_bytes(b"")
    store = TokenStore(path=str(p))
    assert store.count() == 0
    assert store.is_unreadable is False


# ─── state 2: file present but unreadable -> loud ─────────────────────────────

def test_foreign_key_encrypted_file_reports_unreadable(tmp_path):
    p = tmp_path / "tokens.enc"
    payload = json.dumps([{
        "fb_user_id": "u1", "name": "N", "user_token": "t",
        "token_expires_at": "", "pages": [],
    }]).encode("utf-8")
    p.write_bytes(Fernet(_foreign_key()).encrypt(payload))

    store = TokenStore(path=str(p))

    assert store.count() == 0
    assert store.is_unreadable is True
    assert store.load_error
    # The message must tell the operator what to actually do.
    assert "kết nối lại" in store.load_error.lower()
    assert "LTT_TOKEN_ENCRYPTION_KEY" in store.load_error


def test_corrupt_garbage_file_reports_unreadable(tmp_path):
    p = tmp_path / "tokens.enc"
    p.write_bytes(b"this is not fernet and not json either")
    store = TokenStore(path=str(p))
    assert store.count() == 0
    assert store.is_unreadable is True


def test_unreadable_message_never_contains_token_material(tmp_path):
    p = tmp_path / "tokens.enc"
    # Assembled at runtime so this fixture does not trip the repo's own
    # source secret scanner (same convention as test_33_secret_scanner).
    secret = "EAA" + "syntheticFixtureTokenValue" + "1234567890"
    payload = json.dumps([{
        "fb_user_id": "u1", "name": "N", "user_token": secret,
        "token_expires_at": "", "pages": [],
    }]).encode("utf-8")
    p.write_bytes(Fernet(_foreign_key()).encrypt(payload))

    store = TokenStore(path=str(p))
    assert secret not in (store.load_error or "")


# ─── state 3: readable -> loads, no error ─────────────────────────────────────

def test_readable_store_roundtrip_has_no_error(tmp_path):
    p = tmp_path / "tokens.enc"
    store = TokenStore(path=str(p))
    store.save_account(AccountInfo(
        fb_user_id="u1", name="N", user_token="t", token_expires_at="",
    ))

    reopened = TokenStore(path=str(p))
    assert reopened.count() == 1
    assert reopened.is_unreadable is False
    assert reopened.load_error is None


def test_plain_json_migration_path_still_works(tmp_path):
    """A pre-encryption plain-JSON store must still load (and not be
    reported as unreadable) — this path predates encryption."""
    p = tmp_path / "tokens.enc"
    p.write_text(json.dumps([{
        "fb_user_id": "u9", "name": "Legacy", "user_token": "t",
        "token_expires_at": "", "pages": [],
    }]), encoding="utf-8")

    store = TokenStore(path=str(p))
    assert store.count() == 1
    assert store.is_unreadable is False


# ─── TikTok store parity ───────────────────────────────────────────────────────

def test_tiktok_store_reports_unreadable_too(tmp_path):
    p = tmp_path / "tt.enc"
    p.write_bytes(Fernet(_foreign_key()).encrypt(b'[{"open_id": "x"}]'))

    store = TikTokTokenStore(path=str(p))

    assert store.count() == 0
    assert store.is_unreadable is True
    assert "TikTok" in (store.load_error or "")


def test_tiktok_absent_file_is_not_an_error(tmp_path):
    store = TikTokTokenStore(path=str(tmp_path / "nope.enc"))
    assert store.is_unreadable is False
    assert store.load_error is None
