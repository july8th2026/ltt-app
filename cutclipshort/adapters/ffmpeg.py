"""FFmpeg/FFprobe adapter.

Wraps all FFmpeg subprocess interactions. No other module should
construct FFmpeg commands directly.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from cutclipshort.adapters.base import BaseAdapter
from cutclipshort.errors import AdapterError
from cutclipshort.types import SourceAsset

logger = logging.getLogger(__name__)


class FFmpegAdapter(BaseAdapter):
    """Adapter for FFmpeg video/audio encoding."""

    def __init__(self, executable_path: str | Path | None = None) -> None:
        super().__init__(executable_path)

    @property
    def tool_name(self) -> str:
        """Return adapter tool name."""
        return "ffmpeg"

    def get_version(self) -> str | None:
        """Return FFmpeg version string or None if unavailable."""
        try:
            result = self._run_command([self.executable, "-version"])
            first_line = result.stdout.split("\n")[0]
            return first_line.strip()
        except AdapterError:
            return None

    def get_capabilities(self) -> dict[str, Any]:
        """Return available encoders and decoders."""
        if self._capabilities_cache is not None:
            return self._capabilities_cache

        caps: dict[str, Any] = {
            "available": self.check_available(),
            "encoders": [],
            "decoders": [],
        }

        if caps["available"]:
            try:
                result = self._run_command(
                    [self.executable, "-encoders"],
                    check=False,
                )
                caps["encoders"] = [
                    parts[1]
                    for line in result.stdout.split("\n")
                    if line.strip().startswith("V")
                    and len(parts := line.strip().split()) >= 2
                ]
            except AdapterError:
                pass

        self._capabilities_cache = caps
        return caps

    def encode(
        self,
        input_path: Path,
        output_path: Path,
        *,
        video_filters: str = "",
        audio_filters: str = "",
        codec: str = "libx264",
        crf: str = "18",
        preset: str = "medium",
        pixel_format: str = "yuv420p",
        audio_codec: str = "aac",
        audio_bitrate: str = "192k",
        audio_sample_rate: int = 44100,
        audio_channels: int = 2,
        start_time: float | None = None,
        duration: float | None = None,
        max_bitrate: str = "",
        bufsize: str = "",
        target_fps: float = 0.0,
        extra_args: list[str] | None = None,
        timeout: float | None = None,
    ) -> Path:
        """Encode video with specified settings.

        Args:
            max_bitrate: VBV max bitrate (e.g. "10M"). Empty = no cap.
            bufsize: VBV buffer size (e.g. "20M"). Empty = 2x maxrate.
            target_fps: Output FPS. 0 = keep original.
        """
        args = [self.executable, "-y"]

        if start_time is not None:
            args += ["-ss", str(start_time)]
        args += ["-i", str(input_path)]
        if duration is not None:
            args += ["-t", str(duration)]

        if video_filters:
            args += ["-vf", video_filters]
        if audio_filters:
            args += ["-af", audio_filters]

        # FPS control
        if target_fps > 0:
            args += ["-r", str(target_fps)]

        # Video codec settings
        is_nvenc = "nvenc" in codec
        if is_nvenc:
            args += ["-c:v", codec, "-preset", preset, "-cq", crf]
        elif codec == "libx265":
            args += ["-c:v", codec, "-preset", preset, "-crf", crf, "-tag:v", "hvc1"]
        else:
            args += ["-c:v", codec, "-preset", preset, "-crf", crf]

        # VBV bitrate capping
        if max_bitrate:
            actual_bufsize = bufsize or f"{int(float(max_bitrate.rstrip('MmKk')) * 2)}M"
            args += ["-maxrate", max_bitrate, "-bufsize", actual_bufsize]

        args += ["-pix_fmt", pixel_format]

        # Audio codec settings
        args += [
            "-c:a", audio_codec,
            "-b:a", audio_bitrate,
            "-ar", str(audio_sample_rate),
            "-ac", str(audio_channels),
        ]

        if extra_args:
            args += extra_args

        args.append(str(output_path))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._run_command(args, timeout=timeout)
        except AdapterError as e:
            raise AdapterError(
                f"Encode video thất bại: {input_path.name} → {output_path.name}. "
                f"Codec: {codec}, CRF: {crf}. Chi tiết: {e}",
                tool_name="ffmpeg",
                stderr=getattr(e, 'stderr', ''),
            ) from e
        return output_path

    def encode_2pass(
        self,
        input_path: Path,
        output_path: Path,
        *,
        target_bitrate: str,
        video_filters: str = "",
        audio_filters: str = "",
        codec: str = "libx264",
        preset: str = "medium",
        pixel_format: str = "yuv420p",
        audio_codec: str = "aac",
        audio_bitrate: str = "192k",
        audio_sample_rate: int = 44100,
        audio_channels: int = 2,
        start_time: float | None = None,
        duration: float | None = None,
        max_bitrate: str = "",
        target_fps: float = 0.0,
        extra_args: list[str] | None = None,
        timeout: float | None = None,
    ) -> Path:
        """2-pass ABR encoding for optimal quality within bitrate budget."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        passlog = str(output_path.parent / f"{output_path.stem}_2pass")

        actual_maxrate = max_bitrate or target_bitrate

        # ── Pass 1 ──
        args1 = [self.executable, "-y"]
        if start_time is not None:
            args1 += ["-ss", str(start_time)]
        args1 += ["-i", str(input_path)]
        if duration is not None:
            args1 += ["-t", str(duration)]
        if video_filters:
            args1 += ["-vf", video_filters]
        if target_fps > 0:
            args1 += ["-r", str(target_fps)]

        is_nvenc = "nvenc" in codec
        if is_nvenc:
            args1 += ["-c:v", codec, "-preset", preset,
                      "-b:v", target_bitrate, "-maxrate", actual_maxrate,
                      "-multipass", "fullres"]
        else:
            args1 += ["-c:v", codec, "-preset", preset,
                      "-b:v", target_bitrate, "-maxrate", actual_maxrate,
                      "-pass", "1", "-passlogfile", passlog]

        args1 += ["-pix_fmt", pixel_format, "-an", "-f", "null"]
        # Windows: use NUL, Unix: /dev/null
        args1.append("NUL" if os.name == "nt" else "/dev/null")

        try:
            self._run_command(args1, timeout=timeout)
        except AdapterError as e:
            raise AdapterError(
                f"2-pass (pass 1) thất bại: {input_path.name}. Chi tiết: {e}",
                tool_name="ffmpeg",
                stderr=getattr(e, 'stderr', ''),
            ) from e

        # ── Pass 2 ──
        args2 = [self.executable, "-y"]
        if start_time is not None:
            args2 += ["-ss", str(start_time)]
        args2 += ["-i", str(input_path)]
        if duration is not None:
            args2 += ["-t", str(duration)]
        if video_filters:
            args2 += ["-vf", video_filters]
        if audio_filters:
            args2 += ["-af", audio_filters]
        if target_fps > 0:
            args2 += ["-r", str(target_fps)]

        if is_nvenc:
            args2 += ["-c:v", codec, "-preset", preset,
                      "-b:v", target_bitrate, "-maxrate", actual_maxrate,
                      "-multipass", "fullres"]
        else:
            args2 += ["-c:v", codec, "-preset", preset,
                      "-b:v", target_bitrate, "-maxrate", actual_maxrate,
                      "-pass", "2", "-passlogfile", passlog]

        args2 += ["-pix_fmt", pixel_format]
        args2 += ["-c:a", audio_codec, "-b:a", audio_bitrate,
                  "-ar", str(audio_sample_rate), "-ac", str(audio_channels)]

        if extra_args:
            args2 += extra_args
        args2.append(str(output_path))

        try:
            self._run_command(args2, timeout=timeout)
        except AdapterError as e:
            raise AdapterError(
                f"2-pass (pass 2) thất bại: {input_path.name}. Chi tiết: {e}",
                tool_name="ffmpeg",
                stderr=getattr(e, 'stderr', ''),
            ) from e
        finally:
            for ext in (".log", "-0.log", "-0.log.mbtree"):
                p = Path(passlog + ext)
                if p.exists():
                    p.unlink(missing_ok=True)

        return output_path

    def extract_audio(
        self,
        input_path: Path,
        output_path: Path,
        *,
        sample_rate: int = 44100,
        channels: int = 2,
        start_time: float | None = None,
        duration: float | None = None,
    ) -> Path:
        """Extract audio from video to WAV."""
        args = [self.executable, "-y"]
        if start_time is not None:
            args += ["-ss", str(start_time)]
        args += ["-i", str(input_path)]
        if duration is not None:
            args += ["-t", str(duration)]
        args += [
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", str(channels),
            str(output_path),
        ]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._run_command(args)
        except AdapterError as e:
            raise AdapterError(
                f"Trích xuất audio thất bại: {input_path.name}. "
                f"Video có thể không có track audio. Chi tiết: {e}",
                tool_name="ffmpeg",
                stderr=getattr(e, 'stderr', ''),
            ) from e
        return output_path

    def concat(
        self,
        file_list_path: Path,
        output_path: Path,
        *,
        codec_copy: bool = False,
    ) -> Path:
        """Concatenate files using concat demuxer."""
        args = [
            self.executable, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(file_list_path),
        ]
        if codec_copy:
            args += ["-c", "copy"]
        else:
            args += ["-c:v", "libx264", "-c:a", "aac"]
        args.append(str(output_path))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_command(args)
        return output_path

    def extract_thumbnail(
        self,
        input_path: Path,
        output_path: Path,
        time_sec: float = 0.0,
        width: int = 320,
        height: int = -1,
    ) -> Path:
        """Extract a single frame as JPEG thumbnail.

        Args:
            input_path: Source video.
            output_path: Where to write the .jpg file.
            time_sec: Timestamp to capture (seconds).
            width: Target width (height auto-scaled if -1).
            height: Target height (-1 = auto from width).
        """
        scale = f"scale={width}:{height}" if height > 0 else f"scale={width}:-1"
        args = [
            self.executable, "-y",
            "-ss", str(time_sec),
            "-i", str(input_path),
            "-vframes", "1",
            "-vf", scale,
            "-q:v", "3",
            str(output_path),
        ]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_command(args, timeout=15.0)
        return output_path

    def replace_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> Path:
        """Replace audio in video without re-encoding video."""
        args = [
            self.executable, "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(output_path),
        ]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_command(args)
        return output_path


