"""Paired-image diagnostics cho Upscale; chưa calibrated, không release gate."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image

from apps.qualitylab.contracts import Dimension, Metric
from platform_core.i18n import N_


def _rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32)


def _luma(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]


def _box_mean(array: np.ndarray, radius: int = 3) -> np.ndarray:
    size = radius * 2 + 1
    padded = np.pad(array.astype(np.float64), ((radius, radius), (radius, radius)),
                    mode="reflect")
    integral = np.pad(padded, ((1, 0), (1, 0)), mode="constant").cumsum(0).cumsum(1)
    total = (integral[size:, size:] - integral[:-size, size:]
             - integral[size:, :-size] + integral[:-size, :-size])
    return total / float(size * size)


def _psnr(reference: np.ndarray, candidate: np.ndarray) -> float:
    mse = float(np.mean((reference.astype(np.float64) - candidate) ** 2))
    return 99.0 if mse == 0 else 20.0 * math.log10(255.0 / math.sqrt(mse))


def _local_ssim(reference: np.ndarray, candidate: np.ndarray) -> float:
    left, right = _luma(reference).astype(np.float64), _luma(candidate).astype(np.float64)
    mean_left, mean_right = _box_mean(left), _box_mean(right)
    var_left = np.maximum(0.0, _box_mean(left * left) - mean_left * mean_left)
    var_right = np.maximum(0.0, _box_mean(right * right) - mean_right * mean_right)
    covariance = _box_mean(left * right) - mean_left * mean_right
    c1, c2 = (0.01 * 255.0) ** 2, (0.03 * 255.0) ** 2
    numerator = (2 * mean_left * mean_right + c1) * (2 * covariance + c2)
    denominator = (mean_left * mean_left + mean_right * mean_right + c1) * (
        var_left + var_right + c2)
    return float(np.mean(numerator / np.maximum(denominator, 1e-12)))


def _gradient_energy(array: np.ndarray) -> float:
    gray = _luma(array)
    horizontal = np.mean(np.abs(np.diff(gray, axis=1))) if gray.shape[1] > 1 else 0.0
    vertical = np.mean(np.abs(np.diff(gray, axis=0))) if gray.shape[0] > 1 else 0.0
    return float(horizontal + vertical)


def _blockiness(array: np.ndarray, block: int = 8) -> float:
    gray = _luma(array)
    parts: list[float] = []
    for axis in (0, 1):
        delta = np.abs(np.diff(gray, axis=axis))
        length = delta.shape[axis]
        if length < block * 2:
            continue
        indices = np.arange(length)
        boundary = indices % block == block - 1
        interior = ~boundary
        moved = np.moveaxis(delta, axis, 0)
        if boundary.any() and interior.any():
            parts.append(float(moved[boundary].mean() - moved[interior].mean()))
    return float(np.mean(parts)) if parts else 0.0


def _paired_scores(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    return {
        "psnr_db": round(_psnr(reference, candidate), 4),
        "ssim_local": round(_local_ssim(reference, candidate), 6),
        "gradient_energy": round(_gradient_energy(candidate), 4),
        "blockiness": round(_blockiness(candidate), 4),
    }


def inspect_upscale_pair(candidate_path: Path, reference_path: Path,
                         low_input_path: Path | None = None
                         ) -> tuple[list[Dimension], dict]:
    try:
        candidate, reference = _rgb(candidate_path), _rgb(reference_path)
    except Exception as exc:
        metric = Metric("paired_decodable", N_("Candidate/reference giải mã được"),
                        False, verdict="FAIL",
                        evidence={"error_type": type(exc).__name__})
        return [Dimension("paired_contract", N_("Đối chiếu cặp"), "FAIL", (metric,))], {}
    same_shape = candidate.shape == reference.shape
    contract = Dimension("paired_contract", N_("Đối chiếu cặp"),
                         "PASS" if same_shape else "FAIL", (
        Metric("paired_decodable", N_("Candidate/reference giải mã được"), True,
               verdict="PASS"),
        Metric("same_dimensions", N_("Kích thước candidate khớp HR"), same_shape,
               verdict="PASS" if same_shape else "FAIL",
               threshold=f"= {reference.shape[1]}x{reference.shape[0]}",
               evidence={"candidate": list(candidate.shape[:2][::-1]),
                         "reference": list(reference.shape[:2][::-1])}),
    ))
    if not same_shape:
        return [contract], {"candidate_shape": list(candidate.shape),
                            "reference_shape": list(reference.shape)}

    candidate_scores = _paired_scores(reference, candidate)
    full_reference = Dimension("full_reference", N_("Full-reference"), "UNKNOWN", (
        Metric("psnr_db", "PSNR", candidate_scores["psnr_db"], "dB", "UNKNOWN",
               direction="higher", valid_range="0..99",
               threshold=N_("Chưa calibrated — chỉ chẩn đoán")),
        Metric("ssim_local", "Local SSIM", candidate_scores["ssim_local"], "ratio",
               "UNKNOWN", direction="higher", valid_range="-1..1",
               threshold=N_("Chưa calibrated — chỉ chẩn đoán")),
    ))
    baseline_scores: dict[str, float] = {}
    baseline_metrics: tuple[Metric, ...]
    baseline_verdict = "UNKNOWN"
    if low_input_path is not None:
        low = _rgb(low_input_path)
        baseline_image = Image.fromarray(low.astype(np.uint8), mode="RGB").resize(
            (reference.shape[1], reference.shape[0]), Image.Resampling.BICUBIC)
        baseline = np.asarray(baseline_image, dtype=np.float32)
        baseline_scores = _paired_scores(reference, baseline)
        psnr_delta = candidate_scores["psnr_db"] - baseline_scores["psnr_db"]
        ssim_delta = candidate_scores["ssim_local"] - baseline_scores["ssim_local"]
        baseline_verdict = "WARN" if psnr_delta < 0 and ssim_delta < 0 else "UNKNOWN"
        baseline_metrics = (
            Metric("bicubic_psnr_db", N_("Bicubic PSNR"), baseline_scores["psnr_db"],
                   "dB", "UNKNOWN", direction="higher", valid_range="0..99"),
            Metric("bicubic_ssim_local", N_("Bicubic local SSIM"),
                   baseline_scores["ssim_local"], "ratio", "UNKNOWN",
                   direction="higher", valid_range="-1..1"),
            Metric("psnr_delta_vs_bicubic", N_("PSNR delta so với bicubic"),
                   round(psnr_delta, 4), "dB", baseline_verdict,
                   direction="higher", threshold=N_("Chưa calibrated")),
            Metric("ssim_delta_vs_bicubic", N_("SSIM delta so với bicubic"),
                   round(ssim_delta, 6), "ratio", baseline_verdict,
                   direction="higher", threshold=N_("Chưa calibrated")),
        )
    else:
        baseline_metrics = (Metric(
            "bicubic_baseline", N_("Bicubic baseline"), None, verdict="UNKNOWN",
            threshold=N_("Cần ảnh LR đầu vào")),)
    baseline_dimension = Dimension("baseline", N_("So với bicubic"),
                                   baseline_verdict, baseline_metrics)
    reference_gradient = _gradient_energy(reference)
    artifact_dimension = Dimension("artifacts", N_("Artifact proxy"), "UNKNOWN", (
        Metric("gradient_ratio", N_("Tỉ lệ năng lượng cạnh"),
               round(candidate_scores["gradient_energy"] /
                     max(reference_gradient, 1e-9), 6), "ratio", "UNKNOWN",
               direction="target", valid_range="0..inf",
               threshold=N_("Target gần 1; chưa calibrated")),
        Metric("blockiness", N_("Block boundary excess"),
               candidate_scores["blockiness"], "luma", "UNKNOWN",
               direction="lower", threshold=N_("Chưa calibrated")),
    ))
    return [contract, full_reference, baseline_dimension, artifact_dimension], {
        "candidate": candidate_scores,
        "bicubic": baseline_scores,
        "reference_gradient_energy": round(reference_gradient, 4),
    }
