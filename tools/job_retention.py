"""Dry-run/apply retention for terminal platform Jobs.

Dry-run is the default. Apply requires an explicit confirmation token and is
intended to run only after a verified backup. Credit ledger and artifacts are
outside this command by design (Q75).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from platform_core import job_events
from platform_core.db import get_session


def main() -> int:
    parser = argparse.ArgumentParser(description="LTT Job retention")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    if args.apply and args.confirm != "PURGE":
        parser.error("--apply requires --confirm PURGE")

    gen = get_session()
    db = next(gen)
    try:
        before = job_events.retention_report(db)
        removed_events = {job_events.CUSTOMER: 0, job_events.INTERNAL: 0}
        removed_jobs = 0
        if args.apply:
            removed_events = job_events.purge_expired(db)
            removed_jobs = job_events.purge_expired_jobs(
                db, batch_size=args.batch_size)
            db.commit()
        result = {
            "mode": "apply" if args.apply else "dry-run",
            "before": before,
            "removed": {"events": removed_events, "jobs": removed_jobs},
        }
        print(json.dumps(result, ensure_ascii=True, default=str, sort_keys=True))
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
