"""
burn.py — khắc phụ đề ASS vào video bằng ffmpeg (đồng bộ).

Di trú từ BOT GEMINI `auto_sub_video/adapters/ffmpeg_adapter.py` (bản async) sang
mô hình worker ĐỒNG BỘ của nền tảng: dùng `platform_core.media` để định vị
ffmpeg, dò encoder GPU (fallback CPU libx264) và chạy có báo tiến độ.

Giữ nguyên: filter `ass=`, escape đường dẫn ASS, preset chất lượng NVENC/x264/
VP9, chế độ bitrate auto/match/explicit, audio copy, movflags faststart.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import logging
import os
import collections
import re
import subprocess
import threading
from typing import Callable, Optional

from platform_core import media

log = logging.getLogger(__name__)

# CRF/preset theo mức chất lượng (CPU libx264).
_X264 = {"draft": ("ultrafast", "28"), "standard": ("medium", "23"),
         "high": ("slow", "18")}
# NVENC dùng -preset + -cq.
_NVENC = {"draft": ("p1", "32"), "standard": ("p4", "23"), "high": ("p7", "18")}
_QSV = {"draft": ("veryfast", "30"), "standard": ("medium", "23"),
        "high": ("veryslow", "18")}
# VP9 (webm) CRF (thang riêng, thấp = đẹp).
_WEBM_CRF = {"draft": "40", "standard": "30", "high": "20"}
_OUT_TIME_US = re.compile(r"^out_time_(?:ms|us)=(\d+)")
_OUT_TIME = re.compile(r"^out_time=(\d+):(\d+):([\d.]+)")


def _run_with_cleanup(cmd: list[str], *, total_duration: float,
                      on_progress: Optional[Callable[[float], None]], timeout: int,
                      cwd: str) -> None:
    """Run FFmpeg and always kill it if a progress callback cancels the job."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, cwd=cwd)
    tail: collections.deque[str] = collections.deque(maxlen=12)
    def drain():
        try:
            assert proc.stderr is not None
            for line in proc.stderr:
                if line.strip(): tail.append(line.strip())
        except Exception:  # pragma: no cover - best effort stderr drain
            pass
    thread = threading.Thread(target=drain, daemon=True); thread.start()
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.strip(); current = None
            match = _OUT_TIME_US.match(line)
            if match: current = int(match.group(1)) / 1_000_000
            else:
                match = _OUT_TIME.match(line)
                if match: current = int(match.group(1))*3600+int(match.group(2))*60+float(match.group(3))
            if current is not None and total_duration > 0 and on_progress:
                on_progress(min(99.0, round(current / total_duration * 100, 1)))
            if line == "progress=end" and on_progress: on_progress(100.0)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        if proc.poll() is None:
            proc.kill(); proc.wait()
        raise media.MediaError(f"ffmpeg quá thời gian ({timeout}s).") from exc
    except BaseException:
        if proc.poll() is None:
            proc.kill(); proc.wait()
        raise
    finally:
        thread.join(timeout=5)
    if proc.returncode != 0:
        raise media.MediaError(f"ffmpeg lỗi (code {proc.returncode}): " + " | ".join(tail))


def _ass_filter_arg(ass_path: str) -> tuple:
    """Trả (tên_file_trần, thư_mục). Chạy ffmpeg với cwd = thư mục chứa .ass rồi
    truyền TÊN FILE TRẦN cho filter `ass=` → khỏi phải escape đường dẫn Windows
    (ổ đĩa `C:` và `\\` làm vỡ bộ phân tích filter — đã gặp thật khi test)."""
    return os.path.basename(ass_path), (os.path.dirname(ass_path) or ".")


def _bitrate_flags(bitrate_mode: str, source_kbps: int) -> tuple:
    """Trả (dùng_target, target, maxrate, bufsize)."""
    if bitrate_mode == "match" and source_kbps > 0:
        kb = int(source_kbps * 1.1)
        return True, f"{kb}k", f"{int(kb * 1.3)}k", f"{int(kb * 2)}k"
    if bitrate_mode not in ("auto", "match"):
        tb = bitrate_mode
        if bitrate_mode.upper().endswith("M"):
            v = float(bitrate_mode[:-1])
            return True, tb, f"{v * 1.3:.1f}M", f"{v * 2:.0f}M"
        if bitrate_mode.upper().endswith("K"):
            v = int(bitrate_mode[:-1])
            return True, tb, f"{int(v * 1.3)}k", f"{int(v * 2)}k"
    return False, "", "", ""


