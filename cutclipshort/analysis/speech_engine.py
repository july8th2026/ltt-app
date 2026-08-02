"""Speech transcription engine.

Uses faster-whisper to produce word-level transcript with timestamps.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from cutclipshort.analysis.base import BaseAnalysisEngine
from cutclipshort.types import SourceAsset

logger = logging.getLogger(__name__)


class SpeechEngine(BaseAnalysisEngine):
    """Whisper-based speech-to-text with word timestamps."""

    @property
    def name(self) -> str:
        """Return engine identifier."""
        return "speech"

    @property
    def version(self) -> str:
        """Return engine semantic version."""
        return "1.0.0"

    def _relevant_config_keys(self, config: dict[str, Any]) -> dict[str, Any]:
        """Config keys that affect cache invalidation."""
        return {
            "whisper_model": config.get("whisper_model", "medium"),
            "whisper_language": config.get("whisper_language", "auto"),
            "whisper_beam_size": config.get("whisper_beam_size", 5),
        }

    def run(
        self,
        source: Path,
        media_info: SourceAsset,
        config: dict[str, Any],
        cache_dir: Path,
        progress_callback: Callable[[float], None],
    ) -> dict[str, Any]:
        """Run Whisper transcription pipeline.

        Pipeline stages:
          0%  → Start
          10% → Check cache
          20% → Extract audio (FFmpeg)
          30% → Load Whisper model
          40% → Detect language (if auto)
          50% → Transcribe (main work)
          85% → Post-process text
          90% → Save cache
          100% → Done
        """
        # ── Stage 0: Check cache ──
        progress_callback(0.0)
        logger.info("━━━ Speech Engine START ━━━")

        cached = self.load_cached(cache_dir)
        if cached is not None:
            seg_count = len(cached.get("segments", []))
            lang = cached.get("language", "?")
            logger.info("Cache HIT: %d segments, lang=%s — skipping Whisper", seg_count, lang)
            progress_callback(1.0)
            return cached

        logger.info("Cache MISS — running Whisper transcription")
        progress_callback(0.1)

        # ── Stage 1: Initialize adapter ──
        try:
            from cutclipshort.adapters.whisper import WhisperAdapter
        except ImportError as e:
            raise RuntimeError(
                f"Không thể import WhisperAdapter: {e}. "
                f"Chạy: pip install faster-whisper"
            ) from e

        model_name = config.get("whisper_model", "medium")
        language = config.get("whisper_language", "auto")
        # "auto" hoặc empty → None để Whisper tự detect ngôn ngữ
        if not language or language.lower() == "auto":
            language = None

        compute_type = config.get("whisper_compute_type", "auto")
        adapter = WhisperAdapter(model_size=model_name, compute_type=compute_type)

        if not adapter.check_available():
            err = ("Whisper KHÔNG khả dụng — chưa cài faster-whisper hoặc openai-whisper. "
                   "Chạy: pip install faster-whisper")
            logger.error(err)
            raise RuntimeError(err)

        caps = adapter.get_capabilities()
        logger.info("Backend: %s | CUDA: %s | Model: %s | Language: %s",
                     caps.get("backend"), caps.get("cuda"), model_name, language or "auto")

        # ── Stage 2: Extract audio ──
        audio_path = cache_dir / "_speech_audio.wav"
        if not audio_path.exists():
            logger.info("Extracting audio from video → WAV")
            cache_dir.mkdir(parents=True, exist_ok=True)
            try:
                from cutclipshort.adapters.ffmpeg import FFmpegAdapter
                ffmpeg = FFmpegAdapter()
                ffmpeg.extract_audio(source, audio_path)
                logger.info("Audio extracted: %s (%.1f MB)",
                             audio_path.name, audio_path.stat().st_size / 1024 / 1024)
            except Exception as e:
                raise RuntimeError(
                    f"Không thể trích xuất audio từ video: {e}. "
                    f"Kiểm tra FFmpeg đã cài đúng chưa."
                ) from e
        else:
            logger.info("Audio cache exists: %s", audio_path.name)
        progress_callback(0.2)

        # ── Stage 3: Transcribe ──
        logger.info("Starting Whisper transcription: model=%s, lang=%s", model_name, language)
        logger.info("This may take 30-120 seconds depending on video length and GPU...")
        progress_callback(0.3)

        try:
            transcript_result = adapter.transcribe(
                audio_path,
                model_size=model_name,
                language=language,
                word_timestamps=True,
            )
        except Exception as e:
            raise RuntimeError(
                f"Whisper transcription thất bại: {e}. "
                f"Có thể do: (1) model '{model_name}' chưa tải xong, "
                f"(2) không đủ RAM/VRAM, (3) file audio bị lỗi. "
                f"Thử đổi model sang 'base' hoặc 'small'."
            ) from e
        progress_callback(0.85)

        # ── Stage 4: Log results ──
        seg_count = len(transcript_result.segments)
        detected_lang = transcript_result.language
        duration = transcript_result.duration_sec

        logger.info("━━━ Transcription Results ━━━")
        logger.info("  Language: %s", detected_lang)
        logger.info("  Segments: %d", seg_count)
        logger.info("  Duration: %.1f seconds", duration)

        if seg_count > 0:
            # Log first 3 segments as sample
            for i, seg in enumerate(transcript_result.segments[:3]):
                text = seg.get("text", "")[:60]
                start = seg.get("start", 0)
                end = seg.get("end", 0)
                word_count = len(seg.get("words", []))
                logger.info("  [%d] %.1f-%.1f: \"%s\" (%d words)",
                             i, start, end, text, word_count)
            if seg_count > 3:
                logger.info("  ... and %d more segments", seg_count - 3)

        # ── Stage 5: Save cache ──
        result = {
            "segments": transcript_result.segments,
            "language": detected_lang,
            "duration_sec": duration,
            "model_used": model_name,
            "backend": caps.get("backend", "unknown"),
        }

        self._save_cache(cache_dir, result)
        logger.info("Cache saved to: %s", cache_dir / "speech.json")
        progress_callback(0.95)

        logger.info("━━━ Speech Engine DONE: %d segments, lang=%s ━━━", seg_count, detected_lang)
        progress_callback(1.0)
        return result
