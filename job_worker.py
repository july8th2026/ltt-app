"""
job_worker.py — entry point của dịch vụ LTTWorker (H2, Q6).

Chạy vòng xử lý hàng đợi job, tiến trình RIÊNG với web. Trên máy chủ, đăng ký
làm dịch vụ Windows `LTTWorker` cạnh `LTTWeb` (setup/2-cai-dat.ps1).

    python job_worker.py

Cần `LTT_DATABASE_URL` (nằm trong secrets/app.env trên máy chủ). Không import
gì từ server/ — worker không phụ thuộc tầng web.
"""
from __future__ import annotations

import logging
import os
import signal
import socket
import sys


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("job_worker")

    try:
        from platform_core.db import database_url
        database_url()
    except Exception as exc:
        log.error("Khong chay duoc worker: %s", exc)
        return 2

    # Định danh worker: hostname + pid, để log và cột worker_id truy được máy nào.
    worker_id = f"{socket.gethostname()}:{os.getpid()}"

    dung = {"flag": False}

    def _xin_dung(signum, frame):
        log.info("nhan tin hieu dung, ket thuc luot hien tai roi thoat")
        dung["flag"] = True

    signal.signal(signal.SIGINT, _xin_dung)
    signal.signal(signal.SIGTERM, _xin_dung)

    from platform_core.job_runner import run_forever
    run_forever(worker_id, stop=lambda: dung["flag"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
