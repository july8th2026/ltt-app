"""Deactivate P13 canary users and revoke their sessions; keep audit rows."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_env(path: Path) -> None:
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            os.environ[name.strip()] = value.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True)
    parser.add_argument("--email", action="append",
                        help="Deactivate only the named canary account; repeatable.")
    args = parser.parse_args()
    load_env(Path(args.env))

    from platform_core.db import get_session
    from platform_core.models import Session as UserSession, User

    emails = set(args.email or {"agent-canary@lttstudios.com",
                                "agent-internal@lttstudios.com",
                                "agent-public@lttstudios.com"})
    db = next(get_session())
    try:
        users = db.query(User).filter(User.email.in_(emails)).all()
        ids = [user.id for user in users]
        if ids:
            db.query(UserSession).filter(UserSession.user_id.in_(ids)).delete(
                synchronize_session=False)
        for user in users:
            user.is_active = False
        db.commit()
        print(f"Deactivated {len(users)} canary users; sessions revoked; audit kept.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
