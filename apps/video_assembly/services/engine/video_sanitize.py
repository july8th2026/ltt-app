"""
engine/video_sanitize.py

Sanitize / normalize AI-generated videos (e.g., Veo3) so that downstream FFmpeg
seeking, trimming, frame extraction, and concatenation are stable.

Why this module exists:
- Many AI MP4s have extremely sparse keyframes (sometimes only at t=0) and/or
  slightly non-standard H.264 reference behavior.
- Pipeline stages like clip_sampling / scene trim rely on seeking (-ss) and
  frame-extraction. Sparse keyframes can cause wrong-frame grabs or decoder warnings
  (e.g., "mmco: unref short failure") and unstable behavior.

What sanitize does (default):
- Re-encode video to H.264 (libx264), closed GOP, regular keyframes every N seconds.
- Regenerate timestamps if needed.
- Keep audio (optional) as AAC; safe for MP4 and editing tools.
- Output MP4 with yuv420p and +faststart for compatibility.

This file is designed to be used by engine.runner.py as a pre-step:
    sanitized_dir = sanitize_folder(cfg, input_dir, os.path.join(job_dir, "_sanitized"))
    ... then pipeline uses sanitized_dir instead of input_dir

Config (optional) keys in cfg["video_sanitize"]:
  enable: bool (default True)
  keyframe_seconds: float (default 2.0)
  preset: str (default "veryfast")
  crf: int (default 18)
  force_fps: int|None (default None)     # set to 30 if you need constant fps
  copy_audio: bool (default False)       # True -> try stream copy audio if safe
  audio_bitrate: str (default "192k")
  overwrite: bool (default False)
  extensions: list[str] (default ["mp4","mov","mkv","webm"])
  logo_crop:
    enable: bool (default False)
    bottom_px: int (default 16)          # pixels to crop from bottom
    right_px: int (default 16)           # pixels to crop from right
"""

from __future__ import annotations

import os
import math
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Optional, Tuple, List

from ..tuong_thich.log import info, warn, exc
from ..tuong_thich.paths import ensure_dir
from ..tuong_thich.ffmpeg import run as ff_run

# [GPU] Bộ dựng args NVENC/NVDEC dùng chung, nằm ở root FULL AUTO VIDEO cạnh
# gpu_arbiter.py. Nếu vì lý do gì đó không import được thì degrade về libx264 —
# module này không bao giờ được phép làm sập pipeline.
try:
    import ffmpeg_gpu as _gpu
except Exception:  # pragma: no cover — chỉ xảy ra khi root không có trong sys.path
    _gpu = None


def _run_ffprobe(cmd: List[str]) -> str:
    """Run ffprobe and return stdout (best-effort).

    [Phase 7] timeout=30s — ffprobe phải hoàn tất nhanh; > 30s là hang."""
    try:
        out = subprocess.check_output(cmd, timeout=30).decode("utf-8", errors="ignore").strip()
        return out
    except subprocess.TimeoutExpired:
        return ""
    except Exception:
        return ""



def is_video_valid(path: str) -> bool:
    """Quick validation: ffprobe must be able to read container and duration."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", path]
    out = _run_ffprobe(cmd)
    if not out:
        return False
    try:
        float(out.strip())
        return True
    except Exception:
        return False

def probe_video_fps(path: str) -> float:
    """
    Best-effort fps probe using ffprobe r_frame_rate.
    Returns 0.0 if unknown.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "default=nk=1:nw=1",
        path
    ]
    out = _run_ffprobe(cmd)
    if not out:
        return 0.0
    # r_frame_rate often "30/1" or "24000/1001"
    try:
        if "/" in out:
            num, den = out.split("/", 1)
            num_f = float(num)
            den_f = float(den)
            if den_f != 0:
                return num_f / den_f
        return float(out)
    except Exception:
        return 0.0


