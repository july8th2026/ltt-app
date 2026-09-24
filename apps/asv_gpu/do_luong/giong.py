"""Bo do `giong`: tieng DA LONG → ASR → WER/CER so voi kich ban may doc da nhan.

    do_giong(doan=[{ma, tep, chu}], ngon_ngu, tu_dien, model, gpu_uuid)
      -> {"ket_qua": {ma: {doc_ra, wer, cer?, so_tu, thay, xoa, chen, ...}},
          "tai_nguyen": {...}}

ASR = faster-whisper voi CUNG ten model san pham dung o TRANSCRIBE
(`giai_doan_chep_loi.MODEL_ASR`, giai doan truyen vao) — khong them model moi.
Weights ghim theo commit Hugging Face o `MODEL_GHIM`; ten model khong co trong
bang ⇒ `khong_kha_dung` (khong tai mot ban khong ghim).

Chuan hoa + cham: `chuan_hoa_loi.py` (mot ham cho ca hai ve) + `jiwer` 4.0.0
(Apache-2.0). Chay trong `qc-venv` qua `giong_runner.py`.
"""
from __future__ import annotations

import wave
from pathlib import Path

from . import chuan_hoa_loi, venv
from .venv import KhongKhaDung

SCRIPT = Path(__file__).with_name("giong_runner.py")

#: Ten model (hang so san pham) -> (repo HF, commit ghim). Commit la ban DA co
#: trong `C:\LTTPlatform\hf-cache` ngay 22/09/2026 — cung ban TRANSCRIBE dang
#: dung (faster-whisper tra `large-v3` ve dung repo nay).
MODEL_GHIM = {
    "large-v3": ("Systran/faster-whisper-large-v3",
                 "edaa852ec7e145841d8ffdb056a99866b5f0a478"),
}

#: Tham so giai ma. Vao phien ban bo do.
#:
#: ⭐ `vad_filter=False`: dau vao la MOT cau da cat san, khong co khoang lang dai
#:    can bo; VAD (Silero) co the cat mat am dau yeu cua cau — sinh loi XOA gia
#:    dung loai loi ta dang do. San pham bat VAD o TRANSCRIBE vi do la ca bai dai.
#: ⭐ `condition_on_previous_text=False`: moi doan doc lap, khong de cau truoc
#:    "moi" chu cho cau sau.
THAM_SO_ASR = {"beam_size": 5, "vad_filter": False,
               "condition_on_previous_text": False, "without_timestamps": True}

PHIEN_BAN = f"asr+jiwer/1/chuan_hoa/{chuan_hoa_loi.PHIEN_BAN_CHUAN_HOA}"


def _giay(tep: str) -> float:
    try:
        with wave.open(str(tep), "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except (OSError, wave.Error, EOFError):
        return 0.0


def do_giong(doan: list[dict], *, ngon_ngu: str, tu_dien: dict | None = None,
             model: str = "large-v3", gpu_uuid: str = "",
             is_cancelled=None) -> dict:
    if model not in MODEL_GHIM:
        raise KhongKhaDung(f"model ASR {model!r} chua ghim commit trong MODEL_GHIM")
    repo, rev = MODEL_GHIM[model]
    doan = [{"ma": str(d["ma"]), "tep": str(d["tep"]), "chu": str(d.get("chu") or "")}
            for d in doan or []]
    tong = sum(_giay(d["tep"]) for d in doan)
    # Nap model ~20 s + giai ma. 3x thoi gian tieng la tran CPU (int8) du phong.
    han = int(300 + 3 * tong)
    return venv.chay(SCRIPT, {"doan": doan, "ngon_ngu": ngon_ngu,
                              "tu_dien": dict(tu_dien or {}), "repo": repo,
                              "revision": rev, "tham_so": THAM_SO_ASR},
                     timeout_s=han, gpu_uuid=gpu_uuid, is_cancelled=is_cancelled)
