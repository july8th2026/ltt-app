"""Isolated WhisperX runner. Execute only with the dedicated sidecar Python.

## `initial_prompt` cho tieng Han — ⛔ khong phai mot tinh chinh, la mot TIEN DE

Do that 24/09 (phim v3, whisperx 3.8.6, nhanh `aligned`, 646 moc tu THAT):

    dau cau trong 646 ky tu ASR tra ve:   。0   ，0   ！0   ？0   、0   . 0

**Khong mot dau cau nao.** Hardsub cua chinh phim do cho 95 dong / 0,97 giay mot
dong. ⇒ Moi cach chia doan theo dau cau — cua WhisperX (`align()` goi NLTK
Punkt), cua `SubtitlesProcessor`, cua ta — deu **khong co gi de bam vao**.

⭐ Va khoang lang cung khong cuu duoc: do tren cung ban ghi, **640/640 khe giua
   hai ky tu lien tiep = 0,000 giay** (WhisperX gan span ky tu LIEN TIEP, im lang
   bi nuot vao do dai cua chinh ky tu do). Khong co dau cau VA khong co khoang
   lang thi khong con mot cho ngat HOP LE nao.

Nguon cach sua — `m-bain/whisperX` **issue #645** *"No punctuation for Chinese"*,
tra loi cua `leexinxu` (17/08/2024, 3 👍):

    asr_options = {"initial_prompt": "以下是中文普通话句子。"}
    whisperx.load_model(..., asr_options=asr_options)

Whisper bam theo VAN PHONG cua `initial_prompt`; mot cau mau CO dau cham cau keo
ca ban chep di theo. `asr.py:47-50` nap prompt do vao `all_tokens`, va
`asr.py:401` cho phep ghi de `default_asr_options`.

⚠️ ⛔ Prompt nay **doi ban chep**, nen no doi ca CER — phai do lai, khong duoc
   suy. Va no chi dat cho `zh`: ep mot cau mau tieng Han vao mot phim tieng Anh
   la ep van phong sai.
"""
from __future__ import annotations

import argparse
import json


#: Cau mau CO dau cau, ep Whisper cham cau cho ngon ngu khong co dau cach.
#: ⛔ Nguon: whisperX issue #645, tra loi cua `leexinxu` — khong phai cau ta soan.
MAU_CO_DAU_CAU = {
    "zh": "以下是中文普通话句子。",
    "ja": "以下は日本語の文章です。",
}


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
    # ⛔ CHI cho ngon ngu khong co dau cach: do la noi Whisper tra ve van ban
    #    KHONG dau cau, va la noi moi phep chia doan chet theo. Xem docstring.
    tuy_chon = {}
    if (args.language or "").lower()[:2] in ("zh", "ja"):
        tuy_chon["initial_prompt"] = MAU_CO_DAU_CAU.get(
            (args.language or "").lower()[:2], "")
    model = whisperx.load_model(args.model, device, compute_type=compute,
                                language=args.language or None,
                                asr_options=tuy_chon or None)
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
