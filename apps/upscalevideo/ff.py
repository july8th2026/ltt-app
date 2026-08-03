"""
ff.py — probe / tách frame / encode cho upscalevideo (ĐỒNG BỘ).

Di trú từ BOT GEMINI `video_upscale/adapters/ffmpeg_adapter.py`. Định vị ffmpeg qua
`platform_core.media` (tôn trọng env LTT_FFMPEG). Giữ nguyên logic:
- giữ đúng tỉ lệ gốc (scale=-2:H), giữ FPS, audio copy;
- xử lý VFR (ép CFR), autorotate, xoay 90/270 đổi w/h;
- encode NVENC (fallback CPU libx264 nếu không có GPU encoder);
- chunk: encode_segment (video-only) + concat_and_mux.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time

from platform_core import media

logger = logging.getLogger(__name__)


class ProcessingCancelled(Exception):
    """The durable job was cancelled while an FFmpeg subprocess was active."""


def _ff() -> str:
    return media.ffmpeg_bin()


def _fp() -> str:
    return media.ffprobe_bin()


def _run(cmd: list, timeout: int = 3600, cancel_check=None,
         cwd: str | None = None) -> subprocess.CompletedProcess:
    if cancel_check is None:
        return subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            cwd=cwd)
    deadline = time.monotonic() + timeout
    while True:
        if cancel_check():
            proc.kill()
            proc.communicate()
            raise ProcessingCancelled("Job đã được hủy.")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            proc.kill()
            out, err = proc.communicate()
            raise subprocess.TimeoutExpired(cmd, timeout, output=out, stderr=err)
        try:
            out, err = proc.communicate(timeout=min(0.5, remaining))
            return subprocess.CompletedProcess(cmd, proc.returncode, out, err)
        except subprocess.TimeoutExpired:
            continue


def probe_video(path: str, cancel_check=None) -> dict:
    """Trả {w,h,fps,fps_str,duration,nb_frames,has_audio,vcodec,is_vfr,rotation}."""
    r = _run([_fp(), "-v", "error", "-print_format", "json",
              "-show_format", "-show_streams", path], timeout=60,
             cancel_check=cancel_check)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe lỗi: {r.stderr.decode(errors='replace')[:300]}")
    data = json.loads(r.stdout.decode(errors="replace"))

    def _rate(s: str) -> float:
        try:
            n, d = s.split("/")
            return float(n) / float(d) if float(d) else 0.0
        except Exception:  # noqa: BLE001
            try:
                return float(s or 0)
            except Exception:  # noqa: BLE001
                return 0.0

    w = h = nb_frames = rotation = 0
    r_fps = avg_fps = 0.0
    fps_str, vcodec = "24/1", ""
    has_audio = False
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and not w:
            w = int(s.get("width", 0) or 0); h = int(s.get("height", 0) or 0)
            vcodec = s.get("codec_name", "") or ""
            fps_str = s.get("r_frame_rate", "24/1") or "24/1"
            r_fps = _rate(fps_str)
            avg_fps = _rate(s.get("avg_frame_rate", "0/0")) or r_fps
            try:
                nb_frames = int(s.get("nb_frames", 0) or 0)
            except (TypeError, ValueError):
                nb_frames = 0
            for sd in s.get("side_data_list", []) or []:
                if "rotation" in sd:
                    try:
                        rotation = int(sd["rotation"]) % 360
                    except (TypeError, ValueError):
                        pass
            if not rotation:
                try:
                    rotation = int(s.get("tags", {}).get("rotate", 0)) % 360
                except (TypeError, ValueError):
                    rotation = 0
        elif s.get("codec_type") == "audio":
            has_audio = True

    is_vfr = bool(r_fps and avg_fps and abs(r_fps - avg_fps) / max(r_fps, 0.01) > 0.02)
    fps = avg_fps if is_vfr else r_fps
    out_fps_str = fps_str if not is_vfr else (f"{avg_fps:.5f}".rstrip("0").rstrip(".") or "24")
    if rotation in (90, 270):
        w, h = h, w
    duration = float(data.get("format", {}).get("duration", 0) or 0)
    if not nb_frames and fps and duration:
        nb_frames = int(round(fps * duration))
    return {"w": w, "h": h, "fps": fps, "fps_str": out_fps_str, "duration": duration,
            "nb_frames": nb_frames, "has_audio": has_audio, "vcodec": vcodec,
            "is_vfr": is_vfr, "rotation": rotation}


def extract_frames(src: str, out_dir: str, cfr_fps=None, max_seconds=None,
                   interpolate_fps=None, cancel_check=None) -> int:
    """Tách frame → out_dir/f%05d.png. Trả số frame."""
    os.makedirs(out_dir, exist_ok=True)
    cmd = [_ff(), "-y", "-i", src]
    if max_seconds:
        cmd += ["-t", f"{max_seconds:.2f}"]
    filters = []
    if cfr_fps:
        filters.append(f"fps={cfr_fps}")
    if interpolate_fps:
        filters.append("minterpolate=" +
                       f"fps={interpolate_fps}:mi_mode=mci:mc_mode=aobmc:"
                       "me_mode=bidir:vsbmc=1")
    if filters:
        cmd += ["-vf", ",".join(filters)]
    cmd += [os.path.join(out_dir, "f%05d.png")]
    r = _run(cmd, cancel_check=cancel_check)
    n = sum(1 for f in os.scandir(out_dir) if f.name.endswith(".png"))
    if r.returncode != 0 or n == 0:
        raise RuntimeError(f"Tách frame thất bại (rc={r.returncode}, n={n})")
    return n


def multiply_rate(rate: str, factor: int = 2) -> str:
    """Nhân rational FPS mà không đổi sang float thiếu ổn định."""
    try:
        if "/" in str(rate):
            numerator, denominator = str(rate).split("/", 1)
            return f"{int(numerator) * int(factor)}/{int(denominator)}"
        return f"{float(rate) * factor:.5f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError, ZeroDivisionError):
        return str(60 if factor == 2 else 30 * factor)


def stabilize_video(src: str, out_path: str, max_seconds=None,
                    cancel_check=None) -> None:
    """Ổn định video hai pass bằng libvidstab; audio được mux từ source ở cuối."""
    workdir = os.path.dirname(out_path) or "."
    os.makedirs(workdir, exist_ok=True)
    transform_name = "motion.trf"
    common = [_ff(), "-y", "-i", src]
    if max_seconds:
        common += ["-t", f"{max_seconds:.2f}"]
    detect = common + ["-vf", "vidstabdetect=shakiness=5:accuracy=9:result=" +
                       transform_name, "-f", "null", "-"]
    first = _run(detect, cancel_check=cancel_check, cwd=workdir)
    if first.returncode != 0:
        raise RuntimeError("Phân tích chống rung thất bại: " +
                           first.stderr.decode(errors="replace")[-300:])
    transform = common + ["-vf", "vidstabtransform=input=" + transform_name +
                          ":smoothing=10:optzoom=1", "-an", "-c:v", "libx264",
                          "-preset", "veryfast", "-crf", "18", "-pix_fmt",
                          "yuv420p", out_path]
    try:
        second = _run(transform, cancel_check=cancel_check, cwd=workdir)
    finally:
        try:
            os.remove(os.path.join(workdir, transform_name))
        except OSError:
            pass
    if second.returncode != 0 or not os.path.isfile(out_path):
        raise RuntimeError("Chống rung thất bại: " +
                           second.stderr.decode(errors="replace")[-300:])


def _venc_args(encoder: str) -> list:
    if encoder in ("h264_nvenc", "hevc_nvenc"):
        args = ["-c:v", encoder, "-preset", "p5", "-cq", "19", "-pix_fmt", "yuv420p"]
        if encoder == "hevc_nvenc":
            args += ["-tag:v", "hvc1"]
        return args
    # CPU fallback
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]


def encode_full(frames_dir: str, src_for_audio: str, out_path: str, fps_str: str,
                target_h: int, has_audio: bool, encoder: str,
                cancel_check=None) -> tuple:
    """Ghép frame upscaled → MP4, giữ tỉ lệ + FPS + audio copy. Trả (out_w, out_h)."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    vf = f"scale=-2:{target_h}:flags=lanczos"
    cmd = [_ff(), "-y", "-framerate", fps_str, "-i", os.path.join(frames_dir, "f%05d.png")]
    if has_audio:
        cmd += ["-i", src_for_audio, "-map", "0:v:0", "-map", "1:a:0"]
    cmd += ["-vf", vf, "-r", fps_str] + _venc_args(encoder)
    if has_audio:
        cmd += ["-c:a", "copy"]
    cmd += [out_path]
    r = _run(cmd, cancel_check=cancel_check)
    if r.returncode != 0 or not os.path.isfile(out_path):
        raise RuntimeError(f"Encode lỗi: {r.stderr.decode(errors='replace')[-400:]}")
    info = probe_video(out_path, cancel_check=cancel_check)
    return info["w"], info["h"]


