"""Lease có tên: cho phép đúng MỘT tiến trình làm một việc, và tự lành.

Nền tảng chạy nhiều tiến trình worker (số tiến trình mặc định = số GPU). Hàng
đợi job được thiết kế cho điều đó từ đầu — `jobs.claim()` dùng
``FOR UPDATE SKIP LOCKED``. Nhưng mọi **việc nền** viết sau đó (dọn dữ liệu, gửi
webhook, quét cảnh báo, ghi metrics) lại được viết với giả định ngầm ngược lại:
"chỉ có một tiến trình chạy vòng này".

Không ai viết giả định đó ra, nên không ai kiểm nó, và nó sai. Module này biến
nó thành một cơ chế có tên gọi.

## Vì sao là bảng, không phải `pg_advisory_lock`

Advisory lock của PostgreSQL sạch hơn và tự nhả khi mất kết nối. Nhưng **SQLite
không có** — nghĩa là đường chạy quan trọng nhất của nền tảng sẽ không có test
nào đi qua nó ở nơi dễ chạy nhất. Lease bằng bảng chạy giống hệt trên cả hai
engine, và mẫu này đã được `platform_core/gpu_lease.py` chứng minh trong
production: giành bằng INSERT, `IntegrityError` nghĩa là **người khác đã giành
trước** — đó là đường chạy bình thường, không phải sự cố.

## Vì sao tự lành quan trọng hơn giành đúng

Tiến trình giữ lease sẽ chết: bị kill, mất điện, worker khởi động lại khi cập
nhật. Nếu lease không hết hạn thì việc nền **dừng vĩnh viễn và im lặng** — không
job nào hỏng để ai nhận ra, chỉ là webhook không còn được gửi. Nên lease có hạn
và phải đập nhịp để giữ; chủ chết thì tiến trình khác nhận trong một chu kỳ.
"""
from __future__ import annotations

import logging
import socket
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import Session as DbSession

from platform_core.models import SingletonLease

log = logging.getLogger(__name__)

#: Lease sống bao lâu nếu không được đập nhịp. Đủ dài để một lượt bảo trì chậm
#: (dọn dữ liệu trên bảng lớn) không làm mất lease giữa chừng, đủ ngắn để việc
#: nền không đứng lâu sau khi chủ chết.
DEFAULT_TTL = timedelta(minutes=2)

#: Tên các lease nền tảng dùng. Đặt hằng số vì tên lease là hợp đồng giữa các
#: tiến trình: gõ sai một chữ nghĩa là hai tiến trình cùng tưởng mình độc quyền.
MAINTENANCE = "maintenance"
WEB = "web"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    """PostgreSQL trả datetime có múi giờ, SQLite trả naive. So sánh cần cùng loại."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def holder_id() -> str:
    """Nhận dạng tiến trình này: máy + pid. Truy được ai đang giữ."""
    return f"{socket.gethostname()}:{os.getpid()}"


def reclaim_expired(db: DbSession, *, name: str,
                    ttl: timedelta = DEFAULT_TTL) -> bool:
    """Xoá lease đã quá hạn đập nhịp. True nếu có xoá."""
    row = db.execute(select(SingletonLease).where(
        SingletonLease.name == str(name))).scalar_one_or_none()
    if row is None:
        return False
    beat = _aware(row.heartbeat_at) or _aware(row.acquired_at)
    if beat is not None and beat > _now() - ttl:
        return False
    log.info("thu hoi lease %r cua %s (qua han dap nhip)", name, row.holder)
    db.delete(row)
    db.flush()
    return True


def acquire(db: DbSession, *, name: str, holder: str = "",
            ttl: timedelta = DEFAULT_TTL) -> SingletonLease | None:
    """Giành lease `name`. Trả None khi tiến trình khác đang giữ.

    None **không phải lỗi**: nó là câu trả lời bình thường cho "tôi có phải
    người chạy việc này không". Caller đợi lượt sau.
    """
    who = holder or holder_id()
    reclaim_expired(db, name=name, ttl=ttl)

    row = SingletonLease(name=str(name), holder=who,
                         acquired_at=_now(), heartbeat_at=_now())
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Tiến trình khác vừa giành đúng lease này giữa lúc ta đọc và ghi. Đây
        # là đường chạy BÌNH THƯỜNG của cơ chế — lùi lại, không phải sự cố.
        db.rollback()
        return None
    db.refresh(row)
    log.info("giu lease %r (%s)", name, who)
    return row


def heartbeat(db: DbSession, lease: SingletonLease) -> bool:
    """Gia hạn lease. False khi lease đã bị người khác thu hồi.

    False nghĩa là **mất quyền**: caller phải dừng việc nền ngay, vì tiến trình
    khác có thể đã nhận. Tiếp tục làm sau khi mất lease là đúng cái mà lease
    sinh ra để ngăn.
    """
    row = db.execute(select(SingletonLease).where(
        SingletonLease.name == lease.name)).scalar_one_or_none()
    if row is None or row.holder != lease.holder:
        return False
    row.heartbeat_at = _now()
    db.commit()
    return True


def release(db: DbSession, lease: SingletonLease) -> None:
    """Nhả lease sớm khi dừng êm, để tiến trình khác nhận ngay thay vì đợi hết hạn."""
    row = db.execute(select(SingletonLease).where(
        SingletonLease.name == lease.name)).scalar_one_or_none()
    if row is not None and row.holder == lease.holder:
        db.delete(row)
        db.commit()
        log.info("nha lease %r (%s)", lease.name, lease.holder)


def current_holder(db: DbSession, *, name: str) -> str:
    """Ai đang giữ lease, hoặc chuỗi rỗng. Dùng cho trang trạng thái/chẩn đoán."""
    row = db.execute(select(SingletonLease).where(
        SingletonLease.name == str(name))).scalar_one_or_none()
    return str(row.holder) if row is not None else ""


__all__ = ["DEFAULT_TTL", "MAINTENANCE", "WEB", "acquire", "current_holder",
           "heartbeat", "holder_id", "reclaim_expired", "release"]
