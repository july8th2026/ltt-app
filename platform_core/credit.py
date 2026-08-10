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

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session as DbSession

from platform_core.models import (CREDIT_GRANT, CREDIT_HOLD, CREDIT_REFUND,
                                  CREDIT_SETTLE, CREDIT_TOPUP, CreditEntry)


class ThieuCreditError(Exception):
    """Số dư không đủ để giữ chỗ. Job KHÔNG được tạo, API KHÔNG được gọi."""


def _khoa_so_du_user(db: DbSession, user_id: str) -> None:
    """Khoá TUẦN TỰ mọi thao tác credit của MỘT user trong transaction hiện tại.

    Vì `so_du` là `SUM` của sổ rồi mới ghi bút toán, hai request song song của
    cùng user (hai tab, script gọi API) có thể CÙNG đọc số dư cũ rồi CÙNG giữ
    chỗ → số dư âm, mất tiền thật (double-spend). `pg_advisory_xact_lock` giữ
    đến khi commit/rollback nên request thứ hai phải xếp hàng, đọc số dư SAU khi
    request đầu đã ghi. Khoá theo khoá riêng của từng user nên user khác không
    bị chặn.

    Chỉ áp dụng cho PostgreSQL. SQLite (test/đơn máy) bỏ qua: nó tuần tự hoá ghi
    ở mức tệp và các test chạy đơn luồng, nên không có race để chặn.
    """
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
                   {"k": f"credit:{user_id}"})


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


class NguoiDungKhongTonTai(ValueError):
    """Cấp credit cho một user_id không có trong bảng `users`."""


def cap_tay(db: DbSession, user_id: str, amount: int, *, by: str = "", note: str = "") -> CreditEntry:
    """Admin cấp/thu credit tay. `amount` âm là thu về. Ghi rõ ai cấp.

    **Bắt buộc kiểm người dùng tồn tại** (F-01, audit 2026-08-07). Trước đây hàm
    này gọi thẳng `_ghi()`, và `credit_entries` cũng không có khoá ngoại — nên gõ
    nhầm một ký tự trong UUID là credit rơi vào hư không, trong khi màn hình admin
    báo "Đã cấp +500 credit. Số dư mới: 500". Không lỗi nào ở đâu cả, và cách duy
    nhất phát hiện là tự đi truy vấn CSDL.

    Kiểm ở đây để có thông báo lỗi tử tế; khoá ngoại trong CSDL là lưới an toàn
    cuối cho mọi đường ghi khác.
    """
    if amount == 0:
        raise ValueError("so credit cap phai khac 0")
    if not _ton_tai(db, user_id):
        raise NguoiDungKhongTonTai(
            f"khong co nguoi dung nao co id {user_id!r} — khong ghi but toan nao")
    ghi_chu = (f"admin={by}; " if by else "") + note
    return _ghi(db, user_id=user_id, delta=amount, kind=CREDIT_GRANT, note=ghi_chu)


class KetQuaCapHangLoat:
    """Kết quả một lượt cấp hàng loạt. `khong_thay` rỗng nghĩa là đã cấp hết."""

    def __init__(self, da_cap: list, khong_thay: list, trung: list):
        self.da_cap = da_cap            # [(email, user_id)]
        self.khong_thay = khong_thay    # [email]
        self.trung = trung              # [email] — xuất hiện nhiều lần trong danh sách

    @property
    def thanh_cong(self) -> bool:
        return not self.khong_thay


