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

from sqlalchemy import (BigInteger, Boolean, DateTime, Float, ForeignKey, Index,
                        Integer, JSON, String, Text,
                        UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base
# Bảng của Public API (Q92) sống ở `platform_core/public_api/tables.py` vì nó là
# domain riêng, không phải bảng của control plane. Import ở đây để Alembic thấy
# nó trong `Base.metadata` — không có dòng này thì autogenerate coi bảng đó là
# bảng lạ và sinh migration XOÁ nó.
from platform_core.public_api.tables import (  # noqa: F401
    ApiBudget, ApiIdempotencyRecord, ApiNotification, ApiProject,
    ApiRequestLog, DeveloperApiKey, WebhookDelivery, WebhookSubscription)
# Cùng lý do, cho Nexus (Q93): danh tính thiết bị là domain riêng ở
# `platform_core/nexus/tables.py`, không phải bảng của control plane.
from platform_core.nexus.tables import (  # noqa: F401
    NexusDevice, NexusEnrollment, NexusSession)


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
      PBKDF2 của `platform_core/password_hashing.py` (tái dùng đúng hàm đang chạy
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
    # Email da chuan hoa theo nha cung cap, CHI de chong trung (xem
    # users.chuan_hoa_email_chong_trung). Gmail giao a@ / a+1@ / a.b@ ve CUNG MOT
    # hop thu; truoc day he thong coi la ba tai khoan khac nhau, moi cai 20 credit
    # dung thu. `email` goc van giu nguyen de hien thi va gui thu.
    email_chuan: Mapped[str] = mapped_column(
        String(255), default="", nullable=False, index=True)
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
    # ⭐ PHẦN LẺ CHƯA THU, đơn vị milli-credit, luôn trong [0, 1000).
    #
    #    Credit là số nguyên, còn một lượt gọi LLM điển hình tốn 0,3 credit. Làm
    #    tròn LÊN mỗi lượt (C1) biến một hội thoại 20 lượt ngắn thành 20 credit
    #    trong khi giá niêm yết của chính ta là ~3 — đo 05/09, xem
    #    `docs/CHATLTT_V3/04_ADR_R2B_TINH_TIEN_LUOT.md`.
    #
    #    Cột này giữ phần lẻ để lượt sau cộng tiếp, nên khách trả **đúng bảng
    #    giá** thay vì trả sàn.
    #
    # ⛔ ĐÂY KHÔNG PHẢI SỔ TIỀN. `credit_entries` vẫn là sự thật duy nhất — mọi
    #    lần thu vẫn là một bút toán. Đây là **bộ đếm dẫn xuất**, cùng hạng với
    #    `chatltt_run.mcredit_tich_luy`. Mất nó thì khách được lợi tối đa
    #    0,999 credit, không ai mất tiền.
    mcredit_du: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<User {self.email} role={self.role} verified={self.is_verified}>"

    @property
    def so_du_credit(self) -> int:
        """Số dư credit hiện tại. Dùng cho trang quản trị (F-04).

        Truy vấn theo từng dòng (N+1). Chấp nhận được ở quy mô hiện tại — danh
        sách người dùng là trang admin, không phải trang khách, và một truy vấn
        đếm trên cột đã đánh chỉ mục thì rẻ. Khi số người dùng lớn lên thì đổi
        sang một truy vấn gộp; ghi ra đây để lúc đó khỏi phải đi tìm nguyên nhân.
        """
        from sqlalchemy import func, select
        from sqlalchemy.orm import object_session
        s = object_session(self)
        if s is None:
            return 0
        return int(s.execute(
            select(func.coalesce(func.sum(CreditEntry.delta), 0))
            .where(CreditEntry.user_id == self.id)).scalar() or 0)

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


APP_PROJECT_ACTIVE = "active"
APP_PROJECT_ARCHIVED = "archived"


class AppProject(Base):
    """Generic, owner-scoped persistence for stateful app editors (Q49).

    The platform owns identity, optimistic revision and lifecycle only. The
    app owns and validates the versioned JSON payload; app-specific columns do
    not belong in this table.
    """

    __tablename__ = "app_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    app_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), default="Project mới", nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=APP_PROJECT_ACTIVE,
                                        nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    __table_args__ = (
        Index("ix_app_projects_owner_app_updated", "user_id", "app_slug", "updated_at"),
    )


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

    # Tài nguyên admission được chụp lúc submit. Không suy lại từ manifest khi
    # worker chạy: một deploy đổi manifest không được đổi hàng đang chờ sang
    # một pool khác. Rỗng giữ tương thích job UI/legacy không qua Public API.
    admission_resource: Mapped[str] = mapped_column(
        String(96), default="", nullable=False, index=True)
    admission_slots: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Scheduler envelope (Q121). ``origin`` is audit metadata; only
    # ``priority_class`` participates in ranking. Defaults are deliberately
    # fail-closed so rows created by an older binary never gain internal
    # priority after an additive migration.
    origin: Mapped[str] = mapped_column(
        String(24), default="unknown", nullable=False)
    priority_class: Mapped[str] = mapped_column(
        String(16), default="external", nullable=False)

    # Quan hệ execution Agent. Chuỗi rỗng giữ tương thích toàn bộ job cũ.
    parent_id: Mapped[str] = mapped_column(String(36), default="", nullable=False,
                                            index=True)
    plan_id: Mapped[str] = mapped_column(String(36), default="", nullable=False,
                                         index=True)
    step_id: Mapped[str] = mapped_column(String(32), default="", nullable=False)

    # Dấu vết dùng chung cho toàn bộ vòng đời job. ``correlation_id`` theo job
    # (không phụ thuộc một request HTTP ngắn); ``retry_of_id`` dựng lineage mà
    # không phải đọc lại params; ``event_sequence`` cấp số tăng dần cho timeline.
    correlation_id: Mapped[str] = mapped_column(
        String(36), default=_uuid, nullable=False, index=True)
    retry_of_id: Mapped[str] = mapped_column(
        String(36), default="", nullable=False, index=True)
    event_sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    worker_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False, index=True)
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Lượt claim gần nhất dùng làm con trỏ fairness bền vững theo account/resource.
    # Khác `started_at`: retry/resource_wait phải cập nhật mỗi lượt để một tenant
    # burst không liên tục đứng đầu hàng.
    last_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    # Substate của lần gọi provider. Job vẫn giữ state machine công khai hiện có;
    # `ambiguous` là lý do terminal, không tạo một hàng đợi/trạng thái song song.
    provider_state: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    provider_dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    # Mốc đầu tiên job thực sự sở hữu đủ tài nguyên để đi vào handler. Khác
    # `started_at` (worker claim): resource_wait có thể xảy ra nhiều lần ở giữa.
    admitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    #: Khi nào `params`/`result`/file của job này hết hạn và đã bị xoá. Hàng vẫn
    #: còn — nó là **bằng chứng** mà bút toán credit trỏ về. Có mốc này thì một
    #: `result` rỗng đọc ra là "đã hết hạn", chứ không phải "mất dữ liệu".
    content_expired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Index đúng câu truy vấn claim (W2.6c): WHERE status=? AND next_run_at<=?
        # ORDER BY created_at. Khi bảng job lớn, quét tuần tự mỗi vòng worker sẽ
        # tốn; index tổng hợp này cho claim đi thẳng vào đúng dòng đến hạn.
        Index("ix_jobs_claim", "status", "next_run_at", "created_at"),
        Index("ix_jobs_admission_queue", "admission_resource", "status",
              "created_at"),
        Index("ix_jobs_fairness", "admission_resource", "user_id",
              "last_claimed_at"),
        Index("ix_jobs_scheduler_queue", "admission_resource", "status",
              "next_run_at", "priority_class", "created_at"),
        Index("ix_jobs_priority_fairness", "admission_resource",
              "priority_class", "user_id", "last_claimed_at"),
        # 🔴 KHỬ TRÙNG BẰNG RÀNG BUỘC, KHÔNG BẰNG `SELECT` RỒI `INSERT`.
        #
        #    `jobs.submit()` chống double-submit bằng cách tìm job cùng
        #    `dedupe_key` chưa kết thúc rồi mới chèn nếu không thấy. Giữa hai câu
        #    đó là một cửa sổ tranh chấp thật: hai request song song (F5, hai tab,
        #    script gọi API) cùng thấy "chưa có", cùng chèn — và khách bị trừ tiền
        #    hai lần cho một yêu cầu.
        #
        # ⭐ Ba hệ độc lập hội tụ về đúng lời giải này: Activepieces
        #    `UNIQUE(flowRunId, stepName)` · n8n `UNIQUE(deduplicationKey) WHERE
        #    NOT NULL` · Trigger.dev `UNIQUE(environmentId, idempotencyKey)`.
        #
        # ⚠️ Phải là chỉ mục **BỘ PHẬN**, hai vế đều bắt buộc:
        #    - `dedupe_key <> ''` : mặc định là chuỗi rỗng và phần lớn job không
        #      dùng nó; một UNIQUE đầy đủ sẽ chặn mọi job thứ hai của một người.
        #    - chỉ khi chưa kết thúc : xong rồi thì gửi lại cùng yêu cầu là hợp lệ
        #      (bấm "Tạo lại"), và job cũ vẫn phải nằm đó làm bằng chứng cho sổ tiền.
        Index("ux_jobs_dedupe_active", "user_id", "dedupe_key", unique=True,
              postgresql_where=text(
                  "dedupe_key <> '' AND status IN ('queued', 'running')"),
              sqlite_where=text(
                  "dedupe_key <> '' AND status IN ('queued', 'running')")),
    )

    def __repr__(self) -> str:      # pragma: no cover
        return f"<Job {self.id[:8]} {self.job_type} {self.status} {self.progress}%>"


