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
import inspect
import json


#: Cau mau CO dau cau, ep Whisper cham cau cho ngon ngu khong co dau cach.
#: ⛔ Nguon: whisperX issue #645, tra loi cua `leexinxu` — khong phai cau ta soan.
MAU_CO_DAU_CAU = {
    "zh": "以下是中文普通话句子。",
    "ja": "以下は日本語の文章です。",
}


def _phien_ban_whisperx() -> str:
    """Phiên bản gói THẬT đang chạy. ⛔ Đừng gõ lại một con số vào mã."""
    try:
        from importlib.metadata import version

        return str(version("whisperx"))
    except Exception:                           # noqa: BLE001
        return ""


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

    # 🔴 **Nhan ngon ngu TRUOC, roi moi dat prompt.** ⛔ Doc `args.language` la
    #    sai: ASV goi runner nay voi `--language` RONG khi khach de "tu doan", va
    #    do la ca THUONG GAP. Do that 24/09: ban va doc `args.language` chay xong
    #    mot luot 25,3 giay tren card ma prompt KHONG HE duoc ap — ban chep ra y
    #    het luot truoc, tung chu, va `khoa_chung` khac nhau nen do khong phai
    #    cache. ⭐ Mot thay doi "da ap dung" ma ket qua khong doi MOT KY TU la
    #    dau hieu no chua bao gio chay, khong phai dau hieu no vo dung.
    ngon = (args.language or model.detect_language(audio) or "").lower()
    mau = MAU_CO_DAU_CAU.get(ngon[:2], "")
    if mau:
        # `TranscriptionOptions` la dataclass (faster-whisper), va whisperx giu
        # no o `pipeline.options` (`asr.py:437`). ⛔ Khong sua goi da cai — chi
        # doi tuy chon cua MOT the hien ta vua tao.
        import dataclasses
        model.options = dataclasses.replace(model.options, initial_prompt=mau)

    raw = model.transcribe(audio, batch_size=8, language=ngon or None)
    language = str(raw.get("language") or args.language or "")
    align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
    aligned = whisperx.align(raw["segments"], align_model, metadata, audio, device,
                             return_char_alignments=False)
    # 🔴 **GHIM THAM SỐ — ⛔ không phải log, là một phần của BẢN GHI.**
    #
    #    Một bản chép lời **không tái lập được** thì mọi con số đo trên nó — CER,
    #    phân đoạn, và mọi điểm DỊCH mà B2 sẽ đo — cũng không tái lập được. Nên
    #    các tham số quyết định đầu ra phải đi **cùng** đầu ra, ⛔ không nằm rải
    #    rác trong mã mà người đọc phải đi tìm.
    #
    # ⭐ Ghi **giá trị THẬT đã dùng**, ⛔ không phải giá trị mặc định ta tưởng:
    #    `chunk_size` không được khai ở đây nên nó là mặc định của
    #    `FasterWhisperPipeline.transcribe` (`whisperx/asr.py:204  chunk_size=30`)
    #    — và chính con số đó là thứ đã sinh ra khối ~30 giây.
    import whisperx.asr as _asr
    from whisperx.alignment import DEFAULT_ALIGN_MODELS_HF, DEFAULT_ALIGN_MODELS_TORCH

    try:
        _ck = inspect.signature(
            _asr.FasterWhisperPipeline.transcribe).parameters["chunk_size"].default
    except Exception:                           # noqa: BLE001
        _ck = None                              # ⛔ không đoán: thiếu thì khai thiếu
    # ⭐ Giá trị ở đây là **MÃ**, ⛔ không phải câu văn: chúng đi vào một bản ghi
    #    JSON để máy `grep` và để đối chiếu giữa các lượt, không hiện ra cho
    #    khách. (Và runner này chạy bằng trình thông dịch sidecar, nơi
    #    `platform_core.i18n` không nhập được.)
    #      whisperx_mac_dinh_ta_khong_khai  `chunk_size` là mặc định của gói
    #      tham_so | detect_language        ngôn ngữ đến từ đâu
    #      whisperx_issue_645               nguồn của `initial_prompt`
    tham_so = {
        "engine": "whisperx", "phien_ban": _phien_ban_whisperx(),
        "model_asr": args.model, "batch_size": 8,
        "chunk_size": _ck, "chunk_size_nguon": "whisperx_mac_dinh_ta_khong_khai",
        "ngon_ngu_yeu_cau": args.language or "", "ngon_ngu_dung": language,
        "ngon_ngu_do_bang": "tham_so" if args.language else "detect_language",
        "initial_prompt": mau or "",
        "initial_prompt_nguon": ("whisperx_issue_645" if mau
                                 else "khong_ap_ngon_ngu_co_dau_cach"),
        "model_can_chinh": (DEFAULT_ALIGN_MODELS_HF.get(language[:2])
                            or DEFAULT_ALIGN_MODELS_TORCH.get(language[:2]) or ""),
        "return_char_alignments": False,
    }
    payload = {"segments": aligned.get("segments") or [], "language": language,
               "engine": "whisperx", "alignment_status": "aligned",
               "fallback_reason": "", "tham_so": tham_so}
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, allow_nan=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
