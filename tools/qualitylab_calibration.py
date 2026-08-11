"""CLI validate/assign/vote/aggregate for blinded Quality Lab calibration."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.qualitylab.calibration import (  # noqa: E402
    aggregate_reviews,
    blind_assignment,
    normalize_vote,
    validate_calibration_suite,
)


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("validate", "assign", "vote", "aggregate"))
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--votes", type=Path)
    parser.add_argument("--case-id", default="")
    parser.add_argument("--selection", choices=("left", "right", "tie", "insufficient"))
    parser.add_argument("--rater-env", default="LTT_QUALITYLAB_RATER_ID")
    args = parser.parse_args()
    suite = validate_calibration_suite(_read(args.suite))
    if args.action == "validate":
        output = {key: suite[key] for key in (
            "schema_version", "calibration_version", "dataset_manifest_sha256",
            "suite_sha256")}
        output["case_count"] = len(suite["cases"])
    elif args.action == "aggregate":
        if args.votes is None:
            raise SystemExit("--votes is required for aggregate")
        secret = os.environ.get("LTT_QUALITYLAB_BLIND_SECRET", "")
        output = aggregate_reviews(suite, _read(args.votes), secret)
    else:
        secret = os.environ.get("LTT_QUALITYLAB_BLIND_SECRET", "")
        rater = os.environ.get(args.rater_env, "")
        case = next((item for item in suite["cases"] if item["id"] == args.case_id), None)
        if case is None:
            raise SystemExit("case id not found")
        if args.action == "assign":
            output = blind_assignment(case, rater, secret)
        else:
            if args.selection is None:
                raise SystemExit("--selection is required for vote")
            output = normalize_vote(case, rater, args.selection, secret)
    print(json.dumps(output, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
