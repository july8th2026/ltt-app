"""Isolated WhisperX runner. Execute only with the dedicated sidecar Python."""
from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--language", default="")
    args = parser.parse_args()

    import torch
    import whisperx
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    audio = whisperx.load_audio(args.input)
    model = whisperx.load_model(args.model, device, compute_type=compute,
                                language=args.language or None)
    raw = model.transcribe(audio, batch_size=8, language=args.language or None)
    language = str(raw.get("language") or args.language or "")
    align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
    aligned = whisperx.align(raw["segments"], align_model, metadata, audio, device,
                             return_char_alignments=False)
    payload = {"segments": aligned.get("segments") or [], "language": language,
               "engine": "whisperx", "alignment_status": "aligned",
               "fallback_reason": ""}
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, allow_nan=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
