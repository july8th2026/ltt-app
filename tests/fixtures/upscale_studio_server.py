"""Isolated H32 Upscale Studio browser fixture.

The fixture renders the real application against a disposable database and
local storage.  It may copy the user-provided source video into that storage
for playback, but it never starts a worker or touches production data.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(os.environ["UPSCALE_STUDIO_FIXTURE_ROOT"]).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
os.environ["LTT_UPSCALE_BROWSER_TEST"] = "1"
os.environ["LTT_DATABASE_URL"] = (
    f"sqlite:///{(ROOT / 'upscale-browser-test.db').as_posix()}"
)
os.environ["LTT_DATA_DIR"] = str(ROOT / "data")
os.environ["LTT_ENV"] = "development"
os.environ["LTT_SESSION_SECRET"] = "upscale-studio-browser-fixture"

config = ROOT / "config.json"
config.write_text(
    json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
    encoding="utf-8",
)
os.environ["LTT_CONFIG_PATH"] = str(config)

from tools.upscale_browser_server import app  # noqa: E402,F401
