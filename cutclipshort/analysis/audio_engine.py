"""Audio analysis engine v2.

Computes energy envelope, silence detection, loudness metrics,
spectral analysis, and voice activity detection.

v2 changes:
- Fixed avg_db bug (was hardcoded -60.0, now computed from actual RMS)
- Added 24/32-bit audio support (converts via struct)
- Added spectral centroid for voice/music discrimination
- Added adaptive silence threshold based on noise floor
- Added voice activity detection (VAD) via energy + spectral features
- Config-driven parameters (silence_threshold, window_sec)
"""

from __future__ import annotations

import logging
import math
import struct
import wave
from pathlib import Path
from typing import Any, Callable

from cutclipshort.analysis.base import BaseAnalysisEngine
from cutclipshort.types import SourceAsset

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
_DEFAULT_SILENCE_THRESHOLD = 0.01
_DEFAULT_WINDOW_SEC = 0.5
_MIN_SILENCE_DURATION = 0.5
_NOISE_FLOOR_PERCENTILE = 0.10  # bottom 10% of energy = noise floor
_VAD_ENERGY_RATIO = 3.0  # energy must be 3x noise floor for speech
_SPECTRAL_VOICE_LOW = 85.0  # Hz — lower bound of voice fundamental
_SPECTRAL_VOICE_HIGH = 3500.0  # Hz — upper bound of voice + harmonics


