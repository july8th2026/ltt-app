"""
models.py — lược đồ CSDL của nền tảng.

Mọi model kế thừa `platform_core.db.Base`. Alembic dò `Base.metadata` để sinh
migration, nên **model mới phải được import ở đây** (hoặc import gián tiếp từ
đây), nếu không Alembic sẽ không thấy và sinh ra một migration rỗng.

Quy ước đặt tên: dùng tiếng Anh cho tên bảng và tên cột (chúng xuất hiện trong
câu lệnh SQL, công cụ quản trị, thông báo lỗi của driver), tiếng Việt cho phần
giải thích.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _bay_gio() -> datetime:
    """Thời điểm hiện tại, luôn kèm múi giờ.

    Dùng hàm thay vì `datetime.utcnow` vì `utcnow()` trả về datetime **không có
    múi giờ**, và một giá trị như vậy đem so sánh với giá trị có múi giờ sẽ ném
    TypeError ở đúng chỗ khó ngờ nhất.
    """
    return datetime.now(timezone.utc)


class PlatformInfo(Base):
    """Một dòng duy nhất ghi lược đồ này được dựng khi nào, bởi bản nào.

    Vì sao cần: khi hỗ trợ một cài đặt đang gặp sự cố, câu hỏi đầu tiên luôn là
    "CSDL này dựng lúc nào, bằng bản nào". Không có bảng này thì phải đoán qua
    log — mà log thì bị xoay vòng.

    Đây cũng là bảng của migration đầu tiên, nên nó làm cho việc kiểm chứng
    `upgrade` → `downgrade` → `upgrade` có ý nghĩa thật.
    """

    __tablename__ = "platform_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    app_version: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    def __repr__(self) -> str:      # pragma: no cover - chi de doc khi go roi
        return f"<PlatformInfo v{self.app_version} @ {self.installed_at:%Y-%m-%d}>"


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """Một người dùng của nền tảng.

    Quyết định thiết kế:

    - **Khoá chính là UUID chuỗi, không phải số tự tăng.** Số tự tăng lộ ra
      quy mô ("tôi là user #3") và cho phép đoán id người khác. UUID thì không.
    - **`email` là danh tính đăng nhập, lưu chữ thường.** Người dùng gõ hoa/
      thường tuỳ hứng; chuẩn hoá về thường lúc ghi để `Bob@x.com` và
      `bob@x.com` không thành hai tài khoản.
    - **`password_hash` không bao giờ chứa mật khẩu thô**, chỉ chứa kết quả
      PBKDF2 của `server/auth/password_hashing.py` (tái dùng đúng hàm đang chạy
      production, không phát minh cách băm thứ hai).
    - **`is_verified` tách khỏi `is_active`.** Chưa xác thực email (Q9) thì
      chưa được cấp credit dùng thử và chưa tạo được job — nhưng vẫn đăng nhập
      xem được. `is_active=False` là bị admin khoá, khác hẳn.
    - **`role`** chỉ hai giá trị `admin`/`user`. Đủ cho hiện tại; khi cần nhiều
      vai trò hơn thì thêm bảng riêng chứ không nhồi thêm cột.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False,
                                       index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    # IP lúc đăng ký — dùng để giới hạn số tài khoản mới trên mỗi IP mỗi ngày
    # (chống lạm dụng credit dùng thử, Q9). Rỗng khi admin tạo tay.
    registration_ip: Mapped[str] = mapped_column(String(45), default="", nullable=False)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<User {self.email} role={self.role} verified={self.is_verified}>"


class Session(Base):
    """Phiên đăng nhập lưu **phía máy chủ**.

    Vì sao cần bảng này thay vì chỉ dùng cookie ký của Starlette:

    Cookie ký chứng minh được "máy chủ đã phát cookie này", nhưng **không thu
    hồi được** — không có id nào để xoá. Không thể "đăng xuất khỏi mọi thiết
    bị", và đổi mật khẩu không đá được các phiên đang mở ra. Với một nền tảng
    tính tiền, một phiên bị lộ mà không thu hồi được là lỗ hổng thật.

    Có bảng này thì cookie chỉ mang một `session_id` ngẫu nhiên; muốn thu hồi
    thì xoá dòng tương ứng. Đổi mật khẩu = xoá mọi phiên của user đó.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(43), primary_key=True)  # token_urlsafe(32)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    # Ghi lại để người dùng nhận ra phiên lạ khi xem "các thiết bị đang đăng nhập".
    user_agent: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    ip: Mapped[str] = mapped_column(String(45), default="", nullable=False)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<Session {self.id[:8]}... user={self.user_id}>"
