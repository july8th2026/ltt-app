"""Tiny deterministic media fixtures for Auto Scan Video (Phase 04).

## Why synthetic and not a real clip

A fixture built from customer or downloaded material carries copyright, PII and an
approval question into every future test run. `ffmpeg`'s `lavfi` sources carry none of
that, and they are **reproducible**: three separate invocations of `tiny_mp4()` on this
machine produced byte-identical files (measured in Phase 01, 42 982 bytes each).

That reproducibility is the point. Phase 08+ has to test a **fingerprint cache**
(ADR-001 D8), and a cache test needs an input whose identity does not drift.

## Why both streams

Auto Scan's first two stages are MEDIA_PREPARE and AUDIO_PREPARE, so a video-only
fixture would leave the second one untestable. `sine` also gives a known frequency, so
an audio stage has a property to assert rather than just a byte count.

⚠ Byte-level determinism is a property of *this* ffmpeg build (8.0.1 here). Assert on
  decoded properties — duration, dimensions, sample rate, stream count — not on a file
  hash, unless the test also pins the encoder version.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

#: Small enough to commit-free-generate in a fraction of a second, long enough that a
#: segmenter has something to segment.
DEFAULT_DURATION_S = 3.0
DEFAULT_SIZE = "320x240"
DEFAULT_FPS = 12
DEFAULT_TONE_HZ = 440


def ffmpeg_bin() -> str | None:
    """Path to ffmpeg, or None. Never raises — callers decide whether to skip."""
    from platform_core import media
    try:
        return media.ffmpeg_bin()
    except Exception:  # noqa: BLE001 - a missing binary is a skip, not an error
        return shutil.which("ffmpeg")


def require_ffmpeg() -> str:
    """ffmpeg path, or skip the test. Media fixtures are worthless without it."""
    binary = ffmpeg_bin()
    if not binary:
        pytest.skip("khong co ffmpeg de dung fixture media")
    return binary


def tiny_mp4(dest: Path, *, duration_s: float = DEFAULT_DURATION_S,
             size: str = DEFAULT_SIZE, fps: int = DEFAULT_FPS,
             tone_hz: int = DEFAULT_TONE_HZ) -> Path:
    """H.264 + AAC MP4 with one video and one audio stream. Deterministic."""
    binary = require_ffmpeg()
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [binary, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc=size={size}:rate={fps}:duration={duration_s}",
         "-f", "lavfi", "-i", f"sine=frequency={tone_hz}:duration={duration_s}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
         str(dest)],
        check=True, capture_output=True)
    return dest


def nap_nguon_vao_kho(kho, tmp_path: Path, *, owner_id: str = "uA",
                      im_lang: bool = False, **kw) -> str:
    """Build a fixture video, put it in storage, return its key.

    Every Auto Scan run needs a real source object from Phase 08 onward — before
    that, tests used a placeholder key because MEDIA_PREPARE was a dummy that
    never opened it. Now it probes, enforces policy and extracts audio, so a
    placeholder produces a failure that says nothing about the code under test.

    `im_lang=True` seeds a video with **no audio stream**, which is what
    `MVP_CONTRACT.md` §2 rejects at submit.
    """
    import io

    nguon = tmp_path / ("cam.mp4" if im_lang else "nguon.mp4")
    (tiny_mp4_silent(nguon, **kw) if im_lang else tiny_mp4(nguon, **kw))
    khoa = f"asv/{owner_id}/nguon/{nguon.name}"
    with open(nguon, "rb") as f:
        kho.put(khoa, io.BytesIO(f.read()), content_type="video/mp4")
    return khoa


def ban_ghi_gia(duration_s: float = DEFAULT_DURATION_S) -> dict:
    """A deterministic raw-engine transcript, shaped like `transcribe_file` returns.

    ## Why chain tests need this

    The video fixtures are `lavfi` tones — they contain **no speech**. Real ASR on
    them correctly returns zero segments, and TRANSCRIBE then correctly refuses the
    run: a video with nothing spoken has nothing to dub.

    That is the right product behaviour and the wrong test input for a chain test,
    which is about the execution spine rather than about recognition accuracy.

    Making the stage tolerate zero segments to keep a fixture working would weaken
    the product to suit the test. Substituting the engine does not.

    ⭐ Real ASR is smoke-tested separately against the real engine
      (`test_407…::test_engine_ASR_that_chay_duoc`). Measured on this machine:
      2 s of audio took 22.8 s with the `tiny` model on CPU — which is also why a
      chain test cannot call it.
    """
    n = max(1, int(duration_s))
    doan = []
    for i in range(n):
        bat, ket = float(i), float(i) + 0.8
        doan.append({
            "start": bat, "end": ket, "text": f"cau thu {i + 1}",
            "words": [{"start": bat, "end": bat + 0.4, "text": "cau"},
                      {"start": bat + 0.4, "end": ket, "text": f"thu-{i + 1}"}],
        })
    return {"segments": doan, "language": "vi", "engine": "gia",
            "alignment_status": "gia"}


def tiny_mp4_silent(dest: Path, *, duration_s: float = DEFAULT_DURATION_S) -> Path:
    """Video with NO audio stream.

    `MVP_CONTRACT.md` §2 rejects this at submit rather than at TRANSCRIBE — a silent
    video has nothing to localize, and finding that out three paid stages later is a
    refund. This fixture is how that rule gets tested.
    """
    binary = require_ffmpeg()
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [binary, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc=size={DEFAULT_SIZE}:rate={DEFAULT_FPS}"
         f":duration={duration_s}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest)],
        check=True, capture_output=True)
    return dest