class ExecutionLease(Base):
    """Quyền dùng một slot thực thi dùng chung cho job, sync và stream.

    Đây không phải hàng đợi và không chứa payload. Ràng buộc UNIQUE biến việc
    giành một slot thành thao tác nguyên tử; heartbeat cho phép thu hồi quyền
    của tiến trình đã chết thay vì khoá tài nguyên vĩnh viễn.
    """

    __tablename__ = "execution_leases"
    __table_args__ = (
        UniqueConstraint("resource", "slot", name="uq_execution_lease_resource_slot"),
        Index("ix_execution_leases_resource_heartbeat", "resource", "heartbeat_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resource: Mapped[str] = mapped_column(String(96), nullable=False)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    holder_id: Mapped[str] = mapped_column(String(128), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False, index=True)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False, index=True)

    # ── Sổ ngân sách KV (multijob, `platform_core/llm/luat_nhan.py`) ─────────
    # Rỗng/0 ở mọi lease cũ và mọi tool không khai `admission_token_pool` —
    # luật nhận khi đó giữ nguyên hành vi "đếm slot" như trước.
    #: `tuong_tac` | `nen` | `noi_bo` — lớp ưu tiên (D-03).
    lop: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    #: `prompt_ước + max_tokens + đệm` — TOÀN BỘ ngữ cảnh chiếm trong pool KV.
    token_dat_truoc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Ước token phải prefill MỚI (sau phần cache trúng) — chỉ để xếp thứ tự.
    token_prefill_moi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Lượt prefill dài (D-05). Tắt khi byte đầu tiên về (prefill đã xong).
    la_whale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class LlmWaiter(Base):
    """Phòng chờ của cửa TƯƠNG TÁC tới model nhà — và **sổ từng lượt** của nó.

    Hai việc trong một bảng, có chủ ý (multijob, chủ dự án 11/09: "xây log lưu
    để phân tích sau"): dòng sinh ra khi request vào hàng, được cập nhật khi nó
    được nhận / rời / hết hạn / xong, rồi **ở lại 30 ngày**. Truy vấn bảng này
    trả lời được: chờ bao lâu, vì sao chờ, ngân sách nào nghẽn, whale nào gây áp
    lực — mà không phải dựng thêm một hệ log thứ hai.

    ⛔ KHÔNG chứa prompt, payload, tool, token bí mật hay credential.
    ⛔ Việc NỀN không có dòng ở đây — hàng bền của nó là bảng `jobs`.
    """

    __tablename__ = "llm_waiters"
    __table_args__ = (
        UniqueConstraint("request_id", name="uq_llm_waiters_request"),
        Index("ix_llm_waiters_resource_state", "resource", "trang_thai", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resource: Mapped[str] = mapped_column(String(96), nullable=False)
    #: Id model **nội bộ** của máy B (`qwen38-api`, `qwen35-api`), không phải bí
    #: danh công khai — bí danh không bao giờ rời máy A (INV-015) và nó đổi được
    #: mà không đổi engine, nên một sổ vận hành khoá theo bí danh sẽ nói về hai
    #: thứ khác nhau trước và sau một lần đổi tên.
    #:
    #: ⭐ VÌ SAO KHÔNG SUY TỪ `resource`. Hôm nay đúng một tài nguyên cho một
    #:    model (`ltt_38_3090` ↔ `qwen38-api`), nên phép suy ấy *chạy được* — và
    #:    đó chính là cái bẫy: phép suy sống trong `platform_core`, nơi **không
    #:    được biết tên của app** (`test_147` layering), nên nó phải nhập một
    #:    bảng ánh xạ từ `apps/` để dịch. Cột này là app tự khai một lần lúc vào
    #:    hàng, và `job_metrics` đọc thẳng. Rỗng = lượt của một cửa chưa khai
    #:    model; nó vào ô `khong_khai` chứ không bị gộp vào một model nào.
    model: Mapped[str] = mapped_column(
        String(64), default="", nullable=False, server_default=text("''"))
    #: `stream` | `sync` | `chatltt` — cửa vào.
    cua: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    lop: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    token_dat_truoc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_prefill_moi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    la_whale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    admitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    #: `cho` → `nhan` → `xong` | `roi` (khách đi khi đang chờ) | `het_han`
    #: (quá trần chờ hoặc mất nhịp tim).
    trang_thai: Mapped[str] = mapped_column(String(16), default="cho", nullable=False)
    #: Mã lý do của nhịp chờ CUỐI (`luat_nhan.CHO_*`).
    ly_do_cho: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    #: Trong tổng thời gian chờ, bao nhiêu giây là chờ vì **cư trú GPU**
    #: (`luat_nhan.CHO_RESIDENCY`, luật 0 — dual-model 5.3, D01 B).
    #:
    #: ⭐ VÌ SAO MỘT CỘT RIÊNG chứ không suy ra từ `ly_do_cho`: `ly_do_cho` giữ
    #:    lý do của nhịp **cuối**, tức nó trả lời "lúc bỏ cuộc thì đang vướng
    #:    gì", không trả lời "đã vướng gì bao lâu". Một lượt chờ 40 s vì cửa sổ
    #:    ảnh rồi 2 s vì hết slot sẽ mang `cho_slot` — và người đọc sổ sẽ đi mua
    #:    thêm slot cho một chuyện do cửa sổ ảnh gây ra.
    #:
    #: `finished_at - created_at` trừ con số này = thời gian chờ vì **năng lực**
    #: (slot, ngân sách KV, hàng). Hai đại lượng ấy dẫn tới hai việc sửa khác
    #: nhau, nên chúng phải đo được rời nhau. `platform_core/llm/phong_cho.py`
    #: cộng vào đây từng khoảng giữa hai nhịp; Task 6.3 công bố nó ở
    #: `/ops/jobs-metrics`.
    cho_residency_s: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False, server_default=text("0"))
    so_nhip: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Kết cục sau khi được nhận: `xong` | `khach_ngat` | `loi` | `thieu_credit` …
    ket_qua: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    lease_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    #: SỐ ĐO của lượt đã được nhận (T4 P2, `THIET_KE_R06_R07_ID_PHIEN.md` §2.3) —
    #: A vốn đếm được (`DemToken`, `KetQua` của cửa một cục) nhưng trước đây chỉ
    #: để trong một dòng log văn bản. Ghi ở `phong_cho.ghi_ket_thuc(so_do=)`.
    #:
    #: ⛔ `NULL`, KHÔNG `0`, khi không đo được (luồng vỡ trước `usage`, đường ra
    #:    bận/lỗi trước lượt) — cùng luật sổ B `llm_gateway/so_luot.py`: 0 là một
    #:    khẳng định, null là thú nhận. ⛔ Không chép TIỀN vào đây: tiền đọc từ
    #:    `credit_entries` qua `job_id = request_id` (hai chỗ ghi tiền sẽ lệch).
    token_vao: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_ra: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Phần của `token_vao` lấy lại từ cache prompt (đã NẰM TRONG `token_vao`).
    token_cache: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Giây từ lúc mở luồng tới byte DỮ LIỆU đầu (bỏ nhịp tim `: ping`), đo ở
    #: **phía A** — gồm mạng A↔B. TTFT phía B nằm ở sổ lượt B (`ttft_s`). Cửa
    #: không stream để NULL: không byte nào chảy trước cả lượt.
    ttfb_s: Mapped[float | None] = mapped_column(Float, nullable=True)


class GpuResidency(Base):
    """Model nào đang **cư trú** trên một nhóm GPU, và nhóm đang ở bước nào của
    việc đổi cư trú. Một dòng cho mỗi nhóm — hôm nay đúng một: `rtx3090`. (D01 B)

    Vì sao một dòng trong CSDL chứ không một biến trong tiến trình trọng tài: máy
    A có **nhiều** tiến trình (web + worker, và worker có thể nhiều máy), nhưng
    RTX 3090 chỉ có **một** cư trú. Cửa admission của LTT-3.8 và của job ảnh đọc
    trạng thái này trong advisory lock của tài nguyên (Task 5.3), nên nó phải
    nằm ở nơi mọi tiến trình cùng thấy. Một biến trong RAM cho hai tiến trình
    hai câu trả lời khác nhau — và hai câu trả lời khác nhau ở đây nghĩa là hai
    model cùng nạp lên một card 24 GB.

    ⛔ Bảng này **không** lưu thứ suy ra được từ `trang_thai`:

    * *thành viên nào đang được mở* — `llm.residency.mo_cho(trang_thai, vai_tro)`
      trả lời, và một cột lưu lại câu đó là hai chỗ khai cùng một điều;
    * *đã vẽ mấy ảnh trong cửa sổ* — đếm từ bảng `jobs` (job `theo_lo` được nhận
      kể từ `cua_so_bat_dau`), là **sự thật**, còn một bộ đếm ghi tay sẽ lệch
      đúng lúc một tiến trình chết giữa cửa sổ.

    `phien_ban` là khoá lạc quan: trọng tài đọc dòng, quyết, rồi ghi kèm
    ``WHERE nhom = … AND phien_ban = <đã đọc>``. Hai trọng tài chạy song song
    (một lượt deploy chồng nhau) thì đúng một cái ghi được.
    """

    __tablename__ = "gpu_residency"
    __table_args__ = (
        # Cố ý TRÙNG với primary key. Drill khôi phục (`tools/restore_drill_schema.py`)
        # đối chiếu ràng buộc **theo tên** trong danh sách sống còn của nó, và một
        # PRIMARY KEY không có tên `uq_` nào để đối chiếu. Mất tính duy nhất của
        # `nhom` sau khi khôi phục = hai dòng cư trú cho một card, tức hai câu trả
        # lời cho câu "3090 đang là của ai". Giá của bản khai thứ hai: một index
        # trên một bảng có một dòng mỗi nhóm.
        UniqueConstraint("nhom", name="uq_gpu_residency_nhom"),
    )

    #: Tên nhóm GPU. `rtx3090` = {`ltt_38_3090` (mac_dinh), `anh_3090` (theo_lo)}.
    nhom: Mapped[str] = mapped_column(String(32), primary_key=True)
    #: Một trong `llm.residency.TRANG_THAI` (`llm`, `xa_llm`, `nha_llm`, `anh`,
    #: `tra_anh`, `nap_llm`, `loi_nap`). Chuỗi chứ không Enum CSDL: máy trạng
    #: thái là nguồn chân lý, và thêm một trạng thái không nên cần migration.
    trang_thai: Mapped[str] = mapped_column(String(16), default="llm", nullable=False)
    #: Vào `trang_thai` hiện tại từ lúc nào — mẫu số của lùi dần và của quan sát.
    tu_luc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    #: Cửa sổ ảnh mở lúc nào. NULL khi nhóm không ở trong một cửa sổ ảnh.
    cua_so_bat_dau: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    lan_nap_loi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    phien_ban: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class JobEvent(Base):
    """Nhật ký append-only của một job, đã tách nội dung khách và nội bộ.

    ``public_message`` là câu an toàn để hiện cho chủ job. Chi tiết kỹ thuật ở
    ``details`` chỉ dành cho operator/support và luôn đi qua bộ lọc bí mật trước
    khi ghi. Không lưu params/provider payload vào bảng này.
    """

    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    app_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_code: Mapped[str] = mapped_column(String(48), nullable=False)
    level: Mapped[str] = mapped_column(String(12), default="info", nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(12), default="customer", nullable=False)
    public_message: Mapped[str] = mapped_column(
        String(255), default="", nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    event_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    __table_args__ = (
        UniqueConstraint("job_id", "sequence", name="uq_job_events_job_sequence"),
        UniqueConstraint("job_id", "event_key", name="uq_job_events_job_event_key"),
        Index("ix_job_events_job_sequence", "job_id", "sequence"),
        Index("ix_job_events_user_app_created", "user_id", "app_slug", "created_at"),
        Index("ix_job_events_visibility_created", "visibility", "created_at"),
    )


UPLOAD_PENDING = "pending"
UPLOAD_READY = "ready"
UPLOAD_ATTACHED = "attached"
UPLOAD_PROMOTED = "promoted"
UPLOAD_DELETED = "deleted"


class UploadSession(Base):
    """Vé upload owner-scoped; artifact chỉ bền vững sau hold credit."""

    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    app_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    staging_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    final_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    filename: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_size: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=UPLOAD_PENDING, nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, onupdate=_bay_gio, nullable=False)

    __table_args__ = (
        Index("ix_upload_sessions_owner_status", "user_id", "status", "expires_at"),
        Index("ix_upload_sessions_app_created", "app_slug", "created_at"),
        Index("ix_upload_sessions_job", "job_id"),
        Index("ix_upload_sessions_project", "project_id", "status"),
    )


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
    # Q62: document v2 is the lossless editor source. Legacy columns remain as
    # an execution projection so rollback can still read every v1 workflow.
    document: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
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


class AgentWorkflowSnapshot(Base):
    """Immutable editor revision used for diff/restore and activity audit."""

    __tablename__ = "agent_workflow_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    document: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    reason: Mapped[str] = mapped_column(String(32), default="save", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    __table_args__ = (
        Index("ux_agent_snapshot_workflow_revision", "workflow_id", "revision", unique=True),
    )


class AgentWorkflowShare(Base):
    """Revocable private share. Only a SHA-256 token digest is persisted."""

    __tablename__ = "agent_workflow_shares"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    permission: Mapped[str] = mapped_column(String(16), default="view", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
#: Trừ phí thuê bao Nexus theo máy/tháng (Q98). Là bút toán âm trực tiếp, không
#: qua hold/settle: đây là phí định kỳ, không phải một lượt job.
CREDIT_NEXUS_BILL = "nexus_bill"


class NhatKyAdmin(Base):
    """Nhật ký thao tác của quản trị viên (F-06, audit 2026-08-07).

    Vì sao cần dù chỉ có một admin: `cap_tay(by=)` đã ghi `admin=` vào ghi chú
    bút toán, nên **tiền** thì truy được. Nhưng đổi vai trò và vô hiệu hoá tài
    khoản thì không để lại dấu vết nào — không biết ai làm, lúc nào. Khi có admin
    thứ hai thì đó là chỗ không trả lời được câu "ai đã tắt tài khoản này".

    Chỉ ghi thêm, không sửa, không xoá — cùng nguyên tắc với sổ credit.
    """

    __tablename__ = "nhat_ky_admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False, index=True)
    admin_email: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    hanh_dong: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    doi_tuong: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    chi_tiet: Mapped[str] = mapped_column(Text, default="", nullable=False)

    def __repr__(self) -> str:
        return f"<NhatKyAdmin {self.admin_email} {self.hanh_dong} {self.doi_tuong}>"


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
    # F-01 (audit 2026-08-07): khoa ngoai la luoi an toan cuoi cho MOI duong ghi.
    # RESTRICT — khong cho xoa nguoi dung con but toan: so credit la bang chung
    # doi soat tien. Ngung mot tai khoan thi dung `is_active=False`.
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"),
        index=True, nullable=False)
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


class GpuLease(Base):
    """Chỗ đã giành trên MỘT GPU. Có dòng = GPU đang bận (H23).

    Vì sao cần bảng này thay vì chỉ đọc VRAM còn trống: đọc rồi quyết định là
    một cuộc đua kinh điển. Hai worker cùng thấy "GPU 0 trống 16 GB", cùng chọn
    GPU 0, cùng nạp model, cùng OOM — và lỗi hiện ra ở giữa job của khách hàng
    chứ không phải lúc xếp lịch. Ràng buộc UNIQUE dưới đây biến việc giành chỗ
    thành **nguyên tử**: hai INSERT cùng lúc thì CSDL cho đúng một cái thắng.

    `gpu_uuid` chứ không phải index mới là khoá thật: driver đánh index theo thứ
    tự bus và **đổi khi cắm thêm/bớt card**. Một lease ghi "GPU 1" sẽ trỏ sang
    card khác sau khi lắp thêm card; UUID thì không đổi. `gpu_index` giữ lại chỉ
    để đọc log cho dễ.

    `host` có mặt vì GPU là tài nguyên **của từng máy**: "GPU 0" trên máy A và
    "GPU 0" trên máy B là hai thứ khác nhau, và sau này worker có thể chạy nhiều
    máy.

    Quy ước v1: **một job một GPU**, không chia sẻ. Cố ý chọn vậy — việc nặng
    của nền tảng (whisper, YOLO, upscale) đều ngốn VRAM, và kế toán VRAM theo
    hứa hẹn sẽ lệch so với thực tế rồi OOM. Muốn chia sẻ thì đổi UNIQUE thành
    kế toán tổng `vram_mb`, nhưng đừng làm khi chưa đo được là cần.
    """

    __tablename__ = "gpu_leases"
    __table_args__ = (
        # Trái tim của cơ chế: một GPU trên một máy chỉ có tối đa một lease sống.
        UniqueConstraint("host", "gpu_uuid", name="uq_gpu_lease_host_uuid"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    host: Mapped[str] = mapped_column(String(128), nullable=False)
    gpu_uuid: Mapped[str] = mapped_column(String(64), nullable=False)
    gpu_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    worker_id: Mapped[str] = mapped_column(String(128), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False, index=True)
    vram_mb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    # Worker chết giữa chừng thì lease phải tự hết hạn, nếu không GPU khoá vĩnh
    # viễn. Cùng cơ chế `heartbeat_at` mà hàng đợi job đã dùng cho job mồ côi.
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False, index=True)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<GpuLease {self.host}:{self.gpu_index} job={self.job_id[:8]}>"


class SingletonLease(Base):
    """Ai được phép làm một việc mà chỉ MỘT tiến trình được làm.

    Cùng ý tưởng với `GpuLease` và cố ý giống hệt: giành bằng INSERT, ràng buộc
    UNIQUE quyết định người thắng, `heartbeat_at` khiến chủ chết thì lease tự
    hết hạn. Khác ở chỗ tài nguyên không phải một card mà là một **vai trò**
    ("người chạy vòng bảo trì").

    Vì sao không dùng `pg_advisory_lock`: xem `platform_core/leases.py`. Tóm
    tắt — SQLite không có, nên đường quan trọng nhất sẽ không test được ở nơi
    dễ chạy nhất.

    Vì sao lease **hết hạn** thay vì giữ mãi: một tiến trình giữ vai trò rồi
    chết sẽ làm việc nền dừng **vĩnh viễn và im lặng** — không job nào hỏng để
    ai nhận ra, chỉ là webhook không còn được gửi nữa.
    """

    __tablename__ = "singleton_leases"
    __table_args__ = (
        # Trái tim của cơ chế: một tên chỉ có tối đa một lease sống. Đặt TÊN cho
        # ràng buộc vì bộ kiểm phục hồi (`tools/restore_drill_schema.py`) đối
        # chiếu theo tên — mất ràng buộc này sau một lần khôi phục nghĩa là mọi
        # tiến trình worker lại cùng chạy việc nền, im lặng.
        UniqueConstraint("name", name="uq_singleton_lease_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    holder: Mapped[str] = mapped_column(String(160), nullable=False)

    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False, index=True)

    def __repr__(self) -> str:      # pragma: no cover
        return f"<SingletonLease {self.name} holder={self.holder}>"


# ── LTT WORKFLOW V2 · Đợt 2.1 — định nghĩa workflow ──────────────────────────
#
# Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §4.1`.
#
# ⚠️ KHÔNG dùng lại `agent_workflows`. Bảng cũ trộn ba thứ vào một hàng — bản
#    đang soạn (sửa được), bản đang chạy (phải bất biến), và phóng chiếu thi
#    hành. Ba vòng đời khác nhau trong một hàng là lý do không thể ghim một
#    lượt chạy vào đúng nội dung nó khởi động cùng.


class Workflow(Base):
    """Danh tính một workflow. KHÔNG chứa nội dung — nội dung ở draft/version."""

    __tablename__ = "workflow"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # Tên mặc định do TẦNG SERVICE đặt, không phải CSDL: nó là chữ hiện cho
    # người dùng nên phải đi qua `N_()` để bộ trích dịch thấy. Một `default=`
    # tiếng Việt ở đây là một chuỗi giao diện nằm ngoài tầm với của i18n.
    name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    # Version mà trigger đang dùng. Rỗng = chưa xuất bản lần nào.
    published_version_id: Mapped[str] = mapped_column(
        String(36), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_workflow_owner_updated", "owner_id", "updated_at"),
    )


class WorkflowDraft(Base):
    """Bản đang soạn — SỬA ĐƯỢC. Một draft cho mỗi workflow.

    `revision` là khoá lạc quan: hai tab cùng mở thì tab đến sau nhận 409 thay
    vì ghi đè âm thầm phần người kia vừa gõ.
    """

    __tablename__ = "workflow_draft"

    workflow_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)


class WorkflowVersion(Base):
    """Một bản đã xuất bản — **BẤT BIẾN** sau khi tạo.

    ⭐ `UNIQUE (workflow_id, graph_hash)` khiến "xuất bản hai lần cùng nội dung"
       trở thành **không thể**, bằng ràng buộc CSDL chứ không bằng mã cẩn thận.
       Ba hệ độc lập đã hội tụ về đúng khuôn này (`12_19 §16`).

    ⚠️ `estimated_max` đóng băng **cùng** graph. Tính lại lúc chạy nghĩa là một
       lượt chạy có thể vượt trần mà người duyệt chưa từng thấy con số ấy.
    """

    __tablename__ = "workflow_version"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    graph: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    graph_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    estimated_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), default="", nullable=False)

    __table_args__ = (
        UniqueConstraint("workflow_id", "seq", name="uq_workflow_version_seq"),
        UniqueConstraint("workflow_id", "graph_hash",
                         name="uq_workflow_version_hash"),
    )


class WorkflowVersionNode(Base):
    """Chỉ mục DẪN XUẤT từ `graph`, sinh tại `xuat_ban()`.

    Tồn tại để trả lời "tool X đang được dùng ở workflow nào?" bằng một câu SQL
    thay vì quét jsonb toàn bảng. Không phải nguồn chân lý — `graph` mới là.
    """

    __tablename__ = "workflow_version_node"

    version_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_type: Mapped[str] = mapped_column(String(96), nullable=False)
    type_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        Index("ix_wvn_type", "node_type"),
    )


