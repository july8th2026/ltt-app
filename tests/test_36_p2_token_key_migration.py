"""
P2 — token-encryption migration (ADR-013) tests.

The FB/TikTok token stores derive their Fernet key from the machine
identity, which means encrypted token files cannot move between machines
(dev -> VPS) without re-authorizing every account. ADR-013 adds an
operator-provisioned external key override (LTT_TOKEN_ENCRYPTION_KEY /
LTT_TOKEN_ENCRYPTION_KEY_FILE) that is independent of machine identity,
while leaving the default (unset) behavior byte-for-byte identical to
before — verified here.
"""
from __future__ import annotations

import importlib

import core.token_store as fb_token_store
import core.tiktok.token_store as tt_token_store


def _clear_env(monkeypatch):
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEY_FILE", raising=False)


def test_default_key_derivation_unchanged_without_env_override(monkeypatch):
    """No env vars set -> identical machine-bound key as before this change."""
    _clear_env(monkeypatch)
    key1 = fb_token_store._derive_key()
    key2 = fb_token_store._derive_key()
    assert key1 == key2
    # Matches the original formula directly (machine id + salt -> sha256 -> b64).
    import base64, hashlib
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(
            fb_token_store._get_machine_id().encode("utf-8") + fb_token_store._SALT
        ).digest()
    )
    assert key1 == expected


def test_external_key_env_var_overrides_machine_binding(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "operator-provisioned-secret-123")
    key_with_override = fb_token_store._derive_key()

    _clear_env(monkeypatch)
    key_without_override = fb_token_store._derive_key()

    assert key_with_override != key_without_override


def test_external_key_is_deterministic_across_process_boundaries(monkeypatch):
    """Same external key -> same derived Fernet key every time (this is what
    makes tokens portable across a VPS reinstall)."""
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "same-secret-value")
    key1 = fb_token_store._derive_key()
    key2 = fb_token_store._derive_key()
    assert key1 == key2


def test_external_key_file_is_read_when_env_var_absent(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    key_file = tmp_path / "token.key"
    key_file.write_text("secret-from-file\n", encoding="utf-8")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY_FILE", str(key_file))

    key = fb_token_store._derive_key()

    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "secret-from-file")
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEY_FILE", raising=False)
    key_from_var = fb_token_store._derive_key()

    assert key == key_from_var  # trailing newline is stripped consistently


def test_fb_and_tiktok_keys_differ_even_with_shared_external_secret(monkeypatch):
    """Per-store salt still applies on top of an external key, so FB and
    TikTok token files are never encrypted with the identical key."""
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "shared-operator-secret")
    fb_key = fb_token_store._derive_key()
    tt_key = tt_token_store._derive_key()
    assert fb_key != tt_key


def test_token_store_roundtrip_survives_simulated_machine_change(monkeypatch, tmp_path):
    """The whole point of ADR-013: encrypt with one 'machine' (env A), then
    decrypt with a different simulated machine (env B) — succeeds only
    because the external key doesn't depend on machine identity."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "portable-key-for-vps-migration")

    path = str(tmp_path / "tokens.enc")
    store_a = fb_token_store.TokenStore(path=path)
    account = fb_token_store.AccountInfo(
        fb_user_id="u1", name="Test User", user_token="tok123",
        token_expires_at="",
    )
    store_a.save_account(account)

    # Simulate moving the encrypted file to a different machine by faking a
    # different machine id — the external key must make this irrelevant.
    monkeypatch.setattr(fb_token_store, "_get_machine_id", lambda: "a-totally-different-machine")
    store_b = fb_token_store.TokenStore(path=path)

    loaded = store_b.get_account("u1")
    assert loaded is not None
    assert loaded.user_token == "tok123"
