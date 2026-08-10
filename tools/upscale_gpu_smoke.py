"""Guarded end-to-end GPU smoke using an isolated storage root."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class SmokeContext:
    job_id = "gpu-smoke"

    def __init__(self, gpu_uuid: str = ""):
        self.gpu_uuid = gpu_uuid
        self.stages = []

    def gpu_env(self) -> dict:
        from platform_core import gpu
        return gpu.env_for(self.gpu_uuid) if self.gpu_uuid else dict(os.environ)

    def progress(self, percent: int, message: str = "") -> None:
        self.stages.append({"percent": int(percent), "message": message})

    def is_cancelled(self) -> bool:
        return False


def _command(args: list[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True, timeout=1800,
                            check=False)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "command failed")[-2000:])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_fingerprint() -> dict:
    """Hash the complete local engine bundle without exposing absolute paths."""
    engine_dir = ROOT / "apps" / "upscalevideo" / "vendor" / "engine"
    artifacts = []
    for path in sorted(item for item in engine_dir.rglob("*") if item.is_file()):
        artifacts.append({
            "path": path.relative_to(engine_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    return {"engine_bundle": "upscalevideo/vendor/engine",
            "artifacts": artifacts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gpu-index", type=int, required=True)
    parser.add_argument("--preset", choices=("fast", "quality"), default="fast")
    parser.add_argument("--target-height", type=int, choices=(1080, 1440, 2160),
                        default=1080)
    parser.add_argument("--max-seconds", type=float, default=0.0)
    parser.add_argument("--sample-interval-ms", type=int, default=200)
    parser.add_argument("--max-baseline-memory-mb", type=int, default=512)
    parser.add_argument("--max-baseline-util-percent", type=int, default=5)
    parser.add_argument("--allow-busy-gpu", action="store_true")
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit("Source video does not exist.")

    from apps.upscalevideo.ff import probe_video
    from apps.upscalevideo.jobs import handle
    from apps.upscalevideo.telemetry import gpu_snapshot
    from apps.qualitylab.services.gpu_evidence import GpuEvidenceSampler
    from platform_core import gpu
    from platform_core.storage import LocalStorage, set_storage

    selected = next((item for item in gpu.list_gpus()
                     if item.index == args.gpu_index), None)
    if selected is None:
        raise SystemExit(f"GPU index {args.gpu_index} is not available.")

    work = Path(tempfile.mkdtemp(prefix="ltt_upscale_gpu_smoke_"))
    storage = LocalStorage(str(work / "storage")); set_storage(storage)
    try:
        derivative = work / "input-480p.mp4"
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                   "-i", str(args.source)]
        if args.max_seconds > 0:
            command += ["-t", str(args.max_seconds)]
        command += ["-vf", "scale=-2:480", "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac", "-movflags", "+faststart", str(derivative)]
        _command(command)
        source_probe = probe_video(str(derivative))
        source_key = "upscalevideo/smoke/input.mp4"
        with derivative.open("rb") as stream:
            storage.put(source_key, stream, content_type="video/mp4")
        ctx = SmokeContext(selected.uuid)
        sampler = GpuEvidenceSampler(
            selected.uuid, interval_seconds=max(50, min(
                5000, args.sample_interval_ms)) / 1000.0)
        started = time.perf_counter()
        with sampler:
            baseline = sampler.baseline
            busy = (baseline.memory_used_mb > args.max_baseline_memory_mb or
                    baseline.utilization_percent > args.max_baseline_util_percent)
            if busy and not args.allow_busy_gpu:
                raise RuntimeError(
                    "Assigned GPU is not idle enough for qualified peak VRAM evidence.")
            result = handle({"video_key": source_key, "owner_id": "",
                             "preset": args.preset,
                             "target_height": args.target_height, "codec": "h264",
                             "preview": False,
                             "preserve_fps": True, "preserve_audio": True}, ctx)
        elapsed = time.perf_counter() - started
        gpu_evidence = sampler.summary()
        gpu_evidence["baseline_gate_passed"] = not busy
        if busy:
            gpu_evidence["qualified"] = False
        output_local = work / "output.mp4"
        with storage.open(result["video_key"]) as source, output_local.open("wb") as target:
            shutil.copyfileobj(source, target)
        output_probe = probe_video(str(output_local))
        passed = (output_probe["h"] == args.target_height and output_probe["w"] > 0 and
                  abs(output_probe["fps"] - source_probe["fps"]) < 0.05 and
                  bool(output_probe["has_audio"]) == bool(source_probe["has_audio"]) and
                  output_local.stat().st_size > 0)
        evidence = {"schema_version": 2, "passed": passed,
                    "source_artifact": {"sha256": _sha256(args.source),
                                        "bytes": args.source.stat().st_size},
                    "requested_gpu": {"index": selected.index,
                                      "uuid_sha256": hashlib.sha256(
                                          selected.uuid.encode("utf-8")).hexdigest(),
                                      "name": selected.name},
                    "preset": args.preset, "target_height": args.target_height,
                    "derived_input": {"width": source_probe["w"], "height": source_probe["h"],
                                      "fps": source_probe["fps"],
                                      "duration_s": source_probe["duration"],
                                      "has_audio": source_probe["has_audio"]},
                    "output": {"width": output_probe["w"], "height": output_probe["h"],
                               "fps": output_probe["fps"],
                               "duration_s": output_probe["duration"],
                               "has_audio": output_probe["has_audio"],
                               "size_bytes": output_local.stat().st_size},
                    "engine_result": {key: value for key, value in result.items()
                                      if key != "video_key"},
                    "elapsed_seconds": round(elapsed, 3), "gpu": gpu_snapshot(),
                    "gpu_memory_evidence": gpu_evidence,
                    "runtime_fingerprint": _runtime_fingerprint(),
                    "progress_stages": ctx.stages}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8", newline="\n")
        print(json.dumps({"passed": passed, "elapsed_seconds": round(elapsed, 3),
                          "output": evidence["output"]}, ensure_ascii=True))
        return 0 if passed else 1
    finally:
        set_storage(None)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
