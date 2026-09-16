"""Chính sách IP OVH rỗi (R16) — chủ dự án chốt 16/09/2026: giữ tối đa MỘT IP rỗi.

## Vì sao cần

IP OVH mua qua web job là dịch vụ **P1M tự gia hạn** ở OVH. Khách xoá máy thì IP
về kho `FREE` để tái dùng, nhưng OVH vẫn thu USD mỗi tháng. Trước đây không có
dòng code nào điều khiển gia hạn: kho có thể tích IP rỗi trả tiền mãi mãi.

## Làm gì

- IP `monthly` đang `FREE`, rỗi ≥ `NGAY_RONG` ngày: sắp theo lúc rỗi, **giữ IP
  rỗi gần nhất** (khách kế tiếp tạo máy không phải chờ mua), các IP còn lại đặt
  `renew.deleteAtExpiration=true` ở OVH và **đọc lại** — dịch vụ vẫn chạy tới
  `expiration` rồi OVH thu hồi. Không xoá gì ngay.
- IP đã đặt không gia hạn **không bao giờ** được cấp cho máy mới
  (`public_ip._renewal_cancelled`), nên không có máy nào bị mất IP giữa chừng.

Đường API: `PUT /ip/service/ip-<IPv4>/serviceInfos` (OVH Manager dùng cùng định
danh dịch vụ; cách huỷ gia hạn đã được cộng đồng kiểm trên API thật).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import select

from apps.vps.tables import VpsIp

log = logging.getLogger(__name__)

GIU_TOI_DA_IP_RONG = 1
NGAY_RONG = 7


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _luc_rong(row: VpsIp) -> datetime | None:
    raw = dict(row.provider_metadata or {}).get("free_since")
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def ap_dung(db, profile, client, *, now: datetime | None = None) -> dict:
    """Một lượt chính sách cho một profile OVH. Caller commit. Trả số đếm."""
    thoi_diem = now or _now()
    rows = list(db.execute(select(VpsIp).where(
        VpsIp.infrastructure_profile_id == profile.id,
        VpsIp.state == "FREE",
        VpsIp.billing_mode == "monthly",
        VpsIp.instance_id.is_(None),
    ).with_for_update()).scalars())

    da_danh_dau = 0
    rong: list[tuple[datetime, VpsIp]] = []
    for row in rows:
        meta = dict(row.provider_metadata or {})
        if meta.get("renewal_cancelled_at"):
            continue
        luc = _luc_rong(row)
        if luc is None:
            # Chưa có đồng hồ rỗi (IP rỗi từ trước khi có R16): bắt đầu đếm từ nay.
            row.provider_metadata = {**meta, "free_since": thoi_diem.isoformat()}
            da_danh_dau += 1
            continue
        rong.append((luc, row))

    # Giữ IP rỗi GẦN NHẤT; chỉ xét huỷ những IP đã rỗi đủ lâu.
    rong.sort(key=lambda cap: cap[0], reverse=True)
    giu, con_lai = rong[:GIU_TOI_DA_IP_RONG], rong[GIU_TOI_DA_IP_RONG:]
    da_huy = loi = 0
    for luc, row in con_lai:
        if thoi_diem - luc < timedelta(days=NGAY_RONG):
            continue
        try:
            ket_qua = client.set_ip_delete_at_expiration(row.dia_chi, True)
        except Exception as exc:  # noqa: BLE001 - one address must not stop the rest
            loi += 1
            log.warning("VPS ip rong: khong huy duoc gia han %s: %s",
                        row.id, type(exc).__name__)
            continue
        row.provider_metadata = {
            **dict(row.provider_metadata or {}),
            "renewal_cancelled_at": thoi_diem.isoformat(),
            "expiration": ket_qua.get("expiration", ""),
        }
        da_huy += 1
        log.warning("VPS ip rong: da huy gia han IP %s (het han %s), giu %s IP rong",
                    row.id, ket_qua.get("expiration", ""), len(giu))
    db.flush()
    return {"giu": len(giu), "da_huy_gia_han": da_huy, "bat_dau_dem": da_danh_dau,
            "loi": loi}
