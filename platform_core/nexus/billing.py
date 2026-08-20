"""Thuê bao Nexus: trừ credit theo số máy đã ghép, mỗi tháng (Q98).

Ba điều Q98 chốt, và một điều cố ý để mở:

* **Trừ CREDIT**, không auto-charge thẻ — nên tránh hẳn thứ Q53 hoãn (consent/
  cap/replay của recurring card). Khách nạp credit trong trình duyệt (PayOS H9);
  ở đây chỉ trừ từ số dư đã có.
* **Theo máy đã ghép, mỗi tháng.** Máy nào còn (chưa thu hồi) thì tính.
* **Hết credit → không điều khiển được** cho tới khi nạp. Không cắt máy, không
  xoá gì — chỉ `cap_ve` từ chối (thi hành ở `sessions.cap_ve`).

**Mặc định AN TOÀN: giá = 0 → miễn phí, tắt hẳn cưỡng chế.** Charter §1: không tự
bật thứ chưa duyệt. Chủ sản phẩm đặt giá (`LTT_NEXUS_GIA_MAY_THANG`) khi muốn thu.
Giá/chu kỳ/ân hạn là tham số của người (D12) — module này nhận chúng làm cấu hình.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from platform_core import credit
from platform_core.models import CREDIT_NEXUS_BILL
from platform_core.nexus.tables import NexusDevice

#: Một chu kỳ thuê bao. 30 ngày. **Giá đã chốt (D12, 2026-08-20): 50 credit/máy/
#: tháng** — đặt `LTT_NEXUS_GIA_MAY_THANG=50` trong secrets/app.env lúc go-live.
#: Mặc định code vẫn 0 (an toàn); 50 là cấu hình vận hành, không phải hằng số.
CHU_KY_NGAY = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def gia_may_thang(env: dict | None = None) -> int:
    """Giá credit mỗi máy mỗi tháng. **0 = miễn phí (mặc định, tắt cưỡng chế).**"""
    src = os.environ if env is None else env
    raw = str(src.get("LTT_NEXUS_GIA_MAY_THANG", "")).strip()
    try:
        return max(0, int(raw)) if raw else 0
    except ValueError:
        return 0


def an_han_ngay(env: dict | None = None) -> int:
    """Số ngày ân hạn sau khi hết thuê bao mà vẫn cho điều khiển. Mặc định 0."""
    src = os.environ if env is None else env
    raw = str(src.get("LTT_NEXUS_AN_HAN_NGAY", "")).strip()
    try:
        return max(0, int(raw)) if raw else 0
    except ValueError:
        return 0


def da_thanh_toan(device: NexusDevice, *, now: datetime | None = None,
                  env: dict | None = None) -> bool:
    """Máy này có được phép điều khiển không (theo thuê bao)?

    Miễn phí (giá 0) → **luôn True**. Có giá → True khi `paid_until` (cộng ân hạn)
    còn ở tương lai. Đây là phép kiểm mà `cap_ve` gọi trước khi cấp vé.
    """
    if gia_may_thang(env) <= 0:
        return True
    han = device.paid_until
    if han is None:
        return False
    if han.tzinfo is None:
        han = han.replace(tzinfo=timezone.utc)
    han = han + timedelta(days=an_han_ngay(env))
    return han > (now or _now())


def thu_phi_thang(db, *, now: datetime | None = None,
                  env: dict | None = None) -> dict:
    """Một lượt tính phí: mỗi máy còn hiệu lực mà thuê bao đã hết → trừ một tháng.

    Chạy trong vòng bảo trì **sau lease** (H36: vòng job chạy ở mọi tiến trình,
    nên một lượt trừ tiền không được nằm trong đó — nếu không mỗi máy bị trừ N lần
    một tháng). Trả thống kê để log.

    Idempotent trong một tháng: chỉ trừ khi `paid_until` đã qua; trừ xong đẩy
    `paid_until` lên một chu kỳ, nên lượt sau trong cùng tháng không trừ lại.

    Không đủ credit thì **không trừ, không đẩy hạn** — máy thành "chưa thanh toán"
    và `cap_ve` sẽ từ chối. Không auto-charge, không nợ.
    """
    gia = gia_may_thang(env)
    ket = {"gia": gia, "tru": 0, "thieu_credit": 0, "bo_qua": 0}
    if gia <= 0:
        return ket                                # miễn phí: không làm gì

    current = now or _now()
    rows = db.execute(select(NexusDevice).where(
        NexusDevice.revoked_at.is_(None))).scalars().all()
    for dev in rows:
        han = dev.paid_until
        if han is not None and han.tzinfo is None:
            han = han.replace(tzinfo=timezone.utc)
        if han is not None and han > current:
            ket["bo_qua"] += 1                    # còn hạn, chưa tới kỳ
            continue
        du = credit.tru(db, dev.user_id, gia, kind=CREDIT_NEXUS_BILL,
                        note=f"nexus thue bao may {dev.id}")
        if du:
            # Đẩy hạn từ mốc cũ nếu còn gần, hoặc từ bây giờ nếu đã quá lâu —
            # tránh dồn nhiều tháng nợ vào một lần trừ.
            goc = han if (han is not None and han > current - timedelta(days=CHU_KY_NGAY)) else current
            dev.paid_until = goc + timedelta(days=CHU_KY_NGAY)
            ket["tru"] += 1
        else:
            ket["thieu_credit"] += 1
    db.flush()
    return ket


__all__ = ["CHU_KY_NGAY", "an_han_ngay", "da_thanh_toan", "gia_may_thang",
           "thu_phi_thang"]
