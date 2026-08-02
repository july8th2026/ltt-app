"""
codex_sidecar_main.py — điểm chạy dịch vụ SIDECAR (NSSM: LTTStudioCodex).

Nghe 127.0.0.1:<LTT_CODEX_SIDECAR_PORT> (mặc định 8110). Bọc Codex app-server; chỉ
platform web/worker (cùng máy, có bearer token) gọi tới.
"""
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.environ.get("LTT_CODEX_SIDECAR_PORT", "8110"))
    uvicorn.run("codex_sidecar.server:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
