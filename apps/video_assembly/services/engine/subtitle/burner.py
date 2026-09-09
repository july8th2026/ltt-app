"""
FFmpeg subtitle burner — burn ASS subtitles into video.

Responsibilities:
  - Probe video metadata (duration, resolution, codec)
  - Burn ASS subtitles into video (hardcoded/burn-in)
  - Stream progress via callback
  - Handle path escaping for Windows
  - Detect GPU hardware encoders (NVENC/QSV/AMF)

Synchronous version extracted from BOT GEMINI auto_sub_video/adapters/ffmpeg_adapter.py.
All async functions converted to synchronous subprocess calls for DUNGVIDEO pipeline.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ── Availability check ───────────────────────────────────────────────────────

def check_ffmpeg() -> bool:
    """Check if FFmpeg is available on PATH."""
    return shutil.which("ffmpeg") is not None


def check_ffprobe() -> bool:
    """Check if ffprobe is available on PATH."""
    return shutil.which("ffprobe") is not None


# ── GPU encoder detection ───────────────────────────────────────────────────

_gpu_encoder_cache: Optional[str] = None  # None = not checked, "" = no GPU


def detect_gpu_encoder() -> str:
    """
    Detect the best available hardware encoder.
    Returns encoder name (e.g., "h264_nvenc", "h264_qsv") or "" if none.
    Results are cached for the process lifetime.
    """
    global _gpu_encoder_cache
    if _gpu_encoder_cache is not None:
        return _gpu_encoder_cache

    if not check_ffmpeg():
        _gpu_encoder_cache = ""
        return ""

    # Priority: NVENC (NVIDIA) > QSV (Intel) > AMF (AMD)
    candidates = ["h264_nvenc", "h264_qsv", "h264_amf"]

    for encoder in candidates:
        if _test_encoder(encoder):
            logger.info("[burner] GPU encoder detected: %s", encoder)
            _gpu_encoder_cache = encoder
            return encoder

    logger.info("[burner] No GPU encoder available, using libx264")
    _gpu_encoder_cache = ""
    return ""


def _test_encoder(encoder: str) -> bool:
    """Test if a hardware encoder works by running a tiny encode.
    NVENC requires minimum ~145x145, so we use 256x256 to be safe."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "color=c=black:s=256x256:d=0.1:r=25",
                "-c:v", encoder, "-frames:v", "1", "-f", "null", "NUL",
            ],
            capture_output=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_encoder_info() -> dict:
    """Return info about the active encoder for status/health checks."""
    gpu = detect_gpu_encoder()
    return {
        "gpu_encoder": gpu or None,
        "gpu_available": bool(gpu),
        "encoder_label": {
            "h264_nvenc": "NVIDIA NVENC",
            "h264_qsv": "Intel Quick Sync",
            "h264_amf": "AMD AMF",
        }.get(gpu, "CPU (libx264)"),
    }


# ── Video probe ──────────────────────────────────────────────────────────────

def probe_video(video_path: str) -> dict:
    """
    Get video metadata using ffprobe (synchronous).
    Returns: {duration, width, height, codec, fps, audio_codec, file_size_mb}
    """
    if not check_ffprobe():
        raise RuntimeError("ffprobe not found on PATH")

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=30)

    if result.returncode != 0:
        err_msg = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"ffprobe failed (code {result.returncode}): {err_msg}")

    try:
        data = json.loads(result.stdout.decode(errors="replace"))
    except json.JSONDecodeError:
        raise RuntimeError("ffprobe returned non-JSON output")

    # Extract info
    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0))
    file_size = int(fmt.get("size", 0))

    width, height, fps, video_codec, audio_codec = 0, 0, 0.0, "", ""
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and not video_codec:
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))
            video_codec = stream.get("codec_name", "")
            # Parse fps from r_frame_rate "30000/1001" or "30/1"
            rfr = stream.get("r_frame_rate", "0/1")
            if "/" in rfr:
                num, den = rfr.split("/")
                fps = float(num) / float(den) if float(den) else 0
            else:
                fps = float(rfr)
        elif stream.get("codec_type") == "audio" and not audio_codec:
            audio_codec = stream.get("codec_name", "")

    # Calculate bitrate (kbps) from file size and duration
    bitrate_kbps = int((file_size * 8) / max(duration, 0.1) / 1000) if duration > 0 else 0

    return {
        "duration": round(duration, 3),
        "width": width,
        "height": height,
        "codec": video_codec,
        "fps": round(fps, 2),
        "audio_codec": audio_codec,
        "file_size_mb": round(file_size / (1024 * 1024), 1),
        "bitrate_kbps": bitrate_kbps,
    }


