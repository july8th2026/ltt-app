"""Run the customer-visible Upscale option matrix with reproducible evidence."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def _cases() -> list[dict]:
    cases = [
        {"name": f"{preset}-{height}-{codec}", "preset": preset,
         "height": height, "codec": codec, "flags": []}
        for preset in ("fast", "quality")
        for height in (1080, 1440, 2160)
        for codec in ("h264", "hevc")
    ]
    cases.extend([
        {"name": "fast-1080-normalize30-noaudio", "preset": "fast",
         "height": 1080, "codec": "h264",
         "flags": ["--no-preserve-fps", "--no-preserve-audio"]},
        {"name": "fast-1080-stabilize", "preset": "fast", "height": 1080,
         "codec": "h264", "flags": ["--stabilize"]},
        {"name": "fast-1080-smooth2x", "preset": "fast", "height": 1080,
         "codec": "h264", "flags": ["--smooth-motion"]},
        {"name": "fast-1080-stabilize-smooth2x", "preset": "fast",
         "height": 1080, "codec": "h264",
         "flags": ["--stabilize", "--smooth-motion"]},
        {"name": "fast-1080-preview", "preset": "fast", "height": 1080,
         "codec": "h264", "flags": ["--preview"]},
    ])
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gpu-index", type=int, default=1)
    parser.add_argument("--max-seconds", type=float, default=1.0)
    parser.add_argument("--resume", action="store_true",
                        help="Reuse case evidence that already passed.")
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit("Source video does not exist.")

    root = Path(__file__).resolve().parents[1]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    started = time.perf_counter()
    for index, case in enumerate(_cases(), 1):
        evidence_file = args.output_dir / f"{case['name']}.json"
        artifact_file = args.output_dir / f"{case['name']}.mp4"
        if args.resume and evidence_file.is_file():
            old = json.loads(evidence_file.read_text(encoding="utf-8"))
            if old.get("passed") is True:
                print(f"[{index}/{len(_cases())}] {case['name']} (reuse PASS)",
                      flush=True)
                results.append({
                    "name": case["name"], "returncode": 0, "passed": True,
                    "elapsed_seconds": old.get("elapsed_seconds"),
                    "output": old.get("output", {}),
                    "gpu_memory_evidence": old.get("gpu_memory_evidence", {}),
                    "error_tail": "",
                })
                continue
        command = [
            sys.executable, str(root / "tools" / "upscale_gpu_smoke.py"),
            str(args.source), "--output", str(evidence_file), "--gpu-index",
            str(args.gpu_index), "--preset", case["preset"], "--target-height",
            str(case["height"]), "--codec", case["codec"], "--max-seconds",
            str(args.max_seconds),
        ] + list(case["flags"])
        if case["name"] == "fast-1080-h264":
            command += ["--artifact-output", str(artifact_file)]
        print(f"[{index}/{len(_cases())}] {case['name']}", flush=True)
        run = subprocess.run(command, cwd=root, capture_output=True, text=True,
                             timeout=1800, check=False)
        evidence = {}
        if evidence_file.is_file():
            evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        results.append({
            "name": case["name"], "returncode": run.returncode,
            "passed": evidence.get("passed") is True,
            "elapsed_seconds": evidence.get("elapsed_seconds"),
            "output": evidence.get("output", {}),
            "gpu_memory_evidence": evidence.get("gpu_memory_evidence", {}),
            "error_tail": (run.stderr or run.stdout)[-1000:]
            if run.returncode else "",
        })

    aggregate = {
        "schema_version": 1,
        "passed": all(row["returncode"] == 0 and row["passed"] for row in results),
        "source_name": args.source.name,
        "gpu_index": args.gpu_index,
        "max_seconds": args.max_seconds,
        "wall_seconds": round(time.perf_counter() - started, 3),
        "cases": results,
    }
    target = args.output_dir / "matrix-summary.json"
    target.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    print(json.dumps({"passed": aggregate["passed"],
                      "wall_seconds": aggregate["wall_seconds"]}), flush=True)
    return 0 if aggregate["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