def encode_segment(frames_dir: str, out_path: str, fps_str: str, target_h: int,
                   encoder: str, cancel_check=None) -> None:
    """Encode 1 batch frame → segment MP4 (video-only) để concat."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    cmd = ([_ff(), "-y", "-framerate", fps_str, "-i", os.path.join(frames_dir, "f%05d.png"),
            "-vf", f"scale=-2:{target_h}:flags=lanczos", "-r", fps_str]
           + _venc_args(encoder) + [out_path])
    r = _run(cmd, cancel_check=cancel_check)
    if r.returncode != 0 or not os.path.isfile(out_path):
        raise RuntimeError(f"Encode segment lỗi: {r.stderr.decode(errors='replace')[-300:]}")


def concat_and_mux(seg_paths: list, src_for_audio: str, out_path: str,
                   has_audio: bool, cancel_check=None) -> tuple:
    """Nối segment (copy) + mux audio gốc 1 lần (giữ sync)."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    list_file = out_path + ".concat.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in seg_paths:
            f.write("file '" + p.replace("\\", "/") + "'\n")
    cmd = [_ff(), "-y", "-f", "concat", "-safe", "0", "-i", list_file]
    if has_audio:
        cmd += ["-i", src_for_audio, "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "copy"]
    else:
        cmd += ["-c", "copy"]
    cmd += [out_path]
    r = _run(cmd, cancel_check=cancel_check)
    try:
        os.remove(list_file)
    except OSError:
        pass
    if r.returncode != 0 or not os.path.isfile(out_path):
        raise RuntimeError(f"Concat/mux lỗi: {r.stderr.decode(errors='replace')[-300:]}")
    info = probe_video(out_path, cancel_check=cancel_check)
    return info["w"], info["h"]
