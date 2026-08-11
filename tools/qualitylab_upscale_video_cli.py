"""Run the existing Quality Lab paired-video diagnostic from the command line."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import uuid
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evaluate(candidate: Path, reference: Path, low_input: Path | None,
             performance: dict) -> dict:
    from apps.qualitylab.contracts import build_report
    from apps.qualitylab.services.upscale_video import inspect_upscale_video_pair

    with tempfile.TemporaryDirectory(prefix="ltt_qualitylab_upscale_video_") as work:
        dimensions, summary = inspect_upscale_video_pair(
            candidate, reference, low_input, Path(work), performance)
    report = build_report(
        evaluation_id=str(uuid.uuid4()), pack="upscale_video_diagnostic",
        source_kind="video", evaluator_version="h32-cli-v1",
        dimensions=dimensions, runtime={"summary": summary},
        source_artifact={
            "candidate_sha256": _sha256(candidate),
            "reference_sha256": _sha256(reference),
            "low_input_sha256": _sha256(low_input) if low_input else "",
        },
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("--low-input", type=Path)
    parser.add_argument("--performance-json", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    required = [args.candidate, args.reference]
    if args.low_input:
        required.append(args.low_input)
    if any(not path.is_file() for path in required):
        raise SystemExit("Candidate/reference/low-input artifact is missing.")
    performance = {}
    if args.performance_json:
        payload = json.loads(args.performance_json.read_text(encoding="utf-8"))
        result = payload.get("engine_result") or {}
        gpu = payload.get("gpu_memory_evidence") or {}
        performance = {
            "processing_seconds": result.get("processing_seconds"),
            "frames": result.get("frames"),
            "peak_vram_mb": gpu.get("peak_delta_memory_mb"),
        }
    report = evaluate(args.candidate, args.reference, args.low_input, performance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    print(json.dumps({"overall_verdict": report["overall_verdict"],
                      "release_gate_eligible": report["release_gate_eligible"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
