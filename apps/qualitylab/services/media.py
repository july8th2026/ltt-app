"""Evaluator media contract bằng Pillow/ffprobe, không dùng model học máy."""
from __future__ import annotations

import json
import math
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image

from apps.qualitylab.contracts import Dimension, Metric
from platform_core.i18n import N_

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


@lru_cache(maxsize=1)
def ffprobe_version() -> str:
    try:
        result = subprocess.run(["ffprobe", "-version"], capture_output=True,
                                text=True, timeout=10, check=False)
        first = (result.stdout or "").splitlines()
        return first[0][:240] if result.returncode == 0 and first else "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def kind_for_name(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in {".srt", ".vtt", ".ass"}:
        return "subtitle"
    return "unknown"


def _ratio(value: str) -> float:
    try:
        left, right = str(value or "0/1").split("/", 1)
        denominator = float(right)
        return float(left) / denominator if denominator else 0.0
    except (TypeError, ValueError):
        return 0.0


def _number(value: object) -> float:
    try:
        number = float(value or 0.0)
        return number if math.isfinite(number) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _close(actual: float, expected: float, *, relative: float = 0.02,
           absolute: float = 0.1) -> bool:
    return math.isclose(actual, expected, rel_tol=relative, abs_tol=absolute)


def inspect_image(path: Path, expectations: dict) -> tuple[str, list[Dimension], dict]:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            mode, fmt = image.mode, image.format or ""
    except Exception as exc:
        metric = Metric("decodable", N_("Ảnh giải mã được"), False, verdict="FAIL",
                        evidence={"error_type": type(exc).__name__})
        return "image", [Dimension("technical", N_("Kỹ thuật"), "FAIL", (metric,))], {}

    metrics = [
        Metric("decodable", N_("Ảnh giải mã được"), True, verdict="PASS"),
        Metric("width", N_("Chiều rộng"), width, "px", "PASS"),
        Metric("height", N_("Chiều cao"), height, "px", "PASS"),
        Metric("format", N_("Định dạng"), fmt, verdict="PASS"),
        Metric("mode", N_("Kênh màu"), mode, verdict="PASS"),
    ]
    verdict = "PASS"
    for key, actual in (("width", width), ("height", height)):
        expected = int(expectations.get(f"expected_{key}") or 0)
        if expected and actual != expected:
            metrics.append(Metric(
                f"{key}_expected", N_(f"{key} đúng yêu cầu"), actual, "px", "FAIL",
                threshold=f"= {expected}", evidence={"expected": expected}))
            verdict = "FAIL"
    return "image", [Dimension("technical", N_("Kỹ thuật"), verdict, tuple(metrics))], {
        "width": width, "height": height, "format": fmt, "mode": mode,
    }


def inspect_av(path: Path, expectations: dict) -> tuple[str, list[Dimension], dict]:
    command = [
        "ffprobe", "-v", "error", "-show_error", "-show_format", "-show_streams",
        "-of", "json", str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        metric = Metric("ffprobe", N_("FFprobe hoạt động"), False, verdict="FAIL",
                        evidence={"error_type": type(exc).__name__})
        return "unknown", [Dimension("technical", N_("Kỹ thuật"), "FAIL", (metric,))], {}
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    videos = [item for item in streams if item.get("codec_type") == "video"]
    audios = [item for item in streams if item.get("codec_type") == "audio"]
    fmt = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    duration = _number(fmt.get("duration"))
    decodable = result.returncode == 0 and bool(streams)
    kind = "video" if videos else ("audio" if audios else "unknown")
    first_video = videos[0] if videos else {}
    width = int(first_video.get("width") or 0)
    height = int(first_video.get("height") or 0)
    fps = _ratio(first_video.get("avg_frame_rate") or "0/1")
    metrics = [
        Metric("decodable", N_("Media giải mã được"), decodable,
               verdict="PASS" if decodable else "FAIL",
               evidence={} if decodable else {"return_code": result.returncode}),
        Metric("duration", N_("Thời lượng"), round(duration, 4), "s",
               "PASS" if duration > 0 else "FAIL"),
        Metric("video_streams", N_("Số luồng hình"), len(videos), verdict="PASS"),
        Metric("audio_streams", N_("Số luồng tiếng"), len(audios), verdict="PASS"),
    ]
    verdict = "PASS" if decodable and duration > 0 else "FAIL"
    if videos:
        metrics.extend((
            Metric("width", N_("Chiều rộng"), width, "px", "PASS"),
            Metric("height", N_("Chiều cao"), height, "px", "PASS"),
            Metric("fps", N_("Tốc độ khung hình"), round(fps, 4), "fps",
                   "PASS" if fps > 0 else "WARN"),
        ))
    expected_audio = expectations.get("expected_audio")
    if expected_audio is not None and bool(audios) != bool(expected_audio):
        metrics.append(Metric("audio_expected", N_("Luồng tiếng đúng yêu cầu"),
                              bool(audios), verdict="FAIL",
                              threshold=str(bool(expected_audio))))
        verdict = "FAIL"
    for key, actual, unit in (("width", width, "px"), ("height", height, "px"),
                              ("duration", duration, "s"), ("fps", fps, "fps")):
        raw = expectations.get(f"expected_{key}")
        if raw in (None, "", 0, 0.0) or (key in {"width", "height", "fps"} and not videos):
            continue
        expected = float(raw)
        ok = (actual == expected if key in {"width", "height"}
              else _close(float(actual), expected))
        metrics.append(Metric(f"{key}_expected", N_(f"{key} đúng yêu cầu"),
                              round(float(actual), 4), unit,
                              "PASS" if ok else "FAIL", threshold=f"≈ {expected}",
                              evidence={"expected": expected}))
        if not ok:
            verdict = "FAIL"
    return kind, [Dimension("technical", N_("Kỹ thuật"), verdict, tuple(metrics))], {
        "duration": round(duration, 4), "width": width, "height": height,
        "fps": round(fps, 4), "video_streams": len(videos),
        "audio_streams": len(audios), "ffprobe_version": ffprobe_version(),
    }


def inspect_media(path: Path, expectations: dict) -> tuple[str, list[Dimension], dict]:
    return (inspect_image(path, expectations) if path.suffix.lower() in IMAGE_EXTENSIONS
            else inspect_av(path, expectations))