class AudioEngine(BaseAnalysisEngine):
    """Audio energy, silence, spectral, and VAD analysis."""

    @property
    def name(self) -> str:
        """Return engine identifier."""
        return "audio"

    @property
    def version(self) -> str:
        """Return engine semantic version."""
        return "2.0.0"

    def _relevant_config_keys(self, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "silence_threshold": config.get("silence_threshold", _DEFAULT_SILENCE_THRESHOLD),
            "window_sec": config.get("audio_window_sec", _DEFAULT_WINDOW_SEC),
        }

    def run(
        self,
        source: Path,
        media_info: SourceAsset,
        config: dict[str, Any],
        cache_dir: Path,
        progress_callback: Callable[[float], None],
    ) -> dict[str, Any]:
        """Run audio analysis and return energy, silence, spectral, and loudness data."""
        cached = self.load_cached(cache_dir)
        if cached is not None:
            return cached

        progress_callback(0.0)

        # Extract audio to 16-bit 16kHz mono WAV for analysis
        wav_path = cache_dir / "_audio_analysis.wav"
        if not wav_path.exists():
            try:
                from cutclipshort.adapters.ffmpeg import FFmpegAdapter
                ffmpeg = FFmpegAdapter()
                cache_dir.mkdir(parents=True, exist_ok=True)
                # Force 16-bit PCM output — handles 24/32-bit sources automatically
                ffmpeg.extract_audio(
                    source, wav_path,
                    sample_rate=16000, channels=1,
                )
            except Exception as e:
                raise RuntimeError(
                    f"Không thể trích xuất audio: {e}. "
                    f"Kiểm tra FFmpeg đã cài và video có track audio."
                ) from e

        progress_callback(0.3)

        window_sec = config.get("audio_window_sec", _DEFAULT_WINDOW_SEC)
        silence_threshold = config.get("silence_threshold", _DEFAULT_SILENCE_THRESHOLD)

        energy_curve, silence_ranges, spectral_data, loudness_stats = (
            self._analyze_wav(wav_path, window_sec, silence_threshold, progress_callback)
        )

        result: dict[str, Any] = {
            "energy_curve": energy_curve,
            "silence_ranges": silence_ranges,
            "spectral_curve": spectral_data,
            "loudness_stats": loudness_stats,
            "sample_rate": 16000,
            "window_sec": window_sec,
        }

        self._save_cache(cache_dir, result)
        progress_callback(1.0)

        logger.info(
            "Audio analysis: %d energy points, %d silence ranges, "
            "noise_floor=%.4f, avg_rms_db=%.1f",
            len(energy_curve), len(silence_ranges),
            loudness_stats.get("noise_floor", 0),
            loudness_stats.get("avg_rms_db", -60),
        )
        return result

    def _analyze_wav(
        self,
        wav_path: Path,
        window_sec: float,
        silence_threshold: float,
        progress_callback: Callable[[float], None],
    ) -> tuple[
        list[dict[str, float]],
        list[dict[str, Any]],
        list[dict[str, float]],
        dict[str, Any],
    ]:
        """Analyze WAV file for energy, silence, spectral features, and loudness.

        Returns:
            (energy_curve, silence_ranges, spectral_curve, loudness_stats)
        """
        energy_curve: list[dict[str, float]] = []
        spectral_curve: list[dict[str, float]] = []
        all_energies: list[float] = []

        try:
            with wave.open(str(wav_path), "rb") as wf:
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                sample_width = wf.getsampwidth()

                window_frames = int(sr * window_sec)
                total_windows = max(1, n_frames // window_frames)

                for i in range(total_windows):
                    raw = wf.readframes(window_frames)
                    if not raw:
                        break

                    samples = _decode_samples(raw, sample_width)
                    if samples is None:
                        time_sec = round(i * window_sec, 3)
                        energy_curve.append({"time_sec": time_sec, "energy": 0.0})
                        spectral_curve.append({
                            "time_sec": time_sec,
                            "spectral_centroid": 0.0,
                            "is_voice_band": False,
                        })
                        continue

                    peak = _peak_for_width(sample_width)

                    # RMS energy normalized to 0.0-1.0
                    rms, energy = _compute_rms_energy(samples, peak)

                    # Compute actual dB from RMS
                    rms_db = _rms_to_db(rms, peak)

                    time_sec = round(i * window_sec, 3)
                    energy_curve.append({
                        "time_sec": time_sec,
                        "energy": round(energy, 4),
                        "rms_db": round(rms_db, 1),
                    })
                    all_energies.append(energy)

                    # Spectral centroid (lightweight frequency analysis)
                    centroid, is_voice = _spectral_centroid(samples, sr)
                    spectral_curve.append({
                        "time_sec": time_sec,
                        "spectral_centroid": round(centroid, 1),
                        "is_voice_band": is_voice,
                    })

                    if i % 100 == 0:
                        progress_callback(0.3 + 0.55 * (i / total_windows))

        except wave.Error as e:
            raise RuntimeError(
                f"Phân tích audio WAV thất bại: {e}. "
                f"File audio có thể bị hỏng hoặc định dạng không hỗ trợ."
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Lỗi khi phân tích audio: {e}"
            ) from e

        # Compute adaptive noise floor and silence ranges
        noise_floor = _compute_noise_floor(all_energies)
        adaptive_threshold = max(silence_threshold, noise_floor * _VAD_ENERGY_RATIO)

        silence_ranges = _detect_silence_ranges(
            energy_curve, adaptive_threshold, window_sec,
        )

        # Loudness statistics
        loudness_stats = _compute_loudness_stats(all_energies, energy_curve, noise_floor)

        progress_callback(0.90)

        return energy_curve, silence_ranges, spectral_curve, loudness_stats


# ══════════════════════════════════════════════════════════════════════════
# PURE HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════

def _decode_samples(
    raw: bytes, sample_width: int,
) -> tuple[int, ...] | None:
    """Decode raw WAV bytes to integer samples.

    Supports 8-bit, 16-bit, 24-bit, and 32-bit PCM.
    Returns None only if format is unrecognized.
    """
    if sample_width == 2:
        n_samples = len(raw) // 2
        if n_samples == 0:
            return None
        return struct.unpack(f"<{n_samples}h", raw)

    if sample_width == 1:
        # 8-bit unsigned: center at 128
        return tuple(b - 128 for b in raw)

    if sample_width == 3:
        # 24-bit signed little-endian → convert to 32-bit range
        samples = []
        for j in range(0, len(raw) - 2, 3):
            # Unpack 3 bytes as little-endian signed 24-bit
            val = raw[j] | (raw[j + 1] << 8) | (raw[j + 2] << 16)
            if val >= 0x800000:
                val -= 0x1000000
            # Scale to 16-bit range for consistency
            samples.append(val >> 8)
        return tuple(samples) if samples else None

    if sample_width == 4:
        # 32-bit signed
        n_samples = len(raw) // 4
        if n_samples == 0:
            return None
        int32_samples = struct.unpack(f"<{n_samples}i", raw)
        # Scale to 16-bit range for consistency
        return tuple(s >> 16 for s in int32_samples)

    return None


def _peak_for_width(sample_width: int) -> float:
    """Return the peak value for normalization based on sample width."""
    if sample_width == 1:
        return 128.0
    # After our decoding, 24/32-bit are scaled to 16-bit range
    return 32768.0


def _compute_rms_energy(
    samples: tuple[int, ...], peak: float,
) -> tuple[float, float]:
    """Compute RMS and normalized energy (0.0-1.0).

    Returns: (raw_rms, normalized_energy)
    """
    if not samples:
        return 0.0, 0.0
    sum_sq = sum(s * s for s in samples)
    rms = (sum_sq / len(samples)) ** 0.5
    energy = min(1.0, rms / peak)
    return rms, energy


def _rms_to_db(rms: float, peak: float) -> float:
    """Convert RMS value to dBFS (decibels relative to full scale).

    Returns value in range [-96, 0]. Silence returns -96.0.
    """
    if rms <= 0 or peak <= 0:
        return -96.0
    ratio = rms / peak
    if ratio < 1e-5:
        return -96.0
    return max(-96.0, 20.0 * math.log10(ratio))


def _spectral_centroid(
    samples: tuple[int, ...], sample_rate: int,
) -> tuple[float, bool]:
    """Compute spectral centroid using DFT magnitude spectrum.

    Returns: (centroid_hz, is_in_voice_band)
    """
    n = len(samples)
    if n < 64:
        return 0.0, False

    # Use a subset for performance (max 2048 samples)
    if n > 2048:
        step = n // 2048
        subset = samples[::step][:2048]
    else:
        subset = samples

    n_sub = len(subset)

    # Simple DFT magnitude via real-valued FFT approximation
    # We compute power spectrum using Goertzel-like approach for key bands
    # For efficiency, bin into frequency bands rather than full FFT
    half = n_sub // 2
    freq_resolution = sample_rate / n_sub

    # Compute magnitude at 32 evenly-spaced frequency bins (not all bins)
    # This reduces O(n*bins) from ~1024 bins to 32 bins = 30x speedup
    _NUM_BINS = 32
    magnitudes: list[float] = []
    freqs: list[float] = []
    max_freq = sample_rate / 2
    for bin_idx in range(_NUM_BINS):
        freq = (bin_idx + 1) * max_freq / _NUM_BINS
        k = int(freq / freq_resolution)
        if k < 1 or k >= half:
            continue
        # Goertzel algorithm for single frequency bin
        coeff = 2.0 * math.cos(2.0 * math.pi * k / n_sub)
        s0 = 0.0
        s1 = 0.0
        s2 = 0.0
        for sample in subset:
            s0 = sample + coeff * s1 - s2
            s2 = s1
            s1 = s0
        raw_mag = math.sqrt(max(0.0, s1 * s1 + s2 * s2 - coeff * s1 * s2))
        # Normalize by sample count so magnitude is independent of window length
        mag = raw_mag / n_sub
        magnitudes.append(mag)
        freqs.append(freq)

    if not magnitudes:
        return 0.0, False

    total_mag = sum(magnitudes)
    if total_mag < 1e-10:
        return 0.0, False

    centroid = sum(f * m for f, m in zip(freqs, magnitudes)) / total_mag
    is_voice = _SPECTRAL_VOICE_LOW <= centroid <= _SPECTRAL_VOICE_HIGH

    return centroid, is_voice


def _compute_noise_floor(energies: list[float]) -> float:
    """Estimate noise floor from the bottom percentile of energy values."""
    if not energies:
        return _DEFAULT_SILENCE_THRESHOLD

    sorted_e = sorted(energies)
    cutoff_idx = max(1, int(len(sorted_e) * _NOISE_FLOOR_PERCENTILE))
    floor_values = sorted_e[:cutoff_idx]
    return sum(floor_values) / len(floor_values)


def _detect_silence_ranges(
    energy_curve: list[dict[str, float]],
    threshold: float,
    window_sec: float,
) -> list[dict[str, Any]]:
    """Detect silence ranges with actual avg_db computation.

    Uses adaptive threshold and computes real dB values for each range.
    """
    silence_ranges: list[dict[str, Any]] = []
    silence_start: float | None = None
    silence_db_values: list[float] = []

    for point in energy_curve:
        energy = point["energy"]
        time_sec = point["time_sec"]
        rms_db = point.get("rms_db", -96.0)

        if energy < threshold:
            if silence_start is None:
                silence_start = time_sec
                silence_db_values = []
            silence_db_values.append(rms_db)
        else:
            if silence_start is not None:
                duration = time_sec - silence_start
                if duration >= _MIN_SILENCE_DURATION:
                    # Compute actual average dB for this silence range
                    avg_db = (
                        sum(silence_db_values) / len(silence_db_values)
                        if silence_db_values
                        else -96.0
                    )
                    silence_ranges.append({
                        "start": silence_start,
                        "end": time_sec,
                        "avg_db": round(avg_db, 1),
                        "duration": round(duration, 3),
                    })
                silence_start = None
                silence_db_values = []

    # Handle trailing silence
    if silence_start is not None and energy_curve:
        last_time = energy_curve[-1]["time_sec"] + window_sec
        duration = last_time - silence_start
        if duration >= _MIN_SILENCE_DURATION:
            avg_db = (
                sum(silence_db_values) / len(silence_db_values)
                if silence_db_values
                else -96.0
            )
            silence_ranges.append({
                "start": silence_start,
                "end": round(last_time, 3),
                "avg_db": round(avg_db, 1),
                "duration": round(duration, 3),
            })

    return silence_ranges


def _compute_loudness_stats(
    all_energies: list[float],
    energy_curve: list[dict[str, float]],
    noise_floor: float,
) -> dict[str, Any]:
    """Compute overall loudness statistics."""
    if not all_energies:
        return {
            "avg_energy": 0.0,
            "max_energy": 0.0,
            "avg_rms_db": -96.0,
            "max_rms_db": -96.0,
            "noise_floor": noise_floor,
            "dynamic_range_db": 0.0,
        }

    avg_energy = sum(all_energies) / len(all_energies)
    max_energy = max(all_energies)

    db_values = [p.get("rms_db", -96.0) for p in energy_curve]
    # Filter out pure silence for meaningful stats
    active_db = [d for d in db_values if d > -90.0]
    avg_rms_db = sum(active_db) / len(active_db) if active_db else -96.0
    max_rms_db = max(active_db) if active_db else -96.0
    min_active_db = min(active_db) if active_db else -96.0
    dynamic_range = max_rms_db - min_active_db

    return {
        "avg_energy": round(avg_energy, 4),
        "max_energy": round(max_energy, 4),
        "avg_rms_db": round(avg_rms_db, 1),
        "max_rms_db": round(max_rms_db, 1),
        "noise_floor": round(noise_floor, 4),
        "dynamic_range_db": round(dynamic_range, 1),
    }
