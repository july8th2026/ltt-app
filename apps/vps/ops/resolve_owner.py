"""Resolve one production owner by exact login email without printing email data."""
from __future__ import annotations

import argparse
import contextlib

from sqlalchemy.orm import Session

from platform_core.db import get_session
from platform_core.users import tim_theo_email


def resolve_owner(db: Session, email: str) -> str | None:
    owner = tim_theo_email(db, email)
    return str(owner.id) if owner is not None else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    sessions = get_session()
    db = next(sessions)
    try:
        owner_id = resolve_owner(db, args.email)
    finally:
        with contextlib.suppress(StopIteration):
            next(sessions)
    if owner_id is None:
        print("OWNER_LOOKUP_FAIL count=0")
        return 1
    print(f"OWNER_LOOKUP_PASS count=1 user_id={owner_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
