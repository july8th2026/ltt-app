"""
job_worker.py — entry point của dịch vụ LTTWorker (H2, Q6).

Chạy vòng xử lý hàng đợi job, tiến trình RIÊNG với web. Trên máy chủ, đăng ký
làm dịch vụ Windows `LTTWorker` cạnh `LTTWeb` (setup/2-cai-dat.ps1).

    python job_worker.py

Cần `LTT_DATABASE_URL` (nằm trong secrets/app.env trên máy chủ). Không import
gì từ server/ — worker không phụ thuộc tầng web.

## Vì sao có nhiều tiến trình (H23)

Một tiến trình chạy **một job tại một thời điểm**. Máy chủ có hai GPU từ
2026-08-06, nên một tiến trình nghĩa là card thứ hai **nằm không vĩnh viễn** —
có phần cứng mà không dùng được.

Số tiến trình mặc định = số GPU (tối thiểu 1), đặt lại bằng
`LTT_WORKER_PROCESSES`. Nhiều tiến trình an toàn vì hai lớp khoá đã có sẵn:
hàng đợi giành job bằng `FOR UPDATE SKIP LOCKED`, và GPU giành bằng
`UNIQUE(host, gpu_uuid)` trong `platform_core.gpu_lease`. Không có lớp thứ hai
thì hai tiến trình sẽ cùng nạp model lên một card và OOM.

Tiến trình con là **tiến trình riêng chứ không phải luồng**: job nặng gọi
thư viện C/CUDA giữ GIL và có thể sập cả tiến trình; một job hỏng không được
kéo theo job của khách hàng khác.
"""
from __future__ import annotations

import logging
import multiprocessing
import os
import signal
import socket
import sys

from platform_core.observability import configure_logging

log = logging.getLogger("job_worker")


def _so_tien_trinh() -> int:
    """Bao nhiêu worker chạy song song. Mặc định = số GPU, tối thiểu 1."""
    dat = (os.environ.get("LTT_WORKER_PROCESSES") or "").strip()
    if dat:
        try:
            return max(1, min(16, int(dat)))
        except ValueError:
            log.warning("LTT_WORKER_PROCESSES=%r không phải số — dùng mặc định", dat)
    try:
        from platform_core import gpu
        return max(1, len(gpu.list_gpus()))
    except Exception:                       # noqa: BLE001
        log.exception("Không đếm được GPU — chạy 1 tiến trình")
        return 1


def _chay_mot_worker(thu_tu: int) -> None:
    """Thân của MỘT tiến trình worker. Phải ở cấp module để Windows spawn được."""
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s %(levelname)s [w{thu_tu}] %(name)s: %(message)s",
    )
    configure_logging(component=f"job-worker-{thu_tu}")
    # pid nằm trong worker_id nên mỗi tiến trình là một worker khác nhau trong
    # bảng jobs — truy được job nào chạy ở đâu.
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    dung = {"flag": False}

    def _xin_dung(signum, frame):
        logging.getLogger("job_worker").info(
            "nhan tin hieu dung, ket thuc luot hien tai roi thoat")
        dung["flag"] = True

    signal.signal(signal.SIGINT, _xin_dung)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _xin_dung)

    from platform_core.job_runner import run_forever
    run_forever(worker_id, stop=lambda: dung["flag"])


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    configure_logging(component="job-worker")

    try:
        from platform_core.db import database_url
        database_url()
    except Exception as exc:
        log.error("Khong chay duoc worker: %s", exc)
        return 2

    n = _so_tien_trinh()
    if n == 1:
        # Đường một tiến trình giữ nguyên như trước: KHÔNG đẻ tiến trình con,
        # nên dịch vụ Windows vẫn giám sát đúng tiến trình đang làm việc.
        log.info("chay 1 tien trinh worker")
        _chay_mot_worker(0)
        return 0

    log.info("chay %s tien trinh worker song song", n)
    con: list = []
    for i in range(n):
        p = multiprocessing.Process(target=_chay_mot_worker, args=(i,),
                                    name=f"ltt-worker-{i}", daemon=False)
        p.start()
        con.append(p)

    def _dung_het(signum, frame):
        log.info("nhan tin hieu dung, bao %s tien trinh con thoat", len(con))
        for p in con:
            if p.is_alive():
                p.terminate()

    signal.signal(signal.SIGINT, _dung_het)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _dung_het)

    # Tiến trình con KHÔNG được sống sót qua cha: dịch vụ Windows dừng cha thì
    # con phải chết theo, nếu không lần khởi động sau sẽ có worker mồ côi vẫn
    # nhặt job và ghi đè kết quả.
    try:
        for p in con:
            p.join()
    finally:
        for p in con:
            if p.is_alive():
                p.terminate()
                p.join(timeout=10)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()        # cần trên Windows (spawn)
    sys.exit(main())
