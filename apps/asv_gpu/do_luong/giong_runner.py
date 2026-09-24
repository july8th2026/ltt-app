"""Runner bo do `giong` — chay TRONG `qc-venv`. Xem `giong.py`.

    python giong_runner.py vao.json ra.json

Nap faster-whisper MOT lan, chep tung doan (ep ngon ngu dich), chuan hoa hai ve
bang `chuan_hoa_loi.chuan_hoa`, cham bang jiwer, roi THOAT (tra VRAM).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from apps.asv_gpu.do_luong import _runner  # noqa: E402


def main() -> None:
    vao, ra = _runner.mo()
    dh = _runner.DongHo()
    try:
        # ⚠️ torch TRUOC faster_whisper: ban torch cu128 dang ky thu muc DLL
        #    cuDNN/cuBLAS cua no, va ctranslate2 tim chung o do tren Windows.
        import torch  # noqa: F401
        import ctranslate2
        from faster_whisper import WhisperModel
        from huggingface_hub import snapshot_download
        import jiwer  # noqa: F401
    except ImportError as exc:
        _runner.khong_kha_dung(f"thieu thu vien trong qc-venv: {exc}")

    from apps.asv_gpu.do_luong import chuan_hoa_loi

    try:
        duong = snapshot_download(vao["repo"], revision=vao["revision"])
    except Exception as exc:                    # noqa: BLE001
        _runner.khong_kha_dung(f"khong lay duoc model {vao['repo']}@"
                               f"{vao['revision'][:10]}: {type(exc).__name__}")
    dh.danh_dau("tim_model")

    co_gpu = ctranslate2.get_cuda_device_count() > 0
    thiet_bi, kieu = ("cuda", "float16") if co_gpu else ("cpu", "int8")
    model = WhisperModel(duong, device=thiet_bi, compute_type=kieu)
    dh.danh_dau("nap_model")

    nn = str(vao.get("ngon_ngu") or "") or None
    tu_dien = vao.get("tu_dien") or {}
    ts = dict(vao.get("tham_so") or {})
    ket: dict = {}
    for d in vao["doan"]:
        doan_asr, info = model.transcribe(d["tep"], language=nn, **ts)
        doc_ra = " ".join(s.text.strip() for s in doan_asr).strip()
        tc = chuan_hoa_loi.chuan_hoa(d["chu"], nn or "", tu_dien)
        gt = chuan_hoa_loi.chuan_hoa(doc_ra, nn or "", tu_dien)
        ket[d["ma"]] = {"doc_ra": doc_ra, "tham_chieu_chuan": tc,
                        "gia_thuyet_chuan": gt,
                        "giay": round(float(getattr(info, "duration", 0.0)), 3),
                        **chuan_hoa_loi.cham(tc, gt, nn or "")}
    dh.danh_dau("chep_va_cham")
    del model
    _runner.ghi(ra, {"ket_qua": ket,
                     "tai_nguyen": dh.ket(thiet_bi=thiet_bi, kieu=kieu,
                                          so_doan=len(ket))})


if __name__ == "__main__":
    main()