def cap_hang_loat(db: DbSession, emails, amount: int, *, by: str = "",
                  note: str = "") -> KetQuaCapHangLoat:
    """Cấp cùng một số credit cho nhiều người, theo email.

    **Nguyên tử: một email sai thì KHÔNG AI được cấp** (chốt D4, audit 2026-08-07).
    Cấp một phần tạo ra trạng thái nửa vời — vài người có credit, vài người không,
    và không ai biết ai — rồi phải đối soát tay đúng lúc đang vội onboarding.

    Hàm này KHÔNG commit. Nơi gọi quyết định ranh giới transaction, nên nếu nó
    ném lỗi thì rollback bỏ sạch, đúng nghĩa nguyên tử.
    """
    if amount == 0:
        raise ValueError("so credit cap phai khac 0")

    da_thay, khong_thay, trung, thu_tu = {}, [], [], []
    for e in emails:
        khoa = (e or "").strip().lower()
        if not khoa:
            continue
        if khoa in da_thay or khoa in khong_thay:
            trung.append(khoa)
            continue
        # Nhan CA email LAN user id (chot D3: email la duong chinh, UUID giu lam
        # duong du phong — vd khi doi soat tu log hoac tu CSDL).
        u = tim_theo_email(db, khoa)
        uid = u.id if u is not None else (khoa if _ton_tai(db, khoa) else None)
        if uid is None:
            khong_thay.append(khoa)
        else:
            da_thay[khoa] = uid
            thu_tu.append(khoa)

    # Kiểm HẾT rồi mới ghi — không ghi dở dang xong mới phát hiện email sai.
    if khong_thay:
        return KetQuaCapHangLoat([], khong_thay, trung)

    for khoa in thu_tu:
        cap_tay(db, da_thay[khoa], amount, by=by, note=note)
    return KetQuaCapHangLoat([(k, da_thay[k]) for k in thu_tu], [], trung)


def _ton_tai(db: DbSession, user_id: str) -> bool:
    from platform_core.models import User
    if not (user_id or "").strip():
        return False
    return db.execute(
        select(User.id).where(User.id == user_id)).first() is not None


def tim_theo_email(db: DbSession, email: str):
    """Tìm người dùng theo email (chuẩn hoá). Trả `None` nếu không có.

    Có ở đây để đường cấp credit nhận **email** thay vì UUID (F-02): UUID là chuỗi
    con người không kiểm được bằng mắt, nên nó vừa gây mệt vừa là điều kiện làm
    F-01 nguy hiểm.
    """
    from platform_core.models import User
    e = (email or "").strip().lower()
    if not e:
        return None
    return db.execute(
        select(User).where(func.lower(User.email) == e)).scalar_one_or_none()


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
    # Khoá TRƯỚC khi đọc số dư: từ đây tới hết transaction, chỉ request này được
    # giữ chỗ cho user này → check-then-write trở thành nguyên tử, hết double-spend.
    _khoa_so_du_user(db, user_id)
    con = so_du(db, user_id)
    if con < amount:
        raise ThieuCreditError(
            f"Khong du credit: can {amount}, con {con}.")
    _ghi(db, user_id=user_id, delta=-amount, kind=CREDIT_HOLD, job_id=job_id,
         note=f"giu cho job {job_id[:8]}")
    # Durable internal event: support can explain the hold without reading the
    # credit note or the app's private params.  It is in the same transaction
    # as the hold, so a rollback cannot leave a misleading log row.
    from platform_core import job_events
    from platform_core.models import Job
    job = db.get(Job, job_id)
    if job is not None:
        job_events.append(
            db, job, "credit_held", visibility=job_events.INTERNAL,
            details={"credit": int(amount)}, event_key="credit-held",
        )


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
    from platform_core import job_events
    from platform_core.models import Job
    job = db.get(Job, job_id)
    if job is not None:
        job_events.append(
            db, job, "credit_settled", visibility=job_events.INTERNAL,
            details={"held_credit": int(held), "credit": int(actual),
                     "adjustment": int(dieu_chinh)}, event_key="credit-settled",
        )


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
    from platform_core import job_events
    from platform_core.i18n import N_
    from platform_core.models import Job
    job = db.get(Job, job_id)
    if job is not None:
        job_events.append(
            db, job, "credit_refunded", public_message=N_("Credit đã được hoàn lại."),
            details={"credit": int(held), "status": job.status},
            event_key="credit-refunded",
        )
