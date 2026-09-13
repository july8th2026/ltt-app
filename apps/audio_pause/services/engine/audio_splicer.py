from __future__ import annotations

import os
import struct
import subprocess
import wave
from pathlib import Path
from typing import Optional, List, Tuple

from .nhat_ky import info, debug, exc


_ffmpeg_ok: bool | None = None


# ======================================================
# Silence-snap: tìm điểm im lặng thực trong audio
# ======================================================

def _load_wav_samples(wav_path: str) -> Tuple[tuple, int]:
    """Load PCM 16-bit mono samples + sample rate. Cached per path."""
    wf = wave.open(wav_path, "rb")
    sr = wf.getframerate()
    nframes = wf.getnframes()
    raw = wf.readframes(nframes)
    wf.close()
    samples = struct.unpack("<" + str(nframes) + "h", raw)
    return samples, sr


def _rms_window(samples: tuple, sr: int, center_sec: float,
                window_sec: float = 0.020) -> float:
    """RMS energy of a small window centered at center_sec."""
    half = int(window_sec * sr) // 2
    center_idx = int(center_sec * sr)
    s = max(0, center_idx - half)
    e = min(len(samples), center_idx + half)
    if e <= s:
        return 0.0
    chunk = samples[s:e]
    return (sum(x * x for x in chunk) / len(chunk)) ** 0.5


def find_silence_point(
    wav_path: str,
    at_sec: float,
    word_before_end: float,
    word_after_start: Optional[float] = None,
    search_margin: float = 0.05,
    step_sec: float = 0.005,
    window_sec: float = 0.020,
    _samples: Optional[tuple] = None,
    _sr: Optional[int] = None,
) -> float:
    """
    Tìm điểm im lặng thực (RMS thấp nhất) SAU word_before.

    Vùng tìm kiếm:
      start = word_before_end          (bắt đầu ngay SAU từ cuối)
      end   = word_after_start + margin (nếu có) hoặc word_before_end + 0.5s

    QUAN TRỌNG: chỉ tìm PHÍA SAU word_before, không tìm trước.

    Args:
        wav_path: đường dẫn file WAV
        at_sec: vị trí sơ bộ từ Whisper (dùng làm fallback)
        word_before_end: thời điểm kết thúc từ cuối TRƯỚC pause
        word_after_start: thời điểm bắt đầu từ đầu SAU pause (None nếu cuối file)
        search_margin: mở rộng vùng tìm thêm sau word_after_start
        step_sec: bước scan (5ms)
        window_sec: cửa sổ tính RMS (20ms)
        _samples/_sr: pre-loaded samples để tránh đọc WAV nhiều lần

    Returns:
        at_sec đã snap vào điểm im lặng thực
    """
    if _samples is not None and _sr is not None:
        samples, sr = _samples, _sr
    else:
        samples, sr = _load_wav_samples(wav_path)

    audio_duration = len(samples) / sr

    # Vùng tìm: chỉ SAU word_before_end
    search_start = word_before_end
    if word_after_start is not None:
        gap = word_after_start - word_before_end
        if gap < 0.10:
            # Whisper báo gap quá nhỏ hoặc 0 → mở rộng tìm kiếm thêm 0.3s
            # vì Whisper timestamps thường sớm hơn thực tế 100-200ms
            search_end = min(word_after_start + 0.30, audio_duration)
        else:
            search_end = min(word_after_start + search_margin, audio_duration)
    else:
        # Cuối file: tìm thêm 0.5s sau word_before_end
        search_end = min(word_before_end + 0.5, audio_duration)

    # Đảm bảo vùng tìm hợp lệ
    if search_end <= search_start:
        search_end = min(search_start + 0.2, audio_duration)

    best_t = at_sec
    best_rms = float("inf")

    t = search_start
    while t <= search_end:
        rms = _rms_window(samples, sr, t, window_sec)
        if rms < best_rms:
            best_rms = rms
            best_t = t
        t += step_sec

    debug("silence_snap",
          original=round(at_sec, 3),
          snapped=round(best_t, 3),
          shift=round(best_t - at_sec, 3),
          rms=round(best_rms, 1),
          search_range=f"{round(search_start, 3)}-{round(search_end, 3)}")

    return round(best_t, 4)


