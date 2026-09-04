"""Bảng CSDL riêng của ChatLTT. Tiền tố `chatltt_` theo `MANIFEST.table_prefix`. (H43 Phase 07)

## Vì sao bảng RIÊNG, không sửa `chat_conversations`/`chat_messages`

Hai bảng đó (`platform_core/models.py:796-834`) là của Chat AI Studio: tuyến
tính, gắn `codex_thread_id`, nằm trong lõi nền tảng và đang phục vụ khách. Hội
thoại của ChatLTT là **một cây** (sửa-gửi-lại = anh em mới, tạo-lại = anh em
mới, nhánh chọn được) và nội dung là **khối typed** (text/reasoning/image/audio/
file/status). Ép hai hình dạng vào một bảng là hai app cùng đổi schema của nhau.
Kế hoạch H43 §4 D4 chấm phương án C; Phase 07 xác nhận.

## Ba bảng, và ranh giới giữa chúng

* `chatltt_conversation` — **hộp**: chủ, tiêu đề, alias model mặc định,
  `current_leaf_id` (nhánh đang xem — lưu ở CSDL, KHÔNG ở trình duyệt: reload
  giữa nhánh cũ phải quay lại đúng nhánh đó, AC-07 của Phase 01), lưu trữ/xoá mềm.
* `chatltt_message` — **nút của cây**: `parent_id` (NULL = gốc), `role`,
  `blocks` JSON, `status`. Cây dựng lại từ danh sách phẳng bằng `parent_id`;
  không có cột `children`, không có `siblingIdx` (LibreChat cũng vậy, và 5 test
  `convoStructure.spec.ts` của họ là đặc tả cho `test_619`).
* `chatltt_execution` — **một lượt thi hành** (stream text hoặc job ảnh/tiếng)
  gắn vào một message assistant: `partial_text` ghi theo nhịp để **reload dựng
  lại được sự thật từ CSDL** (D6), `request_id`/`job_id` để đối chiếu sổ tiền,
  `status` một enum duy nhất (LibreChat có hai quy ước mâu thuẫn — báo cáo
  Phase 01 §5, ChatLTT chọn một).

## Hai bất biến ở tầng GHI (không phải tầng đọc)

1. `created_at(con) > created_at(cha)` — `hoi_thoai.them_thong_diep` ép; đồng
   hồ hệ thống lùi thì vẫn đúng. LibreChat phải vá muộn ở `fork.js:46-56` vì
   họ không ép lúc ghi.
2. Mọi truy vấn có `user_id` — không có hàm nào đọc theo `id` trần. IDOR chặn ở
   tầng service, route không có cách nào "quên".

⛔ `owner`/`user_id` là `String(36)` (UUID chuỗi của `User.id`) — bài học
   `apps/ltt_voice/tables.py:66-75` (khai số ⇒ mọi khách thành chủ số 0).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def sinh_id(tien_to: str) -> str:
    """`cv_…` / `msg_…` / `ex_…` — id có tiền tố tự nói nó là gì trong log và lỗi."""
    return tien_to + uuid.uuid4().hex


#: Vai trong hội thoại.
VAI = ("user", "assistant", "system")
#: Trạng thái của một message. MỘT enum cho cả message lẫn execution.
TRANG_THAI = ("draft", "streaming", "queued", "done", "failed", "cancelled")
#: Loại khối nội dung mà bộ hiển thị biết vẽ (kế hoạch §5.2).
LOAI_KHOI = ("text", "reasoning", "image", "audio", "file", "status", "error")


class ChatlttConversation(Base):
    __tablename__ = "chatltt_conversation"
    __table_args__ = (
        Index("ix_chatltt_conv_user_updated", "user_id", "deleted_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True,
                                    default=lambda: sinh_id("cv_"))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    model_alias: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    #: Lá của nhánh đang xem. NULL khi chưa có message nào.
    current_leaf_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Xoá MỀM. Dọn thật theo retention (Q75) là việc của vòng bảo trì, không của route.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 onupdate=_now, nullable=False)


class ChatlttMessage(Base):
    __tablename__ = "chatltt_message"
    __table_args__ = (
        Index("ix_chatltt_msg_conv_parent", "conversation_id", "parent_id"),
        Index("ix_chatltt_msg_conv_created", "conversation_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True,
                                    default=lambda: sinh_id("msg_"))
    conversation_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    #: NULL = gốc. Anh em = cùng `parent_id`.
    parent_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    #: `[{"type": "text", "text": ...}, {"type": "image", "key": ..., ...}, ...]`
    blocks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="done", nullable=False)
    model_alias: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    execution_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 onupdate=_now, nullable=False)


class ChatlttExecution(Base):
    __tablename__ = "chatltt_execution"
    __table_args__ = (
        Index("ix_chatltt_exec_conv_status", "conversation_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True,
                                    default=lambda: sinh_id("ex_"))
    message_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    #: "stream" (text) | "job" (ảnh/tiếng).
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Mã lượt của sổ tiền (`thanh_toan.ma_luot`) — đối chiếu credit khi cần.
    request_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="streaming", nullable=False)
    partial_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reasoning_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    finish_reason: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    usage: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    credit_giu: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_thu: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_hoan: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    error_text: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    #: Số sự kiện đã áp — client nối lại hỏi "sau seq nào".
    seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 onupdate=_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
