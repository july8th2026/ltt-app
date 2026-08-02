"""Reproducible local benchmark for the Upscale AI Detail decision gate.

Creates degraded low-resolution frames from the source, runs installed models,
then compares reconstruction and temporal error against the held-out originals.
No source frame or generated image is retained; only aggregate JSON is written.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

MODELS = ("realesr-general-x4v3", "realesrgan-x4plus")


def _run(command: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            timeout=1800, check=False)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "command failed")[-2000:])


def _psnr(reference: np.ndarray, output: np.ndarray) -> float:
    mse = float(np.mean((reference.astype(np.float32) - output.astype(np.float32)) ** 2))
    return 99.0 if mse == 0 else 20 * math.log10(255.0 / math.sqrt(mse))


def _ssim(reference: np.ndarray, output: np.ndarray) -> float:
    x = reference.astype(np.float64).mean(axis=2); y = output.astype(np.float64).mean(axis=2)
    ux, uy = x.mean(), y.mean(); vx, vy = x.var(), y.var()
    covariance = ((x - ux) * (y - uy)).mean()
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    return float(((2 * ux * uy + c1) * (2 * covariance + c2)) /
                 ((ux * ux + uy * uy + c1) * (vx + vy + c2)))


def benchmark(source: Path, engine_dir: Path, sample_count: int = 12) -> dict:
    work = Path(tempfile.mkdtemp(prefix="ltt_ai_detail_bench_"))
    try:
        originals = work / "original"; low = work / "low"
        originals.mkdir(); low.mkdir()
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
              "-vf", f"fps=2", "-frames:v", str(sample_count),
              str(originals / "f%04d.png")])
        original_paths = sorted(originals.glob("*.png"))
        if len(original_paths) < 2:
            raise RuntimeError("Video cần ít nhất hai frame benchmark.")
        reference_arrays = []
        for path in original_paths:
            with Image.open(path) as image:
                image = image.convert("RGB")
                width, height = image.width // 4 * 4, image.height // 4 * 4
                reference = image.crop((0, 0, width, height))
                reference_arrays.append(np.asarray(reference))
                reference.resize((width // 4, height // 4), Image.Resampling.BICUBIC).save(
                    low / path.name)
        results = {}
        executable = engine_dir / "realesrgan-ncnn-vulkan.exe"
        for model in MODELS:
            output_dir = work / model; output_dir.mkdir()
            started = time.perf_counter()
            _run([str(executable), "-i", str(low), "-o", str(output_dir),
                  "-n", model, "-s", "4", "-m", "models", "-f", "png",
                  "-t", "256", "-j", "1:2:2"], cwd=engine_dir)
            runtime = time.perf_counter() - started
            outputs = []
            psnr_values, ssim_values = [], []
            for reference, path in zip(reference_arrays, sorted(output_dir.glob("*.png"))):
                with Image.open(path) as image:
                    output = np.asarray(image.convert("RGB").resize(
                        (reference.shape[1], reference.shape[0]), Image.Resampling.BICUBIC))
                outputs.append(output); psnr_values.append(_psnr(reference, output))
                ssim_values.append(_ssim(reference, output))
            temporal = [float(np.mean(np.abs(
                (outputs[i].astype(np.float32) - outputs[i - 1].astype(np.float32)) -
                (reference_arrays[i].astype(np.float32) - reference_arrays[i - 1].astype(np.float32)))))
                        for i in range(1, len(outputs))]
            results[model] = {"frames": len(outputs), "runtime_seconds": round(runtime, 3),
                              "fps": round(len(outputs) / runtime, 3),
                              "psnr_db": round(float(np.mean(psnr_values)), 4),
                              "ssim_global": round(float(np.mean(ssim_values)), 6),
                              "temporal_error": round(float(np.mean(temporal)), 4)}
        return {"source_name": source.name, "sample_frames": len(reference_arrays),
                "gpu": _gpu_name(), "models": results,
                "ai_detail_enabled": False,
                "decision": "DEFER: no distinct AI Detail temporal model is installed."}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _gpu_name() -> str:
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name",
                                 "--format=csv,noheader"], capture_output=True,
                                text=True, timeout=5, check=False)
        return result.stdout.splitlines()[0].strip() if result.stdout.strip() else "unavailable"
    except OSError:
        return "unavailable"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=12)
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit("Source video does not exist.")
    root = Path(__file__).resolve().parents[1]
    data = benchmark(args.source, root / "apps" / "upscalevideo" / "vendor" / "engine",
                     max(2, min(30, args.samples)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(data, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
