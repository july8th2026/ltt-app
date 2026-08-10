"""Paired-video diagnostics cho Upscale; CPU sampling, chưa calibrated."""
from __future__ import annotations

import hashlib
import json
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from apps.qualitylab.contracts import Dimension, Metric
from apps.qualitylab.services.upscale import paired_scores
from platform_core import media
from platform_core.i18n import N_

MAX_SAMPLES = 8
VMAF_MODEL = "vmaf_v0.6.1"


@lru_cache(maxsize=1)
def libvmaf_runtime_fingerprint() -> dict[str, str]:
    """Pin implementation/model embedded bằng hash binary, không lộ local path."""
    try:
        binary = Path(media.ffmpeg_bin())
        digest = hashlib.sha256()
        with binary.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        result = subprocess.run([str(binary), "-version"], capture_output=True,
                                text=True, timeout=10, check=False)
        version = (result.stdout or "").splitlines()[0][:160]
        return {"binary_sha256": digest.hexdigest(), "ffmpeg_version": version,
                "model": VMAF_MODEL}
    except (OSError, subprocess.SubprocessError):
        return {"binary_sha256": "", "ffmpeg_version": "unavailable",
                "model": VMAF_MODEL}


def _vmaf_metric(candidate_path: Path, reference_path: Path, work: Path) -> Metric:
    log_path = work / "vmaf.json"
    graph = (
        "[0:v]settb=AVTB,setpts=PTS-STARTPTS[dist];"
        "[1:v]settb=AVTB,setpts=PTS-STARTPTS[ref];"
        f"[dist][ref]libvmaf=model=version={VMAF_MODEL}:"
        "log_fmt=json:log_path=vmaf.json:n_threads=2")
    command = [media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error",
               "-i", str(candidate_path), "-i", str(reference_path),
               "-lavfi", graph, "-f", "null", "-"]
    try:
        result = subprocess.run(command, cwd=work, capture_output=True, text=True,
                                timeout=300, check=False)
        if result.returncode != 0 or not log_path.is_file():
            raise RuntimeError(N_("FFmpeg/libvmaf không sẵn sàng."))
        payload = json.loads(log_path.read_text(encoding="utf-8"))
        score = float(payload["pooled_metrics"]["vmaf"]["mean"])
        version = str(payload.get("version") or "")[:80]
        if not np.isfinite(score):
            raise ValueError(N_("VMAF trả điểm không hữu hạn."))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, KeyError,
            TypeError, ValueError, RuntimeError) as exc:
        return Metric("vmaf_v0_6_1", "VMAF v0.6.1", None, "score", "UNKNOWN",
                      direction="higher", threshold=N_("Evaluator chưa sẵn sàng"),
                      evidence={"reason": type(exc).__name__, "model": VMAF_MODEL})
    fingerprint = libvmaf_runtime_fingerprint()
    return Metric(
        "vmaf_v0_6_1", "VMAF v0.6.1", round(score, 6), "score", "UNKNOWN",
        direction="higher", valid_range="0..100",
        threshold=N_("Chưa calibrated; model gốc nhắm 1080p HDTV ở khoảng 3H"),
        evidence={"libvmaf_version": version, "model": VMAF_MODEL,
                  "ffmpeg_binary_sha256": fingerprint["binary_sha256"]})


def _sample_times(duration: float) -> list[float]:
    count = max(2, min(MAX_SAMPLES, int(max(duration, 1.0) * 2)))
    # Không lấy sát EOF: container duration thường dài hơn timestamp frame cuối,
    # nên seek 0.95s trong clip 4fps/1s có thể không trả frame nào.
    start = min(0.05, max(duration * 0.1, 0.001))
    end = max(start, duration * 0.75)
    return [float(value) for value in np.linspace(start, end, count)]


def _extract(path: Path, directory: Path, times: list[float]) -> list[np.ndarray]:
    directory.mkdir(parents=True, exist_ok=True)
    frames: list[np.ndarray] = []
    for index, timestamp in enumerate(times):
        target = directory / f"frame-{index:03d}.png"
        command = [media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
                   "-ss", f"{timestamp:.6f}", "-i", str(path), "-frames:v", "1",
                   str(target)]
        result = subprocess.run(command, capture_output=True, timeout=60, check=False)
        if result.returncode != 0 or not target.is_file():
            raise RuntimeError(N_("Không trích được frame video để đánh giá."))
        with Image.open(target) as image:
            frames.append(np.asarray(image.convert("RGB"), dtype=np.float32))
    return frames


