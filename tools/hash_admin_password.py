"""
Operator helper: hash an admin password for LTT_ADMIN_PASSWORD_HASH (P3).

Prints only the hash — the plaintext password is read via getpass (not
echoed) and never written to disk, a log, or this repository. Copy the
printed value into your process environment / secrets manager as
LTT_ADMIN_PASSWORD_HASH; do not commit it anywhere.

Usage:
    python tools/hash_admin_password.py
"""
from __future__ import annotations

import getpass
import sys

from platform_core.password_hashing import hash_password


def main() -> int:
    pw1 = getpass.getpass("New admin password: ")
    pw2 = getpass.getpass("Confirm: ")
    if pw1 != pw2:
        print("Passwords did not match.", file=sys.stderr)
        return 1
    if len(pw1) < 12:
        print("Password must be at least 12 characters.", file=sys.stderr)
        return 1
    print(hash_password(pw1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