class WorkflowVersionEdge(Base):
    """Chỉ mục dẫn xuất cho cạnh. `kind` ∈ {DATA, CONTROL, RESOURCE}."""

    __tablename__ = "workflow_version_edge"

    version_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    edge_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_node: Mapped[str] = mapped_column(String(64), nullable=False)
    source_port: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    target_node: Mapped[str] = mapped_column(String(64), nullable=False)
    target_port: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="DATA", nullable=False)
    condition: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_wve_version", "version_id"),
    )


# ── LTT WORKFLOW V2 · Đợt 2.2 — thi hành (mô hình C) ─────────────────────────
#
# Chốt `Q3` (`12_19 §16.2`): trạng thái mỗi node là một **chuỗi ảnh chụp BẤT
# BIẾN**, không phải một khối JSON sửa tại chỗ.
#
# 🔴 `M1` là lý do tồn tại. `agent/executor.tick()` đọc cả `checkpoint`, sửa,
#    ghi lại — `O(31+N)` mỗi lượt tiến dù chỉ một node đổi. Ở đây một lượt tiến
#    là `INSERT` đúng những node vừa đổi + `UPDATE` con trỏ.


class WorkflowRun(Base):
    """Một lượt chạy. `version_id` GHIM và không bao giờ đổi.

    ⭐ Ghim là điểm khác cốt lõi với `AgentRun`: sửa workflow lúc 10:00 **không**
       được đổi lượt chạy bắt đầu 09:58. Không ghim thì một lượt chạy dài không
       có nội dung xác định — báo cáo sự cố của nó nói về một đồ thị không còn
       tồn tại.
    """

    __tablename__ = "workflow_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="CREATED",
                                        nullable=False, index=True)
    trigger_kind: Mapped[str] = mapped_column(String(24), default="manual",
                                              nullable=False)
    # Rỗng = lượt này không dùng khoá. Ràng buộc duy nhất phải là BỘ PHẬN, nếu
    # không mọi lượt chạy thứ hai của một người sẽ bị chặn — cùng bài học với
    # `ux_jobs_dedupe_active` (`c9d4e1a77b02`).
    idempotency_key: Mapped[str] = mapped_column(String(120), default="",
                                                 nullable=False)
    estimated_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actual_cost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hold_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    # ⭐ Dấu KẾT SỔ. Nó là thứ làm hệ con `finally` **luỹ đẳng**, và luỹ đẳng là
    #   điều kiện để gọi được nó ở nhiều chỗ mà vẫn an toàn — một hệ con chỉ an
    #   toàn ở một chỗ thì sớm muộn cũng bị bỏ sót ở chỗ thứ hai.
    #   `NULL` = chưa kết sổ. Xem `platform_core/workflow/ket_so.py`.
    ket_so_luc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    ly_do_ket_so: Mapped[str] = mapped_column(String(200), default="",
                                              nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ux_workflow_run_idem", "owner_id", "idempotency_key",
              unique=True, postgresql_where=text("idempotency_key <> ''"),
              sqlite_where=text("idempotency_key <> ''")),
        Index("ix_workflow_run_owner_created", "owner_id", "created_at"),
    )


