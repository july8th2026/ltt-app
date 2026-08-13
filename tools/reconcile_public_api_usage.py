"""Reconcile what the API reports against the credit ledger.

    python tools\reconcile_public_api_usage.py --days 30
    python tools\reconcile_public_api_usage.py --user <id> --days 7

Why it exists even though usage is *derived* from the ledger: derived today does
not mean derived forever. The day somebody adds a projection table for speed,
this command is what proves the projection still agrees with the money — and
running it now, while the answer is trivially yes, is what makes it trustworthy
then.

Read-only. Prints a report and exits non-zero when anything disagrees, so it can
be wired into a scheduled check.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--user", default="")
    args = parser.parse_args()

    from platform_core.db import get_session
    from platform_core.public_api import usage

    until = datetime.now(timezone.utc)
    since = until - timedelta(days=max(1, args.days))

    gen = get_session()
    db = next(gen)
    try:
        report = usage.reconcile(db, user_id=args.user, since=since, until=until)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    print(json.dumps(report, indent=1, default=str))
    print("RECONCILE:", "PASS" if report["ok"] else "FAIL")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
