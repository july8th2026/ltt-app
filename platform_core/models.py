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

from sqlalchemy import (BigInteger, Boolean, DateTime, Index, Integer, JSON, String, Text,
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

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA-256 hex cua token (khong luu token tho)
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
JOB_CANCELLED = "cancelled"

AGENT_PLANNING = "planning"
AGENT_AWAITING_APPROVAL = "awaiting_approval"
AGENT_RUNNING = "running"
AGENT_DONE = "done"
AGENT_ERROR = "error"
AGENT_CANCELLED = "cancelled"


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

    # Quan hệ execution Agent. Chuỗi rỗng giữ tương thích toàn bộ job cũ.
    parent_id: Mapped[str] = mapped_column(String(36), default="", nullable=False,
                                            index=True)
    plan_id: Mapped[str] = mapped_column(String(36), default="", nullable=False,
                                         index=True)
    step_id: Mapped[str] = mapped_column(String(32), default="", nullable=False)

    worker_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False, index=True)
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Index đúng câu truy vấn claim (W2.6c): WHERE status=? AND next_run_at<=?
        # ORDER BY created_at. Khi bảng job lớn, quét tuần tự mỗi vòng worker sẽ
        # tốn; index tổng hợp này cho claim đi thẳng vào đúng dòng đến hạn.
        Index("ix_jobs_claim", "status", "next_run_at", "created_at"),
    )

    def __repr__(self) -> str:      # pragma: no cover
        return f"<Job {self.id[:8]} {self.job_type} {self.status} {self.progress}%>"