# ── Subtitle burn-in ────────────────────────────────────────────────────────

_PROGRESS_RE = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")


_QUALITY_PRESETS = {
    "draft":    {"preset": "ultrafast", "crf": "28"},
    "standard": {"preset": "medium",    "crf": "23"},
    "high":     {"preset": "slow",      "crf": "18"},
}

# NVENC quality presets — uses -preset and -cq (constant quality) instead of -crf
_NVENC_QUALITY = {
    "draft":    {"preset": "p1", "cq": "32"},     # fastest
    "standard": {"preset": "p4", "cq": "23"},     # balanced
    "high":     {"preset": "p7", "cq": "18"},     # best quality
}

# QSV quality presets
_QSV_QUALITY = {
    "draft":    {"preset": "veryfast", "global_quality": "30"},
    "standard": {"preset": "medium",   "global_quality": "23"},
    "high":     {"preset": "veryslow", "global_quality": "18"},
}

# VP9 (WebM) uses different CRF scale — lower = better quality
_WEBM_QUALITY_CRF = {
    "draft":    "40",
    "standard": "30",
    "high":     "20",
}


def burn_subtitles(
    *,
    video_path: str,
    ass_path: str,
    output_path: str,
    output_format: str = "mp4",
    quality: str = "standard",
    bitrate_mode: str = "auto",
    source_bitrate_kbps: int = 0,
    total_duration: float = 0.0,
    on_progress: Optional[Callable[[float], None]] = None,
    timeout: int = 600,
) -> str:
    """
    Burn ASS subtitles into video using FFmpeg + libass (synchronous).

    Args:
        video_path:          Input video file
        ass_path:            ASS subtitle file to burn
        output_path:         Output video file path
        output_format:       mp4 / mkv / webm
        quality:             draft / standard / high (CRF preset tier)
        bitrate_mode:        "auto" (CRF), "match" (source bitrate), or explicit e.g. "15M"
        source_bitrate_kbps: Source video bitrate in kbps (used for "match" mode)
        total_duration:      Video duration (seconds) for progress calculation
        on_progress:         Callback(percent: 0-100) called during encoding
        timeout:             Max seconds before killing FFmpeg

    Returns: output file path
    Raises: RuntimeError on FFmpeg failure, TimeoutError
    """
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg not found on PATH")

    for path, label in [(video_path, "Video"), (ass_path, "ASS subtitle")]:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{label} file does not exist: {path}")

    # Pre-check: verify video file is not corrupt (non-zero, readable)
    video_size = os.path.getsize(video_path)
    if video_size == 0:
        raise ValueError(f"Video file is empty (0 bytes): {video_path}")

    # Pre-check: disk space (need at least video_size * 1.5 free)
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        disk_usage = shutil.disk_usage(str(output_dir.resolve()))
        min_free = max(video_size * 1.5, 100 * 1024 * 1024)  # at least 100MB
        if disk_usage.free < min_free:
            free_mb = disk_usage.free / (1024 * 1024)
            need_mb = min_free / (1024 * 1024)
            raise RuntimeError(
                f"Not enough disk space: {free_mb:.0f}MB free, need at least {need_mb:.0f}MB"
            )
    except OSError:
        pass  # Can't check disk — proceed anyway

    # Build FFmpeg command
    # Escape ASS path for FFmpeg filter graph syntax:
    # Windows absolute paths contain ":" (e.g. D:\path) which FFmpeg interprets
    # as filter option separator. Use f='escaped_path' syntax to avoid this.
    # Steps: backslash→forward slash, then escape : and ' for filter graph.
    _ass_esc = ass_path.replace("\\", "/")
    _ass_esc = _ass_esc.replace("'", "'\\''").replace(":", "\\:")
    ass_filter_expr = f"ass=f='{_ass_esc}'"

    # ── Resolve bitrate mode ──
    use_target_bitrate = False
    target_bv = ""
    max_bv = ""
    bufsize = ""

    if bitrate_mode == "match" and source_bitrate_kbps > 0:
        target_kbps = int(source_bitrate_kbps * 1.1)
        target_bv = f"{target_kbps}k"
        max_bv = f"{int(target_kbps * 1.3)}k"
        bufsize = f"{int(target_kbps * 2)}k"
        use_target_bitrate = True
        logger.info("[burner] bitrate=match -> target %sk (source %sk)", target_kbps, source_bitrate_kbps)
    elif bitrate_mode not in ("auto", "match"):
        target_bv = bitrate_mode
        if bitrate_mode.upper().endswith("M"):
            val = float(bitrate_mode[:-1])
            max_bv = f"{val * 1.3:.1f}M"
            bufsize = f"{val * 2:.0f}M"
        elif bitrate_mode.upper().endswith("K"):
            val = int(bitrate_mode[:-1])
            max_bv = f"{int(val * 1.3)}k"
            bufsize = f"{int(val * 2)}k"
        use_target_bitrate = True
        logger.info("[burner] bitrate=explicit -> target %s", target_bv)

    # Select encoder: GPU (if available and format is mp4/mkv) or CPU
    gpu_encoder = ""
    if output_format != "webm":
        gpu_encoder = detect_gpu_encoder()

    q = _QUALITY_PRESETS.get(quality, _QUALITY_PRESETS["standard"])

    if gpu_encoder == "h264_nvenc":
        nv = _NVENC_QUALITY.get(quality, _NVENC_QUALITY["standard"])
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", ass_filter_expr,
            "-c:v", "h264_nvenc",
            "-preset", nv["preset"],
        ]
        if use_target_bitrate:
            cmd += ["-b:v", target_bv, "-maxrate", max_bv, "-bufsize", bufsize]
        else:
            cmd += ["-cq", nv["cq"], "-b:v", "0"]
        cmd += [
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            "-nostats",
            output_path,
        ]
    elif gpu_encoder == "h264_qsv":
        qsv = _QSV_QUALITY.get(quality, _QSV_QUALITY["standard"])
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", ass_filter_expr,
            "-c:v", "h264_qsv",
            "-preset", qsv["preset"],
        ]
        if use_target_bitrate:
            cmd += ["-b:v", target_bv, "-maxrate", max_bv, "-bufsize", bufsize]
        else:
            cmd += ["-global_quality", qsv["global_quality"]]
        cmd += [
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            "-nostats",
            output_path,
        ]
    elif gpu_encoder == "h264_amf":
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", ass_filter_expr,
            "-c:v", "h264_amf",
        ]
        if use_target_bitrate:
            cmd += ["-rc", "cbr", "-b:v", target_bv, "-maxrate", max_bv, "-bufsize", bufsize]
        else:
            cmd += [
                "-quality", "balanced" if quality == "standard" else ("speed" if quality == "draft" else "quality"),
                "-rc", "cqp",
                "-qp_i", q["crf"], "-qp_p", q["crf"],
            ]
        cmd += [
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            "-nostats",
            output_path,
        ]
    else:
        # CPU fallback (libx264)
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", ass_filter_expr,
            "-c:v", "libx264",
            "-preset", q["preset"],
        ]
        if use_target_bitrate:
            cmd += ["-b:v", target_bv, "-maxrate", max_bv, "-bufsize", bufsize]
        else:
            cmd += ["-crf", q["crf"]]
        cmd += [
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            "-nostats",
            output_path,
        ]

    # Adjust codec for different formats
    if output_format == "webm":
        webm_crf = _WEBM_QUALITY_CRF.get(quality, _WEBM_QUALITY_CRF["standard"])
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", ass_filter_expr,
            "-c:v", "libvpx-vp9",
        ]
        if use_target_bitrate:
            cmd += ["-b:v", target_bv, "-maxrate", max_bv]
        else:
            cmd += ["-crf", webm_crf, "-b:v", "0"]
        cmd += [
            "-c:a", "libopus",
            "-progress", "pipe:1",
            "-nostats",
            output_path,
        ]
    elif output_format == "mkv":
        if "-movflags" in cmd:
            idx = cmd.index("-movflags")
            cmd.pop(idx)
            cmd.pop(idx)

    encoder_label = gpu_encoder or "libx264" if output_format != "webm" else "libvpx-vp9"
    logger.info("[burner] burn [%s] cmd: %s", encoder_label, " ".join(cmd))

    # Run FFmpeg synchronously with progress monitoring
    # Use a thread to drain stderr so we avoid deadlock when stderr buffer fills up
    import threading

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stderr_chunks: list[bytes] = []

    def _drain_stderr():
        assert proc.stderr is not None
        while True:
            chunk = proc.stderr.read(4096)
            if not chunk:
                break
            stderr_chunks.append(chunk)

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    try:
        # Read stdout for progress
        while True:
            if proc.stdout is None:
                break

            line = proc.stdout.readline()
            if not line:
                break

            decoded = line.decode(errors="replace").strip()

            # Parse progress from FFmpeg -progress pipe output
            if on_progress and total_duration > 0:
                if decoded.startswith("out_time_ms=") or decoded.startswith("out_time_us="):
                    try:
                        time_us = int(decoded.split("=", 1)[1])
                        current_s = time_us / 1_000_000
                        pct = min(99.0, (current_s / total_duration) * 100)
                        if pct > 0:
                            on_progress(round(pct, 1))
                    except (ValueError, ZeroDivisionError):
                        pass
                elif decoded.startswith("out_time="):
                    try:
                        ts = decoded.split("=", 1)[1].strip()
                        parts = ts.split(":")
                        if len(parts) == 3:
                            h, m = int(parts[0]), int(parts[1])
                            s = float(parts[2])
                            current_s = h * 3600 + m * 60 + s
                            pct = min(99.0, (current_s / total_duration) * 100)
                            if pct > 0:
                                on_progress(round(pct, 1))
                    except (ValueError, IndexError):
                        pass

            if decoded == "progress=end":
                if on_progress:
                    on_progress(100.0)
                break

        # Wait for process and stderr thread to finish
        proc.wait(timeout=timeout)
        stderr_thread.join(timeout=10)
        stderr_data = b"".join(stderr_chunks)

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        stderr_thread.join(timeout=5)
        raise TimeoutError(f"FFmpeg exceeded timeout ({timeout}s)")

    # Check result
    if proc.returncode != 0:
        stderr_text = stderr_data.decode(errors="replace") if stderr_data else ""
        friendly = _parse_ffmpeg_error(stderr_text, proc.returncode)
        raise RuntimeError(friendly)

    if not os.path.isfile(output_path):
        raise RuntimeError("FFmpeg completed but output file does not exist — path may contain special characters")

    output_size = os.path.getsize(output_path)
    if output_size == 0:
        os.unlink(output_path)
        raise RuntimeError("FFmpeg created 0-byte file — video may be corrupt or codec incompatible")

    logger.info(
        "[burner] burn complete: %s (%.1f MB)",
        output_path, output_size / (1024 * 1024),
    )

    return output_path


