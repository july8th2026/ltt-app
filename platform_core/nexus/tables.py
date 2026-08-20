"""Bảng của Nexus: thiết bị và mã ghép.

Hai bảng, và ranh giới giữa chúng là ranh giới bảo mật chứ không phải chuyện gọn
gàng: `nexus_devices` giữ **khoá công khai** của một máy đã được tin, còn
`nexus_enrollments` giữ **mã ghép dùng một lần** — thứ duy nhất đủ để biến một
máy lạ thành một máy được tin, và cũng là thứ kẻ lừa đảo sẽ nhắm vào (T1).

## Vì sao chỉ có khoá công khai

Q93 ràng buộc 1: khoá riêng **không bao giờ rời máy đó**. Máy sinh cặp khoá tại
chỗ, cất bằng cơ chế của hệ điều hành, và chỉ gửi lên phần công khai. Hệ quả:
**đọc trộm toàn bộ hai bảng này không cho phép giả mạo một thiết bị nào** — khác
hẳn một bảng chứa bearer token, nơi rò rỉ CSDL là mất tất cả.

Đây cũng là chỗ **không** chép lại mẹo mà một app trong repo đang dùng cho tiến
trình cục bộ của nó: nhét token vào bảng `sessions` với một nhãn `user_agent`.
Mẹo đó đủ cho một tiến trình copy file, nhưng không đủ cho danh tính thiết bị —
không chống được nhân bản token, và không thu hồi được theo từng máy.
(`platform_core` không được nhắc tên app, kể cả trong chú thích — `AGENTS.md` 8.4.)

## Vì sao mã ghép được băm

Cùng lý do khoá API của khách được băm (Q92): không có gì cần đọc lại mã gốc,
chỉ cần kiểm một lần. Băm cả mã ghép nghĩa là một bản dump CSDL rơi ra ngoài
cũng **không** cho kẻ cầm nó ghép được máy nào.

Ở đây dùng SHA-256 có domain separation chứ không dùng KDF chậm: mã ghép sống
vài phút, dùng một lần, và có trần số lần thử — không có cửa sổ để tấn công
ngoại tuyến như với mật khẩu người dùng.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, ForeignKey, Index, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base

#: Tiền tố khoá công khai, để một chuỗi lạc ra ngoài còn nhận ra được là gì.
DEVICE_KEY_PREFIX = "ltt_dev"

#: Mã ghép hết hạn sau bao lâu. Ngắn có chủ ý: đây là cửa sổ mà kẻ lừa đảo dùng
#: để bảo nạn nhân đọc mã qua điện thoại (T1). Năm phút đủ cho người thật cài
#: xong phần mềm và gõ mã, và đủ ngắn để một cuộc gọi lừa đảo phải vội.
ENROLL_TTL_S = 300

#: Sai bao nhiêu lần thì mã chết hẳn. Mã ngắn để người gõ được, nên phải có
#: trần — không thì nó thành thứ dò được.
ENROLL_MAX_ATTEMPTS = 5


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


class NexusDevice(Base):
    """Một máy đã được ghép vào một tài khoản.

    `revoked_at` chứ không xoá dòng: sau sự cố, câu hỏi duy nhất quan trọng là
    "máy nào đã từng được tin, và bị gỡ lúc nào". Xoá dòng là xoá luôn câu trả
    lời đó.
    """

    __tablename__ = "nexus_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    #: Tên do khách đặt. Hiện cho khách, nên không tin là an toàn khi render.
    display_name: Mapped[str] = mapped_column(String(120), default="",
                                              nullable=False)

    #: Khoá CÔNG KHAI của thiết bị. Không bao giờ có khoá riêng ở đây.
    public_key: Mapped[str] = mapped_column(Text, nullable=False)

    #: Dấu vân tay phần cứng do agent khai. Dùng để NHẬN RA một máy cài lại, KHÔNG
    #: dùng làm danh tính — nó giả được, còn khoá riêng thì không.
    hardware_fingerprint: Mapped[str] = mapped_column(String(128), default="",
                                                      nullable=False)
    platform: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    agent_version: Mapped[str] = mapped_column(String(32), default="",
                                               nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    #: Nhịp tim gần nhất. NULL = chưa bao giờ kết nối.
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    #: Ai thu hồi: `owner`, `admin:<user_id>`, `system:<lý do>`. Q93 ràng buộc 5
    #: đòi mọi hành động của admin để lại dấu chủ thiết bị đọc được.
    revoked_by: Mapped[str] = mapped_column(String(64), default="",
                                            nullable=False)

    __table_args__ = (
        # Một khoá công khai chỉ thuộc về một thiết bị. Nếu hai dòng cùng khoá
        # thì "thu hồi thiết bị này" trở thành câu hỏi không có câu trả lời.
        UniqueConstraint("public_key", name="uq_nexus_devices_public_key"),
        Index("ix_nexus_devices_user", "user_id"),
        Index("ix_nexus_devices_seen", "last_seen_at"),
    )

    def is_usable(self, *, now: datetime | None = None) -> bool:
        return self.revoked_at is None

    def __repr__(self) -> str:      # pragma: no cover - chi de doc khi go roi
        trang_thai = "revoked" if self.revoked_at else "active"
        return f"<NexusDevice {self.display_name!r} {trang_thai}>"


class NexusEnrollment(Base):
    """Mã ghép dùng một lần: biến một máy lạ thành một máy được tin.

    Chỉ giữ **digest**, không giữ mã gốc. `consumed_at` khác NULL nghĩa là đã
    dùng — và một mã đã dùng thì chết vĩnh viễn, kể cả khi chưa hết hạn.
    """

    __tablename__ = "nexus_enrollments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    code_digest: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)

    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    #: Thiết bị đã dùng mã này. Giữ lại để dựng được đường đi từ một máy ngược
    #: về lúc nó được ghép.
    device_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: IP của máy đã đổi mã. Ghi để trả lời "máy đó ghép từ đâu" sau sự cố.
    claimed_ip: Mapped[str] = mapped_column(String(64), default="",
                                            nullable=False)

    __table_args__ = (
        # CSDL cưỡng chế tính duy nhất, không để Python đọc-rồi-ghi quyết định.
        # Đây đúng là bài học H36.3: hai tiến trình cùng kiểm "chưa ai dùng" rồi
        # cùng ghi.
        UniqueConstraint("code_digest", name="uq_nexus_enrollments_digest"),
        Index("ix_nexus_enrollments_user", "user_id"),
        Index("ix_nexus_enrollments_expires", "expires_at"),
    )

    def is_open(self, *, now: datetime | None = None) -> bool:
        """Còn đổi được không: chưa dùng, chưa hết hạn, chưa quá số lần thử."""
        current = now or _bay_gio()
        han = self.expires_at
        if han is not None and han.tzinfo is None:
            han = han.replace(tzinfo=timezone.utc)
        return (self.consumed_at is None
                and self.attempts < ENROLL_MAX_ATTEMPTS
                and han is not None and han > current)


class NexusSession(Base):
    """Một phiên điều khiển: vé được cấp, được đổi, rồi kết thúc.

    Dòng này **vừa là vé vừa là bản ghi kiểm toán**, và đó là chủ ý: nếu vé sống
    ở một chỗ còn nhật ký ở chỗ khác thì sẽ có ngày hai chỗ lệch nhau, và lúc
    cần đối chiếu sau sự cố thì không biết tin cái nào.

    Không bao giờ xoá, không bao giờ sửa lại quá khứ (Q93 ràng buộc 6). Kết thúc
    là **ghi thêm** `ended_at` + `end_reason`.
    """

    __tablename__ = "nexus_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    #: Người điều khiển. Cũng là chủ thiết bị — `sessions.cap_ve` cưỡng chế điều
    #: đó, nên hai cột này không bao giờ trỏ về hai tài khoản khác nhau.
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("nexus_devices.id", ondelete="CASCADE"),
        nullable=False)

    #: Chỉ digest. Vé gốc chỉ tồn tại trong một phản hồi HTTP duy nhất.
    ticket_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    quyen: Mapped[str] = mapped_column(String(16), nullable=False)
    controller_ip: Mapped[str] = mapped_column(String(64), default="",
                                               nullable=False)

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    #: Lúc vé được đổi thành phiên. NULL = vé chưa dùng.
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    end_reason: Mapped[str] = mapped_column(String(32), default="",
                                            nullable=False)

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str] = mapped_column(String(64), default="",
                                            nullable=False)

    #: Cầu nối tới engine truyền (RustDesk). Agent của máy đích BÁO hai thứ này
    #: khi đổi vé (W3/W4): `engine_id` là định danh kết nối của RustDesk (số, KHÔNG
    #: bí mật — như số điện thoại), `engine_secret_enc` là mật khẩu MỘT-LẦN của
    #: phiên, **mã hoá at-rest** bằng `platform_core.secretbox` (không bao giờ lưu
    #: thô). Cả hai rỗng cho tới khi agent báo, và bị **xoá** khi phiên kết thúc
    #: hoặc bị thu hồi (W2) — mật khẩu phiên không được sống lâu hơn phiên.
    engine_id: Mapped[str] = mapped_column(String(64), default="",
                                           nullable=False)
    engine_secret_enc: Mapped[str] = mapped_column(Text, default="",
                                                   nullable=False)
    engine_reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("ticket_digest", name="uq_nexus_sessions_ticket"),
        Index("ix_nexus_sessions_user", "user_id"),
        Index("ix_nexus_sessions_device", "device_id"),
        Index("ix_nexus_sessions_issued", "issued_at"),
    )

    def con_doi_duoc(self, *, now: datetime | None = None) -> bool:
        """Vé còn đổi được không: chưa dùng, chưa thu hồi, chưa hết hạn."""
        current = now or _bay_gio()
        han = self.expires_at
        if han is not None and han.tzinfo is None:
            han = han.replace(tzinfo=timezone.utc)
        return (self.consumed_at is None and self.revoked_at is None
                and han is not None and han > current)

    def dang_chay(self, *, now: datetime | None = None) -> bool:
        """Phiên đang mở: đã đổi vé, chưa kết thúc, chưa bị thu hồi."""
        return (self.consumed_at is not None and self.ended_at is None
                and self.revoked_at is None)

    def __repr__(self) -> str:      # pragma: no cover - chi de doc khi go roi
        return f"<NexusSession {self.quyen} device={self.device_id[:8]}>"


__all__ = ["DEVICE_KEY_PREFIX", "ENROLL_MAX_ATTEMPTS", "ENROLL_TTL_S",
           "NexusDevice", "NexusEnrollment", "NexusSession"]
