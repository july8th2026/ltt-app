"""Isolated Seedance browser fixture for H32.5 visual audit.

The fixture renders the real app routes with representative history states.  It
never starts a worker or calls the video provider.  An optional local MP4 may be
copied into fixture storage solely to exercise the real HTML video/card layout.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(os.environ["SEEDANCE_STUDIO_FIXTURE_ROOT"]).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(ROOT / 'browser.db').as_posix()}"
os.environ["LTT_DATA_DIR"] = str(ROOT / "data")
os.environ["LTT_ENV"] = "development"
os.environ["LTT_SESSION_SECRET"] = "seedance-studio-browser-fixture"

config = ROOT / "config.json"
config.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                  encoding="utf-8")

import platform_core.db as dbmod  # noqa: E402
import platform_core.models  # noqa: E402,F401
from platform_core.credit import cap_tay  # noqa: E402
from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR,  # noqa: E402
                                  JOB_RUNNING, Job, User)
from platform_core.storage import get_storage  # noqa: E402
from platform_core.users import tao_nguoi_dung  # noqa: E402


dbmod.Base.metadata.create_all(dbmod.get_engine())
gen = dbmod.get_session(); db = next(gen)
try:
    user = db.query(User).filter_by(email="seedance-browser@example.com").one_or_none()
    if user is None:
        user = tao_nguoi_dung(db, email="seedance-browser@example.com",
                              password="Browser-pass-123", is_verified=True)
        db.flush(); cap_tay(db, user.id, 500, by="fixture", note="browser H32.5")

    if not db.query(Job).filter_by(user_id=user.id, app_slug="taovideo").first():
        source = Path(os.environ.get("SEEDANCE_FIXTURE_VIDEO", ""))
        video_key = ""
        if source.is_file():
            video_key = f"taovideo/{user.id}/fixture/result.mp4"
            with source.open("rb") as stream:
                get_storage().put(video_key, stream, content_type="video/mp4")

        image_ref = f"taovideo/{user.id}/refs/fixture-character.png"
        common = {"resolution": "720p", "duration": 5, "aspect_ratio": "16:9"}
        db.add_all([
            Job(user_id=user.id, app_slug="taovideo", job_type="taovideo.generate",
                status=JOB_DONE, progress=100,
                params={**common, "model": "seedance-2.0-mini",
                        "prompt": "Máy quay tiến chậm qua thành phố đêm mưa, ánh đèn neon phản chiếu.",
                        "raw_prompt": "Máy quay tiến chậm qua thành phố đêm mưa, ánh đèn neon phản chiếu.",
                        "refs": [{"storage_key": image_ref, "kind": "image",
                                  "role": "reference_image", "handle": "@nhanvat",
                                  "name": "Nhân vật chính.png", "size": 734003}]},
                result={"video_key": video_key, "model": "seedance-2.0-mini"}),
            Job(user_id=user.id, app_slug="taovideo", job_type="taovideo.generate",
                status=JOB_RUNNING, progress=64, progress_msg="Đang dựng chuyển động",
                params={**common, "model": "seedance-2.0-fast",
                        "aspect_ratio": "9:16", "duration": 4,
                        "prompt": "Vũ công biểu diễn dưới sân khấu ánh sáng đỏ."}),
            Job(user_id=user.id, app_slug="taovideo", job_type="taovideo.generate",
                status=JOB_ERROR, progress=22, error="Không thể tạo video. Hãy thử lại sau.",
                params={**common, "model": "seedance-2.0",
                        "prompt": "Cảnh hành động tốc độ cao trong nhà kho."}),
            Job(user_id=user.id, app_slug="taovideo", job_type="taovideo.generate",
                status=JOB_CANCELLED, progress=31,
                params={**common, "model": "seedance-2.0-mini", "aspect_ratio": "1:1",
                        "prompt": "Phong cảnh núi lúc bình minh."}),
        ])
    db.commit()
finally:
    try: next(gen)
    except StopIteration: pass

from server.app import create_app  # noqa: E402

app = create_app(env={
    "LTT_ENV": "development", "LTT_CONFIG_PATH": str(config),
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
})