class NodeRun(Base):
    """CON TRỎ: một hàng mỗi node mỗi run, trỏ tới ảnh chụp mới nhất.

    Bảng này **được sửa**; `node_run_snapshot` thì không. Tách hai vai đó là
    điều khiến `M1` đạt được: đọc trạng thái hiện tại là một `JOIN` chứ không
    phải một lần quét lịch sử.
    """

    __tablename__ = "node_run"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    latest_snapshot_id: Mapped[str] = mapped_column(String(36), nullable=False)


class NodeRunSnapshot(Base):
    """⭐⭐ CHỈ THÊM — KHÔNG BAO GIỜ SỬA.

    Bốn thứ được giải quyết cùng lúc bởi bảng này (`21_22`:
    `G18`·`G19`·`G20`·`G21`·`G44`), và đó là lý do nó thay được **hai** bảng:

      lịch sử đầy đủ          mỗi lần chuyển là một hàng, không đè lên nhau
      chuyển bị TỪ CHỐI       `is_valid=False` — điều tra được ai thua và vì sao
      chi phí theo attempt    `cost_credit` ghi LÚC KẾT THÚC, không tính lại
      dòng thời gian          không cần một bảng nhật ký thứ hai

    ⛔ `output_ref` chỉ giữ **tham chiếu** artifact, không giữ bytes. Một ảnh
       chụp là siêu dữ liệu; nhét nội dung vào đây biến bảng chỉ-thêm thành một
       kho nhị phân không xoá được.
    """

    __tablename__ = "node_run_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # Rỗng = ảnh chụp đầu tiên của node này. Chuỗi liên kết ngược cho phép đọc
    # lại đúng đường đi mà không cần sắp theo thời gian — hai ảnh chụp có thể
    # cùng mốc thời gian, nhưng không thể cùng một cha.
    previous_snapshot_id: Mapped[str] = mapped_column(
        String(36), default="", nullable=False)
    execution_status: Mapped[str] = mapped_column(String(24), nullable=False)
    run_status: Mapped[str] = mapped_column(String(24), default="",
                                            nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1,
                                                nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    output_ref: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    cost_credit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    __table_args__ = (
        Index("ix_nrs_run", "run_id", "created_at"),
    )


# ── LTT WORKFLOW V2 · Đợt 2.3 — waitpoint ────────────────────────────────────
#
# Nguồn thiết kế: `23_24 §4.3`. Ba quyết định, ba khiếm khuyết đo được ở kho
# khác: nhiều-nhiều (Activepieces không biểu đạt nổi 20 node chờ 1 job) ·
# `sealed` (không có nó thì `ALL` vô nghĩa khi số nhánh động) ·
# `NOT_DISPATCHED` (một nhánh chết treo barrier vĩnh viễn).


class Waitpoint(Base):
    """Một thứ mà node đang chờ. KHÔNG gắn cứng vào một node — xem `NodeRunWaitpoint`."""

    __tablename__ = "waitpoint"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # DELAY | JOB | WEBHOOK | HUMAN | CHILD_RUN | BARRIER
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # PENDING | COMPLETED | EXPIRED | CANCELLED
    status: Mapped[str] = mapped_column(String(16), default="PENDING",
                                        nullable=False)
    # ⭐ "sẽ không còn tín hiệu nào nữa". Không có cờ này thì `ALL` không định
    #    nghĩa được: "đủ tất cả" so với cái gì, khi nhánh còn có thể sinh thêm?
    sealed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 0 = ALL (chỉ kết luận được sau khi `sealed`). >0 = N-of-M.
    required_successes: Mapped[int] = mapped_column(Integer, default=0,
                                                    nullable=False)
    release_on_first_failure: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), default="",
                                            nullable=False)
    output_ref: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_is_error: Mapped[bool] = mapped_column(Boolean, default=False,
                                                  nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), default="",
                                                 nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    __table_args__ = (
        # Bộ phận: phần lớn waitpoint không dùng khoá. Cùng bài học với
        # `ux_jobs_dedupe_active` (`c9d4e1a77b02`).
        Index("ux_waitpoint_idem", "owner_id", "idempotency_key", unique=True,
              postgresql_where=text("idempotency_key <> ''"),
              sqlite_where=text("idempotency_key <> ''")),
        # ⭐ Chỉ số BỘ PHẬN: bộ quét chỉ quan tâm cái đang chờ và có hẹn giờ.
        #    Hội tụ độc lập ba lần (Activepieces · n8n · Trigger.dev, `23_24 §3`).
        Index("ix_waitpoint_due", "due_at",
              postgresql_where=text("status = 'PENDING' AND due_at IS NOT NULL"),
              sqlite_where=text("status = 'PENDING' AND due_at IS NOT NULL")),
    )


