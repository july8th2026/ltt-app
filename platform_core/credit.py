"""
credit.py — sổ credit (H3). Phần ít code nhất, ít được phép sai nhất.

Nguyên tắc bất di bất dịch:

1. **Số dư = tổng của sổ.** Không có ô `balance` nào bị sửa đè. `so_du()` luôn
   cộng lại từ bảng `credit_entries`.
2. **Chỉ ghi thêm.** Không sửa, không xoá bút toán. Sai thì ghi bút toán bù.
3. **Giữ chỗ → quyết toán → hoàn** đều trong transaction của caller (cùng với
   việc tạo job), nên tiền và job không bao giờ lệch nhau.
4. **Quyết toán/hoàn idempotent theo job.** Worker có thể gọi lại (retry, khởi
   động lại) — mỗi job chỉ được quyết toán hoặc hoàn đúng một lần.

Không hàm nào tự commit — caller (web request giữ chỗ cùng lúc tạo job; worker
quyết toán khi job xong) quyết định ranh giới transaction.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import (CREDIT_GRANT, CREDIT_HOLD, CREDIT_REFUND,
                                  CREDIT_SETTLE, CREDIT_TOPUP, CreditEntry)


class ThieuCreditError(Exception):
    """Số dư không đủ để giữ chỗ. Job KHÔNG được tạo, API KHÔNG được gọi."""


def so_du(db: DbSession, user_id: str) -> int:
    """Số dư hiện tại = tổng mọi bút toán của user."""
    tong = db.execute(
        select(func.coalesce(func.sum(CreditEntry.delta), 0))
        .where(CreditEntry.user_id == user_id)
    ).scalar_one()
    return int(tong)


def _ghi(db: DbSession, *, user_id: str, delta: int, kind: str,
         job_id: str = "", note: str = "") -> CreditEntry:
    e = CreditEntry(user_id=user_id, delta=int(delta), kind=kind,
                    job_id=job_id, note=note[:255])
    db.add(e)
    db.flush()
    return e


# ── Cộng tiền ─────────────────────────────────────────────────────────────────

def nap(db: DbSession, user_id: str, amount: int, note: str = "") -> CreditEntry:
    """Người dùng nạp tiền → +credit. (Thanh toán thật ở H6; hàm này là điểm nối.)"""
    if amount <= 0:
        raise ValueError("so credit nap phai duong")
    return _ghi(db, user_id=user_id, delta=amount, kind=CREDIT_TOPUP, note=note)


def cap_tay(db: DbSession, user_id: str, amount: int, *, by: str = "", note: str = "") -> CreditEntry:
    """Admin cấp/thu credit tay. `amount` âm là thu về. Ghi rõ ai cấp."""
    if amount == 0:
        raise ValueError("so credit cap phai khac 0")
    ghi_chu = (f"admin={by}; " if by else "") + note
    return _ghi(db, user_id=user_id, delta=amount, kind=CREDIT_GRANT, note=ghi_chu)


# ── Giữ chỗ / quyết toán / hoàn ───────────────────────────────────────────────

def so_da_giu(db: DbSession, job_id: str) -> int:
    """Tổng đã giữ cho một job (số dương). 0 nếu chưa giữ."""
    tong = db.execute(
        select(func.coalesce(func.sum(CreditEntry.delta), 0))
        .where(CreditEntry.job_id == job_id, CreditEntry.kind == CREDIT_HOLD)
    ).scalar_one()
    return -int(tong)      # hold ghi delta âm → đổi dấu ra số đã giữ


def giu_cho(db: DbSession, user_id: str, amount: int, job_id: str) -> None:
    """Giữ chỗ `amount` credit cho `job_id`. Raise `ThieuCreditError` nếu thiếu.

    Kiểm số dư TRƯỚC khi ghi: đây là chốt chặn "không đủ tiền thì không tạo job,
    không gọi API". Vì chạy trong cùng transaction với `jobs.submit`, nếu thiếu
    thì cả job lẫn bút toán đều rollback.
    """
    if amount < 0:
        raise ValueError("so credit giu cho khong the am")
    if amount == 0:
        return
    if so_du(db, user_id) < amount:
        raise ThieuCreditError(
            f"Khong du credit: can {amount}, con {so_du(db, user_id)}.")
    _ghi(db, user_id=user_id, delta=-amount, kind=CREDIT_HOLD, job_id=job_id,
         note=f"giu cho job {job_id[:8]}")


def _da_ket_so(db: DbSession, job_id: str) -> bool:
    """Job đã được quyết toán hoặc hoàn chưa (chống làm hai lần)."""
    n = db.execute(
        select(func.count()).select_from(CreditEntry).where(
            CreditEntry.job_id == job_id,
            CreditEntry.kind.in_((CREDIT_SETTLE, CREDIT_REFUND)),
        )
    ).scalar_one()
    return n > 0


def quyet_toan(db: DbSession, user_id: str, job_id: str, actual: int) -> None:
    """Chốt job xong theo giá thật `actual`. Idempotent theo job.

    Đã giữ `held` lúc submit; giờ trừ đúng `actual`. Ghi một bút toán điều chỉnh
    delta = held - actual:
    - actual < held (giá thật rẻ hơn ước tính) → delta dương → hoàn phần dư;
    - actual > held (đắt hơn) → delta âm → trừ thêm.
    Kết cục cho job: -held + (held-actual) = -actual. Đúng bằng giá thật.
    """
    if _da_ket_so(db, job_id):
        return
    if actual < 0:
        actual = 0
    held = so_da_giu(db, job_id)
    dieu_chinh = held - actual
    _ghi(db, user_id=user_id, delta=dieu_chinh, kind=CREDIT_SETTLE, job_id=job_id,
         note=f"quyet toan job {job_id[:8]}: giu {held}, that {actual}")


def hoan(db: DbSession, user_id: str, job_id: str) -> None:
    """Hoàn toàn bộ phần đã giữ cho job (khi job lỗi). Idempotent theo job.

    Kết cục cho job: -held + held = 0. Người dùng không mất gì cho một job thất
    bại — đây là lý do phải giữ-chỗ-trước chứ không trừ-thẳng.
    """
    if _da_ket_so(db, job_id):
        return
    held = so_da_giu(db, job_id)
    if held == 0:
        return
    _ghi(db, user_id=user_id, delta=held, kind=CREDIT_REFUND, job_id=job_id,
         note=f"hoan job {job_id[:8]}: tra lai {held}")
