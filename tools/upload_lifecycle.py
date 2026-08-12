"""Operator CLI cho upload staging: xem trước, dọn và đối soát object/DB.

Mặc định chỉ dry-run. Chỉ ``--apply`` mới xóa artifact hết hạn. Lệnh không in
storage key, filename hay dữ liệu khách hàng; báo cáo chỉ gồm id/trạng thái/bytes.
"""
from __future__ import annotations

import argparse
import json

from platform_core import upload_sessions
from platform_core.db import get_session
from platform_core.storage import get_storage


def run(*, apply: bool = False, reconcile: bool = False,
        limit: int = 500) -> dict:
    gen = get_session(); db = next(gen)
    try:
        report = upload_sessions.sweep(
            db, get_storage(), dry_run=not apply, limit=limit)
        if reconcile:
            report["reconcile"] = upload_sessions.reconcile(
                db, get_storage(), limit=limit)
        if apply:
            db.commit()
        else:
            db.rollback()
        return report
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit/dọn upload session hết hạn")
    parser.add_argument("--apply", action="store_true",
                        help="Xóa thật; mặc định chỉ dry-run")
    parser.add_argument("--reconcile", action="store_true",
                        help="Đối soát artifact được DB theo dõi")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    print(json.dumps(run(apply=args.apply, reconcile=args.reconcile,
                         limit=max(1, min(args.limit, 5000))),
                     ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
