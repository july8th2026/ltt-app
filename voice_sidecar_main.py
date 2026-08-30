"""
voice_sidecar_main.py — diem chay dich vu SIDECAR (NSSM: LTTStudioVoice).

    C:\LTTPlatform\vieneu-venv\Scripts\python.exe voice_sidecar_main.py

Nghe 127.0.0.1:<LTT_VOICE_SIDECAR_PORT> (mac dinh 8120). Boc VieNeu-TTS v3 Turbo;
chi platform web/worker (cung may, co bearer token) goi toi.

Khuon lay tu `codex_sidecar_main.py` da chay that tren may A.
"""
from __future__ import annotations

import logging
import os

import uvicorn


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LTT_VOICE_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    port = int(os.environ.get("LTT_VOICE_SIDECAR_PORT", "8120"))
    # KHONG BAO GIO doi khoi 127.0.0.1. Cong nay khong co xac thuc nao ngoai mot
    # bearer token dung chung, va no nhan duong dan tep cuc bo.
    uvicorn.run("voice_sidecar.server:app", host="127.0.0.1", port=port,
                log_level="info", workers=1)


if __name__ == "__main__":
    main()