def _mean(values: list[float]) -> float:
    return round(float(np.mean(values)), 6) if values else 0.0


def temporal_scores(reference: list[np.ndarray], candidate: list[np.ndarray]) -> dict[str, float]:
    """Residual theo thời gian; proxy chẩn đoán, không phải optical-flow metric."""
    if len(reference) != len(candidate) or len(reference) < 2:
        raise ValueError(N_("Cần ít nhất hai cặp frame đồng bộ."))
    delta_errors: list[float] = []
    luma_flicker: list[float] = []
    for index in range(1, len(reference)):
        ref_delta = reference[index].astype(np.float64) - reference[index - 1]
        out_delta = candidate[index].astype(np.float64) - candidate[index - 1]
        delta_errors.append(float(np.mean(np.abs(out_delta - ref_delta))))
        ref_luma = float(np.mean(reference[index])) - float(np.mean(reference[index - 1]))
        out_luma = float(np.mean(candidate[index])) - float(np.mean(candidate[index - 1]))
        luma_flicker.append(abs(out_luma - ref_luma))
    return {"temporal_delta_mae": _mean(delta_errors),
            "luma_flicker_residual": _mean(luma_flicker)}


def _performance(snapshot: dict[str, Any]) -> Dimension:
    seconds = float(snapshot.get("processing_seconds") or 0.0)
    frames = int(snapshot.get("frames") or 0)
    peak_vram = int(snapshot.get("peak_vram_mb") or 0)
    throughput = round(frames / seconds, 4) if frames > 0 and seconds > 0 else None
    metrics = (
        Metric("processing_seconds", N_("Thời gian xử lý Upscale"),
               round(seconds, 4) if seconds > 0 else None, "s", "UNKNOWN",
               direction="lower", threshold=N_("Chưa có baseline theo model/slice")),
        Metric("processed_frames", N_("Số frame đã xử lý"), frames or None,
               "frame", "UNKNOWN"),
        Metric("throughput_fps", N_("Thông lượng xử lý"), throughput,
               "frame/s", "UNKNOWN", direction="higher",
               threshold=N_("Chưa có baseline theo GPU/model/resolution")),
        Metric("peak_vram_mb", N_("Peak VRAM"), peak_vram or None, "MB", "UNKNOWN",
               threshold=(N_("Chưa có baseline theo model/slice") if peak_vram else
                          N_("Runtime Upscale chưa ghi peak VRAM theo job"))),
    )
    return Dimension("performance", N_("Hiệu năng job nguồn"), "UNKNOWN", metrics)


