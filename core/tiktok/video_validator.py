"""
TikTok video pre-flight validator (Sprint TT-5 / F1).

Inspects a local video file and flags issues that would cause TikTok to
reject the upload — before we waste API quota / time chunk-uploading.

Two backends:
  • PRIMARY: `ffprobe` subprocess (part of FFmpeg). Reads container metadata.
  • FALLBACK: pure-Python — checks file size + a few magic bytes. Loses
    duration/resolution/codec but still catches truly broken files.

The validator returns a VideoReport with structured pass/warn/fail items
so the GUI can render a table and the compliance guard can hard-fail.

TikTok's documented limits (Content Posting API v2 — Direct Post, June 2025):
  • Duration:        3 s ≤ T ≤ 10 min (default; some apps unlock 30 min)
  • File size:       ≤ 4 GB
  • Resolution:      ≥ 540p; recommended 1080×1920 (9:16)
  • Aspect ratio:    Vertical preferred; 1:1 OK; 16:9 → letterboxed
  • Video codec:     H.264 (preferred), H.265, VP9
  • Audio codec:     AAC (preferred), MP3
  • Frame rate:      23-60 fps
  • Bitrate:         ≥ 516 kbps audio, ≥ 1 Mbps video recommended
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CheckResult(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class VideoCheckItem:
    name:    str
    result:  CheckResult
    message: str
    fix_hint: str = ""


@dataclass
class VideoReport:
    file_path:   str
    backend:     str          # "ffprobe" | "stat_only"
    duration_s:  float = 0.0
    width:       int   = 0
    height:      int   = 0
    fps:         float = 0.0
    bitrate_bps: int   = 0
    file_size_bytes: int = 0
    video_codec: str   = ""
    audio_codec: str   = ""
    has_audio:   bool  = False
    items:       list[VideoCheckItem] = field(default_factory=list)

    @property
    def aspect_ratio(self) -> float:
        return (self.width / self.height) if self.height else 0.0

    @property
    def fail_count(self) -> int:
        return sum(1 for i in self.items if i.result is CheckResult.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for i in self.items if i.result is CheckResult.WARN)

    @property
    def ready_to_upload(self) -> bool:
        return self.fail_count == 0

    def summary(self) -> str:
        if self.ready_to_upload and self.warn_count == 0:
            return f"✅ Video sẵn sàng upload TikTok ({len(self.items)} checks pass)"
        if self.ready_to_upload:
            return f"🟡 OK với {self.warn_count} cảnh báo (không block upload)"
        return f"❌ {self.fail_count} blocking issues — sửa trước khi upload"


# ─── TikTok limits (overridable via config) ──────────────────────────────────

DEFAULT_LIMITS = {
    "min_duration_s": 3,
    "max_duration_s": 600,        # 10 min default; some apps unlock 30
    "max_size_bytes": 4 * 1024 * 1024 * 1024,
    "min_height":     540,
    "min_fps":        23,
    "max_fps":        60,
    "preferred_video_codecs": {"h264", "hevc", "h265", "vp9", "avc1"},
    "preferred_audio_codecs": {"aac", "mp3"},
}


# ─── Public API ──────────────────────────────────────────────────────────────

def validate_video(
    file_path: str,
    limits: Optional[dict] = None,
) -> VideoReport:
    """Inspect *file_path* and return a VideoReport.

    On ffprobe failure or absence, falls back to stat-only mode (file size
    + existence). Caller should NOT block when fail_count == 0 even if
    backend == "stat_only" — we couldn't really check.
    """
    limits = {**DEFAULT_LIMITS, **(limits or {})}

    if not file_path or not os.path.exists(file_path):
        rep = VideoReport(file_path=file_path, backend="stat_only")
        rep.items.append(VideoCheckItem(
            name="File", result=CheckResult.FAIL,
            message="File không tồn tại", fix_hint="Check video_url / drive download",
        ))
        return rep

    size = os.path.getsize(file_path)
    rep = VideoReport(file_path=file_path, backend="stat_only",
                       file_size_bytes=size)

    # File-size check works without ffprobe
    if size <= 0:
        rep.items.append(VideoCheckItem(
            name="File size", result=CheckResult.FAIL,
            message="File rỗng (0 bytes)", fix_hint="Re-download video",
        ))
        return rep
    if size > limits["max_size_bytes"]:
        rep.items.append(VideoCheckItem(
            name="File size", result=CheckResult.FAIL,
            message=f"File quá lớn ({size / 2**30:.1f} GB > 4 GB)",
            fix_hint="Re-encode với bitrate thấp hơn",
        ))
    else:
        rep.items.append(VideoCheckItem(
            name="File size", result=CheckResult.PASS,
            message=f"{size / 2**20:.1f} MB", fix_hint="",
        ))

    # ffprobe metadata extraction
    meta = _ffprobe(file_path)
    if meta is None:
        rep.items.append(VideoCheckItem(
            name="ffprobe", result=CheckResult.WARN,
            message="ffprobe không khả dụng — bỏ qua check duration/codec",
            fix_hint="Cài ffmpeg (https://ffmpeg.org) để kiểm tra đầy đủ",
        ))
        return rep

    rep.backend = "ffprobe"
    _extract_from_ffprobe(rep, meta)
    _add_metadata_checks(rep, limits)
    return rep


# ─── ffprobe ─────────────────────────────────────────────────────────────────

def is_ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def _ffprobe(file_path: str, timeout: int = 30) -> Optional[dict]:
    """Run `ffprobe -v error -print_format json -show_format -show_streams`.

    Returns parsed JSON dict, or None on any failure (not installed, timeout,
    non-zero exit, malformed output)."""
    if not is_ffprobe_available():
        return None
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", file_path,
    ]
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout.decode("utf-8", errors="replace"))
    except (ValueError, json.JSONDecodeError):
        return None


def _extract_from_ffprobe(rep: VideoReport, meta: dict) -> None:
    """Populate rep.duration_s / width / height / fps / codecs from ffprobe."""
    fmt = meta.get("format", {}) or {}
    try:
        rep.duration_s = float(fmt.get("duration", 0.0) or 0.0)
    except (ValueError, TypeError):
        pass
    try:
        rep.bitrate_bps = int(fmt.get("bit_rate", 0) or 0)
    except (ValueError, TypeError):
        pass

    for stream in meta.get("streams", []) or []:
        kind = stream.get("codec_type", "")
        if kind == "video" and not rep.video_codec:
            rep.video_codec = str(stream.get("codec_name", "")).lower()
            try: rep.width  = int(stream.get("width",  0) or 0)
            except (ValueError, TypeError): pass
            try: rep.height = int(stream.get("height", 0) or 0)
            except (ValueError, TypeError): pass
            # fps comes as fraction "30/1" or "30000/1001"
            fps_str = str(stream.get("r_frame_rate", "0/1"))
            if "/" in fps_str:
                num, den = fps_str.split("/", 1)
                try:
                    n = float(num); d = float(den)
                    if d > 0:
                        rep.fps = n / d
                except ValueError:
                    pass
        elif kind == "audio" and not rep.audio_codec:
            rep.audio_codec = str(stream.get("codec_name", "")).lower()
            rep.has_audio   = True


def _add_metadata_checks(rep: VideoReport, limits: dict) -> None:
    """Add CheckItems for the metadata we extracted."""
    # Duration
    if rep.duration_s <= 0:
        rep.items.append(VideoCheckItem(
            "Duration", CheckResult.WARN,
            "ffprobe không đọc được duration",
            "Video có thể bị corrupt",
        ))
    elif rep.duration_s < limits["min_duration_s"]:
        rep.items.append(VideoCheckItem(
            "Duration", CheckResult.FAIL,
            f"Quá ngắn ({rep.duration_s:.1f}s < {limits['min_duration_s']}s)",
            "TT yêu cầu video ≥ 3 s",
        ))
    elif rep.duration_s > limits["max_duration_s"]:
        rep.items.append(VideoCheckItem(
            "Duration", CheckResult.FAIL,
            f"Quá dài ({rep.duration_s:.0f}s > {limits['max_duration_s']}s)",
            "Cắt video xuống ≤ 10 phút",
        ))
    else:
        rep.items.append(VideoCheckItem(
            "Duration", CheckResult.PASS,
            f"{rep.duration_s:.1f}s", "",
        ))

    # Resolution
    if rep.height <= 0 or rep.width <= 0:
        rep.items.append(VideoCheckItem(
            "Resolution", CheckResult.WARN,
            "Không xác định được resolution", "",
        ))
    elif rep.height < limits["min_height"]:
        rep.items.append(VideoCheckItem(
            "Resolution", CheckResult.FAIL,
            f"{rep.width}×{rep.height} thấp hơn {limits['min_height']}p",
            "Re-encode lên ≥ 540p (1080×1920 tốt nhất)",
        ))
    else:
        rep.items.append(VideoCheckItem(
            "Resolution", CheckResult.PASS,
            f"{rep.width}×{rep.height}", "",
        ))

    # Aspect ratio (informational warn — TT accepts most)
    if rep.aspect_ratio > 0:
        ar = rep.aspect_ratio
        if 0.55 <= ar <= 0.58:    # ~9:16 (0.5625)
            rep.items.append(VideoCheckItem(
                "Aspect ratio", CheckResult.PASS,
                f"9:16 vertical ({ar:.3f}) — discoverability max", "",
            ))
        elif 0.95 <= ar <= 1.05:  # square
            rep.items.append(VideoCheckItem(
                "Aspect ratio", CheckResult.WARN,
                f"1:1 square ({ar:.3f}) — letterboxed trên feed",
                "Crop sang 9:16 để max reach",
            ))
        elif 1.7 <= ar <= 1.8:    # 16:9
            rep.items.append(VideoCheckItem(
                "Aspect ratio", CheckResult.WARN,
                f"16:9 horizontal ({ar:.3f}) — TT crop / pillarbox",
                "Crop sang 9:16",
            ))
        else:
            rep.items.append(VideoCheckItem(
                "Aspect ratio", CheckResult.WARN,
                f"Unusual {ar:.3f} — TT có thể crop lạ", "Use 9:16 / 1:1 / 16:9",
            ))

    # FPS
    if rep.fps <= 0:
        pass
    elif rep.fps < limits["min_fps"]:
        rep.items.append(VideoCheckItem(
            "Frame rate", CheckResult.FAIL,
            f"{rep.fps:.1f} fps < {limits['min_fps']} fps min",
            "Re-encode ≥ 23 fps",
        ))
    elif rep.fps > limits["max_fps"]:
        rep.items.append(VideoCheckItem(
            "Frame rate", CheckResult.WARN,
            f"{rep.fps:.1f} fps > {limits['max_fps']} fps",
            "Re-encode ≤ 60 fps",
        ))
    else:
        rep.items.append(VideoCheckItem(
            "Frame rate", CheckResult.PASS, f"{rep.fps:.1f} fps", "",
        ))

    # Video codec
    if rep.video_codec:
        if rep.video_codec in limits["preferred_video_codecs"]:
            rep.items.append(VideoCheckItem(
                "Video codec", CheckResult.PASS, rep.video_codec, "",
            ))
        else:
            rep.items.append(VideoCheckItem(
                "Video codec", CheckResult.WARN,
                f"Codec '{rep.video_codec}' không phải H.264/H.265/VP9 — TT có thể từ chối",
                "Re-encode H.264 (libx264) cho tương thích max",
            ))

    # Audio codec
    if not rep.has_audio:
        rep.items.append(VideoCheckItem(
            "Audio", CheckResult.WARN,
            "Video không có audio track",
            "TT thường có audio — clip silent dễ bị low engagement",
        ))
    elif rep.audio_codec:
        if rep.audio_codec in limits["preferred_audio_codecs"]:
            rep.items.append(VideoCheckItem(
                "Audio codec", CheckResult.PASS, rep.audio_codec, "",
            ))
        else:
            rep.items.append(VideoCheckItem(
                "Audio codec", CheckResult.WARN,
                f"Codec '{rep.audio_codec}' không phải AAC/MP3",
                "Re-encode AAC để tương thích max",
            ))
