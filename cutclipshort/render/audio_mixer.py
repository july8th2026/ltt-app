"""Audio processing pipeline.

Handles: extract → demucs separate → stem mix → loudnorm.
Ported from NerfWarAI's audio.py patterns.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cutclipshort.types import AudioConfig

logger = logging.getLogger(__name__)


def process_audio(
    source_path: Path,
    output_path: Path,
    audio_config: AudioConfig,
    start_time: float | None = None,
    duration: float | None = None,
) -> Path:
    """Full audio processing pipeline for a clip.

    Steps:
    1. Extract audio segment from source
    2. Demucs separation (if enabled)
    3. Stem mixing (if demucs ran)
    4. Loudnorm to target LUFS
    """
    from cutclipshort.adapters.ffmpeg import FFmpegAdapter

    ffmpeg = FFmpegAdapter()
    work_dir = output_path.parent
    work_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract audio segment
    extracted = work_dir / "_extracted.wav"
    ffmpeg.extract_audio(
        source_path, extracted,
        start_time=start_time, duration=duration,
    )

    current_audio = extracted

    # Step 2: Demucs separation (if enabled)
    if audio_config.demucs_enabled:
        current_audio = _run_demucs(current_audio, work_dir, audio_config)

    # Step 3: Loudnorm — [Phase2] 2-pass for better quality
    if audio_config.loudnorm_enabled:
        normed = work_dir / "_normed.wav"
        lufs = audio_config.loudnorm_lufs
        tp = audio_config.loudnorm_true_peak_db
        current_audio = _loudnorm_2pass(
            ffmpeg, current_audio, normed, lufs, tp,
        )

    # Copy to final output
    if current_audio != output_path:
        import shutil
        shutil.copy2(current_audio, output_path)

    logger.info("Audio processed: %s", output_path.name)
    return output_path


def _loudnorm_2pass(
    ffmpeg,
    input_path: Path,
    output_path: Path,
    target_lufs: float,
    true_peak_db: float,
) -> Path:
    """
    [Phase2] 2-pass loudnorm de tranh clipping.

    Pass 1: Do measured_I, measured_TP, measured_LRA, measured_thresh
    Pass 2: Apply loudnorm voi measured values -> chinh xac hon
    Fallback: 1-pass neu parse fail
    """
    import subprocess
    import json
    import re

    lra = 11  # Target loudness range

    # ── Pass 1: Measure ──
    af_measure = f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA={lra}:print_format=json"
    try:
        cmd = [
            ffmpeg.executable, "-i", str(input_path),
            "-af", af_measure,
            "-f", "null", "-"
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
        )
        stderr = result.stderr or ""

        # Parse JSON block from stderr
        json_match = re.search(r'\{[^{}]*"input_i"[^{}]*\}', stderr, re.DOTALL)
        if json_match:
            measured = json.loads(json_match.group())
            m_i = measured.get("input_i", "-24.0")
            m_tp = measured.get("input_tp", "-1.0")
            m_lra = measured.get("input_lra", "7.0")
            m_thresh = measured.get("input_thresh", "-34.0")

            logger.info(
                "Loudnorm pass 1: I=%s TP=%s LRA=%s thresh=%s",
                m_i, m_tp, m_lra, m_thresh,
            )

            # ── Pass 2: Apply with measured values ──
            af_apply = (
                f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA={lra}"
                f":measured_I={m_i}:measured_TP={m_tp}"
                f":measured_LRA={m_lra}:measured_thresh={m_thresh}"
                f":linear=true"
            )
            ffmpeg.encode(
                input_path=input_path,
                output_path=output_path,
                video_filters="",
                audio_filters=af_apply,
                codec="pcm_s16le" if output_path.suffix == ".wav" else "aac",
                crf="0",
                preset="medium",
                extra_args=["-vn"],
            )
            logger.info("Loudnorm 2-pass complete: %s", output_path.name)
            return output_path
        else:
            logger.warning("Loudnorm pass 1: cannot parse measured values, fallback to 1-pass")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        logger.warning("Loudnorm 2-pass failed (%s), fallback to 1-pass", e)

    # ── Fallback: 1-pass ──
    af_single = f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA={lra}"
    ffmpeg.encode(
        input_path=input_path,
        output_path=output_path,
        video_filters="",
        audio_filters=af_single,
        codec="pcm_s16le" if output_path.suffix == ".wav" else "aac",
        crf="0",
        preset="medium",
        extra_args=["-vn"],
    )
    return output_path


def _run_demucs(
    audio_path: Path,
    work_dir: Path,
    config: AudioConfig,
) -> Path:
    """Run demucs and mix stems according to gains."""
    from cutclipshort.adapters.demucs import DemucsAdapter

    demucs = DemucsAdapter()
    if not demucs.check_available():
        logger.warning("Demucs not available, skipping separation")
        return audio_path

    try:
        stems = demucs.separate(audio_path, work_dir / "demucs_out", model=config.demucs_model)
    except Exception as e:
        logger.warning("Demucs failed, using original audio: %s", e)
        return audio_path

    # Mix stems according to gains
    from cutclipshort.adapters.ffmpeg import FFmpegAdapter
    ffmpeg = FFmpegAdapter()

    inputs_and_gains: list[tuple[Path, float]] = []
    for stem_name, gain in config.stem_gains.items():
        stem_path = getattr(stems, stem_name, None)
        if stem_path and stem_path.exists() and gain > 0:
            inputs_and_gains.append((stem_path, gain))

    if not inputs_and_gains:
        return audio_path

    if len(inputs_and_gains) == 1:
        return inputs_and_gains[0][0]

    # Use FFmpeg amix to combine stems
    mixed = work_dir / "_mixed_stems.wav"
    args = [ffmpeg.executable, "-y"]
    for path, _ in inputs_and_gains:
        args += ["-i", str(path)]

    filter_parts = []
    for idx, (_, gain) in enumerate(inputs_and_gains):
        filter_parts.append(f"[{idx}]volume={gain}[s{idx}]")

    mix_inputs = "".join(f"[s{i}]" for i in range(len(inputs_and_gains)))
    filter_parts.append(
        f"{mix_inputs}amix=inputs={len(inputs_and_gains)}:normalize=0[out]"
    )

    args += ["-filter_complex", ";".join(filter_parts)]
    args += ["-map", "[out]", str(mixed)]

    ffmpeg._run_command(args)
    return mixed
