"""Isolated local server for Scheduler V1 browser acceptance.

Uses an OS-temporary SQLite database and synthetic accounts only. It never
reads production credentials or production data.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EMAIL = "scheduler-browser@example.com"
PASSWORD = "Browser-test-123"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8117)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="ltt-scheduler-browser-") as directory:
        root = Path(directory)
        os.environ["LTT_DATABASE_URL"] = (
            f"sqlite:///{(root / 'scheduler.db').as_posix()}")
        os.environ["LTT_DATA_DIR"] = str(root / "data")

        import platform_core.db as dbmod
        import platform_core.models  # noqa: F401
        from platform_core import credit, jobs
        from platform_core.db import Base, get_engine, get_session
        from platform_core.users import tao_nguoi_dung

        dbmod.reset_engine()
        Base.metadata.create_all(get_engine())
        gen = get_session()
        db = next(gen)
        try:
            user = tao_nguoi_dung(
                db, email=EMAIL, password=PASSWORD, is_verified=True)
            credit.cap_tay(db, user.id, 100, by="scheduler-browser")
            external = jobs.submit(
                db, user_id=user.id, app_slug="thumbnail",
                job_type="thumbnail.generate", params={"topic": "external"},
                admission_resource="browser-gpu", admission_slots=1,
                origin="public_api", priority_class="external")
            internal = jobs.submit(
                db, user_id="internal-product", app_slug="thumbnail",
                job_type="thumbnail.generate", params={"topic": "internal"},
                admission_resource="browser-gpu", admission_slots=1,
                origin="internal_runtime", priority_class="internal")
            db.commit()
            external_id, internal_id = external.id, internal.id
        finally:
            db.close()

        from server.app import create_app

        app = create_app(env={
            "LTT_ENV": "development",
            "LTT_SESSION_SECRET": "scheduler-browser-session-secret",
            "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
            "LTT_CONFIG_PATH": str(root / "config.json"),
            "LTT_PUBLIC_API": "0",
        })
        print(f"URL=http://127.0.0.1:{args.port}", flush=True)
        print(f"EMAIL={EMAIL}", flush=True)
        print(f"PASSWORD={PASSWORD}", flush=True)
        print(f"EXTERNAL_JOB={external_id}", flush=True)
        print(f"INTERNAL_JOB={internal_id}", flush=True)

        import uvicorn

        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
