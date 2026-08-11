"""CLI offline để kiểm kê và materialize dataset Quality Lab có provenance."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "apps").is_dir() and (parent / "tools").is_dir())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.qualitylab.datasets import readiness_report
from apps.qualitylab.materializer import inspect_intake, materialize_dataset


def _json(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Quality Lab dataset materializer")
    parser.add_argument("action", choices=("inspect", "materialize", "readiness"))
    parser.add_argument("--intake")
    parser.add_argument("--manifest")
    parser.add_argument("--source-root")
    parser.add_argument("--output-root")
    args = parser.parse_args()

    if args.action == "readiness":
        if not args.manifest:
            parser.error("readiness requires --manifest")
        result = readiness_report(_json(args.manifest))
    else:
        if not args.intake or not args.source_root:
            parser.error(f"{args.action} requires --intake and --source-root")
        intake = _json(args.intake)
        if args.action == "inspect":
            manifest = inspect_intake(intake, Path(args.source_root))["manifest"]
        else:
            if not args.output_root:
                parser.error("materialize requires --output-root")
            manifest = materialize_dataset(
                intake, Path(args.source_root), Path(args.output_root))
        result = readiness_report(manifest)
        result["item_count"] = len(manifest["items"])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