# ── FFmpeg error parser ───────────────────────────────────────────────────────

_FFMPEG_ERROR_PATTERNS = [
    ("No such file or directory", "Video or subtitle file not found — check paths"),
    ("Permission denied", "Permission denied — check output directory permissions"),
    ("No space left on device", "Disk full — free up space or use a different drive"),
    ("Invalid data found when processing input", "Video corrupt or unsupported format — try converting to MP4"),
    ("moov atom not found", "MP4 file corrupt (missing moov atom) — re-download video"),
    ("Avi header not found", "AVI file corrupt or incomplete"),
    ("Could not find codec", "Video codec not supported — convert to H.264/MP4"),
    ("Unknown decoder", "Video codec not installed on system"),
    ("Decoder.*not found", "Decoder not available — install full FFmpeg with codecs"),
    ("Encoder.*not found", "Encoder not available — check FFmpeg installation"),
    ("Error opening filters", "FFmpeg filter error — check ASS subtitle file"),
    ("Fontconfig error", "Font error — selected font not available on system"),
    ("ass subtitle", "Error reading ASS subtitle file — check format"),
    ("Out of memory", "Out of RAM — video too large or system overloaded"),
    ("kill", "FFmpeg killed — possibly out of RAM or timeout"),
]


def _parse_ffmpeg_error(stderr_text: str, returncode: int) -> str:
    """Parse FFmpeg stderr into a user-friendly error message."""
    stderr_lower = stderr_text.lower()

    for pattern, friendly_msg in _FFMPEG_ERROR_PATTERNS:
        if re.search(pattern.lower(), stderr_lower):
            return friendly_msg

    # Fallback: extract last meaningful lines
    err_lines = [l for l in stderr_text.strip().split("\n") if l.strip()][-3:]
    err_summary = "\n".join(err_lines) if err_lines else "Unknown error"
    return f"FFmpeg failed (code {returncode}):\n{err_summary}"
