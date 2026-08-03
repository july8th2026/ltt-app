"""Reproducible local benchmark for the Upscale enhancement decision gate.

Builds deterministic bicubic/noise/blur inputs, runs every installed supported
model and compares reconstruction plus temporal error. Temporary frames are
always removed; the output JSON contains only aggregate metrics and hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

MODEL_CANDIDATES = (
    "realesr-general-x4v3",
    "realesr-general-wdn-x4v3",
    "realesrgan-x4plus",
)
DEGRADATIONS = ("bicubic", "noise", "blur")


def _run(command: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            timeout=1800, check=False)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "command failed")[-2000:])


def _psnr(reference: np.ndarray, output: np.ndarray) -> float:
    mse = float(np.mean((reference.astype(np.float32) - output.astype(np.float32)) ** 2))
    return 99.0 if mse == 0 else 20 * math.log10(255.0 / math.sqrt(mse))


def _ssim(reference: np.ndarray, output: np.ndarray) -> float:
    x = reference.astype(np.float64).mean(axis=2)
    y = output.astype(np.float64).mean(axis=2)
    ux, uy = x.mean(), y.mean()
    vx, vy = x.var(), y.var()
    covariance = ((x - ux) * (y - uy)).mean()
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    return float(((2 * ux * uy + c1) * (2 * covariance + c2)) /
                 ((ux * ux + uy * uy + c1) * (vx + vy + c2)))


def _degrade(reference: Image.Image, kind: str, seed: int) -> Image.Image:
    """Tạo đầu vào thấp deterministic để các lần benchmark so sánh được."""
    width, height = reference.size
    low = reference.resize((width // 4, height // 4), Image.Resampling.BICUBIC)
    if kind == "bicubic":
        return low
    if kind == "blur":
        return low.filter(ImageFilter.GaussianBlur(radius=1.25))
    if kind == "noise":
        pixels = np.asarray(low).astype(np.float32)
        noise = np.random.default_rng(seed).normal(0, 10, pixels.shape)
        return Image.fromarray(np.clip(pixels + noise, 0, 255).astype(np.uint8), "RGB")
    raise ValueError(f"Unknown degradation: {kind}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _installed_models(engine_dir: Path) -> list[str]:
    models = engine_dir / "models"
    return [name for name in MODEL_CANDIDATES
            if (models / f"{name}.param").is_file()
            and (models / f"{name}.bin").is_file()]


def _feature_gates(installed: list[str]) -> dict:
    """Gate sản phẩm từ capability thật, không suy tên model thành feature."""
    return {
        "ai_detail": {
            "status": "DEFER",
            "reason": "No distinct temporal restoration model is installed.",
        },
        "denoise": {
            "status": "DEFER",
            "reason": (
                "The installed NCNN binary has no adjustable -dn/DNI control; "
                "the WDN endpoint alone is not a complete denoise-strength feature."
                if "realesr-general-wdn-x4v3" in installed else
                "No distinct controllable denoise engine is installed."
            ),
        },
        "deblur": {
            "status": "DEFER",
            "reason": "No installed model declares a dedicated deblur capability.",
        },
    }


def _score(reference_arrays: list[np.ndarray], output_paths: list[Path]) -> dict:
    if len(reference_arrays) != len(output_paths):
        raise RuntimeError("Engine output frame count does not match benchmark input.")
    outputs, psnr_values, ssim_values = [], [], []
    for reference, path in zip(reference_arrays, output_paths):
        with Image.open(path) as image:
            output = np.asarray(image.convert("RGB").resize(
                (reference.shape[1], reference.shape[0]), Image.Resampling.BICUBIC))
        outputs.append(output)
        psnr_values.append(_psnr(reference, output))
        ssim_values.append(_ssim(reference, output))
    temporal = [float(np.mean(np.abs(
        (outputs[i].astype(np.float32) - outputs[i - 1].astype(np.float32)) -
        (reference_arrays[i].astype(np.float32) -
         reference_arrays[i - 1].astype(np.float32)))))
                for i in range(1, len(outputs))]
    return {
        "frames": len(outputs),
        "psnr_db": round(float(np.mean(psnr_values)), 4),
        "ssim_global": round(float(np.mean(ssim_values)), 6),
        "temporal_error": round(float(np.mean(temporal)), 4),
    }


def _gpu_info() -> dict:
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version",
                                 "--format=csv,noheader"], capture_output=True,
                                text=True, timeout=5, check=False)
        if not result.stdout.strip():
            return {"name": "unavailable", "driver": "unavailable"}
        name, driver = [part.strip() for part in result.stdout.splitlines()[0].rsplit(",", 1)]
        return {"name": name, "driver": driver}
    except OSError:
        return {"name": "unavailable", "driver": "unavailable"}


def benchmark(source: Path, engine_dir: Path, sample_count: int = 12) -> dict:
    work = Path(tempfile.mkdtemp(prefix="ltt_ai_detail_bench_"))
    try:
        originals = work / "original"
        originals.mkdir()
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
              "-vf", "fps=2", "-frames:v", str(sample_count),
              str(originals / "f%04d.png")])
        original_paths = sorted(originals.glob("*.png"))
        if len(original_paths) < 2:
            raise RuntimeError("Video cần ít nhất hai frame benchmark.")
        reference_arrays: list[np.ndarray] = []
        references: list[Image.Image] = []
        for path in original_paths:
            with Image.open(path) as image:
                image = image.convert("RGB")
                width, height = image.width // 4 * 4, image.height // 4 * 4
                reference = image.crop((0, 0, width, height))
                reference_arrays.append(np.asarray(reference))
                references.append(reference.copy())
        installed = _installed_models(engine_dir)
        if not installed:
            raise RuntimeError("No supported benchmark model is installed.")
        results: dict[str, dict] = {model: {} for model in installed}
        executable = engine_dir / "realesrgan-ncnn-vulkan.exe"
        for case_index, degradation in enumerate(DEGRADATIONS):
            low = work / f"low-{degradation}"
            low.mkdir()
            for frame_index, (reference, path) in enumerate(zip(references, original_paths)):
                _degrade(reference, degradation,
                         seed=20260803 + case_index * 1000 + frame_index).save(low / path.name)
            for model in installed:
                output_dir = work / f"{model}-{degradation}"
                output_dir.mkdir()
                started = time.perf_counter()
                _run([str(executable), "-i", str(low), "-o", str(output_dir),
                      "-n", model, "-s", "4", "-m", "models", "-f", "png",
                      "-t", "256", "-j", "1:2:2"], cwd=engine_dir)
                runtime = time.perf_counter() - started
                score = _score(reference_arrays, sorted(output_dir.glob("*.png")))
                score.update({"runtime_seconds": round(runtime, 3),
                              "fps": round(score["frames"] / runtime, 3)})
                results[model][degradation] = score
        artifacts = {path.name: _sha256(path) for model in installed
                     for path in (engine_dir / "models").glob(f"{model}.*")}
        return {
            "schema_version": 2,
            "source_name": source.name,
            "sample_frames": len(reference_arrays),
            "degradations": list(DEGRADATIONS),
            "gpu": _gpu_info(),
            "engine_sha256": _sha256(executable),
            "model_sha256": artifacts,
            "models": results,
            "feature_gates": _feature_gates(installed),
            "decision": "DEFER: installed engine does not satisfy any new feature gate.",
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


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
