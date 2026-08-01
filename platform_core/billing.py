"""
billing.py — nghiệp vụ nạp credit (H9). Cầu nối cổng thanh toán ↔ sổ credit H3.

Bất biến TIỀN:
- **Idempotent tuyệt đối:** một đơn chỉ cộng credit ĐÚNG MỘT LẦN (`credited`),
  dù webhook gửi lại nhiều lần hay admin bấm "đã trả" lại. Guard = khoá dòng đơn
  (`with_for_update`) + cờ `credited`.
- **Mọi credit vào đều qua `credit.nap`** (sổ append-only H3) — không đường tắt.
- `credits` chốt tại lúc TẠO đơn (snapshot gồm bonus) → đổi giá gói sau không
  ảnh hưởng đơn cũ.

Không tự commit — caller quyết định ranh giới transaction (như module khác).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from platform_core import billing_math, credit
from platform_core.models import (ORDER_EXPIRED, ORDER_PAID, ORDER_PENDING,
                                  CreditPackage, PaymentOrder)

ORDER_TTL_PHUT = 30       # đơn chưa trả quá hạn sau 30 phút


class BillingError(Exception):
    pass


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# ── Gói nạp ────────────────────────────────────────────────────────────────────
def goi_active(db: DbSession) -> list:
    return list(db.execute(
        select(CreditPackage).where(CreditPackage.active.is_(True))
        .order_by(CreditPackage.sort_order, CreditPackage.price_vnd)
    ).scalars().all())


def lay_goi(db: DbSession, package_id: str) -> Optional[CreditPackage]:
    return db.get(CreditPackage, package_id)


def _sinh_order_code(db: DbSession) -> int:
    """Sinh order_code nguyên duy nhất (PayOS yêu cầu số). Thử lại nếu trùng."""
    for _ in range(20):
        code = 1_000_000_000 + secrets.randbelow(9_000_000_000)   # 10 chữ số
        trung = db.execute(
            select(PaymentOrder.id).where(PaymentOrder.order_code == code)
        ).first()
        if not trung:
            return code
    raise BillingError("khong sinh duoc order_code duy nhat")


# ── Tạo đơn ────────────────────────────────────────────────────────────────────
def tao_don(db: DbSession, *, user_id: str, package: CreditPackage, gateway_id: str,
            return_url: str = "", cancel_url: str = "") -> PaymentOrder:
    """Tạo đơn nạp (pending) + gọi cổng lấy checkout_url. Nếu cổng chưa cấu hình
    thì đơn vẫn được tạo (checkout_url rỗng) — admin có thể xác nhận tay."""
    credits = billing_math.tong_credits(package.credits_base, package.bonus_percent)
    order = PaymentOrder(
        order_code=_sinh_order_code(db), user_id=user_id, package_id=package.id,
        price_vnd=package.price_vnd, credits=credits,
        bonus_percent=package.bonus_percent, gateway=gateway_id,
        status=ORDER_PENDING, expires_at=_bay_gio() + timedelta(minutes=ORDER_TTL_PHUT),
    )
    db.add(order); db.flush()

    from platform_core import payments
    gw = payments.get(gateway_id)
    if gw is not None and gw.da_cau_hinh():
        try:
            res = gw.tao_thanh_toan(
                order_code=order.order_code, amount_vnd=order.price_vnd,
                description=f"LTTAI {order.order_code}",
                return_url=return_url, cancel_url=cancel_url)
            order.checkout_url = (res.get("checkout_url") or "")[:500]
            order.gateway_ref = (res.get("ref") or "")[:120]
        except Exception as e:  # noqa: BLE001 - cổng lỗi không được làm mất đơn
            order.note = f"gateway loi: {type(e).__name__}"[:255]
    db.flush()
    return order


# ── Ghi nhận đã trả (idempotent) ───────────────────────────────────────────────
def ghi_nhan_tra(db: DbSession, order_code: int, *, gateway_ref: str = "",
                 by: str = "") -> Optional[PaymentOrder]:
    """Đánh dấu đơn đã trả + cộng credit — **idempotent**. Trả đơn, hoặc None nếu
    không tìm thấy. Gọi lại nhiều lần chỉ cộng credit MỘT lần."""
    stmt = select(PaymentOrder).where(PaymentOrder.order_code == order_code)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    order = db.execute(stmt).scalar_one_or_none()
    if order is None:
        return None
    if order.credited:
        return order                       # đã cộng rồi -> không cộng đôi
    credit.nap(db, order.user_id, order.credits,
               note=f"Nap credit don {order_code}")
    order.credited = True
    order.status = ORDER_PAID
    order.paid_at = _bay_gio()
    if gateway_ref:
        order.gateway_ref = gateway_ref[:120]
    if by:
        order.note = (order.note + f" | xac nhan boi {by}")[:255]
    db.flush()
    return order


def het_han_don(db: DbSession) -> int:
    """Đánh dấu các đơn pending đã quá hạn -> expired. Trả số đơn đổi."""
    now = _bay_gio()
    rows = db.execute(
        select(PaymentOrder).where(PaymentOrder.status == ORDER_PENDING)
    ).scalars().all()
    n = 0
    for o in rows:
        if o.expires_at and _aware(o.expires_at) <= now:
            o.status = ORDER_EXPIRED
            n += 1
    if n:
        db.flush()
    return n


# ── Truy vấn ───────────────────────────────────────────────────────────────────
def lay_don(db: DbSession, order_id: str) -> Optional[PaymentOrder]:
    return db.get(PaymentOrder, order_id)


def lay_don_theo_code(db: DbSession, order_code: int) -> Optional[PaymentOrder]:
    return db.execute(
        select(PaymentOrder).where(PaymentOrder.order_code == order_code)
    ).scalar_one_or_none()


def liet_ke_don(db: DbSession, *, user_id: Optional[str] = None,
                status: Optional[str] = None, limit: int = 200) -> list:
    stmt = select(PaymentOrder).order_by(PaymentOrder.created_at.desc())
    if user_id:
        stmt = stmt.where(PaymentOrder.user_id == user_id)
    if status:
        stmt = stmt.where(PaymentOrder.status == status)
    return list(db.execute(stmt.limit(limit)).scalars().all())


def doanh_thu(db: DbSession) -> dict:
    """Tổng kết doanh thu: tổng VND đã thu, tổng credit đã bán, số đơn đã trả."""
    row = db.execute(
        select(func.coalesce(func.sum(PaymentOrder.price_vnd), 0),
               func.coalesce(func.sum(PaymentOrder.credits), 0),
               func.count(PaymentOrder.id))
        .where(PaymentOrder.status == ORDER_PAID)
    ).one()
    return {"vnd": int(row[0]), "credits": int(row[1]), "orders": int(row[2])}
