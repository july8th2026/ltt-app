"""Isolated UI fixture for H13.upscalevideo Playwright flows.

Guarded so it can never attach to production data. The optional source video is
copied into isolated LocalStorage and is not modified.
"""
from __future__ import annotations

import os

if os.environ.get("LTT_UPSCALE_BROWSER_TEST") != "1":
    raise SystemExit("Set LTT_UPSCALE_BROWSER_TEST=1 for the isolated UI fixture.")
if "upscale-browser-test" not in os.environ.get("LTT_DATABASE_URL", ""):
    raise SystemExit("Refusing to run without an upscale-browser-test database path.")

from platform_core import credit
from platform_core.db import Base, get_engine, get_session
from platform_core.models import JOB_DONE, JOB_ERROR, JOB_RUNNING, Job
import platform_core.models  # noqa: F401
from platform_core.storage import get_storage
from platform_core.users import tao_nguoi_dung

Base.metadata.drop_all(get_engine())
Base.metadata.create_all(get_engine())
gen = get_session(); db = next(gen)
user = tao_nguoi_dung(db, email="upscale-ui@example.com",
                      password="Browser-test-123", is_verified=True)
credit.cap_tay(db, user.id, 1000, by="browser-test")

source_path = os.environ.get("LTT_UPSCALE_BROWSER_VIDEO", "").strip()
source_key = f"taovideo/{user.id}/browser/source.mp4"
output_key = f"upscalevideo/{user.id}/browser/output.mp4"
if source_path and os.path.isfile(source_path):
    storage = get_storage()
    with open(source_path, "rb") as fh:
        storage.put(source_key, fh, content_type="video/mp4")
    with open(source_path, "rb") as fh:
        storage.put(output_key, fh, content_type="video/mp4")

seedance = Job(
    user_id=user.id, app_slug="taovideo", job_type="taovideo.generate",
    status=JOB_DONE,
    params={"prompt": "Browser fixture Seedance", "duration": 5,
            "resolution": "1080p", "aspect_ratio": "16:9"},
    result={"video_key": source_key, "duration": 5},
)
running = Job(
    user_id=user.id, app_slug="upscalevideo", job_type="upscalevideo.render",
    status=JOB_RUNNING, progress=65, progress_msg="nâng nét…",
    params={"video_key": source_key, "duration_s": 5, "target_height": 1080,
            "preset": "fast", "codec": "h264", "owner_id": user.id},
)
done = Job(
    user_id=user.id, app_slug="upscalevideo", job_type="upscalevideo.render",
    status=JOB_DONE, progress=100,
    params={"video_key": source_key, "duration_s": 5, "target_height": 1080,
            "preset": "fast", "codec": "h264", "owner_id": user.id},
    result={"video_key": output_key, "duration_s": 5, "target_height": 1080},
)
failed = Job(
    user_id=user.id, app_slug="upscalevideo", job_type="upscalevideo.render",
    status=JOB_ERROR, progress=12, error="Browser fixture: engine unavailable",
    params={"video_key": source_key, "duration_s": 5, "target_height": 2160,
            "preset": "quality", "codec": "hevc", "owner_id": user.id},
)
db.add_all([seedance, running, done, failed])
db.commit(); db.close()

from server.app import create_app

app = create_app(env={
    "LTT_ENV": "local-server-test",
    "LTT_CONFIG_PATH": os.environ["LTT_CONFIG_PATH"],
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_ADMIN_USERNAME": "",
    "LTT_ADMIN_PASSWORD_HASH": "",
})
