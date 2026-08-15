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
import time

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


def _doi_hinh() -> list:
    """Đội hình worker: mỗi phần tử là (tập năng lực, số tiến trình).

    Vì sao cần chia lớp. Số tiến trình mặc định bằng **số GPU**, nhưng phần lớn
    công cụ đang mở chỉ khai ``requires=('api',)`` — chúng ngồi chờ mạng nhà
    cung cấp và không đụng tới card. Sizing theo GPU bắt chúng xếp hàng sau nhau
    không vì lý do gì, và một job chờ tám giây chiếm trọn một slot đáng lẽ dành
    cho việc dùng card.

    Khai bằng ``LTT_WORKER_POOLS``, ví dụ::

        LTT_WORKER_POOLS = "api:8, gpu:2"

    Tên pool là **năng lực** trong ``manifest.requires``, nên nền tảng vẫn không
    biết tên app nào (`AGENTS.md` 8.4). Một pool chỉ nhặt job của app khai đủ
    năng lực nằm gọn trong tập của nó — `jobs.claim()` đã lọc như vậy sẵn.

    Không khai thì giữ nguyên hành vi cũ: một pool đa năng. Đổi ngầm đội hình
    của một máy chủ đang chạy là thứ không ai muốn gặp sau khi cập nhật.

    Vì sao không tự suy ra đội hình: số worker `api` tối ưu phụ thuộc độ trễ nhà
    cung cấp và băng thông — hai thứ không đo được lúc khởi động. Đoán một con
    số rồi gọi là "tự động" chỉ là giấu một tham số, không phải bỏ nó đi.
    """
    dat = (os.environ.get("LTT_WORKER_POOLS") or "").strip()
    if not dat:
        return [(None, _so_tien_trinh())]

    doi_hinh: list = []
    for phan in dat.split(","):
        phan = phan.strip()
        if not phan:
            continue
        ten, _, so = phan.partition(":")
        ten = ten.strip().lower()
        try:
            n = max(1, min(16, int(so.strip() or "1")))
        except ValueError:
            log.warning("LTT_WORKER_POOLS: %r khong phai so — bo qua", phan)
            continue
        if not ten:
            continue
        # Pool `gpu` vẫn phải chạy được job chỉ cần `api`: một worker khai nhiều
        # năng lực hơn thì nhặt được nhiều loại hơn, không phải ít hơn.
        nang_luc = {"api"} | {t.strip() for t in ten.split("+") if t.strip()}
        doi_hinh.append((nang_luc, n))

    if not doi_hinh:
        log.warning("LTT_WORKER_POOLS khong doc duoc — dung mac dinh")
        return [(None, _so_tien_trinh())]
    return doi_hinh


def _chay_mot_worker(thu_tu: int, nang_luc=None) -> None:
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
    run_forever(worker_id, stop=lambda: dung["flag"],
                capabilities=set(nang_luc) if nang_luc else None)


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

    doi_hinh = _doi_hinh()
    tong = sum(so for _nang_luc, so in doi_hinh)
    if tong == 1 and doi_hinh[0][0] is None:
        # Đường một tiến trình giữ nguyên như trước: KHÔNG đẻ tiến trình con,
        # nên dịch vụ Windows vẫn giám sát đúng tiến trình đang làm việc.
        log.info("chay 1 tien trinh worker")
        _chay_mot_worker(0)
        return 0

    log.info("chay %s tien trinh worker: %s", tong,
             ", ".join(f"{sorted(nl) if nl else 'da nang'}x{so}"
                       for nl, so in doi_hinh))
    con: list = []
    #: Vị trí -> (năng lực, chỉ số pool). Cần để thay thế một con đã chết bằng
    #: đúng lớp của nó; thay bằng worker đa năng sẽ lặng lẽ đổi đội hình.
    nhan: list = []
    i = 0
    for nang_luc, so in doi_hinh:
        for _ in range(so):
            nhan.append((nang_luc, i))
            p = multiprocessing.Process(
                target=_chay_mot_worker,
                args=(i, sorted(nang_luc) if nang_luc else None),
                name=f"ltt-worker-{i}", daemon=False)
            p.start()
            con.append(p)
            i += 1

    # Con chết thì THAY THẾ. Trước đây cha chỉ `join()` rồi thôi, nên một tiến
    # trình con chết vì bất cứ lý do gì (OOM, thư viện C sập, vượt trần thời
    # gian) sẽ biến mất cho tới lần khởi động lại dịch vụ — đội hình teo dần và
    # không ai được báo. Với `LTT_WORKER_POOLS` thì điều đó còn tệ hơn: mất một
    # con nghĩa là mất cả một lớp tài nguyên.
    #
    # Vòng giám sát này cũng là thứ làm cho trần thời gian chạy an toàn: một job
    # treo kết thúc tiến trình của nó, và chỗ đó được lấp lại trong vài giây.
    dung_het = {"flag": False}

    def _dung_het(signum, frame):
        log.info("nhan tin hieu dung, bao %s tien trinh con thoat", len(con))
        dung_het["flag"] = True
        for p in con:
            if p.is_alive():
                p.terminate()

    signal.signal(signal.SIGINT, _dung_het)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _dung_het)

    try:
        while not dung_het["flag"]:
            for vi_tri, p in enumerate(con):
                if p.is_alive():
                    continue
                log.warning("worker %s (pid %s) da chet ma %s — thay the",
                            p.name, p.pid, p.exitcode)
                nang_luc, _ = nhan[vi_tri]
                moi = multiprocessing.Process(
                    target=_chay_mot_worker,
                    args=(vi_tri, sorted(nang_luc) if nang_luc else None),
                    name=f"ltt-worker-{vi_tri}", daemon=False)
                moi.start()
                con[vi_tri] = moi
            time.sleep(2.0)
    finally:
        # Tiến trình con KHÔNG được sống sót qua cha: dịch vụ Windows dừng cha
        # thì con phải chết theo, nếu không lần khởi động sau sẽ có worker mồ
        # côi vẫn nhặt job và ghi đè kết quả.
        for p in con:
            if p.is_alive():
                p.terminate()
                p.join(timeout=10)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()        # cần trên Windows (spawn)
    sys.exit(main())
