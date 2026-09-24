"""WhisperX-first transcription with an explicit faster-whisper fallback."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)

#: Khoá gồm cả `device_index`: hai card khác nhau là hai model khác nhau.
_MODELS: dict[tuple[str, str, str, int], object] = {}
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


def _chi_so_card(gpu_uuid: str) -> int:
    """CUDA ordinal của card nền tảng đã cấp. `-1` = torch không thấy card đó.

    🔑 Vì sao hỏi **torch** chứ không hỏi `platform_core.gpu.by_uuid().index`:
       `index` của `nvidia-smi` là số thứ tự TOÀN MÁY và không đổi theo
       `CUDA_VISIBLE_DEVICES`, còn `device_index` của CTranslate2 là số thứ tự
       trong tập card CUDA **nhìn thấy được**. Hai số đó bằng nhau khi tiến
       trình thấy mọi card và khác nhau khi không — một chỗ lệch im lặng đủ để
       đẩy job sang card đang phục vụ LTT VOICE.

    ⛔ Đường này chạy TRONG tiến trình worker, nên không ghim card bằng
       `CUDA_VISIBLE_DEVICES` được (`platform_core.gpu.env_for` chỉ ghim được
       tiến trình CON — xem `whisperx_runner`, `demucs_runner`, `do_luong/venv`).
       `device_index` là cách ghim duy nhất còn lại ở đây.
    """
    try:
        import torch
    except ImportError:
        return -1
    can = gpu_uuid.strip().lower().removeprefix("gpu-")
    if not can:
        return -1
    try:
        so = torch.cuda.device_count()
    except (AssertionError, RuntimeError):
        return -1
    for i in range(so):
        try:
            u = str(torch.cuda.get_device_properties(i).uuid).lower()
        except (AttributeError, RuntimeError):
            continue
        if u.removeprefix("gpu-") == can:
            return i
    return -1


def _thiet_bi_asr(gpu_uuid: str) -> tuple[str, str, int, str]:
    """(device, compute_type, device_index, lý do lùi về CPU).

    🔴 Bản trước mặc định `device="cuda"` **bất kể có lease hay không**, rồi
       `except Exception` nuốt mọi lỗi và lùi về `cpu/int8` **không để lại dấu
       vết nào**. Hai hậu quả đã trả giá thật:

       1. Không có lease mà vẫn lấy card ⇒ tranh card với LTT VOICE (khách trả
          tiền, `voice_sidecar`) mà nền tảng không hề biết — đúng thứ
          `platform_core.gpu_lease` sinh ra để chặn.
       2. Lùi về CPU im lặng ⇒ một lượt chạy chậm hàng chục lần mà báo cáo vẫn
          ghi "chạy GPU". Nghiệm thu `NEN_V3` (23/09) đoán sai đúng chỗ này.

    ⭐ Nên quy tắc ở đây là: **chỉ dùng card khi nền tảng đã cấp VÀ ghim được**.
       Người vận hành vẫn ép được bằng `LTT_AUTOSUB_WHISPER_DEVICE` —
       đó là một quyết định NÓI RA, không phải một mặc định lặng lẽ.
    """
    ep = os.environ.get("LTT_AUTOSUB_WHISPER_DEVICE", "").strip()
    ep_kieu = os.environ.get("LTT_AUTOSUB_WHISPER_COMPUTE", "").strip()
    if ep:
        return ep, (ep_kieu or ("float16" if ep == "cuda" else "int8")), 0, ""
    if not gpu_uuid.strip():
        return "cpu", (ep_kieu or "int8"), 0, "nen tang khong cap card (khong co lease)"
    i = _chi_so_card(gpu_uuid)
    if i < 0:
        return "cpu", (ep_kieu or "int8"), 0, (
            f"nen tang cap card {gpu_uuid[:20]} nhung torch khong thay no")
    return "cuda", (ep_kieu or "float16"), i, ""


def _get_faster_model(model_name: str, *, gpu_uuid: str = "") -> tuple[object, dict]:
    """Model faster-whisper + bản khai NÓ ĐANG CHẠY Ở ĐÂU.

    ⚠️ `import torch` **trước** `faster_whisper`: bản `torch …+cu128` đăng ký
       thư mục DLL của nó (`torch/lib`, nơi có `cublas64_12.dll`,
       `cudnn*64_9.dll`) qua `os.add_dll_directory`, và trên Windows
       CTranslate2 tìm cuBLAS/cuDNN ở đó. Đảo thứ tự thì `WhisperModel(
       device="cuda")` ném `Could not load library cublas64_12.dll` —
       `apps/asv_gpu/do_luong/giong_runner.py` đã gặp và ghi lại đúng bẫy này.

    ⛔ Không nuốt lỗi: mỗi lần lùi về CPU đều ghi log VÀ trả lý do ra ngoài.
    """
    try:
        import torch  # noqa: F401  (đăng ký thư mục DLL CUDA trên Windows)
    except ImportError:
        pass
    from faster_whisper import WhisperModel

    device, compute, chi_so, ly_do = _thiet_bi_asr(gpu_uuid)
    key = (model_name, device, compute, chi_so)
    with _MODEL_LOCK:
        if key not in _MODELS:
            try:
                _MODELS[key] = WhisperModel(model_name, device=device,
                                            compute_type=compute,
                                            device_index=chi_so)
            except Exception as exc:                          # noqa: BLE001
                if device == "cpu":
                    raise
                ly_do = f"{type(exc).__name__}: {exc}"[:300]
                log.warning("faster-whisper khong nap duoc tren %s/%s -> lui ve "
                            "cpu/int8: %s", device, compute, ly_do)
                device, compute, chi_so = "cpu", "int8", 0
                key = (model_name, device, compute, chi_so)
                if key not in _MODELS:
                    _MODELS[key] = WhisperModel(model_name, device="cpu",
                                                compute_type="int8")
        if ly_do:
            log.info("faster-whisper chay tren CPU: %s", ly_do)
        return _MODELS[key], {"asr_device": device, "asr_compute": compute,
                              "asr_device_index": chi_so,
                              "asr_cpu_reason": ly_do}


#: Câu mẫu CÓ dấu câu, ép Whisper chấm câu cho ngôn ngữ viết không có dấu cách.
#: ⛔ Nguồn: whisperX issue #645, trả lời của `leexinxu` (17/08/2024) — không phải
#:    câu ta soạn. Giữ khớp `whisperx_runner.MAU_CO_DAU_CAU`.
MAU_CO_DAU_CAU = {
    "zh": "以下是中文普通话句子。",
    "ja": "以下は日本語の文章です。",
}


def _transcribe_faster(media_path: str, *, language: str, model_name: str,
                       on_progress=None, is_cancelled=None,
                       gpu_uuid: str = "") -> dict:
    if on_progress:
        on_progress(8, "fallback faster-whisper")
    model, khai = _get_faster_model(model_name, gpu_uuid=gpu_uuid)
    # 🔴 **Cùng một sửa lỗi SẢN PHẨM như nhánh whisperx** (whisperX issue #645):
    #    Whisper trả về văn Hán KHÔNG một dấu câu nào, và điều đó làm hỏng **cả
    #    bước dịch** ở hạ nguồn, không riêng bước cắt đoạn. ⛔ Không phải mẹo để
    #    qua một cổng — nhánh này còn không đi qua cổng đó.
    #    Đo 24/09: 0 dấu câu / 646 ký tự trên nhánh mặc định trước khi vá.
    # ⚠️ `detect_language` đòi **mảng float 1-D 16 kHz**, ⛔ KHÔNG nhận đường dẫn
    #    (`faster_whisper.WhisperModel.detect_language(audio: np.ndarray)`).
    #    Bản vá đầu đưa `media_path` vào ⇒ ném ⇒ bị nuốt ⇒ `mau=None` ⇒ prompt
    #    **không hề chạy**, và bản chép ra y hệt lượt chưa vá — ⭐ đúng cái bẫy đã
    #    ghi ở `edbcbd57`, bắt được bằng đúng cách đó: kết quả không đổi MỘT ký tự.
    from faster_whisper.audio import decode_audio

    tieng = decode_audio(media_path, sampling_rate=16000)
    ngon = (language or "").lower()
    if not ngon:
        ngon = str(model.detect_language(tieng)[0] or "").lower()
    mau = MAU_CO_DAU_CAU.get(ngon[:2], None)
    # Truyền lại chính mảng đã giải mã: ⛔ đừng giải mã tệp hai lần.
    segments, info = model.transcribe(tieng, language=ngon or None,
                                      word_timestamps=True, vad_filter=True,
                                      beam_size=5, initial_prompt=mau)
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
            "fallback_reason": "whisperx_sidecar_unavailable", **khai}


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
            log.warning("WhisperX sidecar hong -> lui ve faster-whisper: %s",
                        str(exc)[:300])
            fallback = _transcribe_faster(media_path, language=language,
                                          model_name=model_name, on_progress=on_progress,
                                          is_cancelled=is_cancelled, gpu_uuid=gpu_uuid)
            fallback["fallback_reason"] = str(exc)[:300]
            return fallback
    return _transcribe_faster(media_path, language=language, model_name=model_name,
                              on_progress=on_progress, is_cancelled=is_cancelled,
                              gpu_uuid=gpu_uuid)