class AgentRun(Base):
    """Plan đã chuẩn hoá cùng checkpoint để resume executor sau khi worker chết."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    app_slug: Mapped[str] = mapped_column(String(64), default="agent", nullable=False)
    goal: Mapped[str] = mapped_column(Text, default="", nullable=False)
    plan: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default=AGENT_PLANNING,
                                        nullable=False, index=True)
    budget_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actual: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    decision_log: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_agent_runs_user_created", "user_id", "created_at"),
    )


WORKFLOW_DRAFT = "draft"
WORKFLOW_VALIDATED = "validated"
WORKFLOW_APPROVED = "approved"
WORKFLOW_ARCHIVED = "archived"


class AgentWorkflow(Base):
    """Canvas lưu layout/config; Plan thực thi luôn được dựng lại ở server."""

    __tablename__ = "agent_workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), default="Workflow mới", nullable=False)
    goal: Mapped[str] = mapped_column(Text, default="", nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    nodes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    edges: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    viewport: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=WORKFLOW_DRAFT,
                                        nullable=False, index=True)
    budget_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_workflow_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    __table_args__ = (
        Index("ix_agent_workflows_user_updated", "user_id", "updated_at"),
    )


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


# ── Trạng thái API key (H8) ────────────────────────────────────────────────────
# active    : dùng được
# cooldown  : tạm nghỉ (429 / lỗi tạm) tới cooldown_until, tự hồi
# exhausted : hết quota (reset theo ngày/quota provider)
# error     : lỗi lặp nhiều lần
# disabled  : admin tắt HOẶC 401/403 liên tiếp >= ngưỡng
APIKEY_ACTIVE = "active"
APIKEY_COOLDOWN = "cooldown"
APIKEY_EXHAUSTED = "exhausted"
APIKEY_ERROR = "error"
APIKEY_DISABLED = "disabled"

# Category (năng lực) một key có thể phục vụ — "4 loại" người dùng nêu (Q/APIKEYS).
APIKEY_CAT_MODEL = "model_control"
APIKEY_CAT_CHAT = "chat"
APIKEY_CAT_IMAGE = "image"
APIKEY_CAT_VIDEO = "video"


class ApiKey(Base):
    """Một API key của nền tảng (H8) — nguồn API mà nền tảng cung cấp cho app.

    App KHÔNG giữ key: app xin key từ `platform_core.api_pool` theo (provider,
    category, model). Nhờ vậy đổi/xoay/thêm key là việc của admin ở một chỗ, và
    thêm loại API mới = thêm một dòng Provider Registry, không sửa app.

    **`credential_enc` là secret ĐÃ MÃ HOÁ** (Fernet, khoá dẫn xuất từ
    `LTT_TOKEN_ENCRYPTION_KEY` — xem `platform_core/secretbox.py`). KHÔNG BAO GIỜ
    lộ credential thô ra API/UI; chỉ hiện `key_preview` (4 số cuối).

    `provider` xác định cách kết nối (auth_style, base_url, endpoint) qua Provider
    Registry — KHÔNG lưu auth_style ở đây để không lệch với registry.
    `categories`/`supported_models` lọc key khi cấp phát (rỗng supported_models =
    mọi model của provider).
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_user_id: Mapped[str] = mapped_column(String(36), default="", nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    categories: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    credential_enc: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet token
    key_preview: Mapped[str] = mapped_column(String(16), default="", nullable=False)  # 4 số cuối, hiện an toàn
    base_url: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    supported_models: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    default_model: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    status: Mapped[str] = mapped_column(String(16), default=APIKEY_ACTIVE, nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    health_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    auth_error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_success: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Telemetry rpm/tpm/token (H8 Pha 2). Giới hạn 0 = không giới hạn. Cửa sổ cố
    # định 60s ngay trong hàng (không cần bảng time-series cho quy mô này):
    # allocator bỏ qua key đã chạm rpm/tpm trong cửa sổ, tự reset khi quá hạn.
    rpm_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tpm_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<ApiKey {self.provider} {self.name!r} {self.status}>"


# ── Thanh toán / nạp credit (H9) ───────────────────────────────────────────────
# Trạng thái đơn nạp:
# pending   : đã tạo, chờ khách chuyển tiền
# paid      : đã nhận tiền + đã cộng credit (idempotent qua cờ credited)
# expired   : quá hạn chưa trả
# cancelled : khách/admin huỷ
# failed    : cổng báo lỗi
ORDER_PENDING = "pending"
ORDER_PAID = "paid"
ORDER_EXPIRED = "expired"
ORDER_CANCELLED = "cancelled"
ORDER_FAILED = "failed"


class CreditPackage(Base):
    """Một gói nạp credit (H9). Admin sửa giá/credit/bonus — không hardcode.

    `credits_base` = số credit gốc (theo tỉ giá 1 credit = 100đ → thường
    price_vnd//100), `bonus_percent` = % tặng thêm. Tổng credit khách nhận tính
    ở `platform_core/billing_math.py` (một chỗ) để trang bán + đơn hàng luôn khớp.
    """

    __tablename__ = "credit_packages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    price_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_base: Mapped[int] = mapped_column(Integer, nullable=False)
    bonus_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<CreditPackage {self.name!r} {self.price_vnd}d +{self.bonus_percent}%>"


class PaymentOrder(Base):
    """Một đơn nạp credit (H9). Cầu nối giữa cổng thanh toán và sổ credit H3.

    **Idempotent:** `credited` chỉ True MỘT lần — webhook lặp hay admin mark-paid
    lại đều KHÔNG cộng credit hai lần (guard ở `platform_core/billing.py`).

    `order_code` là số nguyên duy nhất PayOS yêu cầu để khớp giao dịch. `credits`
    là TỔNG credit sẽ cộng (đã gồm bonus) — chốt tại thời điểm tạo đơn để đổi giá
    gói sau này không ảnh hưởng đơn cũ.
    """

    __tablename__ = "payment_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_code: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    package_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)

    price_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)          # tổng (gồm bonus)
    bonus_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # snapshot

    status: Mapped[str] = mapped_column(String(16), default=ORDER_PENDING, nullable=False, index=True)
    credited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gateway: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    gateway_ref: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    checkout_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<PaymentOrder {self.order_code} {self.status} {self.credits}cr>"


# ── Hội thoại chat AI (dùng bởi app chat) ─────────────────────────────────────
# Hội thoại + tin nhắn lưu bền theo user (cá nhân hóa). Ngữ cảnh model giữ ở
# thread phía trợ lý (codex_thread_id) để resume; nội dung hiển thị lưu ở Postgres
# để KHÔNG phụ thuộc vòng đời rollout của trợ lý + để đính ảnh (R2) vào transcript.

class ChatConversation(Base):
    """Một hội thoại của một user. Cô lập theo user_id (bất biến A-không-đọc-B)."""

    __tablename__ = "chat_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(64), default="gpt-5.6-sol", nullable=False)
    custom_instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    codex_thread_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False, index=True)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<ChatConversation {self.id[:8]} u={self.user_id[:8]} {self.title!r}>"


class ChatMessage(Base):
    """Một tin nhắn trong hội thoại. `image_key` != '' → tin là ẢNH (R2)."""

    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_conv_created", "conversation_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_key: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    image_prompt: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    tokens_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<ChatMessage {self.id[:8]} {self.role} img={bool(self.image_key)}>"
