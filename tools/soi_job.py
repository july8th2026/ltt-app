r"""soi_job.py — in trạng thái một job và số dư của chủ nó. Chỉ đọc.

    ... tools\soi_job.py <job_id>

Dùng khi cần biết một job kết thúc ra sao và **khách có bị trừ tiền không** —
hai câu hỏi luôn đi cùng nhau, và tách chúng ra là cách bỏ sót lỗi tiền.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job_id")
    a = ap.parse_args(argv)

    from sqlalchemy import select

    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.models import Job

    gen = get_session()
    db = next(gen)
    try:
        j = db.execute(select(Job).where(Job.id == a.job_id)).scalar_one_or_none()
        if j is None:
            print(f"khong thay job {a.job_id}", file=sys.stderr)
            return 2
        for k in ("status", "job_type", "app_slug", "attempts", "user_id",
                  "created_at", "finished_at"):
            print(f"  {k:<12} {getattr(j, k, '?')}")
        print(f"  {'error':<12} {(j.error or '')[:200]}")
        print(f"  {'result':<12} {str(j.result)[:200]}")
        print(f"  {'so du chu':<12} {credit.so_du(db, j.user_id)} credit")
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
