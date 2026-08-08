"""Isolated local browser fixture for PROMPT AI OMMI (never production data)."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(os.environ["OMMI_FIXTURE_ROOT"]).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(ROOT / 'browser.db').as_posix()}"
os.environ["LTT_DATA_DIR"] = str(ROOT / "data")
os.environ["LTT_ENV"] = "development"
os.environ["LTT_SESSION_SECRET"] = "prompt-ai-ommi-browser-fixture"
os.environ["LTT_PROMPT_AI_OMMI_ROLLOUT"] = "public"

config = ROOT / "config.json"
config.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                              "sheet_id": "browser-fixture"}), encoding="utf-8")

import platform_core.db as dbmod
import platform_core.models  # noqa: E402,F401
import apps.prompt_ai_ommi.tables  # noqa: E402,F401
from platform_core.credit import cap_tay  # noqa: E402
from platform_core.models import User  # noqa: E402
from platform_core.users import tao_nguoi_dung  # noqa: E402

dbmod.Base.metadata.create_all(dbmod.get_engine())
gen = dbmod.get_session(); db = next(gen)
try:
    user = db.query(User).filter_by(email="ommi-browser@example.com").one_or_none()
    if user is None:
        user = tao_nguoi_dung(db, email="ommi-browser@example.com",
                              password="Browser-pass-123", is_verified=True)
        db.flush(); cap_tay(db, user.id, 200, by="fixture", note="browser E2E")
    db.commit()
finally:
    try: next(gen)
    except StopIteration: pass

from server.app import create_app  # noqa: E402

app = create_app(env={"LTT_ENV": "development", "LTT_CONFIG_PATH": str(config),
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"], "LTT_ADMIN_USERNAME": "",
    "LTT_ADMIN_PASSWORD_HASH": ""})
