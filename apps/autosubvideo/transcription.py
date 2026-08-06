"""WhisperX-first transcription with an explicit faster-whisper fallback."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

_MODELS: dict[tuple[str, str, str], object] = {}
_MODEL_LOCK = threading.Lock()


class TranscriptionError(RuntimeError):
    pass


def _stop_process_tree(proc: subprocess.Popen) -> None:
    """Stop the sidecar and its model-loader children, best effort."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False, timeout=15)
    else:  # pragma: no cover - deployment is Windows, kept portable for dev.
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait()


def _sidecar_python() -> str:
    configured = os.environ.get("LTT_WHISPERX_PYTHON", "").strip()
    return configured if configured and os.path.isfile(configured) else ""


def whisperx_available() -> bool:
    return bool(_sidecar_python())


def _transcribe_whisperx(media_path: str, *, language: str, model_name: str,
                         on_progress=None, is_cancelled=None,
                         gpu_uuid: str = "") -> dict:
    python = _sidecar_python()
    if not python:
        raise TranscriptionError("WhisperX sidecar chưa được cấu hình.")
    output = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    output.close()
    error_log = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
    error_log.close()
    runner = str(Path(__file__).with_name("whisperx_runner.py"))
    args = [python, runner, "--input", media_path, "--output", output.name,
            "--model", model_name]
    if language:
        args.extend(["--language", language])
    try:
        if on_progress:
            on_progress(8, "WhisperX đang chép lời")
        log_handle = open(error_log.name, "w", encoding="utf-8", errors="replace")
        try:
            # Ghim tiến trình con vào ĐÚNG card nền tảng đã cấp. WhisperX bên
            # trong chỉ gọi `torch.cuda.is_available()` rồi dùng `cuda` — tức là
            # luôn `cuda:0`. Máy có hai card thì mọi job đều dồn vào card 0
            # trong khi card 1 nằm không, và hai job song song thì OOM.
            proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=log_handle,
                text=True, encoding="utf-8", errors="replace",
                env=_env_ghim_gpu(gpu_uuid), creationflags=(
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        finally:
            log_handle.close()
        timeout_s = max(60, int(os.environ.get("LTT_WHISPERX_TIMEOUT_SECONDS", "10800")))
        deadline = time.monotonic() + timeout_s
        while proc.poll() is None:
            if is_cancelled and is_cancelled():
                _stop_process_tree(proc)
                raise TranscriptionError("Tác vụ đã bị hủy.")
            if time.monotonic() >= deadline:
                _stop_process_tree(proc)
                raise TranscriptionError(f"WhisperX quá thời gian ({timeout_s}s).")
            try:
                proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                continue
        if proc.returncode != 0:
            try:
                message = Path(error_log.name).read_text(
                    encoding="utf-8", errors="replace")[-1000:]
            except OSError:
                message = ""
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
        try:
            os.unlink(error_log.name)
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


def _env_ghim_gpu(gpu_uuid: str) -> dict:
    """Môi trường cho tiến trình con, đã ghim vào một card. Rỗng = giữ nguyên."""
    if not gpu_uuid:
        return dict(os.environ)
    from platform_core import gpu as gpu_mod
    return gpu_mod.env_for(gpu_uuid)


def transcribe_file(media_path: str, *, language: str = "", model_name: str = "large-v3",
                    on_progress=None, is_cancelled=None, gpu_uuid: str = "") -> dict:
    """Use WhisperX by default; make fallback explicit in the returned contract."""
    if whisperx_available():
        try:
            return _transcribe_whisperx(media_path, language=language,
                                        model_name=model_name, on_progress=on_progress,
                                        is_cancelled=is_cancelled, gpu_uuid=gpu_uuid)
        except TranscriptionError as exc:
            fallback = _transcribe_faster(media_path, language=language,
                                          model_name=model_name, on_progress=on_progress,
                                          is_cancelled=is_cancelled)
            fallback["fallback_reason"] = str(exc)[:300]
            return fallback
    return _transcribe_faster(media_path, language=language, model_name=model_name,
                              on_progress=on_progress, is_cancelled=is_cancelled)
