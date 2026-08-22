"""
users.py — nghiệp vụ người dùng và phiên đăng nhập phía máy chủ.

Tách khỏi route: route lo HTTP (form, cookie, redirect), file này lo quy tắc
(băm mật khẩu, chuẩn hoá email, tạo/thu hồi phiên). Nhờ vậy test được logic mà
không cần dựng cả một request giả.

Băm mật khẩu **tái dùng** `platform_core/password_hashing.py` — đúng hàm PBKDF2
đang chạy production. Không phát minh cách băm thứ hai: hai cách băm trong một
hệ thống là hai chỗ có thể sai, và tài khoản tạo bằng cách này phải đăng nhập
được bằng đường kia trong suốt giai đoạn chạy song song.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import Session as SessionRow
from platform_core.models import User
from platform_core.password_hashing import hash_password, verify_password

# Phiên sống 8 giờ không hoạt động — khớp với SESSION_MAX_AGE_SECONDS cũ của
# cookie Starlette, nên hành vi hết hạn không đổi dưới mắt người dùng.
SESSION_TTL = timedelta(hours=8)


class UserError(Exception):
    """Lỗi nghiệp vụ người dùng, thông điệp an toàn để hiện cho người dùng."""


def chuan_hoa_email(email: str) -> str:
    """Chuẩn hoá để LƯU và HIỂN THỊ. Chỉ bỏ khoảng trắng và hạ chữ thường."""
    return (email or "").strip().lower()


# Nhà cung cấp coi dấu chấm và hậu tố `+…` là CÙNG một hộp thư.
_MIEN_ALIAS = {"gmail.com", "googlemail.com"}


def chuan_hoa_email_chong_trung(email: str) -> str:
    """Chuẩn hoá để KIỂM TRÙNG — khác `chuan_hoa_email`.

    Gmail giao `a@gmail.com`, `a+1@gmail.com`, `a.b@gmail.com` về **cùng một hộp
    thư**. Trước đây hệ thống coi chúng là ba email khác nhau, nên một hộp Gmail
    tạo được vô hạn tài khoản, mỗi cái 20 credit dùng thử. Xác thực email không
    cản được: chính người đó nhận hết thư xác thực.

    Hàm này CHỈ dùng cho cột `email_chuan` (chống trùng). Email gốc vẫn giữ
    nguyên để hiển thị và gửi thư — người dùng nhập `a.b@gmail.com` thì phải
    thấy đúng chuỗi đó, không phải chuỗi ta tự sửa.

    Cố ý chỉ áp cho Gmail: mỗi nhà cung cấp một luật, đoán bừa cho miền khác sẽ
    gộp nhầm hai người thành một.
    """
    e = chuan_hoa_email(email)
    if "@" not in e:
        return e
    ten, mien = e.rsplit("@", 1)
    if mien == "googlemail.com":
        mien = "gmail.com"
    if mien in _MIEN_ALIAS:
        ten = ten.split("+", 1)[0].replace(".", "")
    return f"{ten}@{mien}"


# ── Tạo và xác thực người dùng ────────────────────────────────────────────────

def tao_nguoi_dung(
    db: DbSession, *, email: str, password: str, display_name: str = "",
    role: str = "user", is_verified: bool = False, registration_ip: str = "",
) -> User:
    """Tạo một người dùng. Ném `UserError` nếu email đã tồn tại.

    KHÔNG commit — nơi gọi quyết định thời điểm chốt giao dịch, vì việc tạo user
    thường đi cùng những thao tác khác (cấp credit dùng thử) phải cùng thành
    hoặc cùng bại.
    """
    email = chuan_hoa_email(email)
    if not email or "@" not in email:
        raise UserError("Email không hợp lệ.")
    if not password:
        raise UserError("Mật khẩu không được rỗng.")

    # Kiem trung theo email_chuan, KHONG theo email goc: gmail giao
    # a@ / a+1@ / a.b@ ve cung mot hop thu (xem chuan_hoa_email_chong_trung).
    chuan = chuan_hoa_email_chong_trung(email)
    trung = db.execute(
        select(User).where(User.email_chuan == chuan)).scalar_one_or_none()
    if trung is not None:
        raise UserError("Email này đã được đăng ký.")

    user = User(
        email=email,
        email_chuan=chuan,
        display_name=display_name.strip() or email.split("@")[0],
        password_hash=hash_password(password),
        role=role,
        is_verified=is_verified,
        registration_ip=(registration_ip or "")[:45],
    )
    db.add(user)
    db.flush()      # gán id ngay, nhưng chưa commit
    return user


def tim_theo_email(db: DbSession, email: str) -> Optional[User]:
    return db.execute(
        select(User).where(User.email == chuan_hoa_email(email))
    ).scalar_one_or_none()


def xac_thuc(db: DbSession, *, email: str, password: str) -> Optional[User]:
    """Trả về User nếu email+mật khẩu đúng và tài khoản còn hoạt động.

    Trả `None` cho **mọi** trường hợp sai — không phân biệt "email không tồn
    tại" với "sai mật khẩu". Phân biệt hai cái đó là tiết lộ email nào đã đăng
    ký, tức là làm lộ danh sách khách hàng cho kẻ dò.

    Vẫn băm-và-so ngay cả khi email không tồn tại, để thời gian phản hồi không
    tiết lộ tài khoản nào có thật (timing oracle).
    """
    user = tim_theo_email(db, email)
    if user is None:
        # So với một hash giả để tiêu tốn thời gian tương đương.
        verify_password(password, _HASH_GIA)
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


# Một hash PBKDF2 thật của một chuỗi ngẫu nhiên, tính một lần lúc nạp module.
# Dùng để so khi email không tồn tại — không bao giờ khớp, chỉ để tốn thời gian.
_HASH_GIA = hash_password(secrets.token_urlsafe(16))


def doi_mat_khau(db: DbSession, user: User, mat_khau_moi: str) -> None:
    """Đổi mật khẩu và **thu hồi mọi phiên** của user đó.

    Thu hồi phiên là điểm mấu chốt: đổi mật khẩu mà các phiên cũ vẫn sống thì
    một kẻ đã chiếm phiên vẫn vào được sau khi nạn nhân đã đổi mật khẩu.
    """
    if not mat_khau_moi:
        raise UserError("Mật khẩu không được rỗng.")
    user.password_hash = hash_password(mat_khau_moi)
    thu_hoi_moi_phien(db, user.id)
    db.flush()


# ── Phiên đăng nhập phía máy chủ ──────────────────────────────────────────────

def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    """Bảo đảm datetime có múi giờ (coi naive là UTC).

    PostgreSQL với `DateTime(timezone=True)` trả về datetime có múi giờ, nhưng
    SQLite không giữ tzinfo nên đọc ra là naive. So một cái naive với một cái
    aware ném TypeError. Chuẩn hoá tại điểm so sánh để code chạy đúng trên cả
    hai backend — production là Postgres, test là SQLite.
    """
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _bam_sid(sid: str) -> str:
    """Băm token phiên để LƯU (không lưu token thô).

    `id` của bảng `sessions` vừa là token vừa là KHOÁ CHÍNH. sqladmin phơi khoá
    chính ra checkbox/URL của từng dòng, nên nếu id = token thô thì admin xem
    trang Phiên là lấy được token sống → mạo danh không cần mật khẩu (P0-5).
    Giải pháp: cookie mang token THÔ, còn DB chỉ lưu SHA-256 của nó; tra cứu thì
    băm token trong cookie rồi so với hash. Dump CSDL cũng không lộ token dùng
    được (băm một chiều).
    """
    return hashlib.sha256(sid.encode("utf-8")).hexdigest()


def tao_phien(db: DbSession, user: User, *, user_agent: str = "", ip: str = "",
              ttl: Optional[timedelta] = None) -> str:
    """Tạo một phiên, trả về session_id (token THÔ) để đặt vào cookie.

    Token là 32 byte ngẫu nhiên mã hoá urlsafe — không đoán được, không mang
    thông tin gì về user. CSDL chỉ lưu HASH của token (xem `_bam_sid`), không
    lưu token thô.

    `ttl` để rút ngắn tuổi thọ cho những phiên **không phải** cookie trình duyệt
    — cụ thể là vé SSO của ứng dụng Nexus, thứ đi qua thanh địa chỉ nên phải chết
    nhanh (xem `platform_core.nexus.sso`). Bỏ trống → `SESSION_TTL` như cũ.
    """
    sid = secrets.token_urlsafe(32)
    db.add(SessionRow(
        id=_bam_sid(sid), user_id=user.id,
        expires_at=_bay_gio() + (ttl or SESSION_TTL),
        user_agent=(user_agent or "")[:255], ip=(ip or "")[:45],
    ))
    user.last_login_at = _bay_gio()
    db.flush()
    return sid


def lay_user_tu_phien(db: DbSession, sid: Optional[str]) -> Optional[User]:
    """Đổi session_id (token thô trong cookie) lấy User, hoặc None nếu phiên
    sai/hết hạn/user bị khoá. Băm token trước khi tra vì DB chỉ lưu hash.

    Phiên hết hạn thì xoá luôn tại chỗ — dọn rác dần thay vì để bảng phình mãi.
    """
    if not sid:
        return None
    row = db.get(SessionRow, _bam_sid(sid))
    if row is None:
        return None
    if _aware(row.expires_at) <= _bay_gio():
        db.delete(row)
        db.flush()
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None
    return user


def thu_hoi_phien(db: DbSession, sid: str) -> None:
    """Đăng xuất một phiên. Băm token trước khi tra (DB lưu hash)."""
    row = db.get(SessionRow, _bam_sid(sid))
    if row is not None:
        db.delete(row)
        db.flush()


def thu_hoi_moi_phien(db: DbSession, user_id: str) -> int:
    """Đăng xuất khỏi mọi thiết bị. Trả về số phiên đã xoá."""
    rows = db.execute(
        select(SessionRow).where(SessionRow.user_id == user_id)
    ).scalars().all()
    for r in rows:
        db.delete(r)
    db.flush()
    return len(rows)


def don_phien_het_han(db: DbSession) -> int:
    """Xoá mọi phiên đã hết hạn. Dành cho tác vụ dọn dẹp định kỳ."""
    rows = db.execute(
        select(SessionRow).where(SessionRow.expires_at <= _bay_gio())
    ).scalars().all()
    for r in rows:
        db.delete(r)
    db.flush()
    return len(rows)