class WaitpointSignal(Base):
    """Một tín hiệu tới một waitpoint. `seq` phân biệt nhánh.

    ⭐ `NOT_DISPATCHED` = tín hiệu **lẽ ra phải gửi mà chưa bao giờ gửi**. Thiếu
       trạng thái này, một nhánh chết không SUCCEEDED cũng không FAILED — nó
       **vắng mặt**, và `ALL` sau khi niêm phong đứng mãi. Ghi nó ra biến một
       treo vô hạn thành một kết luận.
    """

    __tablename__ = "waitpoint_signal"

    waitpoint_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    # PENDING | SUCCEEDED | FAILED | CANCELLED | NOT_DISPATCHED
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    ref_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    result_ref: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)


class NodeRunWaitpoint(Base):
    """⭐ NHIỀU-NHIỀU: một waitpoint chặn N node, một node chờ N waitpoint.

    `WF-204`: 20 node ForEach cùng chờ **một** job GPU. Mô hình
    một-waitpoint-một-bước không biểu đạt nổi kịch bản ấy, và nó không phải
    kịch bản hiếm — nó là hình dạng mặc định của ForEach có tài nguyên chung.
    """

    __tablename__ = "node_run_waitpoint"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    waitpoint_id: Mapped[str] = mapped_column(String(36), primary_key=True)


