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

#: Nhịp tim im lâu hơn mốc này thì dòng lease được coi là **rác**, bất kể tên.
#:
#: 🔴 VÌ SAO CẦN MỘT MỐC THỨ HAI, KHI ĐÃ CÓ `DEFAULT_TTL`
#:
#:    `reclaim_expired` nhắm **đúng một tên** — cái tên mà người gọi đang xin. Đủ
#:    cho việc giành lại một *vai trò* (`maintenance`, `web`): luôn có người xin
#:    lại nó. ⛔ Không đủ cho lease mang tên **sinh ra từ nội dung**:
#:    `asvcc:<băm>` chỉ được xin lại nếu có người nộp đúng nội dung ấy lần nữa.
#:    Không ai xin lại ⇒ ⛔ **không bao giờ** có ai dọn.
#:
#:    Đo trên CSDL production 26/09: `asvcc:82839212a287…` nằm lại **hơn một
#:    ngày**, nhịp tim dừng từ 25/09 15:57, tiến trình chủ (25716) đã chết —
#:    trong khi dòng `maintenance` cạnh nó có nhịp tim tươi. Cơ chế nhịp tim
#:    chạy; thiếu là bước DỌN.
#:
#: ⚠️ VÌ SAO RỘNG (2 giờ) CHỨ KHÔNG PHẢI `DEFAULT_TTL`
#:
#:    Người quét **không biết TTL riêng của từng lease**, nên nó phải rộng hơn
#:    TTL dài nhất trong kho — hiện là `apps/vps/jobs.KHOA_MAY_TTL` = **45 phút**,
#:    và đường đó ⛔ **không đập nhịp**: nhịp tim đứng yên từ lúc giành. Lấy mốc
#:    hẹp thì người quét **cướp** khoá của một job cài VPS đang chạy, và hai job
#:    cùng làm việc trên một máy — đúng sự cố 25/08 mà khoá ấy sinh ra để chặn.
#:    `tests/test_3061::test_BANH_COC_nguong_quet_RONG_hon_moi_TTL_trong_kho` đọc
#:    mọi `leases.acquire(..., ttl=…)` trong kho và chốt điều đó bằng máy.
#:
#: ⭐ Cùng khuôn `platform_core/gpu_lease.ORPHAN_TIMEOUT` (10 phút) — ở đó mốc hẹp
#:    được vì mọi chủ lease GPU đều đập nhịp.
ORPHAN_TIMEOUT = timedelta(hours=2)


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


def reclaim_orphans(db: DbSession, *, timeout: timedelta = ORPHAN_TIMEOUT) -> int:
    """Xoá MỌI lease mà chủ đã im nhịp quá `timeout`. Trả số lease thu hồi được.

    ⭐ Cùng khuôn `gpu_lease.reclaim_orphans` — cố ý giống hệt, kể cả tên và chữ
       ký. Hai khuôn cho cùng một việc là hai chỗ sẽ lệch nhau;
       `tests/test_3061::test_dung_lai_KHUON_cua_gpu_lease` chốt hình dạng ấy.

    🔴 Khác `reclaim_expired` ở **phạm vi**, không ở thuật toán: hàm kia hỏi *"cái
       tên TÔI đang xin có rảnh chưa"*, hàm này hỏi *"còn dòng nào là rác không"*.
       Thiếu hàm này thì lease mang tên sinh từ nội dung (`asvcc:<băm>`) nằm lại
       vĩnh viễn, vì ⛔ không ai xin lại đúng cái tên đó.

    ⛔ Quét **không lọc theo máy** — khác `gpu_lease` (GPU thuộc một máy). Lease
       singleton là hợp đồng giữa mọi tiến trình của cả cụm, nên một dòng của máy
       khác đã im nhịp 2 giờ cũng là rác, và để lại thì chính nó chặn cụm.
    """
    cutoff = _now() - timeout
    n = 0
    for row in db.execute(select(SingletonLease)).scalars().all():
        beat = _aware(row.heartbeat_at) or _aware(row.acquired_at)
        if beat is not None and beat >= cutoff:
            continue
        log.warning("thu hoi lease mo coi %r cua %s (im nhip tu %s)",
                    row.name, row.holder, beat)
        db.delete(row)
        n += 1
    if n:
        db.commit()
    return n


def acquire(db: DbSession, *, name: str, holder: str = "",
            ttl: timedelta = DEFAULT_TTL) -> SingletonLease | None:
    """Giành lease `name`. Trả None khi tiến trình khác đang giữ.

    None **không phải lỗi**: nó là câu trả lời bình thường cho "tôi có phải
    người chạy việc này không". Caller đợi lượt sau.
    """
    who = holder or holder_id()
    # ⭐ Đúng chỗ `gpu_lease.acquire` gọi `reclaim_orphans` (dòng 151): mọi lượt
    #    giành là một dịp quét, nên ⛔ không cần thêm một vòng nền thứ hai — và
    #    `leases.MAINTENANCE` được xin lại mỗi chu kỳ bảo trì, nên cụm luôn có
    #    người quét kể cả khi không app nào chạy.
    reclaim_orphans(db)
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


__all__ = ["DEFAULT_TTL", "MAINTENANCE", "ORPHAN_TIMEOUT", "WEB", "acquire",
           "current_holder", "heartbeat", "holder_id", "reclaim_expired",
           "reclaim_orphans", "release"]
