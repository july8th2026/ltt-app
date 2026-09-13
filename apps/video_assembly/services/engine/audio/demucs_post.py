from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

from ...tuong_thich.log import info


def _run(cmd: list[str], timeout: float = 1800) -> str:
    # Run a command and return combined stdout/stderr; raise with output on failure.
    # [Phase 7] timeout=1800s (30 phút) — Demucs 87 segments cần ~20min trên CUDA;
    # ffmpeg extract/mux audio < 1min. > 30 phút = chắc chắn hang.
    try:
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"Demucs/FFmpeg timeout ({timeout:.0f}s):\n" + " ".join(cmd[:6]) + "..."
        ) from e
    if p.returncode != 0:
        raise RuntimeError("CMD FAIL:\n" + " ".join(cmd) + "\n\n" + (p.stdout or ""))
    return p.stdout or ""


def make_base_video_novocals(cfg: Dict[str, Any], base_video: str, out_video: str) -> str:
    # Post-process AFTER assemble step:
    # base_video.mp4 -> extract audio -> demucs -> no_vocals.wav -> mux back -> out_video
    # Does NOT change gain/loudness; it only replaces base video audio with no_vocals stem.
    base_video_p = Path(base_video)
    out_video_p = Path(out_video)
    out_video_p.parent.mkdir(parents=True, exist_ok=True)

    dcfg = (cfg or {}).get("demucs", {}) or {}
    model = dcfg.get("model", "htdemucs")
    device = dcfg.get("device", "cuda")
    two_stems = bool(dcfg.get("two_stems", True))

    tmp_dir = out_video_p.parent / "tmp_demucs"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    info("demucs_post_start", base_video=str(base_video_p), model=model, device=device, two_stems=two_stems)

    # 1) Extract audio for Demucs
    wav_in = tmp_dir / "base_audio.wav"
    _run([
        "ffmpeg", "-y",
        "-i", str(base_video_p),
        "-vn",
        "-ac", "2",
        "-ar", "44100",
        "-acodec", "pcm_s16le",
        str(wav_in)
    ])

    # 2) Run Demucs CLI
    demucs_out = tmp_dir / "demucs_out"
    demucs_out.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "demucs", "-n", str(model), "--device", str(device), "-o", str(demucs_out)]
    if two_stems:
        cmd += ["--two-stems", "vocals"]
    cmd.append(str(wav_in))
    _run(cmd)

    # 3) Find no_vocals.wav
    track_dir = demucs_out / str(model) / wav_in.stem
    no_vocals = track_dir / "no_vocals.wav"
    if not no_vocals.exists():
        cands = list(demucs_out.rglob("no_vocals.wav"))
        if cands:
            no_vocals = cands[0]
        else:
            raise RuntimeError(f"Demucs output no_vocals.wav not found under: {demucs_out}")

    info("demucs_post_stem_ready", no_vocals=str(no_vocals))

    # 4) Mux no_vocals back into base video (copy video, encode audio)
    _run([
        "ffmpeg", "-y",
        "-i", str(base_video_p),
        "-i", str(no_vocals),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-ar", "48000",
        "-ac", "2",
        str(out_video_p)
    ])

    info("demucs_post_done", out=str(out_video_p))
    return str(out_video_p)
