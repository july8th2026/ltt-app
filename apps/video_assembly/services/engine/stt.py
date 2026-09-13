import os, json
from ..tuong_thich.log import info, warn
from faster_whisper import WhisperModel


def transcribe_whisper(cfg: dict, voice_dir: str, out_json: str):
    audio_files = [
        f for f in os.listdir(voice_dir)
        if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"))
    ]
    if not audio_files:
        raise FileNotFoundError(
            f"Không tìm thấy file audio trong VOICE/: {voice_dir}\n"
            f"Hỗ trợ: .mp3, .wav, .m4a, .aac, .flac, .ogg"
        )
    voice_file = audio_files[0]
    voice_path = os.path.join(voice_dir, voice_file)

    wcfg = cfg.get("whisper", {})

    # Language: None = auto-detect (recommended for EN/VI mixed tabs)
    # Explicit "vi" or "en" = forced (faster, more accurate if known)
    language = wcfg.get("language") or None  # empty string → None = auto-detect
    if language:
        language = language.strip().lower() or None

    model_size = wcfg.get("model", "large-v3")

    # [ĐA GPU 2026-09] Đường STT CHÍNH của DUNGVIDEO. Trước đây chỉ đặt
    # device="cuda" (= cuda:0) nên mọi job đều dồn vào card 0 bất kể gpu_arbiter
    # cấp card nào. Model nạp TRONG process bot nên CUDA_VISIBLE_DEVICES không
    # còn tác dụng — phải truyền thẳng device_index cho ctranslate2.
    # (evaluation/adapters/whisper.py là đường KHÁC, đã sửa riêng.)
    try:
        from gpu_arbiter import current_gpu
        _gpu_idx = int(current_gpu())
    except Exception:
        _gpu_idx = 0
    model = WhisperModel(model_size, device="cuda", device_index=_gpu_idx,
                         compute_type="float16")
    info("whisper_model_pinned", gpu=_gpu_idx)

    info("whisper_start",
         voice=voice_path,
         model=model_size,
         language=language or "auto-detect")

    segments_gen, info_obj = model.transcribe(
        voice_path,
        language=language,
        word_timestamps=False,
        vad_filter=True,                    # suppress hallucinations in silence/music
        vad_parameters={
            "min_silence_duration_ms": 500, # ignore silence < 0.5s
            "threshold": 0.5,               # VAD sensitivity
        },
        condition_on_previous_text=False,   # prevent repeating previous text in long audio
        beam_size=5,
        temperature=0.0,                    # deterministic, reduces hallucination
    )

    out = [
        {"start": s.start, "end": s.end, "text": (s.text or "").strip()}
        for s in segments_gen
        if (s.text or "").strip()
    ]

    # Log detected language when auto
    if not language:
        detected = getattr(info_obj, "language", "unknown")
        detected_prob = getattr(info_obj, "language_probability", 0)
        info("whisper_detected_language", language=detected, probability=f"{detected_prob:.2f}")
        if detected_prob < 0.7:
            warn("whisper_low_language_confidence",
                 detected=detected,
                 probability=f"{detected_prob:.2f}",
                 suggestion="Consider setting explicit language in whisper config")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    info("whisper_done", voice=voice_path, segments=len(out))

    # Giải phóng Whisper model khỏi VRAM — tránh block GpuSlot check ở job tiếp theo
    del model
    try:
        import gc
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

    return out
