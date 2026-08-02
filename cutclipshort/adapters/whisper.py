"""Whisper adapter — bilingual Vietnamese/English speech-to-text.

Pipeline:
  1. Detect language via short audio sample (2-pass approach)
  2. Transcribe with language-specific optimized parameters
  3. Post-process: fix common errors per language
  4. Return word-level timestamps for caption sync

Supports:
  - faster-whisper (preferred: GPU, faster, lower memory)
  - openai-whisper (fallback: CPU-friendly)

Language strategy:
  - If language is forced (config), use it directly
  - If auto-detect, run a 30s detect pass first, then full transcribe
  - Vietnamese: initial_prompt with tonal patterns, post-process d→đ fixes
  - English: no special prompt needed, post-process capitalization only
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cutclipshort.adapters.base import BaseAdapter
from cutclipshort.errors import AdapterError

logger = logging.getLogger(__name__)


@dataclass
class TranscriptResult:
    """Result of a transcription."""
    language: str
    segments: list[dict[str, Any]]  # [{start, end, text, words}]
    duration_sec: float


# ══════════════════════════════════════════════════════════════════════
# LANGUAGE-SPECIFIC CONFIGURATION
# ══════════════════════════════════════════════════════════════════════

# Vietnamese prompt — primes Whisper to output correct tonal marks.
# Contains common Vietnamese words that Whisper frequently gets wrong,
# especially the đ/d confusion and tonal mark errors.
_PROMPT_VI = (
    "Đây là nội dung tiếng Việt có phụ đề. "
    "Các từ thường gặp: không, được, người, những, cũng, đã, đang, đến, để, "
    "rồi, thì, mà, là, của, này, đó, ấy, đi, về, lại, ra, vào, lên, xuống, "
    "anh, chị, em, bạn, tôi, mình, chúng tôi, họ, "
    "nhưng, nếu, vì, nên, hay, hoặc, với, từ, trong, ngoài, "
    "một, hai, ba, bốn, năm, sáu, bảy, tám, chín, mười, "
    "thật, rất, quá, lắm, nhiều, ít, "
    "biết, hiểu, nghĩ, nói, làm, có, muốn, cần, phải."
)

# English prompt — minimal, just sets the context
_PROMPT_EN = (
    "This is a video with English subtitles. "
    "Transcribe accurately with proper punctuation and capitalization."
)

# Transcription parameters per language
_LANG_PARAMS = {
    "vi": {
        "initial_prompt": _PROMPT_VI,
        "beam_size": 5,
        "temperature": 0.0,
        # condition_on_previous_text=False: ngan Whisper lap lai cau bia
        # (hallucination) suot video khi audio khong co thoai ro rang.
        "condition_on_previous_text": False,
        "vad_filter": True,
        "vad_parameters": {"min_silence_duration_ms": 250},
        # Vietnamese speech has shorter pauses between phrases
    },
    "en": {
        "initial_prompt": _PROMPT_EN,
        "beam_size": 5,
        "temperature": 0.0,
        "condition_on_previous_text": False,
        "vad_filter": True,
        "vad_parameters": {"min_silence_duration_ms": 500},
    },
}

# Default params for any other language
_LANG_PARAMS_DEFAULT = {
    "beam_size": 5,
    "temperature": 0.0,
    "condition_on_previous_text": False,
    "vad_filter": True,
}


# ══════════════════════════════════════════════════════════════════════
# VIETNAMESE COMMON ERROR CORRECTIONS
# ══════════════════════════════════════════════════════════════════════

# Whisper's #1 Vietnamese error: confusing đ (đờ) with d (dờ).
# In Vietnamese, "đ" and "d" are completely different consonants.
# Whisper (trained mostly on English) maps them both to "d".
# These corrections cover the most frequent words.
_VI_D_TO_Đ = {
    # Extremely common words where Whisper writes "d" instead of "đ"
    "dã": "đã", "dang": "đang", "dến": "đến", "dể": "để",
    "dó": "đó", "dây": "đây", "di": "đi", "dược": "được",
    "dầu": "đầu", "dồng": "đồng", "diều": "điều", "dội": "đội",
    "dẹp": "đẹp", "dúng": "đúng", "dủ": "đủ", "dạt": "đạt",
    "dọc": "đọc", "dặt": "đặt", "dổi": "đổi", "dối": "đối",
    "dau": "đau", "dêm": "đêm", "dịnh": "định", "dường": "đường",
    "diểm": "điểm", "diện": "điện", "dông": "đông", "dỗ": "đỗ",
    "dưa": "đưa", "dứng": "đứng", "dịa": "địa", "dề": "đề",
    "deo": "đeo", "dè": "đè", "dôi": "đôi",
    # v2: added missing high-frequency words
    "dòng": "đòng", "dục": "đục", "dàng": "đàng", "dạng": "đạng",
    "dở": "đở", "dựa": "đựa", "dôn": "đôn",
    "dăng": "đăng", "dối": "đối", "dáng": "đáng", "dá": "đá",
    "dịch": "địch", "diểm": "điểm", "dình": "đình",
}

# Informal/abbreviated words Whisper might output
_VI_ABBREVIATIONS = {
    "ko": "không", "k": "không",
    "dc": "được", "đc": "được",
    "ntn": "như thế nào",
    "bik": "biết", "bt": "biết",
    "trc": "trước",
    "nc": "nước",
    "ng": "người",
    "j": "gì",
    "z": "vậy",
    "r": "rồi",
    "mk": "mình",
    "ms": "mới",
    "cx": "cũng",
    "vs": "với",
    "đag": "đang",
}

# Whisper hallucination patterns (appears when audio is silent/unclear)
_VI_HALLUCINATIONS = [
    # Vietnamese auto-generated endings
    "Cảm ơn đã xem video",
    "Hãy like và subscribe",
    "Đăng ký kênh",
    "Nhấn nút đăng ký",
    "Cảm ơn các bạn đã theo dõi",
    "Xin cảm ơn",
    "Cảm ơn đã theo dõi",
    "Hãy đăng ký kênh",
    "Nhấn chuông thông báo",
    "Bấm like",
    # English auto-generated endings
    "Thank you for watching",
    "Please subscribe",
    "Like and subscribe",
    "Don't forget to subscribe",
    "Hit the bell",
    # Filler/noise patterns (common on silent sections)
    "Ừm",
    "Hmm",
    "Uh",
    # Mixed VI-EN hallucinations
    "Cảm ơn thank you",
    "Subscribe đăng ký",
]


class WhisperAdapter(BaseAdapter):
    """Bilingual Vietnamese/English Whisper speech-to-text adapter.

    Features:
    - 2-pass: detect language first, then transcribe with optimized params
    - Language-specific initial prompts for accuracy
    - Vietnamese post-processing (d→đ, abbreviations, punctuation)
    - English post-processing (capitalization, punctuation)
    - Hallucination filtering
    - Model caching (don't reload for same model_size)
    """

    def __init__(self, model_size: str = "base", compute_type: str = "auto") -> None:
        super().__init__()
        self._model_size = model_size
        self._compute_type = compute_type  # "auto", "int8", "float16", "float32"
        self._backend: str | None = None
        # Model cache to avoid reloading
        self._cached_model = None
        self._cached_model_size: str = ""
        self._cached_compute_type: str = ""

    @property
    def tool_name(self) -> str:
        return "whisper"

    def _find_executable(self) -> str:
        return "whisper"

    def check_available(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
            self._backend = "faster_whisper"
            return True
        except ImportError:
            pass
        try:
            import whisper  # noqa: F401
            self._backend = "openai_whisper"
            return True
        except ImportError:
            pass
        return False

    def get_version(self) -> str | None:
        if self._backend == "faster_whisper":
            try:
                import faster_whisper
                return f"faster-whisper {faster_whisper.__version__}"
            except (ImportError, AttributeError):
                return "faster-whisper"
        elif self._backend == "openai_whisper":
            try:
                import whisper
                return f"openai-whisper {whisper.__version__}"
            except (ImportError, AttributeError):
                return "openai-whisper"
        return None

    def get_capabilities(self) -> dict[str, Any]:
        available = self.check_available()
        caps: dict[str, Any] = {"available": available, "backend": self._backend}
        if available:
            try:
                import torch
                caps["cuda"] = torch.cuda.is_available()
                if caps["cuda"]:
                    caps["cuda_device"] = torch.cuda.get_device_name(0)
            except ImportError:
                caps["cuda"] = False
        return caps

    # ══════════════════════════════════════════════════════════════
    # MAIN TRANSCRIBE API
    # ══════════════════════════════════════════════════════════════

    def transcribe(
        self,
        audio_path: Path,
        *,
        model_size: str | None = None,
        language: str | None = None,
        word_timestamps: bool = True,
        progress_callback: Any = None,
    ) -> TranscriptResult:
        """Transcribe audio to text with word-level timestamps.

        Args:
            audio_path: Path to audio/video file
            model_size: Whisper model (tiny/base/small/medium/large-v3)
            language: Force language ("vi"/"en") or None for auto-detect
            word_timestamps: Include per-word timing
            progress_callback: Optional progress function

        Returns:
            TranscriptResult with segments, language, duration
        """
        if not self.check_available():
            raise AdapterError(
                "No whisper backend. Install: pip install faster-whisper",
                tool_name="whisper",
            )

        model_size = model_size or self._model_size

        # Step 1: Detect language if not forced
        if language is None:
            language = self._detect_language(audio_path, model_size)
            logger.info("Auto-detected language: %s", language)

        # Step 2: Transcribe with language-optimized parameters
        logger.info("Transcribing: model=%s, lang=%s, backend=%s",
                     model_size, language, self._backend)

        if self._backend == "faster_whisper":
            result = self._transcribe_faster(
                audio_path, model_size, language, word_timestamps)
        else:
            result = self._transcribe_openai(
                audio_path, model_size, language, word_timestamps)

        # Step 3: Post-process per language
        result.segments = self._postprocess_segments(result.segments, result.language)

        logger.info("Transcription complete: %d segments, lang=%s",
                     len(result.segments), result.language)
        return result

    # ══════════════════════════════════════════════════════════════
    # LANGUAGE DETECTION (2-pass approach)
    # ══════════════════════════════════════════════════════════════

    def _detect_language(self, audio_path: Path, model_size: str) -> str:
        """Detect language from first 30s of audio.

        Uses Whisper's built-in language detection which analyzes
        the first 30 seconds of audio mel spectrogram.
        """
        try:
            if self._backend == "faster_whisper":
                model = self._get_or_load_model_faster(model_size)

                # Try fast language detection (faster-whisper ≥0.10)
                lang = None
                prob = 0.0
                try:
                    if hasattr(model, 'detect_language_multi_segment'):
                        # Fast path: only analyzes mel spectrogram, no transcription
                        lang_results = model.detect_language_multi_segment(str(audio_path))
                        if lang_results:
                            lang = lang_results[0][0]
                            prob = lang_results[0][1]
                            logger.info("Fast language detection: %s (%.1f%%)", lang, prob * 100)
                except Exception:
                    pass  # Fall through to transcription-based detection

                if lang is None:
                    # Fallback: use transcribe with minimal processing
                    segments_gen, info = model.transcribe(
                        str(audio_path),
                        language=None,
                        word_timestamps=False,
                        vad_filter=False,
                    )
                    # Consume just first segment to get info
                    for _ in segments_gen:
                        break
                    lang = info.language
                    prob = info.language_probability
                logger.info("Language detection: %s (%.1f%%)", lang, prob * 100)
                # If confidence < 70%, fall back to Vietnamese (target audience)
                if prob < 0.7:
                    logger.warning("Low confidence (%.1f%%), defaulting to 'vi'", prob * 100)
                    return "vi"
                return lang
            else:
                import whisper
                model = self._get_or_load_model_openai(model_size)
                audio = whisper.load_audio(str(audio_path))
                audio = whisper.pad_or_trim(audio)
                mel = whisper.log_mel_spectrogram(audio).to(model.device)
                _, probs = model.detect_language(mel)
                lang = max(probs, key=probs.get)
                logger.info("Language detection: %s (%.1f%%)", lang, probs[lang] * 100)
                if probs[lang] < 0.7:
                    return "vi"
                return lang
        except Exception as e:
            logger.warning("Language detection failed: %s, defaulting to 'vi'", e)
            return "vi"

    # ══════════════════════════════════════════════════════════════
    # FASTER-WHISPER BACKEND
    # ══════════════════════════════════════════════════════════════

    def _get_or_load_model_faster(self, model_size: str):
        """Load faster-whisper model with caching and tier-aware compute type."""
        # Resolve compute type from config (or auto-detect)
        device = "cuda" if self.get_capabilities().get("cuda") else "cpu"
        if self._compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"
        elif self._compute_type == "float16" and device == "cpu":
            # float16 not supported on CPU — fallback to int8
            compute_type = "int8"
            logger.info("float16 not available on CPU, using int8")
        else:
            compute_type = self._compute_type

        # Return cached model if same model+compute
        if (self._cached_model
                and self._cached_model_size == model_size
                and self._cached_compute_type == compute_type):
            return self._cached_model

        # Release old model before loading new one (prevent OOM)
        if self._cached_model is not None:
            logger.info("Releasing previous model: %s (%s)",
                        self._cached_model_size, self._cached_compute_type)
            del self._cached_model
            self._cached_model = None
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

        from faster_whisper import WhisperModel

        # Check for bundled local model first (shipped with exe)
        model_path_or_name = self._find_local_model(model_size) or model_size
        if model_path_or_name != model_size:
            logger.info("Using bundled local model: %s", model_path_or_name)

        logger.info("Loading faster-whisper model=%s device=%s compute=%s",
                     model_path_or_name, device, compute_type)

        try:
            self._cached_model = WhisperModel(
                model_path_or_name, device=device, compute_type=compute_type,
            )
        except Exception as e:
            # OOM or model not found — try fallback
            from cutclipshort.core.quality_tiers import get_whisper_fallback
            fallback = get_whisper_fallback(model_size)
            if fallback:
                logger.warning(
                    "Failed to load %s (%s): %s — falling back to %s",
                    model_size, compute_type, e, fallback,
                )
                fallback_path = self._find_local_model(fallback) or fallback
                self._cached_model = WhisperModel(
                    fallback_path, device=device, compute_type=compute_type,
                )
                model_size = fallback
            else:
                raise

        self._cached_model_size = model_size
        self._cached_compute_type = compute_type
        return self._cached_model

    def _transcribe_faster(
        self, audio_path: Path, model_size: str,
        language: str, word_timestamps: bool,
    ) -> TranscriptResult:
        """Transcribe using faster-whisper with per-language optimization."""
        model = self._get_or_load_model_faster(model_size)

        # Get language-specific parameters
        params = _LANG_PARAMS.get(language, _LANG_PARAMS_DEFAULT).copy()
        params["language"] = language
        params["word_timestamps"] = word_timestamps

        # Anti-hallucination hardening (faster-whisper only). Suppresses the
        # model echoing its own initial_prompt or repeating phrases over
        # music/SFX/silence (e.g. nerf-gun action with no clear narration).
        params.setdefault("no_speech_threshold", 0.6)
        params.setdefault("compression_ratio_threshold", 2.4)
        params.setdefault("log_prob_threshold", -1.0)

        segments_gen, info = model.transcribe(str(audio_path), **params)

        segments = []
        for seg in segments_gen:
            seg_dict: dict[str, Any] = {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
            }
            if word_timestamps and seg.words:
                seg_dict["words"] = [
                    {
                        "word": w.word.strip(),
                        "start": w.start,
                        "end": w.end,
                        "confidence": round(w.probability, 3),
                    }
                    for w in seg.words
                ]
            segments.append(seg_dict)

        return TranscriptResult(
            language=info.language,
            segments=segments,
            duration_sec=info.duration,
        )

    # ══════════════════════════════════════════════════════════════
    # OPENAI-WHISPER BACKEND
    # ══════════════════════════════════════════════════════════════

    def _get_or_load_model_openai(self, model_size: str):
        """Load openai-whisper model with caching.

        Note: openai-whisper does NOT support compute_type parameter.
        It auto-selects fp16 on CUDA, fp32 on CPU.
        """
        if self._cached_model and self._cached_model_size == model_size:
            return self._cached_model

        # Release old model
        if self._cached_model is not None:
            del self._cached_model
            self._cached_model = None

        if self._compute_type not in ("auto", ""):
            logger.info("openai-whisper does not support compute_type='%s' — using auto detection",
                        self._compute_type)

        import whisper
        logger.info("Loading openai-whisper model=%s (compute_type=auto)", model_size)
        try:
            self._cached_model = whisper.load_model(model_size)
        except Exception as e:
            from cutclipshort.core.quality_tiers import get_whisper_fallback
            fallback = get_whisper_fallback(model_size)
            if fallback:
                logger.warning("Failed to load %s: %s — falling back to %s", model_size, e, fallback)
                self._cached_model = whisper.load_model(fallback)
                model_size = fallback
            else:
                raise
        self._cached_model_size = model_size
        return self._cached_model

    def _transcribe_openai(
        self, audio_path: Path, model_size: str,
        language: str, word_timestamps: bool,
    ) -> TranscriptResult:
        """Transcribe using openai-whisper with per-language optimization."""
        model = self._get_or_load_model_openai(model_size)

        params = _LANG_PARAMS.get(language, _LANG_PARAMS_DEFAULT).copy()
        # openai-whisper doesn't support vad_filter/vad_parameters
        params.pop("vad_filter", None)
        params.pop("vad_parameters", None)
        params["language"] = language
        params["word_timestamps"] = word_timestamps

        result = model.transcribe(str(audio_path), **params)

        segments = []
        for seg in result.get("segments", []):
            seg_dict: dict[str, Any] = {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
            }
            if "words" in seg:
                seg_dict["words"] = [
                    {
                        "word": w["word"].strip(),
                        "start": w["start"],
                        "end": w["end"],
                        "confidence": round(w.get("probability", 0.0), 3),
                    }
                    for w in seg["words"]
                ]
            segments.append(seg_dict)

        return TranscriptResult(
            language=result.get("language", language),
            segments=segments,
            duration_sec=0.0,
        )

    # ══════════════════════════════════════════════════════════════
    # POST-PROCESSING
    # ══════════════════════════════════════════════════════════════

    def _postprocess_segments(
        self, segments: list[dict], language: str,
    ) -> list[dict]:
        """Apply language-specific post-processing to all segments."""
        result = []
        for seg in segments:
            text = seg["text"]

            # Filter hallucinations (text patterns + prompt-echo)
            if self._is_hallucination(text, language):
                logger.debug("Filtered hallucination: '%s'", text[:50])
                continue

            # Filter low-confidence segments. Whisper bia chu tren audio
            # nhac/SFX/im lang co confidence gan 0 (vd nerf-gun action).
            if self._is_low_confidence_segment(seg):
                logger.debug("Filtered low-confidence segment: '%s'", text[:50])
                continue

            # Apply language-specific fixes
            if language == "vi":
                text = self._fix_vietnamese(text)
            elif language == "en":
                text = self._fix_english(text)

            # Skip empty segments after processing
            text = text.strip()
            if not text:
                continue

            seg = dict(seg)  # Copy to avoid mutating original
            seg["text"] = text

            # Also fix word-level text (for subtitle sync accuracy)
            # IMPORTANT: Only apply d→đ and abbreviation fixes to words.
            # Do NOT apply capitalization or period-adding — those are
            # sentence-level fixes that break word-level display.
            if "words" in seg and language == "vi":
                fixed_words = []
                for w in seg["words"]:
                    w = dict(w)
                    w["word"] = self._fix_vietnamese_word(w.get("word", ""))
                    fixed_words.append(w)
                seg["words"] = fixed_words

            result.append(seg)

        return result

    @staticmethod
    def _is_hallucination(text: str, language: str) -> bool:
        """Detect Whisper hallucination patterns (expanded v2)."""
        text_lower = text.strip().lower()
        if not text_lower:
            return True

        # Repeated words (3+ times = hallucination)
        words = text_lower.split()
        if len(words) >= 3 and len(set(words)) == 1:
            return True

        # Mostly repeated (80%+ same word in 5+ word segment)
        if len(words) >= 5:
            most_common = max(set(words), key=words.count)
            if words.count(most_common) / len(words) >= 0.8:
                return True

        # Very short filler segments (1-2 chars only)
        if len(text_lower) <= 2 and text_lower in ("ừ", "uh", "hm", "à", "ờ", "ơ"):
            return True

        # Prompt-echo: Whisper nha lai chinh initial_prompt khi khong co thoai.
        # Vd: "Transcribe accurately with proper punctuation and capitalization."
        # hoac "This is a video with English subtitles."
        _PROMPT_ECHO_MARKERS = (
            "transcribe accurately",
            "proper punctuation",
            "punctuation and capitalization",
            "this is a video with english subtitles",
            "phien am chinh xac",
            "ban ghi chep tieng viet",
        )
        for marker in _PROMPT_ECHO_MARKERS:
            if marker in text_lower:
                return True

        # Known hallucination phrases
        if language == "vi":
            for h in _VI_HALLUCINATIONS:
                if h.lower() in text_lower:
                    return True
        elif language == "en":
            en_hallucinations = [
                "thank you for watching",
                "please subscribe",
                "like and subscribe",
            ]
            for h in en_hallucinations:
                if h in text_lower:
                    return True

        return False

    @staticmethod
    def _is_low_confidence_segment(seg: dict, threshold: float = 0.30) -> bool:
        """Detect hallucinated segments via near-zero word confidence.

        Real speech from large-v3 averages 0.6-0.95 per word. Hallucinations
        on music/SFX/silence average < 0.1. We drop a segment only when it has
        enough words (>=3) to judge reliably, so genuine short interjections
        ("Yes!", "Wow") are never removed.
        """
        words = seg.get("words") or []
        confs = [
            float(w.get("confidence", 0.0))
            for w in words
            if (w.get("word") or "").strip()
        ]
        if len(confs) < 3:
            return False  # Not enough data — keep (avoid dropping real short segs)
        avg_conf = sum(confs) / len(confs)
        return avg_conf < threshold

    @staticmethod
    def _fix_vietnamese(text: str) -> str:
        """Fix common Whisper errors in Vietnamese.

        Main fixes:
        1. d → đ correction (Whisper's #1 Vietnamese error)
        2. Abbreviation expansion
        3. Punctuation normalization
        4. Capitalization
        """
        if not text:
            return text

        # Pad with spaces for word-boundary matching
        padded = f" {text} "

        # ── Fix d → đ (word-boundary safe) ──
        for wrong, right in _VI_D_TO_Đ.items():
            # Match as whole word (case-insensitive for first char)
            padded = re.sub(
                rf'(?<=\s){re.escape(wrong)}(?=[\s.,!?])',
                right, padded, flags=re.IGNORECASE,
            )

        # ── Fix abbreviations (whole-word only) ──
        for abbr, full in _VI_ABBREVIATIONS.items():
            padded = re.sub(
                rf'(?<=\s){re.escape(abbr)}(?=[\s.,!?])',
                full, padded, flags=re.IGNORECASE,
            )

        text = padded.strip()

        # ── Capitalization ──
        if text:
            # Capitalize first character
            text = text[0].upper() + text[1:]
            # Capitalize after sentence-ending punctuation
            text = re.sub(
                r'([.!?]\s+)(\w)',
                lambda m: m.group(1) + m.group(2).upper(),
                text,
            )

        # ── Punctuation cleanup ──
        text = re.sub(r' +', ' ', text)           # Double spaces
        text = re.sub(r' ([.!?,])', r'\1', text)  # Space before punct
        text = text.strip()

        # Add period if missing at end
        if text and text[-1] not in ".!?…":
            text += "."

        return text

    @staticmethod
    def _fix_vietnamese_word(word: str) -> str:
        """Fix d→đ and abbreviations for a SINGLE WORD only.

        Unlike _fix_vietnamese(), this does NOT:
        - Add period at end (would produce "Rằng." "Họ." "Không.")
        - Capitalize first letter (would capitalize every word)
        - Normalize punctuation across sentence boundaries

        Only applies safe word-level corrections:
        1. d → đ mapping (if exact match)
        2. Abbreviation expansion (if exact match)
        """
        if not word:
            return word
        stripped = word.strip()
        if not stripped:
            return word

        # Check d→đ mapping (case-insensitive)
        lower = stripped.lower()
        if lower in _VI_D_TO_Đ:
            # Preserve original casing pattern
            replacement = _VI_D_TO_Đ[lower]
            if stripped[0].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            return replacement

        # Check abbreviation mapping
        if lower in _VI_ABBREVIATIONS:
            return _VI_ABBREVIATIONS[lower]

        return word

    @staticmethod
    def _fix_english(text: str) -> str:
        """Fix common Whisper errors in English.

        Light-touch fixes (Whisper is generally good at English):
        1. Capitalization (first letter, after period)
        2. Punctuation
        3. Common contractions
        """
        if not text:
            return text

        # Capitalize first letter
        text = text[0].upper() + text[1:] if text else text

        # Capitalize after sentence-ending punctuation
        text = re.sub(
            r'([.!?]\s+)(\w)',
            lambda m: m.group(1) + m.group(2).upper(),
            text,
        )

        # Capitalize "I" as standalone word
        text = re.sub(r'\bi\b', 'I', text)

        # Punctuation cleanup
        text = re.sub(r' +', ' ', text)
        text = re.sub(r' ([.!?,])', r'\1', text)
        text = text.strip()

        if text and text[-1] not in ".!?…":
            text += "."

        return text

    def _find_local_model(self, model_size: str) -> str | None:
        """Find a bundled whisper model in the app's models/ directory.

        Search order (for requested model_size, then smaller fallbacks):
        1. <app_root>/models/faster-whisper-<size>/  (bundled with exe)
        2. <app_root>/models/whisper-<size>/
        3. Fallback to smaller models: medium → base → small → tiny
        4. None (will download from HuggingFace)

        A valid local model directory must have 'model.bin' with size > 1MB.
        """
        import sys
        from pathlib import Path

        if getattr(sys, 'frozen', False):
            app_root = Path(sys.executable).parent
        else:
            app_root = Path(__file__).resolve().parent.parent.parent

        # Fallback chain: try requested size first, then smaller models
        _FALLBACK_ORDER = {
            "large-v3": ["large-v3", "medium", "base", "small", "tiny"],
            "medium": ["medium", "base", "small", "tiny"],
            "small": ["small", "base", "tiny"],
            "base": ["base", "tiny"],
            "tiny": ["tiny"],
        }
        sizes_to_try = _FALLBACK_ORDER.get(model_size, [model_size, "base", "tiny"])

        for size in sizes_to_try:
            search_names = [
                f"faster-whisper-{size}",
                f"whisper-{size}",
                size,
            ]
            for name in search_names:
                model_dir = app_root / "models" / name
                model_bin = model_dir / "model.bin"
                if model_dir.is_dir() and model_bin.exists():
                    # Verify model.bin is not empty (symlink copy bug)
                    if model_bin.stat().st_size > 1_000_000:  # > 1MB
                        if size != model_size:
                            logger.info("Local model '%s' not found, using '%s' instead: %s",
                                        model_size, size, model_dir)
                        else:
                            logger.info("Found local model: %s", model_dir)
                        return str(model_dir)
                    else:
                        logger.warning("Model file too small (corrupt?): %s (%d bytes)",
                                       model_bin, model_bin.stat().st_size)

        logger.warning("No local model found for '%s' in %s/models/", model_size, app_root)
        return None

    def available_models(self) -> list[str]:
        return ["tiny", "base", "small", "medium", "large-v3"]
