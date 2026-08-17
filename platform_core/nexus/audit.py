"""Dòng thời gian mà CHỦ THIẾT BỊ đọc được (Q93 ràng buộc 5 và 6).

Nền tảng đã có `nhat_ky_admin` — nhưng đó là nhật ký để **admin** xem. Q93 đòi
một thứ khác hẳn: mọi hành động của admin phải để lại bản ghi **chủ thiết bị**
đọc được. Một nhật ký chỉ người làm hành động mới xem được thì không trả lời
được câu hỏi duy nhất quan trọng sau sự cố: *"ai đã vào máy tôi, và ai đã đụng
vào thiết bị của tôi."*

## Không có bảng mới, và đó là chủ ý

Mọi sự kiện dưới đây **suy ra** từ các dòng đã có: `nexus_enrollments` biết máy
được ghép lúc nào từ IP nào, `nexus_devices` biết ai thu hồi, `nexus_sessions`
biết vé cấp lúc nào, phiên bắt đầu và kết thúc ra sao.

Thêm một bảng `nexus_audit_events` sẽ tạo **nguồn chân lý thứ hai**: có ngày một
phiên tồn tại mà không có dòng nhật ký tương ứng (hoặc ngược lại), và lúc cần
đối chiếu thì không biết tin cái nào. Suy ra thì không lệch được — dữ liệu chỉ
có một bản.

Đổi lại: đọc chậm hơn (ba truy vấn thay vì một) và không ghi được sự kiện nào
không tương ứng với một dòng có thật. Cái giá thứ hai chính là tính năng.

## Owner-scoped, luôn luôn

Mọi hàm ở đây nhận `user_id` và lọc theo nó. Không có đường nào lấy dòng thời
gian của người khác, kể cả cho admin — admin muốn điều tra thì dùng trang quản
trị, và việc đó sẽ tự xuất hiện trong dòng thời gian của chủ.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from platform_core.nexus.tables import (NexusDevice, NexusEnrollment,
                                        NexusSession)

# Loại sự kiện. Hằng số vì chúng đi vào giao diện và vào báo cáo — đổi chúng là
# đổi một hợp đồng, không phải đổi một chuỗi trong code.
GHEP = "ghep_thiet_bi"
THU_HOI_THIET_BI = "thu_hoi_thiet_bi"
CAP_VE = "cap_ve"
BAT_DAU_PHIEN = "bat_dau_phien"
KET_THUC_PHIEN = "ket_thuc_phien"
THU_HOI_PHIEN = "thu_hoi_phien"

#: Ai gây ra sự kiện, khi không phải chính chủ.
BOI_CHU = "owner"


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _su_kien(luc, loai, *, device_id="", boi=BOI_CHU, chi_tiet="") -> dict:
    return {"luc": _aware(luc), "loai": loai, "device_id": str(device_id or ""),
            "boi": str(boi or BOI_CHU), "chi_tiet": str(chi_tiet or "")}


def do_admin_lam(su_kien: dict) -> bool:
    """Sự kiện này có phải do admin gây ra không.

    Tách thành hàm vì giao diện phải **làm nổi bật** những dòng này: một lần
    admin đụng vào máy của khách mà trôi lẫn giữa các dòng khác thì coi như
    không có ai đọc.
    """
    return str(su_kien.get("boi", "")).startswith("admin:")


def dong_thoi_gian(db, *, user_id: str, device_id: str = "",
                   limit: int = 200) -> list:
    """Mọi thứ đã xảy ra với thiết bị của tài khoản này, mới nhất trước.

    `device_id` rỗng = mọi thiết bị. Truyền id của người khác thì không lọt: mọi
    truy vấn đều kẹp thêm `user_id`.
    """
    chu = str(user_id or "").strip()
    if not chu:
        return []
    loc_may = str(device_id or "").strip()

    ra: list = []

    # 1. Ghép máy — từ mã đã dùng.
    stmt = select(NexusEnrollment).where(
        NexusEnrollment.user_id == chu,
        NexusEnrollment.consumed_at.isnot(None))
    if loc_may:
        stmt = stmt.where(NexusEnrollment.device_id == loc_may)
    for row in db.execute(stmt).scalars():
        ra.append(_su_kien(row.consumed_at, GHEP, device_id=row.device_id or "",
                           chi_tiet=f"tu IP {row.claimed_ip}"
                           if row.claimed_ip else ""))

    # 2. Thu hồi thiết bị.
    stmt = select(NexusDevice).where(NexusDevice.user_id == chu,
                                     NexusDevice.revoked_at.isnot(None))
    if loc_may:
        stmt = stmt.where(NexusDevice.id == loc_may)
    for row in db.execute(stmt).scalars():
        ra.append(_su_kien(row.revoked_at, THU_HOI_THIET_BI, device_id=row.id,
                           boi=row.revoked_by or BOI_CHU))

    # 3. Vòng đời phiên. Một dòng `nexus_sessions` sinh ra tới bốn sự kiện —
    #    đó là lý do nó được giữ nguyên vẹn thay vì bị cập nhật chồng lên.
    stmt = select(NexusSession).where(NexusSession.user_id == chu)
    if loc_may:
        stmt = stmt.where(NexusSession.device_id == loc_may)
    for row in db.execute(stmt).scalars():
        ra.append(_su_kien(row.issued_at, CAP_VE, device_id=row.device_id,
                           chi_tiet=row.quyen))
        if row.consumed_at is not None:
            ra.append(_su_kien(row.consumed_at, BAT_DAU_PHIEN,
                               device_id=row.device_id,
                               chi_tiet=f"tu IP {row.controller_ip}"
                               if row.controller_ip else ""))
        if row.revoked_at is not None:
            ra.append(_su_kien(row.revoked_at, THU_HOI_PHIEN,
                               device_id=row.device_id,
                               boi=row.revoked_by or BOI_CHU))
        elif row.ended_at is not None:
            ra.append(_su_kien(row.ended_at, KET_THUC_PHIEN,
                               device_id=row.device_id,
                               chi_tiet=row.end_reason))

    ra.sort(key=lambda item: (item["luc"] is not None, item["luc"]), reverse=True)
    return ra[:max(1, min(int(limit), 1000))]


def admin_da_lam_gi(db, *, user_id: str, limit: int = 200) -> list:
    """Chỉ những sự kiện do admin gây ra, trong phạm vi tài khoản này.

    Đây là câu trả lời trực tiếp cho *"có ai bên LTT đụng vào máy tôi không"* —
    và nó phải trả lời được **mà không cần hỏi LTT**.
    """
    return [item for item in dong_thoi_gian(db, user_id=user_id, limit=1000)
            if do_admin_lam(item)][:max(1, min(int(limit), 1000))]


__all__ = ["BAT_DAU_PHIEN", "BOI_CHU", "CAP_VE", "GHEP", "KET_THUC_PHIEN",
           "THU_HOI_PHIEN", "THU_HOI_THIET_BI", "admin_da_lam_gi",
           "do_admin_lam", "dong_thoi_gian"]