# ── LTT WORKFLOW V2 · Đợt 2.4 — đánh thức ────────────────────────────────────


class Wakeup(Base):
    """Nguồn CHÂN LÝ của việc đánh thức. `LISTEN/NOTIFY` chỉ rút ngắn độ trễ.

    🔴 Vì sao bảng chứ không phải `NOTIFY` — một con số, không phải sở thích:
       worker restart **13,6 lần/ngày** (`01 §A.6`). Một `NOTIFY` phát đúng lúc
       worker đang khởi động lại **biến mất không dấu vết**. Bảng thì không.

    🔴 `M2`: một run chờ 60 phút có **một** hàng ở đây và phát sinh **0** câu
       SQL trong 60 phút đó. Bộ quét hỏi *"có hàng nào tới hạn chưa"* bằng
       **một** truy vấn cho **toàn hệ thống**, đi thẳng vào `ix_wakeup_due`.
    """

    __tablename__ = "wakeup"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    node_run_id: Mapped[str] = mapped_column(String(64), default="",
                                             nullable=False)
    # job_done | waitpoint_due | approval | child_run | resource_free
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                             nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    __table_args__ = (
        # ⭐ Khử trùng bằng RÀNG BUỘC. Hai đường (bảng và `NOTIFY`) cùng hẹn một
        #    lần đánh thức là trạng thái BÌNH THƯỜNG, không phải sự cố — chốt
        #    `Q4` đòi cả hai đường luỹ đẳng, và chỗ cưỡng chế là đây.
        UniqueConstraint("run_id", "node_run_id", "kind", "due_at",
                         name="uq_wakeup_khu_trung"),
        # ⭐ Chỉ số BỘ PHẬN: hàng đã nhặt không còn là việc, đừng để nó làm
        #    phình chỉ số mà bộ quét đi qua mỗi 5 giây.
        Index("ix_wakeup_due", "due_at",
              postgresql_where=text("claimed_at IS NULL"),
              sqlite_where=text("claimed_at IS NULL")),
    )


