"""Benchmark the developer API key verification path (Prompt 03 acceptance).

Why this exists: the auth check runs on **every** API request, so its cost is a
denial-of-service question, not a micro-optimisation one. A password-grade KDF
here (bcrypt/argon2, tens of milliseconds by design) would let an anonymous
caller burn a CPU core per request. This script measures what we actually ship
so the claim "verification is cheap" is a number, not an opinion.

    python tools\\bench_public_api_key.py            # digest only, no database
    python tools\\bench_public_api_key.py --db       # full path incl. one query

The database run needs ``LTT_TEST_DATABASE_URL`` (PostgreSQL used for tests) or
``--sqlite`` for a throwaway file database.
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from platform_core.public_api import keys as devkeys  # noqa: E402

BENCH_PEPPER = "bench-pepper-" + "x" * 40
SAMPLES = 2000


def _percentiles(samples: list[float]) -> dict:
    ordered = sorted(samples)
    return {
        "n": len(ordered),
        "p50_us": round(statistics.median(ordered) * 1e6, 2),
        "p95_us": round(ordered[int(0.95 * (len(ordered) - 1))] * 1e6, 2),
        "p99_us": round(ordered[int(0.99 * (len(ordered) - 1))] * 1e6, 2),
        "per_second": int(1 / statistics.median(ordered)) if ordered else 0,
    }


def bench_digest(samples: int = SAMPLES) -> dict:
    secret = devkeys._new_secret()
    devkeys.digest_secret(secret, BENCH_PEPPER)  # warm up
    timings = []
    for _ in range(samples):
        started = time.perf_counter()
        devkeys.digest_secret(secret, BENCH_PEPPER)
        timings.append(time.perf_counter() - started)
    return _percentiles(timings)


def bench_full(url: str, samples: int = 500) -> dict:
    import sqlalchemy as sa
    from sqlalchemy.orm import sessionmaker

    import platform_core.models  # noqa: F401 - registers tables
    from platform_core.db import Base
    from platform_core.users import tao_nguoi_dung

    env = {devkeys.PEPPER_ENV: BENCH_PEPPER}
    engine = sa.create_engine(url, future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        user = tao_nguoi_dung(session, email=f"bench-{uuid.uuid4().hex[:8]}@x.com",
                              password="bench-password-123")
        session.commit()
        _key, token = devkeys.issue(session, user_id=user.id, name="bench", env=env)
        session.commit()
        devkeys.verify(session, token, env=env)  # warm up
        timings = []
        for _ in range(samples):
            started = time.perf_counter()
            devkeys.verify(session, token, env=env)
            timings.append(time.perf_counter() - started)
        return _percentiles(timings)
    finally:
        session.close()
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", action="store_true",
                        help="also measure verify() including the lookup query")
    parser.add_argument("--sqlite", action="store_true",
                        help="use a throwaway SQLite file for --db")
    args = parser.parse_args()

    digest = bench_digest()
    print("digest HMAC-SHA256 :", digest)

    if args.db:
        url = os.environ.get("LTT_TEST_DATABASE_URL", "").strip()
        if args.sqlite or not url:
            path = Path(tempfile.gettempdir()) / f"ltt-bench-{uuid.uuid4().hex}.db"
            url = f"sqlite:///{path.as_posix()}"
            print("using throwaway SQLite:", path.name)
        print("verify() full path :", bench_full(url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