def snap_all_cut_points(
    wav_path: str,
    insertion_plan: list,
    matched_anchors: list,
) -> list:
    """
    Snap tất cả at_sec trong insertion_plan vào điểm im lặng thực.

    Args:
        wav_path: file WAV gốc
        insertion_plan: danh sách {at_sec, pause_ms, id}
        matched_anchors: danh sách matched từ anchor_map (chứa word_before/word_after)

    Returns:
        insertion_plan đã cập nhật at_sec (và thêm _original_at_sec để debug)
    """
    # Load WAV 1 lần duy nhất
    samples, sr = _load_wav_samples(wav_path)

    # Lookup matched by id
    matched_by_id = {m.get("id"): m for m in matched_anchors}

    snapped_count = 0
    for p in insertion_plan:
        pid = p.get("id")
        m = matched_by_id.get(pid, {})
        wb = m.get("word_before")
        wa = m.get("word_after")

        if not wb:
            # Không có word context → giữ nguyên
            continue

        word_before_end = wb["end"]
        word_after_start = wa["start"] if wa else None

        original = p["at_sec"]
        p["at_sec"] = find_silence_point(
            wav_path,
            at_sec=original,
            word_before_end=word_before_end,
            word_after_start=word_after_start,
            _samples=samples,
            _sr=sr,
        )
        p["_original_at_sec"] = original

        if abs(p["at_sec"] - original) > 0.001:
            snapped_count += 1

    if snapped_count:
        info("silence_snap_summary",
             total=len(insertion_plan),
             snapped=snapped_count)

    return insertion_plan


def check_ffmpeg() -> bool:
    """Check if FFmpeg is installed (cached after first call)."""
    global _ffmpeg_ok
    if _ffmpeg_ok is not None:
        return _ffmpeg_ok
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        _ffmpeg_ok = result.returncode == 0
    except Exception:
        _ffmpeg_ok = False
    return _ffmpeg_ok


def convert_to_wav(
    input_path: str,
    output_path: str,
    sample_rate: int = 24000,
    channels: int = 1,
) -> str:
    """
    Convert audio to WAV format (mono, specific sample rate).
    
    Args:
        input_path: Input audio file (MP3, etc.)
        output_path: Output WAV file path
        sample_rate: Target sample rate (Hz)
        channels: Number of channels (1=mono, 2=stereo)
    
    Returns:
        Path to output WAV file
    """
    
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-c:a", "pcm_s16le",  # Force consistent codec for all pipeline stages
        "-y",  # Overwrite
        output_path,
    ]
    
    debug("ffmpeg_convert_start", input=input_path, output=output_path)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes max
        )
        
        if result.returncode != 0:
            exc("ffmpeg_convert_stderr", RuntimeError(result.stderr[:2000]))
            raise RuntimeError(f"FFmpeg convert failed (rc={result.returncode}): {result.stderr[:500]}")

        size_mb = os.path.getsize(output_path) / 1024 / 1024
        info("ffmpeg_convert_done", output=output_path, size_mb=round(size_mb, 2))
        
        return output_path
    
    except Exception as e:
        exc("ffmpeg_convert_error", e)
        raise


