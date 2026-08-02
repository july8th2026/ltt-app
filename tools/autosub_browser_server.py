"""Isolated Auto Sub Studio server for Playwright regression checks.

The double guard prevents this fixture from ever touching production data.
"""
from __future__ import annotations

import os

if os.environ.get("LTT_AUTOSUB_BROWSER_TEST") != "1":
    raise SystemExit("Set LTT_AUTOSUB_BROWSER_TEST=1 for the isolated browser fixture.")
if "autosub-browser-test" not in os.environ.get("LTT_DATABASE_URL", ""):
    raise SystemExit("Refusing to run without an autosub-browser-test database path.")

from platform_core import credit
from platform_core.db import Base, get_engine, get_session
import platform_core.models  # noqa: F401
from platform_core.users import tao_nguoi_dung

Base.metadata.drop_all(get_engine())
Base.metadata.create_all(get_engine())
gen = get_session(); db = next(gen)
user = tao_nguoi_dung(db, email="autosub-ui@example.com",
                      password="Browser-test-123", is_verified=True)
credit.cap_tay(db, user.id, 1000, by="browser-test")
db.commit()
db.close()

from server.app import create_app

app = create_app(env={
    "LTT_ENV": "local-server-test",
    "LTT_CONFIG_PATH": os.environ["LTT_CONFIG_PATH"],
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_AUTOSUB_STUDIO_ROLLOUT": "public",
    "LTT_ADMIN_USERNAME": "",
    "LTT_ADMIN_PASSWORD_HASH": "",
})
