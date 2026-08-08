"""Deterministic H26 queue/event/metric soak on an isolated SQLite database.

This does not call providers and is not a replacement for GPU/browser canary.
It exercises the real Job state functions and produces per-app SLO evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="H26 isolated queue soak")
    parser.add_argument("--jobs-per-app", type=int, default=100)
    args = parser.parse_args()
    per_app = max(20, min(int(args.jobs_per_app), 1000))
    profiles = {
        "soak-api": ("api",),
        "soak-compute": ("gpu", "ffmpeg"),
        "soak-browser": ("browser",),
    }

    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ltt_h26_soak_") as tmp:
        os.environ["LTT_DATABASE_URL"] = (
            f"sqlite:///{(pathlib.Path(tmp) / 'soak.db').as_posix()}")
        import platform_core.db as dbmod
        dbmod.reset_engine()
        import platform_core.models  # noqa: F401
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        from platform_core import job_metrics, jobs
        from platform_core.models import CREDIT_HOLD, CREDIT_SETTLE, CreditEntry

        gen = dbmod.get_session(); db = next(gen)
        try:
            base = datetime.now(timezone.utc)
            for app_slug in profiles:
                for index in range(per_app):
                    row = jobs.submit(
                        db, user_id=f"user-{app_slug}", app_slug=app_slug,
                        job_type=f"{app_slug}.run", params={"index": index},
                        max_attempts=1)
                    row.created_at = base - timedelta(seconds=1 + index % 5)
            db.commit()

            processed = 0
            while True:
                row = jobs.claim(db, worker_id=f"soak-worker-{processed % 4}")
                if row is None:
                    break
                if processed % 50 == 0:
                    jobs.fail(db, row, "synthetic provider outage")
                else:
                    jobs.complete(db, row, {"artifact_count": 1})
                    db.add_all([
                        CreditEntry(user_id=row.user_id, delta=-5, kind=CREDIT_HOLD,
                                    job_id=row.id),
                        CreditEntry(user_id=row.user_id, delta=2, kind=CREDIT_SETTLE,
                                    job_id=row.id),
                    ])
                processed += 1
                if processed % 50 == 0:
                    db.commit()
            db.commit()

            evidence = {"kind": "synthetic_sqlite_queue", "jobs": processed,
                        "apps": {}, "wall_seconds": 0.0, "passed": True}
            now = datetime.now(timezone.utc)
            for app_slug, requires in profiles.items():
                metrics = job_metrics.snapshot(db, now=now, app_slug=app_slug)
                slo = job_metrics.evaluate_slo(
                    metrics, job_metrics.slo_budget(requires))
                evidence["apps"][app_slug] = {"metrics": metrics, "slo": slo}
                evidence["passed"] = evidence["passed"] and slo["state"] == "pass"
            evidence["wall_seconds"] = round(time.perf_counter() - started, 3)
            print(json.dumps(evidence, ensure_ascii=True, default=str,
                             sort_keys=True))
            return 0 if evidence["passed"] else 1
        finally:
            db.close()
            dbmod.reset_engine()
            try:
                next(gen)
            except StopIteration:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
