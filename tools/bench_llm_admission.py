"""CPU-only load harness cho admission/queue LTT LLM.

Chỉ dùng CSDL SQLite vứt đi và provider giả bằng việc complete job trực tiếp;
không đọc GPU, không gọi mạng, không đụng dữ liệu production.

    python tools\bench_llm_admission.py --accounts 10 --jobs 1000 --polls 3
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from platform_core.db import Base


def _rate(count: int, seconds: float) -> float:
    return round(count / max(seconds, 0.000001), 2)


def run(*, accounts: int = 10, total_jobs: int = 1000, polls: int = 3) -> dict:
    """Chạy tải DB/queue/poll cô lập và trả report JSON-serializable."""
    from platform_core import job_history, job_metrics, jobs
    from platform_core.public_api import metrics
    import platform_core.models  # noqa: F401 - đăng ký toàn bộ bảng

    account_count = max(1, int(accounts))
    job_count = max(1, int(total_jobs))
    poll_count = max(0, int(polls))
    metrics.reset()

    with tempfile.TemporaryDirectory(prefix="ltt-llm-admission-") as temp_dir:
        path = Path(temp_dir) / "queue.db"
        engine = sa.create_engine(f"sqlite:///{path.as_posix()}", future=True)
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine, expire_on_commit=False, future=True)()
        try:
            started = time.perf_counter()
            for index in range(job_count):
                jobs.submit(
                    db, user_id=f"bench-account-{index % account_count}",
                    app_slug="bench", job_type="bench.llm", params={},
                    admission_resource="llm_remote", admission_slots=1)
            db.commit()
            submit_s = time.perf_counter() - started

            poll_samples = []
            started = time.perf_counter()
            for _ in range(poll_count):
                for account in range(account_count):
                    tick = time.perf_counter()
                    job_history.list_owned(
                        db, f"bench-account-{account}", status="queued", limit=50)
                    poll_samples.append(time.perf_counter() - tick)
            poll_s = time.perf_counter() - started

            started = time.perf_counter()
            drained = 0
            while True:
                job = jobs.claim(db, worker_id="bench-worker")
                if job is None:
                    db.commit()
                    break
                jobs.mark_admitted(db, job)
                jobs.complete(db, job, {"mock": True})
                db.commit()
                drained += 1
            drain_s = time.perf_counter() - started
            snap = job_metrics.snapshot(db)
            local_metrics = metrics.snapshot()
            return {
                "accounts": account_count,
                "jobs": job_count,
                "polls": poll_count * account_count,
                "submitted_per_s": _rate(job_count, submit_s),
                "drained_per_s": _rate(drained, drain_s),
                "poll_p50_ms": round(
                    statistics.median(poll_samples) * 1000, 3)
                    if poll_samples else 0.0,
                "poll_total_s": round(poll_s, 3),
                "drained": drained,
                "queue_depth_end": snap["queue_depth"],
                "admission_delay_p95_s": snap["admission_delay_p95_s"],
                "metric_observations_in_process": sum(
                    bucket["count"] for bucket in
                    local_metrics["latency"].values()),
                "provider_calls": 0,
                "gpu_reads": 0,
            }
        finally:
            db.close()
            engine.dispose()
            metrics.reset()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accounts", type=int, default=10)
    parser.add_argument("--jobs", type=int, default=1000, dest="total_jobs")
    parser.add_argument("--polls", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(run(**vars(args)), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
