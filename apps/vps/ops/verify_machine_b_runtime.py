"""Print a sanitized verdict for a mirrored Machine B runtime bundle."""
from __future__ import annotations

import argparse

from apps.vps.services.machine_b_runtime import read_machine_b_runtime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("--max-age-seconds", type=int, default=300)
    args = parser.parse_args()
    evidence = read_machine_b_runtime(
        args.directory, max_age_seconds=args.max_age_seconds)
    generated = evidence.generated_at.isoformat() if evidence.generated_at else "UNKNOWN"
    print(f"status={evidence.status} machine_health={evidence.machine_health} "
          f"generated_at={generated}")
    if evidence.reason:
        print(f"reason={evidence.reason}")
    return 0 if evidence.status == "HEALTHY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
