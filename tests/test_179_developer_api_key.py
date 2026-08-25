"""Q92 / Prompt 03 — developer API key domain.

The properties held here are the ones whose absence is expensive later: a key
that survives revocation, a plaintext that lingers in the database, one customer
reading another's keys, or an auth path that tells an attacker which key ids
exist.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from platform_core.public_api import keys as devkeys
from platform_core.public_api.scopes import (DEFAULT_SCOPES, SCOPE_JOBS_CREATE,
                                             ScopeError, normalize_scopes)
from platform_core.public_api.tables import (DEVKEY_ACTIVE, DEVKEY_DISABLED,
                                             DEVKEY_EXPIRED, DEVKEY_REVOKED,
                                             DeveloperApiKey, KEY_PREFIX)

PEPPER = "test-pepper-" + "a" * 40
OTHER_PEPPER = "rotated-pepper-" + "b" * 40
ENV = {devkeys.PEPPER_ENV: PEPPER}


@pytest.fixture()
def db(tmp_path):
    import platform_core.models  # noqa: F401 - registers every table
    from platform_core.db import Base

    engine = sa.create_engine(f"sqlite:///{(tmp_path / 'keys.db').as_posix()}",
                              future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _user(db, email: str = "dev@example.com"):
    from platform_core.users import tao_nguoi_dung

    user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
    db.commit()
    return user


def _issue(db, user, **kwargs):
    key, token = devkeys.issue(db, user_id=user.id, env=ENV, **kwargs)
    db.commit()
    return key, token


# ── Configuration ─────────────────────────────────────────────────────────────

def test_issuing_without_a_pepper_fails_closed(db):
    user = _user(db)
    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.issue(db, user_id=user.id, env={})
    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.issue(db, user_id=user.id, env={devkeys.PEPPER_ENV: "too-short"})


def test_pepper_is_never_written_to_the_row(db):
    user = _user(db)
    key, _token = _issue(db, user)
    assert PEPPER not in "".join(str(value) for value in [
        key.verifier_digest, key.key_id, key.name])


# ── Token format and entropy ──────────────────────────────────────────────────

def test_token_shape_is_recognisable_and_high_entropy(db):
    user = _user(db)
    key, token = _issue(db, user, name="ci")
    assert token.startswith(f"{KEY_PREFIX}_")
    parsed = devkeys.parse_token(token)
    assert parsed is not None
    key_id, secret = parsed
    assert key_id == key.key_id
    assert len(key_id) == devkeys.KEY_ID_LENGTH
    # 43 urlsafe-base64 characters carry >= 256 bits.
    assert len(secret) == devkeys.SECRET_LENGTH


@pytest.mark.parametrize("bad", [
    "", "not-a-token", "ltt_sk_short_secret", "ltt_pk_" + "a" * 32 + "_" + "b" * 43,
    "ltt_sk_" + "z" * 32 + "_" + "b" * 43,          # key_id not hex
    "ltt_sk_" + "a" * 31 + "_" + "b" * 43,          # key_id too short
    "ltt_sk_" + "a" * 32 + "_" + "b" * 42,          # secret too short
    "ltt_sk_" + "a" * 32 + "_" + "b" * 43 + "_x",   # extra segment
])
def test_malformed_tokens_are_rejected_by_shape(bad):
    assert devkeys.parse_token(bad) is None


def test_a_secret_containing_an_underscore_still_parses(db, monkeypatch):
    """Regression: the secret is urlsafe base64, so "_" is part of its alphabet.

    A naive ``split("_")`` shredded roughly a third of all issued tokens — they
    verified in one test run and failed in the next, which is the worst possible
    failure mode for a credential.
    """
    user = _user(db)
    tricky = "a_b-c" + "d" * (devkeys.SECRET_LENGTH - 5)
    monkeypatch.setattr(devkeys, "_new_secret", lambda: tricky)
    _key, token = _issue(db, user)
    assert devkeys.parse_token(token) == (token.split("_", 3)[2], tricky)
    assert devkeys.verify(db, token, env=ENV) is not None


def test_two_keys_never_share_material(db):
    user = _user(db)
    first, first_token = _issue(db, user)
    second, second_token = _issue(db, user)
    assert first.key_id != second.key_id
    assert first.verifier_digest != second.verifier_digest
    assert first_token != second_token


def test_key_id_collision_is_retried_not_crashed(db, monkeypatch):
    user = _user(db)
    taken, _token = _issue(db, user)
    generated = iter([taken.key_id, "f" * 32])
    monkeypatch.setattr(devkeys, "_new_key_id", lambda: next(generated))
    key, token = _issue(db, user)
    assert key.key_id == "f" * 32
    assert devkeys.verify(db, token, env=ENV) is not None


# ── One-time reveal / no plaintext at rest ────────────────────────────────────

def test_plaintext_exists_only_in_the_issue_return_value(db):
    user = _user(db)
    key, token = _issue(db, user)
    _key_id, secret = devkeys.parse_token(token)

    row = db.execute(sa.text("SELECT * FROM developer_api_keys")).mappings().one()
    serialized = " ".join(str(value) for value in row.values())
    assert secret not in serialized
    assert token not in serialized
    # The digest is present, and it is not the secret.
    assert key.verifier_digest in serialized
    assert repr(key).find(secret) == -1


def test_a_reloaded_key_cannot_reproduce_its_token(db):
    user = _user(db)
    _key, token = _issue(db, user)
    db.expire_all()
    reloaded = db.execute(sa.select(DeveloperApiKey)).scalar_one()
    assert not hasattr(reloaded, "secret")
    assert token.split("_")[-1] not in reloaded.verifier_digest


# ── Verification ──────────────────────────────────────────────────────────────

def test_a_valid_token_resolves_to_its_key(db):
    user = _user(db)
    key, token = _issue(db, user)
    resolved = devkeys.verify(db, token, env=ENV)
    assert resolved is not None and resolved.id == key.id


def test_wrong_secret_for_a_real_key_id_is_refused(db):
    user = _user(db)
    key, _token = _issue(db, user)
    forged = devkeys.format_token(key.key_id, "c" * devkeys.SECRET_LENGTH)
    assert devkeys.verify(db, forged, env=ENV) is None


def test_unknown_key_id_and_malformed_token_answer_the_same_way(db):
    user = _user(db)
    _issue(db, user)
    unknown = devkeys.format_token("d" * 32, "e" * devkeys.SECRET_LENGTH)
    assert devkeys.verify(db, unknown, env=ENV) is None
    assert devkeys.verify(db, "garbage", env=ENV) is None
    assert devkeys.verify(db, "", env=ENV) is None


def test_verification_hashes_even_for_unknown_keys(db, monkeypatch):
    """No early return that would make "key exists" measurable."""
    user = _user(db)
    _issue(db, user)
    calls = []
    original = devkeys.digest_secret
    monkeypatch.setattr(devkeys, "digest_secret",
                        lambda secret, pepper: calls.append(1) or original(secret, pepper))

    devkeys.verify(db, devkeys.format_token("d" * 32, "e" * devkeys.SECRET_LENGTH),
                   env=ENV)
    assert calls, "unknown key id must still perform a digest"
    calls.clear()
    devkeys.verify(db, "totally-malformed", env=ENV)
    assert calls, "malformed token must still perform a digest"


def test_revoked_disabled_and_expired_keys_stop_working(db):
    user = _user(db)
    now = datetime.now(timezone.utc)

    revoked_key, revoked_token = _issue(db, user)
    devkeys.revoke(db, revoked_key)
    db.commit()
    assert devkeys.verify(db, revoked_token, env=ENV) is None
    assert revoked_key.status() == DEVKEY_REVOKED

    disabled_key, disabled_token = _issue(db, user)
    devkeys.set_enabled(db, disabled_key, False)
    db.commit()
    assert devkeys.verify(db, disabled_token, env=ENV) is None
    assert disabled_key.status() == DEVKEY_DISABLED

    expiring_key, expiring_token = _issue(db, user,
                                          expires_at=now + timedelta(minutes=5))
    assert devkeys.verify(db, expiring_token, env=ENV) is not None
    later = now + timedelta(minutes=10)
    assert devkeys.verify(db, expiring_token, env=ENV, now=later) is None
    assert expiring_key.status(now=later) == DEVKEY_EXPIRED
    assert expiring_key.status(now=now) == DEVKEY_ACTIVE


def test_revocation_cannot_be_undone(db):
    user = _user(db)
    key, _token = _issue(db, user)
    assert devkeys.revoke(db, key) is True
    assert devkeys.revoke(db, key) is False
    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.set_enabled(db, key, True)
    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.rotate(db, key, env=ENV)


def test_rotation_invalidates_the_previous_secret(db):
    user = _user(db)
    key, old_token = _issue(db, user, name="ci", scopes=[SCOPE_JOBS_CREATE])
    new_token = devkeys.rotate(db, key, env=ENV)
    db.commit()
    assert new_token != old_token
    assert devkeys.verify(db, old_token, env=ENV) is None
    rotated = devkeys.verify(db, new_token, env=ENV)
    assert rotated is not None and rotated.id == key.id
    # Policy and identity survive the rotation; only the secret material moves.
    assert rotated.name == "ci" and rotated.scopes == [SCOPE_JOBS_CREATE]
    assert rotated.rotated_at is not None


# ── Pepper rotation ───────────────────────────────────────────────────────────

def test_a_key_issued_under_an_old_pepper_still_verifies(db):
    user = _user(db)
    old_env = {devkeys.PEPPER_ENV: PEPPER, devkeys.PEPPER_VERSION_ENV: "1"}
    key, token = devkeys.issue(db, user_id=user.id, env=old_env)
    db.commit()
    assert key.pepper_version == 1

    rotated_env = {
        devkeys.PEPPER_ENV: OTHER_PEPPER,
        devkeys.PEPPER_VERSION_ENV: "2",
        f"{devkeys.RETIRED_PEPPER_PREFIX}1": PEPPER,
    }
    assert devkeys.verify(db, token, env=rotated_env) is not None

    # New keys are issued under the new pepper.
    fresh_key, fresh_token = devkeys.issue(db, user_id=user.id, env=rotated_env)
    db.commit()
    assert fresh_key.pepper_version == 2
    assert devkeys.verify(db, fresh_token, env=rotated_env) is not None


def test_a_missing_old_pepper_fails_closed_rather_than_open(db):
    user = _user(db)
    key, token = devkeys.issue(
        db, user_id=user.id,
        env={devkeys.PEPPER_ENV: PEPPER, devkeys.PEPPER_VERSION_ENV: "1"})
    db.commit()
    assert key.pepper_version == 1
    lost = {devkeys.PEPPER_ENV: OTHER_PEPPER, devkeys.PEPPER_VERSION_ENV: "2"}
    assert devkeys.verify(db, token, env=lost) is None


# ── Ownership ─────────────────────────────────────────────────────────────────

def test_one_customer_cannot_reach_another_customers_key(db):
    alice = _user(db, "alice@example.com")
    bob = _user(db, "bob@example.com")
    alice_key, alice_token = _issue(db, alice)
    _bob_key, _bob_token = _issue(db, bob)

    assert devkeys.get_owned(db, user_id=bob.id, key_id=alice_key.key_id) is None
    assert devkeys.get_owned(db, user_id=alice.id, key_id=alice_key.key_id) is not None
    assert [key.id for key in devkeys.list_for_user(db, bob.id)] != [alice_key.id]
    assert alice_key.id not in [key.id for key in devkeys.list_for_user(db, bob.id)]
    # Alice's token still resolves to Alice, never to Bob.
    resolved = devkeys.verify(db, alice_token, env=ENV)
    assert resolved is not None and resolved.user_id == alice.id


def test_a_key_must_belong_to_someone(db):
    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.issue(db, user_id="", env=ENV)


# ── Limits and policy ─────────────────────────────────────────────────────────

def test_scopes_are_validated_and_defaulted(db):
    user = _user(db)
    default_key, _token = _issue(db, user)
    assert default_key.scopes == list(DEFAULT_SCOPES)

    with pytest.raises(ScopeError):
        normalize_scopes(["jobs:write", "not-a-scope"])
    with pytest.raises(ScopeError):
        devkeys.issue(db, user_id=user.id, scopes=["make:coffee"], env=ENV)


def test_allowed_tools_are_deduplicated_and_optional(db):
    user = _user(db)
    key, _token = _issue(db, user, allowed_tools=["a.b", "a.b", " c.d "])
    assert key.allowed_tools == ["a.b", "c.d"]
    other, _token2 = _issue(db, user)
    assert other.allowed_tools == []


def test_expiry_must_be_sane(db):
    user = _user(db)
    now = datetime.now(timezone.utc)
    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.issue(db, user_id=user.id, expires_at=now - timedelta(days=1), env=ENV)
    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.issue(db, user_id=user.id, expires_at=now + timedelta(days=400), env=ENV)


def test_a_user_cannot_hoard_unlimited_keys(db):
    user = _user(db)
    for _ in range(devkeys.MAX_KEYS_PER_USER):
        _issue(db, user)
    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.issue(db, user_id=user.id, env=ENV)
    # Revoking one frees a slot.
    devkeys.revoke(db, devkeys.list_for_user(db, user.id)[0])
    db.commit()
    _issue(db, user)


# ── last_used bucketing ───────────────────────────────────────────────────────

def test_last_used_is_bucketed_instead_of_written_per_request(db):
    user = _user(db)
    key, _token = _issue(db, user)
    start = datetime.now(timezone.utc)

    assert devkeys.touch_last_used(db, key, now=start) is True
    assert devkeys.touch_last_used(db, key, now=start + timedelta(seconds=30)) is False
    assert devkeys.touch_last_used(db, key, now=start + timedelta(minutes=2)) is False
    later = start + devkeys.LAST_USED_BUCKET + timedelta(seconds=1)
    assert devkeys.touch_last_used(db, key, now=later) is True
    assert key.last_used_at is not None


# ── Boundary with the provider credential domain ──────────────────────────────

def test_the_developer_key_domain_never_touches_provider_credentials():
    """Two credential domains, opposite requirements — they must not converge."""
    source = (devkeys.__file__, )
    from pathlib import Path

    text = Path(source[0]).read_text(encoding="utf-8")
    assert "lay_credential" not in text
    assert "secretbox" not in text
    assert "from platform_core.api_keys" not in text
    assert "from platform_core import api_keys" not in text


def test_provider_api_keys_still_work_unchanged(db):
    """The provider table keeps its encrypt/decrypt behaviour."""
    from platform_core import api_keys as provider_keys

    import platform_core.secretbox as secretbox
    secretbox_key = "unit-test-token-encryption-key-0123456789"
    import os
    previous = os.environ.get("LTT_TOKEN_ENCRYPTION_KEY")
    os.environ["LTT_TOKEN_ENCRYPTION_KEY"] = secretbox_key
    try:
        secretbox.reset_cache() if hasattr(secretbox, "reset_cache") else None
        key = provider_keys.tao_key(db, provider="gemini", credential="secret-value",
                                    categories=["image"])
        db.commit()
        assert provider_keys.lay_credential(db, key) == "secret-value"
        assert key.credential_enc != "secret-value"
    finally:
        if previous is None:
            os.environ.pop("LTT_TOKEN_ENCRYPTION_KEY", None)
        else:
            os.environ["LTT_TOKEN_ENCRYPTION_KEY"] = previous


# ── PostgreSQL-only guarantees ────────────────────────────────────────────────
#
# SQLite enforces UNIQUE too, but the platform runs on PostgreSQL and the claim
# being made is about *that* engine, under concurrent inserts. Set
# LTT_TEST_DATABASE_URL to a throwaway database to run these (the file's other
# tests stay engine-agnostic so a laptop without PostgreSQL is still green).

import os as _os

# Qua `pg_scratch`, vì fixture dưới đây gọi `drop_all()` — xem file đó vì sao
# một biến môi trường gõ nhầm là chuyện nghiêm trọng trên máy chủ.
from tests.pg_scratch import scratch_url

PG_URL = scratch_url()
postgres_only = pytest.mark.skipif(
    not PG_URL, reason="Set LTT_TEST_DATABASE_URL to a scratch PostgreSQL database.")


@pytest.fixture()
def pg_sessionmaker():
    import platform_core.models  # noqa: F401
    from platform_core.db import Base

    engine = sa.create_engine(PG_URL, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield maker
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@postgres_only
def test_key_id_is_unique_at_the_database_level(pg_sessionmaker):
    """The uniqueness of key_id is part of authentication, not just tidiness."""
    from sqlalchemy.exc import IntegrityError

    session = pg_sessionmaker()
    user = _user(session, "pg-owner@example.com")
    key, _token = devkeys.issue(session, user_id=user.id, env=ENV)
    session.commit()

    clone = DeveloperApiKey(
        id="00000000-0000-0000-0000-000000000001", user_id=user.id,
        key_id=key.key_id, verifier_digest="0" * 64, pepper_version=1,
        scopes=[], allowed_tools=[], created_at=datetime.now(timezone.utc))
    session.add(clone)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.close()


@postgres_only
def test_a_user_with_keys_cannot_be_deleted(pg_sessionmaker):
    """RESTRICT: a key is evidence about who spent what; deactivate, don't delete."""
    from sqlalchemy.exc import IntegrityError
    from platform_core.models import User

    session = pg_sessionmaker()
    user = _user(session, "pg-restrict@example.com")
    devkeys.issue(session, user_id=user.id, env=ENV)
    session.commit()

    session.execute(sa.delete(User).where(User.id == user.id))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.close()


# ── Verification cost (DoS guard) ─────────────────────────────────────────────

def test_verification_is_cheap_enough_to_run_on_every_request(db):
    """A KDF-priced verifier here would be an anonymous CPU amplifier."""
    import time

    user = _user(db)
    _key, token = _issue(db, user)
    devkeys.verify(db, token, env=ENV)
    started = time.perf_counter()
    for _ in range(50):
        devkeys.verify(db, token, env=ENV)
    per_call_ms = (time.perf_counter() - started) * 1000 / 50
    # Generous ceiling: the digest itself is microseconds, the rest is one
    # indexed lookup. This fails loudly if someone swaps in bcrypt/argon2.
    assert per_call_ms < 10, f"verify() takes {per_call_ms:.2f} ms per call"
