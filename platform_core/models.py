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

from sqlalchemy import (Boolean, DateTime, Integer, JSON, String, Text,
                        UniqueConstraint)
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


class AppAccess(Base):
    """Quyền của MỘT người dùng với MỘT app — chỉ lưu khi KHÁC mặc định.

    Mặc định là "mở" (Q25), nên bảng này chỉ chứa các ngoại lệ: app bị khoá
    hoặc ẩn với một user cụ thể. Không có dòng nào = mở. Cách này giữ bảng nhỏ
    (không sinh N_user × M_app dòng) và làm "thêm app mới thì mọi user thấy
    ngay" trở thành hành vi mặc định, không cần cấp quyền hàng loạt.

    `level`:
    - `enabled` — thấy và dùng được (cũng là mặc định khi không có dòng);
    - `locked`  — thấy trên trang chủ nhưng vào bị chặn (dùng cho "sắp mở");
    - `hidden`  — không thấy, vào thẳng URL cũng bị chặn.
    """

    __tablename__ = "app_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    app_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "app_slug", name="uq_app_access_user_app"),
    )

    def __repr__(self) -> str:      # pragma: no cover
        return f"<AppAccess user={self.user_id} {self.app_slug}={self.level}>"


# ── Trạng thái job ────────────────────────────────────────────────────────────
# queued  : đang chờ worker nhặt
# running : một worker đang chạy
# done    : xong, có result
# error   : thất bại sau khi hết lượt thử
JOB_QUEUED = "queued"
JOB_RUNNING = "running"
JOB_DONE = "done"
JOB_ERROR = "error"


class Job(Base):
    """Một công việc trong hàng đợi (H2, Q26).

    Bảng này là **nguồn chân lý duy nhất** cho hàng đợi — không có kho thứ hai.
    Web tạo dòng job (và trừ credit) trong **cùng một transaction**; worker nhặt
    bằng `SELECT … FOR UPDATE SKIP LOCKED` nên nhiều worker không bao giờ nhặt
    trùng. Xem `platform_core/jobs.py`.

    Vì sao các cột này có mặt:
    - `params`/`result` là JSON — mỗi loại job một hình dạng riêng, không nhồi
      vào cột cứng.
    - `heartbeat_at` + `worker_id`: để nhận ra job **mồ côi** (worker chết giữa
      chừng) — job `running` mà lâu không đập nhịp sẽ được nhặt lại.
    - `attempts`/`max_attempts` + `next_run_at`: retry có giới hạn và có giãn
      cách; thử lại một lỗi tham số vô hạn chỉ tốn tiền API.
    - `dedupe_key`: cùng người gửi cùng thứ trong khi job cũ còn chạy → nhận lại
      job cũ, không tạo job mới (chống double-submit, F5, bấm "Tạo lại").
    """

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    app_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    status: Mapped[str] = mapped_column(String(16), default=JOB_QUEUED,
                                        nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_msg: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(128), default="", nullable=False)

    worker_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False, index=True)
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<Job {self.id[:8]} {self.job_type} {self.status} {self.progress}%>"


# ── Loại bút toán credit ──────────────────────────────────────────────────────
# topup  : người dùng nạp tiền → +credit
# grant  : admin cấp tay (khuyến mãi, dùng thử, bồi thường) → +credit
# hold   : giữ chỗ khi nhận job → -credit (theo giá ước tính)
# settle : quyết toán khi job xong → điều chỉnh cho khớp giá thật
# refund : hoàn khi job lỗi → +credit (trả lại phần đã giữ)
CREDIT_TOPUP = "topup"
CREDIT_GRANT = "grant"
CREDIT_HOLD = "hold"
CREDIT_SETTLE = "settle"
CREDIT_REFUND = "refund"


class CreditEntry(Base):
    """Một bút toán trong sổ credit (H3). **Chỉ ghi thêm, không bao giờ sửa/xoá.**

    Vì sao append-only: số dư là **tổng của sổ**, không phải một ô `balance` bị
    sửa đè. Một ô số dư sửa đè là chỗ hai request đồng thời ghi chồng lên nhau
    và tiền lệch mà không truy được. Sổ append-only thì mọi biến động có dấu
    vết, và số dư luôn tái dựng được từ đầu — với tiền, truy được nguồn gốc
    quan trọng hơn tiết kiệm vài dòng.

    Mỗi bút toán gắn `job_id` (nếu liên quan một job) để:
    - tính đã giữ bao nhiêu cho job đó (`hold`);
    - chặn quyết toán/hoàn **hai lần** cùng một job (idempotent — worker có thể
      gọi lại sau khi retry).
    """

    __tablename__ = "credit_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)   # +nạp/hoàn, -trừ
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False, index=True)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<CreditEntry user={self.user_id} {self.kind} {self.delta:+d}>"
