"""
quality_gate.py — Quality gate runner for Upscale Video.

Ensures model outputs meet baseline standards before release.

Gate types:
- PSNR ≥ 30 dB (libvmaf)
- SSIM ≥ 0.90 (libvmaf)
- VMAF ≥ 50 (libvmaf)
- No excessive blur (pillow)
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, Tuple

from apps.upscalevideo.schemas import Preset

# Baseline thresholds
GATE_THRESHOLDS = {
    Preset.fast: {
        "psnr_db": 30.0,
        "ssim": 0.90,
        "vmaf": 50.0,
    },
    Preset.quality: {
        "psnr_db": 30.0,
        "ssim": 0.90,
        "vmaf": 55.0,
    },
}


def _ffprobe(args: list) -> Tuple[float, float, float]:
    """Run ffprobe with args and return PSNR, SSIM, VMAF."""
    try:
        result = subprocess.run(
            ["ffprobe"] + args,
            capture_output=True, text=True, timeout=60,
        )
        # Parse VMAF score from stderr
        stderr = result.stderr.lower()
        for line in stderr.splitlines():
            line = line.lower()
            if "vmaf" in line and ("psnr" in line or "ssim" in line):
                if "psnr:" in line:
                    psnr = float(line.split("psnr:")[1].split()[0].strip())
                if "ssim:" in line:
                    ssim = float(line.split("ssim:")[1].split()[0].strip())
                if "vmaf:" in line:
                    vmaf = float(line.split("vmaf:")[1].split()[0].strip())
                return psnr, ssim, vmaf
        return None, None, None
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        return None, None, None


def check_quality(output_key: str, preset: Preset, test_video: Optional[str] = None) -> dict:
    """Check output quality against thresholds.

    Args:
        output_key: R2 output key
        preset: Fast or Quality
        test_video: Optional reference video (uses output for self-check)

    Returns:
        {"passed": bool, "metrics": dict, "error": str | None}
    """
    result = {
        "passed": True,
        "metrics": {},
        "error": None,
        "preset": preset.value,
    }

    thresholds = GATE_THRESHOLDS[preset]

    # Use test_video if provided, otherwise use output itself
    video_key = test_video if test_video else output_key

    try:
        # Run ffprobe quality check
        psnr, ssim, vmaf = _ffprobe(["-v", "error", "-select_streams", "v:0",
                                      "-show_frame", "stats_psnr:ssim:vmaf",
                                      "-of", "csv=p=0", video_key])

        if psnr is None or ssim is None or vmaf is None:
            result["error"] = "ffprobe failed to parse quality metrics"
            result["passed"] = False
            return result

        result["metrics"] = {
            "psnr_db": psnr,
            "ssim": ssim,
            "vmaf": vmaf,
        }

        # Check thresholds
        if psnr < thresholds["psnr_db"]:
            result["metrics"]["psnr_failed"] = thresholds["psnr_db"]
            result["error"] = f"PSNR {psnr:.2f} < {thresholds['psnr_db']} dB"
            result["passed"] = False

        if ssim < thresholds["ssim"]:
            result["metrics"]["ssim_failed"] = thresholds["ssim"]
            result["error"] = f"SSIM {ssim:.4f} < {thresholds['ssim']}"
            result["passed"] = False

        if vmaf < thresholds["vmaf"]:
            result["metrics"]["vmaf_failed"] = thresholds["vmaf"]
            result["error"] = f"VMAF {vmaf:.2f} < {thresholds['vmaf']}"
            result["passed"] = False

    except Exception as e:
        result["error"] = str(e)
        result["passed"] = False

    return result


def check_blur(output_key: str) -> dict:
    """Check for excessive blur in output (pillow-based).

    Simple heuristic: check if image is too blurry by variance.
    """
    from PIL import Image
    from platform_core.storage import get_storage

    result = {"passed": True, "blur_score": 0, "error": None}

    try:
        storage = get_storage()
        with storage.open(output_key) as f:
            image_data = f.read()

        # Load image
        with Image.open(image_data) as img:
            # Convert to grayscale and check variance
            gray = img.convert("L")
            pixels = list(gray.getdata())
            
            mean = sum(pixels) / len(pixels)
            variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
            
            # Variance threshold: too blurry if variance < 100
            blur_score = min(variance, 100)
            result["blur_score"] = blur_score

            if blur_score < 100:
                result["passed"] = False
                result["error"] = f"Excessive blur detected (variance: {blur_score:.2f})"

    except Exception as e:
        result["error"] = str(e)
        result["passed"] = False

    return result


def run_quality_gates(output_key: str, preset: Preset, test_video: Optional[str] = None) -> dict:
    """Run all quality gates.

    Returns combined result from all gates.
    """
    from apps.upscalevideo.checkpoint import load_checkpoint, get_job_checkpoints
    
    result = {
        "gates": {},
        "all_passed": True,
        "error": None,
    }

    # Gate 1: Quality metrics
    quality_result = check_quality(output_key, preset, test_video)
    result["gates"]["quality"] = quality_result

    # Gate 2: Blur check
    blur_result = check_blur(output_key)
    result["gates"]["blur"] = blur_result

    # Overall result
    all_passed = quality_result["passed"] and blur_result["passed"]
    result["all_passed"] = all_passed

    if not all_passed:
        errors = [r.get("error") for r in [quality_result, blur_result] if r.get("error")]
        result["error"] = "; ".join(errors) if errors else "One or more gates failed"

    return result
