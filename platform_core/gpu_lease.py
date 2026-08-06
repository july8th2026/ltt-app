"""
gpu_lease.py — giành và trả chỗ trên GPU, nguyên tử (H23).

Bài toán: máy có 2 GPU, worker có thể chạy nhiều tiến trình. Nếu mỗi tiến trình
tự hỏi `nvidia-smi` rồi chọn card trống nhất thì hai tiến trình khởi động cùng
lúc sẽ **cùng đọc thấy GPU 0 trống**, cùng chọn nó, cùng nạp model, cùng OOM.
Lỗi hiện ra giữa job của khách hàng, không phải lúc xếp lịch.

Cách giải: đúng khuôn mà hàng đợi job đã dùng và đã chạy ổn từ H2 —

    thu hồi lease mồ côi → giành chỗ → đập nhịp trong lúc chạy → trả chỗ

Điểm khác một chút: hàng đợi job giành bằng `FOR UPDATE SKIP LOCKED`, ở đây
giành bằng **ràng buộc UNIQUE(host, gpu_uuid)**. Hai INSERT cùng lúc thì CSDL
cho đúng một cái thắng, cái thua nhận `IntegrityError` và thử GPU tiếp theo.
Không cần khoá bảng, không có cửa sổ đọc-rồi-ghi.

Máy không có GPU vẫn dùng được module này: `acquire()` trả None và caller chạy
bằng CPU như trước.
"""
from __future__ import annotations

import logging
import socket
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from platform_core import gpu as gpu_mod
from platform_core.models import GpuLease

log = logging.getLogger(__name__)

# Worker chết giữa chừng thì lease phải tự hết hạn, nếu không GPU khoá vĩnh viễn.
# Rộng hơn nhịp đập nhiều lần để một lần GC dài hay đĩa chậm không cướp mất GPU
# của job đang chạy thật.
ORPHAN_TIMEOUT = timedelta(minutes=10)

# Chừa lại cho phân mảnh và cho phần driver/desktop chiếm. Xin đúng sát dung
# lượng còn trống là công thức chắc chắn OOM.
HEADROOM_MB = 1024


def _now() -> datetime:
    return datetime.now(timezone.utc)


def host_name() -> str:
    return socket.gethostname()


def reclaim_orphans(db: DbSession, *, timeout: timedelta = ORPHAN_TIMEOUT) -> int:
    """Xoá lease của worker đã chết. Trả số lease thu hồi được."""
    cutoff = _now() - timeout
    rows = db.execute(select(GpuLease).where(GpuLease.host == host_name())).scalars().all()
    n = 0
    for row in rows:
        hb = row.heartbeat_at
        if hb is not None and hb.tzinfo is None:        # SQLite trả naive
            hb = hb.replace(tzinfo=timezone.utc)
        if hb is None or hb < cutoff:
            log.warning("Thu hồi lease GPU mồ côi: %s (job=%s, worker=%s)",
                        row.gpu_uuid[:20], row.job_id[:8], row.worker_id)
            db.delete(row)
            n += 1
    if n:
        db.commit()
    return n


def busy_uuids(db: DbSession) -> set[str]:
    """UUID của các GPU đang có lease trên máy này."""
    return set(db.execute(
        select(GpuLease.gpu_uuid).where(GpuLease.host == host_name())
    ).scalars().all())


def acquire(db: DbSession, *, worker_id: str, job_id: str = "",
            need_mb: int = 0) -> GpuLease | None:
    """Giành một GPU còn đủ chỗ. Trả None nếu không có cái nào.

    None có hai nghĩa và caller phải xử cả hai: máy **không có GPU** (chạy CPU),
    hoặc GPU **đều đang bận** (chờ lượt sau). Cả hai đều không phải lỗi.

    Chọn GPU trống nhiều nhất trước — job nặng vào card rảnh nhất, và hai job
    liên tiếp không dồn vào cùng một card.
    """
    gpus = gpu_mod.list_gpus()
    if not gpus:
        return None

    reclaim_orphans(db)
    taken = busy_uuids(db)
    ung_vien = [g for g in gpus
                if g.uuid not in taken and g.free_mb >= need_mb + HEADROOM_MB]
    ung_vien.sort(key=lambda g: g.free_mb, reverse=True)

    for g in ung_vien:
        lease = GpuLease(host=host_name(), gpu_uuid=g.uuid, gpu_index=g.index,
                         worker_id=worker_id, job_id=job_id, vram_mb=need_mb,
                         acquired_at=_now(), heartbeat_at=_now())
        db.add(lease)
        try:
            db.commit()
        except IntegrityError:
            # Worker khác vừa giành đúng GPU này giữa lúc ta đọc và ghi. Đây là
            # đường chạy BÌNH THƯỜNG của cơ chế, không phải sự cố — lùi lại và
            # thử card tiếp theo.
            db.rollback()
            continue
        db.refresh(lease)
        log.info("Giành GPU %s (index %s) cho job %s", g.uuid[:20], g.index, job_id[:8])
        return lease
    return None


def heartbeat(db: DbSession, lease: GpuLease) -> None:
    """Báo lease còn sống. Phải gọi định kỳ suốt thời gian chạy."""
    lease.heartbeat_at = _now()
    db.commit()


def release(db: DbSession, lease: GpuLease) -> None:
    """Trả chỗ. Gọi được nhiều lần mà không sao."""
    obj = db.get(GpuLease, lease.id)
    if obj is not None:
        db.delete(obj)
        db.commit()
        log.info("Trả GPU %s (job %s)", obj.gpu_uuid[:20], obj.job_id[:8])


@contextmanager
def hold(db: DbSession, *, worker_id: str, job_id: str = "", need_mb: int = 0):
    """Giành GPU trong một khối `with`, **luôn** trả lại kể cả khi handler ném.

    Quên trả lease thì GPU khoá tới khi hết hạn mồ côi (10 phút) — đủ để một
    chuỗi job lỗi làm đứng cả hàng đợi. Nên đường dùng mặc định phải là khối
    `with` chứ không phải gọi tay `acquire`/`release`.

        with gpu_lease.hold(db, worker_id=wid, job_id=jid, need_mb=6000) as l:
            env = gpu.env_for(l.gpu_uuid) if l else None
            ...
    """
    lease = acquire(db, worker_id=worker_id, job_id=job_id, need_mb=need_mb)
    try:
        yield lease
    finally:
        if lease is not None:
            try:
                release(db, lease)
            except Exception:               # noqa: BLE001 - trả chỗ không được nuốt job
                log.exception("Không trả được lease GPU %s — sẽ hết hạn sau %s",
                              lease.gpu_uuid[:20], ORPHAN_TIMEOUT)
