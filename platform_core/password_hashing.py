"""
Password hashing — PBKDF2-HMAC-SHA256 (P3).

No new third-party dependency (passlib/bcrypt) was added since PBKDF2 is
built into Python's stdlib `hashlib` and is an OWASP-approved algorithm for
this use case (a single local administrator account, not a high-volume
multi-tenant user table where bcrypt/argon2's extra tuning knobs would
matter more). Iteration count follows OWASP's 2023 minimum recommendation
for PBKDF2-SHA256.

Stored format: "pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>" — the
iteration count travels with the hash so it can be raised later without
invalidating previously-hashed passwords (verify always uses the stored
count; re-hash-on-login-if-outdated is a follow-up, not needed for the
first admin account).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 600_000  # OWASP 2023 minimum for PBKDF2-HMAC-SHA256
_SALT_BYTES = 16


def hash_password(plain_password: str) -> str:
    if not plain_password:
        raise ValueError("plain_password must not be empty")
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, _ITERATIONS)
    return "$".join([
        _ALGO,
        str(_ITERATIONS),
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    ])


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Constant-time verification. Never raises on malformed input —
    returns False instead, so a corrupted/foreign hash just fails closed."""
    try:
        algo, iterations_s, salt_b64, hash_b64 = stored_hash.split("$")
        if algo != _ALGO:
            return False
        iterations = int(iterations_s)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(hash_b64.encode("ascii"))
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), salt, iterations,
    )
    return hmac.compare_digest(candidate, expected)
