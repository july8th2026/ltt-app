"""Isolated browser fixture for Quality Lab; never touches production data."""
from __future__ import annotations

import json
import os
import secrets
import threading
from pathlib import Path

if os.environ.get("LTT_QUALITYLAB_BROWSER_TEST") != "1":
    raise SystemExit("Set LTT_QUALITYLAB_BROWSER_TEST=1 for this fixture.")

ROOT = Path(os.environ["QUALITYLAB_FIXTURE_ROOT"]).resolve()
if "qualitylab-browser" not in ROOT.name:
    raise SystemExit("Refusing to run outside an isolated qualitylab-browser directory.")
ROOT.mkdir(parents=True, exist_ok=True)
os.environ.update({
    "LTT_DATABASE_URL": f"sqlite:///{(ROOT / 'browser.db').as_posix()}",
    "LTT_DATA_DIR": str(ROOT / "data"),
    "LTT_ENV": "development",
    "LTT_SESSION_SECRET": secrets.token_hex(32),
})
config = ROOT / "config.json"
config.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                              "sheet_id": "qualitylab-fixture"}), encoding="utf-8")

import platform_core.db as dbmod  # noqa: E402
import platform_core.models  # noqa: E402,F401
from platform_core.registry import load_app_tables  # noqa: E402
from platform_core.users import tao_nguoi_dung, tim_theo_email  # noqa: E402

load_app_tables()
dbmod.Base.metadata.create_all(dbmod.get_engine())
gen = dbmod.get_session(); db = next(gen)
try:
    if tim_theo_email(db, "qualitylab-admin@example.com") is None:
        tao_nguoi_dung(
            db, email="qualitylab-admin@example.com", password="Browser-test-123",
            role="admin", is_verified=True)
        db.commit()
finally:
    try:
        next(gen)
    except StopIteration:
        pass

from server.app import create_app  # noqa: E402

app = create_app(env={
    "LTT_ENV": "development", "LTT_CONFIG_PATH": str(config),
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
})

from platform_core.job_runner import run_forever  # noqa: E402

threading.Thread(target=run_forever, args=("qualitylab-browser-worker",),
                 daemon=True).start()
