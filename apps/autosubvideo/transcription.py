"""WhisperX-first transcription with an explicit faster-whisper fallback."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

_MODELS: dict[tuple[str, str, str], object] = {}
_MODEL_LOCK = threading.Lock()


class TranscriptionError(RuntimeError):
    pass


def _sidecar_python() -> str:
    configured = os.environ.get("LTT_WHISPERX_PYTHON", "").strip()
    return configured if configured and os.path.isfile(configured) else ""


def whisperx_available() -> bool:
    return bool(_sidecar_python())


def _transcribe_whisperx(media_path: str, *, language: str, model_name: str,
                         on_progress=None, is_cancelled=None) -> dict:
    python = _sidecar_python()
    if not python:
        raise TranscriptionError("WhisperX sidecar chưa được cấu hình.")
    output = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    output.close()
    runner = str(Path(__file__).with_name("whisperx_runner.py"))
    args = [python, runner, "--input", media_path, "--output", output.name,
            "--model", model_name]
    if language:
        args.extend(["--language", language])
    try:
        if on_progress:
            on_progress(8, "WhisperX đang chép lời")
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                errors="replace", creationflags=(
                                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        while proc.poll() is None:
            if is_cancelled and is_cancelled():
                proc.terminate()
                raise TranscriptionError("Tác vụ đã bị hủy.")
            try:
                proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                continue
        if proc.returncode != 0:
            message = (proc.stderr.read() if proc.stderr else "")[-1000:]
            raise TranscriptionError(f"WhisperX lỗi: {message or 'không rõ nguyên nhân'}")
        with open(output.name, encoding="utf-8") as handle:
            result = json.load(handle)
        if on_progress:
            on_progress(88, "đã căn chỉnh word timing")
        return result
    finally:
        try:
            os.unlink(output.name)
        except OSError:
            pass


def _get_faster_model(model_name: str):
    from faster_whisper import WhisperModel
    device = os.environ.get("LTT_AUTOSUB_WHISPER_DEVICE", "cuda").strip() or "cuda"
    compute = os.environ.get("LTT_AUTOSUB_WHISPER_COMPUTE", "float16").strip() or "float16"
    key = (model_name, device, compute)
    with _MODEL_LOCK:
        if key not in _MODELS:
            try:
                _MODELS[key] = WhisperModel(model_name, device=device, compute_type=compute)
            except Exception:
                if device == "cpu":
                    raise
                key = (model_name, "cpu", "int8")
                if key not in _MODELS:
                    _MODELS[key] = WhisperModel(model_name, device="cpu", compute_type="int8")
        return _MODELS[key]


def _transcribe_faster(media_path: str, *, language: str, model_name: str,
                       on_progress=None, is_cancelled=None) -> dict:
    if on_progress:
        on_progress(8, "fallback faster-whisper")
    model = _get_faster_model(model_name)
    segments, info = model.transcribe(media_path, language=language or None,
                                      word_timestamps=True, vad_filter=True,
                                      beam_size=5)
    out = []
    for index, segment in enumerate(segments):
        if is_cancelled and is_cancelled():
            raise TranscriptionError("Tác vụ đã bị hủy.")
        words = [{"start": float(word.start), "end": float(word.end),
                  "text": str(word.word).strip()} for word in (segment.words or [])
                 if word.start is not None and word.end is not None and str(word.word).strip()]
        out.append({"start": float(segment.start), "end": float(segment.end),
                    "text": str(segment.text).strip(), "words": words})
        if on_progress:
            on_progress(min(86, 12 + index), "đang chép lời")
    return {"segments": out, "language": str(getattr(info, "language", language or "")),
            "engine": "faster-whisper", "alignment_status": "fallback_unaligned",
            "fallback_reason": "whisperx_sidecar_unavailable"}


def transcribe_file(media_path: str, *, language: str = "", model_name: str = "large-v3",
                    on_progress=None, is_cancelled=None) -> dict:
    """Use WhisperX by default; make fallback explicit in the returned contract."""
    if whisperx_available():
        try:
            return _transcribe_whisperx(media_path, language=language,
                                        model_name=model_name, on_progress=on_progress,
                                        is_cancelled=is_cancelled)
        except TranscriptionError as exc:
            fallback = _transcribe_faster(media_path, language=language,
                                          model_name=model_name, on_progress=on_progress,
                                          is_cancelled=is_cancelled)
            fallback["fallback_reason"] = str(exc)[:300]
            return fallback
    return _transcribe_faster(media_path, language=language, model_name=model_name,
                              on_progress=on_progress, is_cancelled=is_cancelled)
