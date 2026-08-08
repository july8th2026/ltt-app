"""Run two guarded Upscale smokes concurrently and record thermal evidence."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def _sample() -> list[dict]:
    command = [
        "nvidia-smi",
        "--query-gpu=index,utilization.gpu,temperature.gpu,memory.used,"
        "clocks_event_reasons.sw_thermal_slowdown",
        "--format=csv,noheader,nounits",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=8,
                            check=False)
    if result.returncode != 0:
        return []
    rows = []
    for line in result.stdout.strip().splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 5:
            continue
        rows.append({"index": int(parts[0]), "util_percent": int(parts[1]),
                     "temp_c": int(parts[2]), "vram_used_mb": int(parts[3]),
                     "thermal_slowdown": parts[4]})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit("Source video does not exist.")

    root = Path(__file__).resolve().parents[1]
    evidence_dir = args.output.parent
    evidence_dir.mkdir(parents=True, exist_ok=True)
    worker_files = [evidence_dir / "h26-soak-gpu0.json",
                    evidence_dir / "h26-soak-gpu1.json"]
    processes = []
    started = time.perf_counter()
    for gpu_index, worker_file in enumerate(worker_files):
        command = [sys.executable, str(root / "tools" / "upscale_gpu_smoke.py"),
                   str(args.source), "--gpu-index", str(gpu_index), "--preset", "fast",
                   "--target-height", "1080", "--output", str(worker_file)]
        processes.append(subprocess.Popen(command, cwd=str(root),
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True))

    samples: list[dict] = []
    deadline = time.monotonic() + 900
    while any(process.poll() is None for process in processes):
        samples.extend(_sample())
        if time.monotonic() > deadline:
            for process in processes:
                if process.poll() is None:
                    process.kill()
            raise RuntimeError("Dual-GPU soak exceeded 15 minutes.")
        time.sleep(0.5)

    results = []
    for gpu_index, (process, worker_file) in enumerate(zip(processes, worker_files)):
        stdout, stderr = process.communicate()
        evidence = json.loads(worker_file.read_text(encoding="utf-8")) \
            if worker_file.is_file() else {}
        results.append({"gpu_index": gpu_index, "returncode": process.returncode,
                        "worker_passed": evidence.get("passed") is True,
                        "elapsed_seconds": evidence.get("elapsed_seconds"),
                        "output": evidence.get("output", {}),
                        "error_tail": (stderr or stdout)[-500:] if process.returncode else ""})

    per_gpu = {}
    for gpu_index in (0, 1):
        own = [row for row in samples if row["index"] == gpu_index]
        per_gpu[str(gpu_index)] = {
            "sample_count": len(own),
            "max_util_percent": max((row["util_percent"] for row in own), default=0),
            "max_temp_c": max((row["temp_c"] for row in own), default=0),
            "max_vram_used_mb": max((row["vram_used_mb"] for row in own), default=0),
            "thermal_slowdown_observed": any(
                row["thermal_slowdown"].lower() != "not active" for row in own),
        }
    passed = (all(item["returncode"] == 0 and item["worker_passed"]
                  for item in results)
              and all(data["max_util_percent"] > 0 and data["max_temp_c"] < 85
                      and not data["thermal_slowdown_observed"]
                      for data in per_gpu.values()))
    evidence = {"passed": passed, "source_name": args.source.name,
                "wall_seconds": round(time.perf_counter() - started, 3),
                "workers": results, "telemetry": per_gpu}
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    print(json.dumps(evidence, ensure_ascii=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