def inspect_upscale_video_pair(candidate_path: Path, reference_path: Path,
                                low_input_path: Path | None, work: Path,
                                performance: dict[str, Any] | None = None
                                ) -> tuple[list[Dimension], dict[str, Any]]:
    try:
        candidate_info = media.probe(str(candidate_path))
        reference_info = media.probe(str(reference_path))
    except Exception as exc:
        metric = Metric("video_probe", N_("Candidate/reference giải mã được"), False,
                        verdict="FAIL", evidence={"error_type": type(exc).__name__})
        return [Dimension("video_contract", N_("Contract video"), "FAIL", (metric,))], {}
    same_dimensions = (candidate_info["width"], candidate_info["height"]) == (
        reference_info["width"], reference_info["height"])
    duration_delta = abs(float(candidate_info["duration"]) - float(reference_info["duration"]))
    duration_ok = duration_delta <= max(0.1, float(reference_info["duration"]) * 0.02)
    fps_delta = abs(float(candidate_info["fps"]) - float(reference_info["fps"]))
    fps_ok = fps_delta <= 0.05
    audio_ok = bool(candidate_info.get("audio_codec")) == bool(reference_info.get("audio_codec"))
    contract_ok = same_dimensions and duration_ok and fps_ok and audio_ok
    contract = Dimension("video_contract", N_("Contract video"),
                         "PASS" if contract_ok else "FAIL", (
        Metric("video_decodable", N_("Candidate/reference giải mã được"), True,
               verdict="PASS"),
        Metric("same_dimensions", N_("Kích thước khớp HR"), same_dimensions,
               verdict="PASS" if same_dimensions else "FAIL",
               evidence={"candidate": [candidate_info["width"], candidate_info["height"]],
                         "reference": [reference_info["width"], reference_info["height"]]}),
        Metric("duration_delta", N_("Sai lệch thời lượng"), round(duration_delta, 4),
               "s", "PASS" if duration_ok else "FAIL", threshold="<= max(0.1s, 2%)"),
        Metric("fps_delta", N_("Sai lệch FPS"), round(fps_delta, 4), "fps",
               "PASS" if fps_ok else "FAIL", threshold="<= 0.05 fps"),
        Metric("audio_parity", N_("Trạng thái audio được giữ"), audio_ok,
               verdict="PASS" if audio_ok else "FAIL"),
    ))
    if not contract_ok:
        return [contract, _performance(performance or {})], {
            "candidate_probe": candidate_info, "reference_probe": reference_info}

    try:
        duration = min(float(candidate_info["duration"]), float(reference_info["duration"]))
        times = _sample_times(duration)
        candidate_frames = _extract(candidate_path, work / "candidate-frames", times)
        reference_frames = _extract(reference_path, work / "reference-frames", times)
        scores = [paired_scores(ref, out)
                  for ref, out in zip(reference_frames, candidate_frames)]
        temporal = temporal_scores(reference_frames, candidate_frames)
        baseline_scores: list[dict[str, float]] = []
        if low_input_path is not None:
            low_frames = _extract(low_input_path, work / "low-frames", times)
            target_size = (reference_info["width"], reference_info["height"])
            for ref, low in zip(reference_frames, low_frames):
                resized = np.asarray(Image.fromarray(low.astype(np.uint8), "RGB").resize(
                    target_size, Image.Resampling.BICUBIC), dtype=np.float32)
                baseline_scores.append(paired_scores(ref, resized))
    except Exception as exc:
        metric = Metric("frame_sampling", N_("Lấy mẫu frame đồng bộ"), False,
                        verdict="FAIL", evidence={"error_type": type(exc).__name__})
        return [contract, Dimension("sampling", N_("Lấy mẫu"), "FAIL", (metric,)),
                _performance(performance or {})], {}

    mean_psnr = _mean([item["psnr_db"] for item in scores])
    mean_ssim = _mean([item["ssim_local"] for item in scores])
    baseline_psnr = _mean([item["psnr_db"] for item in baseline_scores]) if baseline_scores else None
    baseline_ssim = _mean([item["ssim_local"] for item in baseline_scores]) if baseline_scores else None
    vmaf = _vmaf_metric(candidate_path, reference_path, work)
    full_reference = Dimension("full_reference", N_("Full-reference theo frame"),
                               "UNKNOWN", (
        Metric("sampled_frames", N_("Số frame đã lấy mẫu"), len(scores), "frame",
               "UNKNOWN"),
        Metric("mean_psnr_db", N_("PSNR trung bình"), mean_psnr, "dB", "UNKNOWN",
               direction="higher", threshold=N_("Chưa calibrated")),
        Metric("mean_ssim_local", N_("Local SSIM trung bình"), mean_ssim, "ratio",
               "UNKNOWN", direction="higher", threshold=N_("Chưa calibrated")),
        Metric("psnr_delta_vs_bicubic", N_("PSNR delta so với bicubic"),
               round(mean_psnr - baseline_psnr, 6) if baseline_psnr is not None else None,
               "dB", "UNKNOWN", direction="higher", threshold=N_("Chưa calibrated")),
        Metric("ssim_delta_vs_bicubic", N_("SSIM delta so với bicubic"),
               round(mean_ssim - baseline_ssim, 6) if baseline_ssim is not None else None,
               "ratio", "UNKNOWN", direction="higher", threshold=N_("Chưa calibrated")),
        vmaf,
    ))
    temporal_dimension = Dimension("temporal", N_("Nhất quán theo thời gian"),
                                   "UNKNOWN", (
        Metric("temporal_delta_mae", N_("Sai số biến thiên frame"),
               temporal["temporal_delta_mae"], "luma", "UNKNOWN",
               direction="lower", threshold=N_("Chưa calibrated")),
        Metric("luma_flicker_residual", N_("Flicker độ sáng dư"),
               temporal["luma_flicker_residual"], "luma", "UNKNOWN",
               direction="lower", threshold=N_("Chưa calibrated")),
    ))
    return [contract, full_reference, temporal_dimension,
            _performance(performance or {})], {
        "sample_times_seconds": [round(value, 4) for value in times],
        "candidate_mean": {"psnr_db": mean_psnr, "ssim_local": mean_ssim},
        "bicubic_mean": {"psnr_db": baseline_psnr, "ssim_local": baseline_ssim},
        "temporal": temporal, "vmaf": vmaf.value,
        "candidate_probe": candidate_info,
        "reference_probe": reference_info,
    }
