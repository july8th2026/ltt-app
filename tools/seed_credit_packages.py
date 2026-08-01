"""
seed_credit_packages.py — nạp vài GÓI CREDIT mặc định (H9). Chạy MỘT lần trên máy
chủ để trang /nap có gói ngay; admin sửa/thêm/xoá sau ở /admin/goi.

Idempotent: chỉ seed khi bảng `credit_packages` đang RỖNG — chạy lại không nhân đôi.

Tỉ giá (Q31): 1 credit = 100đ. Bonus theo % (thang khuyến khích nạp nhiều).

    python tools\seed_credit_packages.py
"""
from __future__ import annotations

# (price_vnd, bonus_percent, name)
GOI_MAC_DINH = [
    (50_000, 0, "Gói 50K"),
    (100_000, 5, "Gói 100K"),
    (200_000, 10, "Gói 200K"),
    (500_000, 15, "Gói 500K"),
    (1_000_000, 20, "Gói 1 triệu"),
]


def main() -> int:
    from platform_core import billing_math
    from platform_core.db import get_session
    from platform_core.models import CreditPackage
    from sqlalchemy import select, func

    gen = get_session(); db = next(gen)
    try:
        n = db.execute(select(func.count(CreditPackage.id))).scalar_one()
        if n:
            print(f"Da co {n} goi -> bo qua seed (idempotent).")
            return 0
        for i, (price, bonus, name) in enumerate(GOI_MAC_DINH):
            db.add(CreditPackage(
                name=name, price_vnd=price,
                credits_base=billing_math.credits_base_tu_vnd(price),
                bonus_percent=bonus, sort_order=(i + 1) * 10))
        db.commit()
        print(f"Da seed {len(GOI_MAC_DINH)} goi credit mac dinh.")
        for price, bonus, name in GOI_MAC_DINH:
            base = billing_math.credits_base_tu_vnd(price)
            print(f"  {name}: {price:,}d -> {billing_math.tong_credits(base, bonus):,} credit (+{bonus}%)")
        return 0
    finally:
        try: next(gen)
        except StopIteration: pass


if __name__ == "__main__":
    raise SystemExit(main())