def probe_has_audio(path: str) -> bool:
    """Return True if input has at least one audio stream."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index",
        "-of", "default=nk=1:nw=1",
        path
    ]
    out = _run_ffprobe(cmd)
    return bool(out.strip())


def _sanitize_params(cfg: Dict) -> Dict:
    vs = (cfg or {}).get("video_sanitize", {}) if isinstance(cfg, dict) else {}
    return {
        "enable": bool(vs.get("enable", True)),
        "keyframe_seconds": float(vs.get("keyframe_seconds", 2.0)),
        "preset": str(vs.get("preset", "veryfast")),
        "crf": int(vs.get("crf", 18)),
        # [GPU] use_gpu=True -> h264_nvenc + NVDEC decode (mặc định).
        #
        # nvenc_cq=25: HIỆU CHỈNH BẰNG ĐO THẬT, không phải đoán. Thang cq của NVENC
        # KHÔNG trùng thang crf của x264 — cq 19 cho ra file 153MB (gấp đôi) mà mắt
        # thường không thấy đẹp hơn. Đo VMAF trên mẫu 96s 1080p30 (2883 frame):
        #
        #     libx264 crf18 veryfast   70 MB   VMAF 93.98   12.3 s
        #     h264_nvenc cq25 bf0      72 MB   VMAF 94.51    8.0 s   <- chọn cái này
        #     h264_nvenc cq22 bf0     106 MB   VMAF 95.25
        #     h264_nvenc cq19 bf0     153 MB   VMAF 81.9/94.x (thừa bitrate)
        #
        # cq 25 cho chất lượng NHỈNH HƠN x264 crf18 ở cùng dung lượng. Muốn đổi thì
        # đo lại bằng scripts/bench_sanitize.py, đừng chỉnh mò.
        "use_gpu": bool(vs.get("use_gpu", True)),
        "nvenc_cq": int(vs.get("nvenc_cq", 25)),
        "force_fps": vs.get("force_fps", None),
        "copy_audio": bool(vs.get("copy_audio", False)),
        "audio_bitrate": str(vs.get("audio_bitrate", "192k")),
        "overwrite": bool(vs.get("overwrite", False)),
        "extensions": list(vs.get("extensions", ["mp4", "mov", "mkv", "webm"])),
        "logo_crop": {
            "enable": bool((vs.get("logo_crop") or {}).get("enable", False)),
            "bottom_px": int((vs.get("logo_crop") or {}).get("bottom_px", 16)),
            "right_px": int((vs.get("logo_crop") or {}).get("right_px", 16)),
        },
    }


def sanitize_video(cfg: Dict, in_path: str, out_path: str) -> str:
    """
    Sanitize a single video file.
    Returns out_path on success.

    Notes:
    - This always re-encodes video (libx264) to create stable GOP/keyframes.
    - Audio handling:
        - if copy_audio=True: attempts -c:a copy (can fail for some sources).
        - otherwise: re-encodes to AAC for maximum compatibility.
    """
    p = _sanitize_params(cfg)
    if not p["enable"]:
        return in_path

    in_p = Path(in_path)
    out_p = Path(out_path)
    ensure_dir(str(out_p.parent))

    if out_p.exists() and (not p["overwrite"]):
        # If already exists, keep it (common for resume) BUT validate it.
        if is_video_valid(str(out_p)):
            return str(out_p)
        warn("video_sanitize_existing_invalid", out_path=str(out_p))
        try:
            out_p.unlink()
        except Exception:
            pass

    fps = probe_video_fps(str(in_p)) or 30.0
    force_fps = p["force_fps"]
    if force_fps:
        try:
            fps = float(force_fps)
        except Exception:
            pass

    # Keyframe interval (keyint) in frames
    ksec = max(0.5, float(p["keyframe_seconds"]))
    keyint = int(max(12, round(fps * ksec)))  # minimum 12 frames (~0.5s @ 24fps)

    has_audio = probe_has_audio(str(in_p))
    audio_args: List[str] = []
    if has_audio:
        if p["copy_audio"]:
            audio_args = ["-c:a", "copy"]
        else:
            audio_args = ["-c:a", "aac", "-b:a", p["audio_bitrate"]]
    else:
        # no audio stream
        audio_args = ["-an"]

    # Build ffmpeg command
    # Important flags:
    # -err_detect ignore_err : survive minor bitstream issues
    # -fflags +genpts       : regenerate timestamps when input is weird
    # -movflags +faststart  : moov atom front for web playback
    # -pix_fmt yuv420p      : broad compatibility (Premiere/phones/YT)
    # Closed GOP and fixed keyint: stable seeking/cutting
    #
    # [GPU 2026-09] Trước đây khối này hardcode libx264. Đây là bước chạy trên
    # MỌI clip tải về, 3 luồng song song, TRƯỚC mọi stage khác — tức hạng mục
    # ngốn CPU lớn nhất toàn hệ thống. Nay dựng qua ffmpeg_gpu để dùng h264_nvenc
    # + NVDEC, và tự rơi về libx264 nếu NVENC không dùng được.
    def _build_cmd(use_gpu: bool) -> List[str]:
        encoder = "libx264"
        preset = p["preset"]
        quality = p["crf"]
        decode: List[str] = []
        if use_gpu and _gpu is not None:
            if _gpu.nvenc_available("h264"):
                encoder = "h264_nvenc"
                preset = _gpu.nvenc_preset_for(p["preset"])
                quality = p["nvenc_cq"]
            decode = _gpu.decode_args()

        c: List[str] = [
            "ffmpeg", "-y",
            "-hide_banner",
            "-loglevel", "warning",
            "-err_detect", "ignore_err",
            "-fflags", "+genpts",
        ]
        # -hwaccel phải đứng TRƯỚC -i thì mới áp cho input đó.
        c += decode
        c += ["-i", str(in_p), "-map", "0:v:0"]

        if has_audio:
            c += ["-map", "0:a:0?"]

        # Logo crop filter (remove Veo watermark from bottom-right)
        # Vẫn là filter CPU — decode_args() cố tình trả frame về RAM để crop chạy được.
        lc = p["logo_crop"]
        if lc["enable"] and (lc["bottom_px"] > 0 or lc["right_px"] > 0):
            crop_expr = f"crop=in_w-{lc['right_px']}:in_h-{lc['bottom_px']}:0:0"
            c += ["-vf", crop_expr]

        # Video encode with bitrate control for consistent quality
        if _gpu is not None:
            c += _gpu.video_encode_args(
                encoder=encoder,
                quality=quality,
                preset=preset,
                keyint=keyint,
                closed_gop=True,      # seek chuẩn từng frame — lý do module này tồn tại
                bitrate="32M",
                maxrate="40M",
                bufsize="64M",
                profile="high",
                pix_fmt="yuv420p",
            )
        else:
            x264_params = f"keyint={keyint}:min-keyint={keyint}:scenecut=0:open-gop=0"
            c += [
                "-c:v", "libx264",
                "-preset", p["preset"],
                "-crf", str(p["crf"]),
                "-b:v", "32M", "-maxrate", "40M", "-bufsize", "64M",
                "-profile:v", "high", "-pix_fmt", "yuv420p",
                "-x264-params", x264_params,
            ]

        # Force 30fps CFR and normalize timebase for ALL videos (Version 2.4.0 - Fix transitions stability)
        # This ensures ALL sanitized videos have identical timebase, critical for complex xfade transitions
        c += [
            "-r", "30",                         # Force 30fps output
            "-vsync", "cfr",                    # Constant frame rate
            "-video_track_timescale", "15360",  # Normalize timebase (same as segment creation)
            "-ar", "48000",                     # Normalize audio sample rate (same as segment creation)
        ]
        c += audio_args
        c += ["-movflags", "+faststart", str(out_p)]
        return c

    _use_gpu = bool(p["use_gpu"]) and _gpu is not None
    cmd: List[str] = _build_cmd(_use_gpu)

    lc = p["logo_crop"]
    if lc["enable"] and (lc["bottom_px"] > 0 or lc["right_px"] > 0):
        info("video_sanitize_crop", bottom=lc["bottom_px"], right=lc["right_px"])

    info("video_sanitize_start", in_path=str(in_p), out_path=str(out_p),
         fps=round(fps, 3), keyint=keyint,
         encoder=("h264_nvenc" if "h264_nvenc" in cmd else "libx264"),
         hwdec=("cuda" if "-hwaccel" in cmd else "cpu"))

    # FIX#2: helper xoá file output dở dang khi sanitize fail (x264 OOM, encoder crash...)
    # Lý do: ffmpeg crash giữa chừng để lại file 22-42KB không phải MP4 hợp lệ.
    # Nếu không xoá, stage CLIP_SAMPLING sẽ thử mở bằng OpenCV → "Unknown C++ exception",
    # clip biến mất khỏi items, scene_id bị thiếu mà không có cảnh báo rõ ràng.
    # Threshold 100KB an toàn: video 8s 1080p libx264 thật luôn ≥500KB.
    def _cleanup_corrupt_output():
        try:
            if out_p.exists():
                sz = out_p.stat().st_size
                if sz < 100_000:
                    out_p.unlink()
                    warn("video_sanitize_cleanup_corrupt_output",
                         out_path=str(out_p), size_bytes=sz)
        except Exception:
            pass

    def _to_aac(c: List[str]) -> List[str]:
        """Đổi nhánh audio của một lệnh đã dựng sang AAC (bỏ -c:a copy)."""
        c2 = list(c)
        if "-c:a" in c2:
            i = c2.index("-c:a")
            del c2[i:i + 2]
            if "-b:a" in c2:
                j = c2.index("-b:a")
                del c2[j:j + 2]
            mv = c2.index("-movflags") if "-movflags" in c2 else len(c2)
            c2[mv:mv] = ["-c:a", "aac", "-b:a", p["audio_bitrate"]]
        return c2

    def _attempt(c: List[str], note: str | None = None) -> str:
        ff_run(c, capture_output=True)
        info("video_sanitize_done", out_path=str(out_p), **({"note": note} if note else {}))
        return str(out_p)

    try:
        return _attempt(cmd)
    except Exception as e:
        # (1) Audio copy hỏng → thử lại với AAC, giữ nguyên encoder video.
        if has_audio and p["copy_audio"]:
            warn("video_sanitize_retry_audio_aac", reason="audio_copy_failed", in_path=str(in_p))
            try:
                return _attempt(_to_aac(cmd), note="retried_aac")
            except Exception as e2:
                e = e2  # rơi tiếp xuống nhánh CPU bên dưới

        # (2) [GPU] NVENC hoặc NVDEC hỏng (card bận, driver TDR, codec NVDEC không đỡ
        #     như VP8) → dựng lại lệnh thuần CPU và chạy một lần nữa. Ở ĐÂY fallback
        #     CPU là ĐÚNG: sanitize là bước bắt buộc phải xong thì pipeline mới chạy
        #     tiếp, và output vẫn hợp lệ — chỉ chậm hơn. Khác với Whisper, nơi chạy
        #     CPU vừa chậm 20x vừa cho ra transcript khác (xem gpu_guard.py).
        if _use_gpu:
            _cleanup_corrupt_output()
            warn("video_sanitize_gpu_failed_retry_cpu",
                 in_path=str(in_p), error=str(e)[:300])
            cpu_cmd = _build_cmd(use_gpu=False)
            try:
                return _attempt(cpu_cmd, note="cpu_fallback")
            except Exception as e3:
                if has_audio and p["copy_audio"]:
                    try:
                        return _attempt(_to_aac(cpu_cmd), note="cpu_fallback_aac")
                    except Exception as e4:
                        e3 = e4
                _cleanup_corrupt_output()
                exc("video_sanitize_failed", e3)
                raise

        _cleanup_corrupt_output()
        exc("video_sanitize_failed", e)
        raise


def sanitize_folder(cfg: Dict, in_dir: str, out_dir: str) -> str:
    """
    Sanitize all supported video files under in_dir into out_dir.
    Preserves relative folder structure and filenames.

    Returns out_dir (for convenience).
    """
    p = _sanitize_params(cfg)
    if not p["enable"]:
        return in_dir

    in_root = Path(in_dir)
    out_root = Path(out_dir)
    ensure_dir(str(out_root))

    exts = set([("." + e.lower().lstrip(".")) for e in p["extensions"]])

    # collect files (folder contains many small files -> keep it efficient)
    files: List[Path] = []
    for ext in exts:
        files.extend(in_root.rglob(f"*{ext}"))
    files = sorted(set(files))

    if not files:
        warn("video_sanitize_no_files", in_dir=str(in_root))
        return in_dir

    # Consumer GPUs support 3-5 concurrent NVENC sessions; libx264 is CPU-bound.
    # Default 3 workers balances throughput vs resource contention.
    max_workers = int((cfg or {}).get("video_sanitize", {}).get("parallel_workers", 3))
    info("video_sanitize_folder_start", in_dir=str(in_root), out_dir=str(out_root),
         count=len(files), parallel_workers=max_workers)

    def _sanitize_one(fp: Path):
        rel = fp.relative_to(in_root)
        out_fp = out_root / rel
        if out_fp.suffix.lower() != ".mp4":
            out_fp = out_fp.with_suffix(".mp4")
        sanitize_video(cfg, str(fp), str(out_fp))
        return str(out_fp)

    # ── Parallel sanitization ──
    # [BUG-3 FIX] Trước đây fail âm thầm: file lỗi → fail_count++ rồi continue,
    # downstream stage (sequential_timeline) mới phát hiện "thiếu video" sau 30-60min.
    # Giờ collect chi tiết lỗi → raise ở cuối với danh sách file fail rõ ràng.
    done_count = 0
    failures: List[Dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_fp = {pool.submit(_sanitize_one, fp): fp for fp in files}
        for future in as_completed(future_to_fp):
            fp = future_to_fp[future]
            done_count += 1
            try:
                future.result()
            except Exception as e:
                exc("video_sanitize_one_failed", e)
                failures.append({"file": fp.name, "error": str(e)[:300]})
            if done_count % 10 == 0 or done_count == len(files):
                info("video_sanitize_progress", done=done_count,
                     total=len(files), failed=len(failures))

    if failures:
        # Structured event để _parse_engine_error_summary parse được
        info(
            "video_sanitize_folder_failed",
            total=len(files),
            ok=len(files) - len(failures),
            failed=len(failures),
            failed_files=[f["file"] for f in failures],
        )
        names = ", ".join(f["file"] for f in failures[:5])
        if len(failures) > 5:
            names += f" ... (+{len(failures) - 5} more)"
        raise RuntimeError(
            f"video_sanitize_folder: {len(failures)}/{len(files)} files failed. "
            f"Failed: [{names}]. First error: {failures[0]['error']}"
        )

    info("video_sanitize_folder_done", out_dir=str(out_root),
         total=len(files), failed=0)
    return str(out_root)


# Optional CLI helper for manual batch usage
if __name__ == "__main__":
    import argparse
    import json as _json

    ap = argparse.ArgumentParser(description="Sanitize AI videos for stable FFmpeg processing.")
    ap.add_argument("--in_dir", required=True, help="Input folder containing AI videos")
    ap.add_argument("--out_dir", required=True, help="Output folder for sanitized videos")
    ap.add_argument("--config", default=None, help="Optional JSON config file to load cfg dict (expects video_sanitize section).")

    args = ap.parse_args()
    _cfg: Dict = {}
    if args.config:
        try:
            _cfg = _json.loads(Path(args.config).read_text(encoding="utf-8"))
        except Exception:
            _cfg = {}
    sanitize_folder(_cfg, args.in_dir, args.out_dir)
