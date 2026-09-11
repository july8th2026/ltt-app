"""Reproducible queue-selection/snapshot benchmark for Scheduler V1.

The script writes only to an OS temporary directory and prints JSON. It keeps
the old FIFO selector beside the canonical selector so each run reports a
same-machine before/after comparison at 1k, 5k and 10k queued rows.
"""
from __future__ import annotations

import json
import os
import pathlib
import statistics
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, select

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _median_ms(action, repeats: int = 5) -> float:
    measured = []
    for _ in range(repeats):
        started = time.perf_counter()
        action()
        measured.append((time.perf_counter() - started) * 1000)
    return round(statistics.median(measured), 3)


def _run(size: int) -> dict:
    import platform_core.db as dbmod
    from platform_core import job_scheduler
    from platform_core.models import JOB_QUEUED, Job

    now = datetime.now(timezone.utc)
    rows = []
    subject_id = ""
    for index in range(size):
        job_id = str(uuid.uuid4())
        priority = "internal" if index % 5 == 0 else "external"
        if index == size - 1:
            subject_id = job_id
            priority = "external"
        rows.append({
            "id": job_id,
            "user_id": f"account-{index % 200}",
            "app_slug": "benchmark",
            "job_type": "benchmark.run",
            "params": {},
            "status": JOB_QUEUED,
            "origin": "internal_runtime" if priority == "internal" else "public_api",
            "priority_class": priority,
            "admission_resource": "benchmark_cpu",
            "admission_slots": 4,
            "created_at": now - timedelta(milliseconds=size - index),
            "next_run_at": now - timedelta(seconds=1),
        })
    dbmod.Base.metadata.drop_all(dbmod.get_engine())
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    try:
        session.execute(insert(Job), rows)
        session.commit()
        fifo = select(Job.id).where(
            Job.status == JOB_QUEUED, Job.next_run_at <= now,
        ).order_by(Job.created_at, Job.id).limit(1)
        canonical = select(Job.id).where(
            Job.status == JOB_QUEUED, Job.next_run_at <= now,
        ).order_by(*job_scheduler.order_expressions(Job, now=now)).limit(1)
        subject = session.get(Job, subject_id)
        assert subject is not None
        fifo_ms = _median_ms(lambda: session.execute(fifo).scalar_one())
        canonical_ms = _median_ms(
            lambda: session.execute(canonical).scalar_one())
        snapshot_ms = _median_ms(
            lambda: job_scheduler.queue_snapshot(session, subject, now=now),
            repeats=3)
        view = job_scheduler.queue_snapshot(session, subject, now=now)
        return {
            "queued_jobs": size,
            "fifo_select_median_ms": fifo_ms,
            "canonical_select_median_ms": canonical_ms,
            "queue_snapshot_median_ms": snapshot_ms,
            "subject_position": view["position"],
            "subject_eta": view["estimated_wait_seconds"],
        }
    finally:
        session.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ltt-scheduler-bench-") as directory:
        os.environ["LTT_DATABASE_URL"] = (
            "sqlite:///" + os.path.join(directory, "queue.db").replace("\\", "/"))
        import platform_core.db as dbmod

        dbmod.reset_engine()
        try:
            result = {
                "engine": "sqlite",
                "samples": [_run(size) for size in (1_000, 5_000, 10_000)],
            }
        finally:
            dbmod.reset_engine()
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