def burn(*, video_path: str, ass_path: str, output_path: str,
         output_format: str = "mp4", quality: str = "standard",
         bitrate_mode: str = "auto", source_bitrate_kbps: int = 0,
         total_duration: float = 0.0,
         target_height: int = 0,
         on_progress: Optional[Callable[[float], None]] = None,
         timeout: int = 1800) -> str:
    """Khắc phụ đề, trả đường dẫn output. Ném media.MediaError khi ffmpeg lỗi."""
    for p, label in ((video_path, "Video"), (ass_path, "ASS")):
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Không có file {label}: {p}")
    if os.path.getsize(video_path) == 0:
        raise ValueError(_t('File video rỗng (0 byte).'))
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    ass, ass_cwd = _ass_filter_arg(ass_path)
    use_tb, tb, maxb, buf = _bitrate_flags(bitrate_mode, source_bitrate_kbps)
    ff = media.ffmpeg_bin()
    video_path = os.path.abspath(video_path)
    output_path = os.path.abspath(output_path)

    video_filter = f"ass={ass}"
    if target_height > 0:
        video_filter = f"scale=-2:{int(target_height)},{video_filter}"

    if output_format == "webm":
        crf = _WEBM_CRF.get(quality, _WEBM_CRF["standard"])
        cmd = [ff, "-y", "-i", video_path, "-vf", video_filter, "-c:v", "libvpx-vp9"]
        cmd += (["-b:v", tb, "-maxrate", maxb] if use_tb else ["-crf", crf, "-b:v", "0"])
        cmd += ["-c:a", "libopus"]
    else:
        gpu = media.detect_gpu_encoder()
        cmd = [ff, "-y", "-i", video_path, "-vf", video_filter]
        if gpu == "h264_nvenc":
            preset, cq = _NVENC.get(quality, _NVENC["standard"])
            cmd += ["-c:v", "h264_nvenc", "-preset", preset]
            cmd += (["-b:v", tb, "-maxrate", maxb, "-bufsize", buf] if use_tb
                    else ["-cq", cq, "-b:v", "0"])
        elif gpu == "h264_qsv":
            preset, gq = _QSV.get(quality, _QSV["standard"])
            cmd += ["-c:v", "h264_qsv", "-preset", preset]
            cmd += (["-b:v", tb, "-maxrate", maxb, "-bufsize", buf] if use_tb
                    else ["-global_quality", gq])
        else:                                          # CPU fallback
            preset, crf = _X264.get(quality, _X264["standard"])
            cmd += ["-c:v", "libx264", "-preset", preset]
            cmd += (["-b:v", tb, "-maxrate", maxb, "-bufsize", buf] if use_tb
                    else ["-crf", crf])
        cmd += ["-c:a", "copy"]
        if output_format != "mkv":
            cmd += ["-movflags", "+faststart"]

    cmd += ["-progress", "pipe:1", "-nostats", output_path]
    log.info("[burn] %s", " ".join(cmd))
    _run_with_cleanup(cmd, total_duration=total_duration,
                      on_progress=on_progress, timeout=timeout, cwd=ass_cwd)

    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise media.MediaError("ffmpeg xong nhưng output rỗng/không tồn tại.")
    return output_path


def burn_preview(*, video_path: str, ass_path: str, output_path: str,
                 preview_duration: float = 8.0, output_format: str = "mp4",
                 timeout: int = 300) -> str:
    """Khắc N giây đầu (xem thử nhanh, libx264 ultrafast)."""
    for p, label in ((video_path, "Video"), (ass_path, "ASS")):
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Không có file {label}: {p}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    ass, ass_cwd = _ass_filter_arg(ass_path)
    ff = media.ffmpeg_bin()
    video_path = os.path.abspath(video_path)
    output_path = os.path.abspath(output_path)
    cmd = [ff, "-y", "-t", str(preview_duration), "-i", video_path,
           "-vf", f"ass={ass}"]
    if output_format == "webm":
        cmd += ["-c:v", "libvpx-vp9", "-crf", "35", "-b:v", "0", "-c:a", "libopus"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"]
    cmd += ["-progress", "pipe:1", "-nostats", output_path]
    log.info("[burn_preview] %s", " ".join(cmd))
    media.run_with_progress(cmd, total_duration=preview_duration, timeout=timeout,
                            cwd=ass_cwd)
    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise media.MediaError("Preview rỗng/không tồn tại.")
    return output_path
