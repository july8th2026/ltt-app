"""Create a disposable production canary session without exposing credentials."""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_env(path: Path) -> None:
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ[name.strip()] = value.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--base-url", default="https://app.lttstudios.com")
    parser.add_argument("--email", default="agent-canary@lttstudios.com")
    parser.add_argument("--role", choices=("admin", "user"), default="admin")
    parser.add_argument("--user-id-file")
    args = parser.parse_args()
    load_env(Path(args.env))

    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import doi_mat_khau, tao_nguoi_dung, tim_theo_email

    email = args.email
    password = secrets.token_urlsafe(32)
    db = next(get_session())
    try:
        user = tim_theo_email(db, email)
        if user is None:
            user = tao_nguoi_dung(db, email=email, password=password, role=args.role,
                                  is_verified=True)
        else:
            doi_mat_khau(db, user, password)
            user.role = args.role
            user.is_active = True
            user.is_verified = True
        if credit.so_du(db, user.id) < 100:
            credit.cap_tay(db, user.id, 100, by="production-canary",
                           note="P13 controlled rollout canary budget")
        db.commit()
        user_id = user.id
    finally:
        db.close()

    with httpx.Client(base_url=args.base_url, follow_redirects=True, timeout=20) as client:
        login = client.get("/login?next=/agent/canvas")
        match = re.search(r'name="csrf_token" value="([^"]+)"', login.text)
        if not match:
            raise RuntimeError("Login CSRF token not found")
        response = client.post("/login", data={"username": email, "password": password,
                                               "csrf_token": match.group(1),
                                               "next": "/agent/canvas"})
        if response.status_code != 200 or "/agent/canvas" not in str(response.url):
            raise RuntimeError("Canary login failed")
        cookies = [{"name": cookie.name, "value": cookie.value,
                    "domain": cookie.domain or "app.lttstudios.com",
                    "path": cookie.path or "/", "expires": -1,
                    "httpOnly": True, "secure": True, "sameSite": "Lax"}
                   for cookie in client.cookies.jar]
    target = Path(args.state)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"cookies": cookies, "origins": []}), encoding="utf-8")
    if args.user_id_file:
        Path(args.user_id_file).write_text(user_id, encoding="ascii")
    print("Canary account/session prepared; credential values were not displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
