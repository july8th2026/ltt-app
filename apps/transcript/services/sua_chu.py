"""Bước giữa STT và dựng dòng thời gian — port ĐÚNG các quy tắc của `bot_transcript`.

Đối chiếu 22/09/2026 (bảng quy tắc legacy ↔ LTT): bản port đầu **chép** fixer V5
nhưng **không gọi**, và không chép ba từ điển — nên mọi sửa từ, viết hoa tên riêng,
lọc câu lặp của legacy đều mất. Tệp này đưa chúng về, theo đúng thứ tự legacy:

```
STT (platform_core.stt)  ->  chuan_doan_tho()        whisper_integration.py:140-150, :75-97
                         ->  sua_chu_v5()            whisper_integration.py:319-339
                         ->  kiem_moc_tu()           engine/stt.py:113-190 (sau V5, :224)
```

Nguồn legacy (chỉ đọc): `D:\\FULL AUTO VIDEO\\BOT_TRANSCRIPT\\Bot_Whisper_FULL\\`.
Từ điển: `engine/{vi_corrections,en_corrections,vi_proper_nouns}.json` — chép nguyên
byte cạnh `engine/comprehensive_fixer_v5.py` (fixer đọc từ chính thư mục của nó).
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from .engine.comprehensive_fixer_v5 import ComprehensiveTranscriptFixerV5


class LoiMocTu(ValueError):
    """Mốc từ thiếu hoặc bị đóng băng — không dựng được dòng thời gian tin được."""


def chuan_doan_tho(doan: list[dict]) -> list[dict]:
    """Đoạn của `platform_core.stt` -> dạng legacy mà V5 và timeline đọc.

    - bỏ đoạn chữ rỗng; đảo `start/end` nếu ngược; bỏ đoạn < 0.02 s
      (`whisper_integration.py:142-150`);
    - từ: khoá chữ là **`word`** (service STT ghi `text`), bỏ từ rỗng và từ
      `end <= start` (`_convert_words`, :75-97).
    """
    ra: list[dict] = []
    for d in doan or []:
        if not isinstance(d, dict):
            continue
        chu = str(d.get("text") or "").strip()
        if not chu:
            continue
        st, en = float(d.get("start", 0.0)), float(d.get("end", 0.0))
        if en < st:
            st, en = en, st
        if en - st < 0.02:
            continue
        tu: list[dict[str, Any]] = []
        for w in d.get("words") or []:
            if not isinstance(w, dict):
                continue
            wchu = str(w.get("word") or w.get("text") or "").strip()
            try:
                wst, wen = float(w.get("start", st)), float(w.get("end", en))
            except (TypeError, ValueError):
                continue
            if not wchu or wen <= wst:
                continue
            tu.append({"word": wchu, "start": wst, "end": wen,
                       "prob": w.get("probability", w.get("prob"))})
        ra.append({"start": st, "end": en, "text": chu, "type": "speech",
                   "words": tu})
    return ra


def sua_chu_v5(doan: list[dict], ngon_ngu: str) -> list[dict]:
    """Fixer V5 với ĐÚNG tham số legacy (`whisper_integration.py:324-336`):
    ảo giác bật (ngưỡng 0.80), nối câu dở bật (trần 30 s), sửa mốc tắt; từ điển
    chọn theo ngôn ngữ đã dò (`set_language`)."""
    fixer = ComprehensiveTranscriptFixerV5(
        max_segment_duration=30.0,
        enable_hallucination_removal=True,
        enable_sentence_completion=True,
        enable_timestamp_fix=False,
        hallucination_similarity_threshold=0.80,
        debug_print=False,
    )
    fixer.set_language(str(ngon_ngu or "").strip().lower())
    return list(fixer.process(doan)["segments"])


def kiem_moc_tu(doan: list[dict], *, nguong_dong_bang: float = 0.20) -> dict:
    """`engine/stt.py::_validate_words_or_error` — HARD RULE của legacy.

    - MỌI đoạn phải có `words` (không cho phép đoạn nào thiếu);
    - "đóng băng": tỉ lệ `max(số từ trùng start, số từ trùng end) / tổng từ`
      >= 0.20 là lỗi (whisper trả cùng một mốc cho hàng loạt từ).
    """
    if not doan:
        raise LoiMocTu("STT segments empty/invalid")
    thieu = sum(1 for d in doan
                if not isinstance(d.get("words"), list) or not d.get("words"))
    if thieu:
        raise LoiMocTu(
            f"word_timestamps_missing: missing_words_segments={thieu}/{len(doan)}")
    starts: list[float] = []
    ends: list[float] = []
    for d in doan:
        for w in d["words"]:
            try:
                st, en = float(w.get("start")), float(w.get("end"))
            except (TypeError, ValueError):
                continue
            if en <= st:
                continue
            starts.append(st)
            ends.append(en)
    tong = len(starts)
    if tong <= 0:
        raise LoiMocTu("word_timestamps_empty_or_invalid: total_words=0")
    dong_bang = max(Counter(starts).most_common(1)[0][1],
                    Counter(ends).most_common(1)[0][1]) / max(1, tong)
    if dong_bang >= nguong_dong_bang:
        raise LoiMocTu(
            f"word_timestamps_frozen: freeze_ratio={dong_bang:.3f} "
            f"(threshold={nguong_dong_bang:.3f}) total_words={tong}")
    return {"total_words": tong, "freeze_ratio": round(dong_bang, 4)}