class FFprobeAdapter(BaseAdapter):
    """Adapter for FFprobe media analysis."""

    def __init__(self, executable_path: str | Path | None = None) -> None:
        super().__init__(executable_path)

    @property
    def tool_name(self) -> str:
        """Return adapter tool name."""
        return "ffprobe"

    def get_version(self) -> str | None:
        """Return FFprobe version string or None if unavailable."""
        try:
            result = self._run_command([self.executable, "-version"])
            first_line = result.stdout.split("\n")[0]
            return first_line.strip()
        except AdapterError:
            return None

    def get_capabilities(self) -> dict[str, Any]:
        """Return availability status."""
        return {"available": self.check_available()}

    def probe(self, input_path: Path) -> dict[str, Any]:
        """Get full probe data as dict."""
        args = [
            self.executable,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(input_path),
        ]
        result = self._run_command(args)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AdapterError(
                f"Failed to parse ffprobe output for {input_path}",
                tool_name="ffprobe",
                details=str(e),
            )

    def get_media_info(self, input_path: Path, source_hash: str) -> SourceAsset:
        """Extract SourceAsset metadata from a video file."""
        data = self.probe(input_path)

        video_stream = None
        audio_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video" and video_stream is None:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and audio_stream is None:
                audio_stream = stream

        if video_stream is None:
            raise AdapterError(
                f"No video stream found in {input_path}",
                tool_name="ffprobe",
            )

        fmt = data.get("format", {})

        # Parse FPS from r_frame_rate (e.g. "30000/1001" or "29.97")
        fps_str = video_stream.get("r_frame_rate", "30/1")
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den)
            else:
                fps = float(fps_str)
        except (ValueError, ZeroDivisionError):
            logger.warning("Unparseable FPS '%s', defaulting to 30.0", fps_str)
            fps = 30.0

        def _safe_int(val, default: int = 0) -> int:
            """Safely convert string/int/None to int."""
            try:
                return int(float(str(val))) if val else default
            except (ValueError, TypeError):
                return default

        return SourceAsset(
            original_path=str(input_path),
            source_hash=source_hash,
            file_name=input_path.name,
            file_size_bytes=_safe_int(fmt.get("size", 0)),
            duration_sec=float(fmt.get("duration", 0) or 0),
            width=_safe_int(video_stream.get("width", 0)),
            height=_safe_int(video_stream.get("height", 0)),
            fps=round(fps, 3),
            video_codec=video_stream.get("codec_name", "unknown"),
            pixel_format=video_stream.get("pix_fmt", "yuv420p"),
            bitrate_kbps=_safe_int(fmt.get("bit_rate", 0)) // 1000,
            audio_codec=audio_stream.get("codec_name", "none") if audio_stream else "none",
            audio_sample_rate=_safe_int(audio_stream.get("sample_rate", 0)) if audio_stream else 0,
            audio_channels=_safe_int(audio_stream.get("channels", 0)) if audio_stream else 0,
            audio_bitrate_kbps=_safe_int(audio_stream.get("bit_rate", 0)) // 1000 if audio_stream else 0,
        )

    def get_duration(self, input_path: Path) -> float:
        """Get video duration in seconds."""
        data = self.probe(input_path)
        return float(data.get("format", {}).get("duration", 0))