# ── LTT WORKFLOW V2 · Đợt 4.3 — ForEach ──────────────────────────────────────


class ForeachVong(Base):
    """Một vòng ForEach. `max_items` là **chặn trên**, không phải gợi ý."""

    __tablename__ = "foreach_vong"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    max_items: Mapped[int] = mapped_column(Integer, nullable=False)
    # `M4`: hôm nay 4 **cứng**. V2 khai được, mặc định 8.
    parallelism: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    so_muc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)


class ForeachMuc(Base):
    """MỘT hàng cho MỖI phần tử, ghi sẵn ngay lúc mở vòng.

    ⭐ Đây là thứ làm `M7` đạt được. Một **con trỏ** "đã tới đâu" chỉ đúng khi
       các phần tử chạy tuần tự; với `parallelism > 1` thì phần tử 7 có thể xong
       trước phần tử 3, và con trỏ **không biểu đạt nổi** trạng thái ấy.

    ⇒ Sau một lần chết, "còn phải chạy gì" là một câu `WHERE xong = false` —
      chính xác, không suy đoán.
    """

    __tablename__ = "foreach_muc"

    vong_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chi_so: Mapped[int] = mapped_column(Integer, primary_key=True)
    dau_vao: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ket_qua: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    xong: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_foreach_muc_chua_xong", "vong_id",
              postgresql_where=text("xong = false"),
              sqlite_where=text("xong = 0")),
    )


