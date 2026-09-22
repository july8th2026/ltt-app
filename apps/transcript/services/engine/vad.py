from __future__ import annotations

import os
import tempfile
import subprocess
import wave
import math
from array import array
from typing import Dict, List, Tuple

from platform_core import media as _media


# ===============================
# Simple VAD (energy-based, ffmpeg-assisted) - OPTIMIZED
# - Faster PCM decode (array('h'))
# - More accurate duration from WAV frames/sr
# ===============================

def _ffmpeg_to_wav16k_mono(src_audio: str, out_wav: str) -> None:
    cmd = [
        # 22/09/2026: ban legacy goi "ffmpeg" TRAN; dich vu worker khong co ffmpeg
        # tren PATH => WinError 2 ngay buoc VAD. Tim nhi phan nhu ca nen tang
        # (LTT_FFMPEG -> PATH -> thu muc cai pho bien).
        _media.ffmpeg_bin(), "-y",
        "-i", src_audio,
        "-ac", "1",
        "-ar", "16000",
        "-vn",
        out_wav,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def _read_pcm16(wav_path: str) -> Tuple[array, int, int]:
    """
    Return (samples_int16_array, sample_rate, nframes)
    Uses array('h') for fast decoding.
    """
    with wave.open(wav_path, "rb") as wf:
        nchan = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sr = wf.getframerate()
        nframes = wf.getnframes()

        if nchan != 1:
            raise RuntimeError(f"Expected mono wav, got {nchan} channels")
        if sampwidth != 2:
            raise RuntimeError(f"Expected 16-bit PCM wav, got sampwidth={sampwidth}")

        raw = wf.readframes(nframes)

    a = array("h")
    a.frombytes(raw)

    # On big-endian systems need byteswap; Windows is little-endian, but keep safe:
    if a.itemsize == 2 and a.typecode == "h":
        # array('h') uses native endianness; WAV is little-endian
        # If platform is big-endian, swap.
        import sys
        if sys.byteorder != "little":
            a.byteswap()

    return a, sr, nframes


def _rms_dbfs_int16(samples: array) -> float:
    if not samples:
        return -120.0
    acc = 0.0
    for s in samples:
        acc += float(s) * float(s)
    rms = math.sqrt(acc / max(1.0, float(len(samples))))
    if rms <= 1e-9:
        return -120.0
    db = 20.0 * math.log10(rms / 32768.0)
    return max(-120.0, min(0.0, db))


def _percentile(vals: List[float], q: float) -> float:
    if not vals:
        return -120.0
    v = sorted(vals)
    idx = int(max(0, min(len(v) - 1, round((len(v) - 1) * q))))
    return v[idx]


def vad_speech_segments(
    audio_path: str,
    *,
    frame_ms: int = 30,
    min_speech_s: float = 0.3,
    min_silence_s: float = 0.8,
    pad_s: float = 0.15,
    thr_db_above_noise: float = 12.0,
) -> List[Dict[str, float]]:
    """
    Return speech segments as [{start,end}, ...] in seconds.
    Energy-based VAD with adaptive threshold.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(audio_path)

    if frame_ms <= 0:
        frame_ms = 30

    with tempfile.TemporaryDirectory(prefix="vad_") as td:
        wav_path = os.path.join(td, "tmp.wav")
        _ffmpeg_to_wav16k_mono(audio_path, wav_path)
        pcm, sr, nframes = _read_pcm16(wav_path)

    if sr <= 0:
        return []

    hop = int(sr * (frame_ms / 1000.0))
    hop = max(1, hop)

    # Compute per-frame dBFS
    dbs: List[float] = []
    # Slice array('h') cheaply (still copies, but much faster overall than int list)
    for i in range(0, len(pcm), hop):
        frame = pcm[i:i + hop]
        dbs.append(_rms_dbfs_int16(frame))

    if not dbs:
        return []

    # Estimate noise floor at 20th percentile
    noise = _percentile(dbs, 0.2)
    thr = noise + float(thr_db_above_noise)

    voiced = [db > thr for db in dbs]

    # Fill short unvoiced holes (hangover)
    min_sil_frames = int((min_silence_s * 1000.0) / frame_ms)
    if min_sil_frames < 1:
        min_sil_frames = 1

    i = 0
    while i < len(voiced):
        if voiced[i]:
            i += 1
            continue
        j = i
        while j < len(voiced) and not voiced[j]:
            j += 1
        gap = j - i
        if gap < min_sil_frames:
            for k in range(i, j):
                voiced[k] = True
        i = j

    # Extract contiguous voiced runs
    runs: List[Tuple[int, int]] = []
    i = 0
    while i < len(voiced):
        if not voiced[i]:
            i += 1
            continue
        j = i
        while j < len(voiced) and voiced[j]:
            j += 1
        runs.append((i, j))
        i = j

    min_speech_frames = int((min_speech_s * 1000.0) / frame_ms)
    if min_speech_frames < 1:
        min_speech_frames = 1

    # Accurate duration from decoded WAV frames
    total_dur = float(nframes) / float(sr)

    out: List[Dict[str, float]] = []
    for a, b in runs:
        if (b - a) < min_speech_frames:
            continue
        st = (a * frame_ms) / 1000.0
        en = (b * frame_ms) / 1000.0
        st = max(0.0, st - float(pad_s))
        en = min(total_dur, en + float(pad_s))
        if en > st + 1e-6:
            out.append({"start": st, "end": en})

    # Merge overlaps
    out.sort(key=lambda x: (x["start"], x["end"]))
    merged: List[Dict[str, float]] = []
    for s in out:
        if not merged:
            merged.append(dict(s))
            continue
        if s["start"] <= merged[-1]["end"] + 1e-6:
            merged[-1]["end"] = max(merged[-1]["end"], s["end"])
        else:
            merged.append(dict(s))
    return merged


def audio_duration_seconds(audio_path: str) -> float:
    """
    Get duration using ffprobe if available, else decode to wav and compute frames/sr.
    """
    try:
        cmd = [
            _media.ffprobe_bin(), "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        val = float((p.stdout or "").strip())
        if val > 0:
            return val
    except Exception:
        pass

    with tempfile.TemporaryDirectory(prefix="dur_") as td:
        wav_path = os.path.join(td, "tmp.wav")
        _ffmpeg_to_wav16k_mono(audio_path, wav_path)
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            sr = wf.getframerate()
        if sr <= 0:
            return 0.0
        return float(frames) / float(sr)