def cut_audio_segment(
    input_path: str,
    output_path: str,
    start_sec: float,
    end_sec: Optional[float] = None,
    fade_ms: int = 10,
) -> str:
    """
    Cut audio segment from input file with optional fade at boundaries.

    Args:
        input_path: Input audio file
        output_path: Output segment file
        start_sec: Start time in seconds
        end_sec: End time in seconds (None = until end)
        fade_ms: Fade-in/fade-out duration in ms at boundaries (0 to disable)

    Returns:
        Path to output segment
    """

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # -ss BEFORE -i = input seeking: filters apply relative to the seek point,
    # not the start of the full file. This prevents afade from silencing audio
    # when start_sec exceeds the fade-out position.
    cmd = [
        "ffmpeg",
        "-ss", str(start_sec),
        "-i", input_path,
    ]

    duration = None
    if end_sec is not None:
        duration = end_sec - start_sec
        cmd.extend(["-t", str(duration)])

    # Apply short fade-in/out to prevent clicks at splice boundaries
    if fade_ms > 0 and duration is not None and duration > fade_ms / 500.0:
        fade_s = fade_ms / 1000.0
        fade_out_start = max(0, duration - fade_s)
        cmd.extend(["-af", f"afade=t=in:d={fade_s},afade=t=out:st={fade_out_start}:d={fade_s}"])

    # Re-encode with PCM for sample-accurate cuts
    cmd.extend(["-c:a", "pcm_s16le", "-y", output_path])

    debug("ffmpeg_cut_segment", start=round(start_sec, 2), end=round(end_sec, 2) if end_sec else "EOF")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg cut failed: {result.stderr}")

        return output_path

    except Exception as e:
        exc("ffmpeg_cut_error", e)
        raise


def generate_silence(
    output_path: str,
    duration_ms: int,
    sample_rate: int = 24000,
    channels: int = 1,
) -> str:
    """
    Generate silence audio file.

    Args:
        output_path: Output silence file path
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate (Hz)
        channels: Number of audio channels (1=mono, 2=stereo)

    Returns:
        Path to silence file
    """

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    duration_sec = duration_ms / 1000.0
    cl = "mono" if channels <= 1 else "stereo"

    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"anullsrc=r={sample_rate}:cl={cl}",
        "-t", str(duration_sec),
        "-c:a", "pcm_s16le",
        "-y",
        output_path,
    ]
    
    debug("ffmpeg_gen_silence", duration_ms=duration_ms, output=output_path)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg silence generation failed: {result.stderr}")
        
        return output_path
    
    except Exception as e:
        exc("ffmpeg_silence_error", e)
        raise


def concat_audio_files(
    file_list: list[str],
    output_path: str,
) -> str:
    """
    Concatenate audio files using FFmpeg concat demuxer.
    
    Args:
        file_list: List of audio file paths (in order)
        output_path: Output concatenated file
    
    Returns:
        Path to output file
    """
    
    if not file_list:
        raise ValueError("No files to concatenate")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Create concat list file
    concat_list_path = str(Path(output_path).parent / "concat_list.txt")
    
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for fpath in file_list:
            # Use absolute path with forward slashes (FFmpeg compatible on all OS)
            abs_path = os.path.abspath(fpath).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{abs_path}'\n")
    
    debug("ffmpeg_concat_list", files=len(file_list), list_path=concat_list_path)
    
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        "-y",
        output_path,
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")
        
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        info("ffmpeg_concat_done", output=output_path, files=len(file_list), size_mb=round(size_mb, 2))
        
        # Cleanup concat list
        os.remove(concat_list_path)
        
        return output_path
    
    except Exception as e:
        exc("ffmpeg_concat_error", e)
        raise


def encode_to_mp3(
    input_path: str,
    output_path: str,
    bitrate: str = "128k",
) -> str:
    """
    Encode audio to MP3 format.
    
    Args:
        input_path: Input audio file (WAV, etc.)
        output_path: Output MP3 file
        bitrate: MP3 bitrate (e.g., "128k", "192k")
    
    Returns:
        Path to output MP3
    """
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-b:a", bitrate,
        "-y",
        output_path,
    ]
    
    debug("ffmpeg_encode_mp3", bitrate=bitrate)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg MP3 encoding failed: {result.stderr}")
        
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        info("ffmpeg_mp3_done", output=output_path, size_mb=round(size_mb, 2))
        
        return output_path
    
    except Exception as e:
        exc("ffmpeg_mp3_error", e)
        raise