# ── LTT WORKFLOW V2 · Đợt 5.1 — artifact ─────────────────────────────────────


class Artifact(Base):
    """Tệp sinh ra bởi một lượt chạy. `id = "<backend>:<key>"` — **TỰ MÔ TẢ**.

    🔴 Bản vá cho một lỗ **sẽ nổ**: ngày R2 chạy song song Local,
       `storage.get_storage()` là singleton toàn cục ⇒ mọi khoá cũ thành mơ hồ.
       Tham chiếu đi vào `output_ref` của bước sau, và **JSONB không tra bảng
       được** — nên backend phải nằm ngay trong id (bài học n8n, `05 §4.1`).
    """

    __tablename__ = "artifact"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # ⭐ LINEAGE: "tệp này từ đâu ra" trả lời được bằng MỘT cột.
    created_by_snapshot_id: Mapped[str] = mapped_column(
        String(36), default="", nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="file", nullable=False)
    mime: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), default="",
                                                 nullable=False)
    # EPHEMERAL | RUN | PROJECT | PERMANENT
    ttl_class: Mapped[str] = mapped_column(String(16), default="RUN",
                                           nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    __table_args__ = (
        Index("ix_artifact_expiry", "expires_at",
              postgresql_where=text(
                  "ttl_class <> 'PERMANENT' AND expires_at IS NOT NULL"),
              sqlite_where=text(
                  "ttl_class <> 'PERMANENT' AND expires_at IS NOT NULL")),
    )


# ── LTT WORKFLOW V2 · Đợt 5.4 — trigger ──────────────────────────────────────


class WorkflowTrigger(Base):
    """Cái gì làm một workflow chạy. Mỗi `kind` là một MÔ-ĐUN, không phải một `if`.

    Nền tảng **không biết tên** loại nào: nó chỉ biết một loại phải trả lời được
    `toi_han()` và `lan_ke_tiep()`. Thêm loại thứ năm là một lần `dang_ky()`,
    không phải một lần sửa `platform_core` (`G42`, bài học Windmill).
    """

    __tablename__ = "workflow_trigger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False,
                                             index=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    next_fire_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)

    __table_args__ = (
        Index("ix_trigger_due", "next_fire_at",
              postgresql_where=text("enabled AND next_fire_at IS NOT NULL"),
              sqlite_where=text("enabled = 1 AND next_fire_at IS NOT NULL")),
    )
