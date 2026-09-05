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
# ⚠️ `tool_call` thêm ở H44 P05. V3 GHI khối này (`luot_v3._them_khoi`), nên hợp
#    đồng phải khai nó — nếu không thì `hoi_thoai.cap_nhat_khoi()` **từ chối**
#    chính tin nhắn mà V3 vừa tạo, và lỗi ấy chỉ nổ ở luồng sửa/tạo-lại.
#
# ⛔ Điều này KHÔNG mâu thuẫn với A5 ("bộ hiển thị bỏ qua khối lạ"): A5 nói về
#    loại **chưa ai định nghĩa**, còn đây là loại ta CHỦ ĐỘNG sinh ra. Một loại
#    mình tự ghi mà không khai là một loại sẽ bị chính mình từ chối.
LOAI_KHOI = ("text", "reasoning", "image", "audio", "file", "status", "error",
             "tool_call")


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

    # ── H44 V3: liên kết lên run/step. Cả hai NULL với mọi hàng V1. ─────────
    run_id: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    step_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


# ══════════════════════════════════════════════════════════════════════════
# H44 V3 — ba bảng của điều phối tool. CHỈ THÊM, không sửa ba bảng trên.
#
# `docs/CHATLTT_V3/02_HOP_DONG.md` §2. `chatltt_execution` **vẫn là** một lần
# gọi model/job, và ba cột tiền vô hướng của nó **vẫn đúng** cho việc đó. `run`
# là khái niệm MỚI ở trên, không phải đổi nghĩa cái cũ.
#
# ⛔ `chatltt_message.blocks` KHÔNG đổi hình dạng. Khối mới (`tool_call`,
#    `tool_result`, `approval`) là **phần tử mới trong mảng cũ** — đó là điều
#    kiện để một bản V1 đọc dữ liệu V3 vẫn vẽ được phần nó hiểu.
# ══════════════════════════════════════════════════════════════════════════

#: 12 trạng thái của một run (`services/dieu_phoi.py`).
TRANG_THAI_RUN = ("CREATED", "MODEL_RUNNING", "TOOL_REQUESTED", "AWAITING_APPROVAL",
                  "TOOL_RUNNING", "WAITING_BACKGROUND", "TOOL_RESULT_READY",
                  "MODEL_RESUMING", "WAITING_SLOT", "COMPLETED", "FAILED", "CANCELLED")
LY_DO_KET = ("xong", "tran_vong", "tran_tool", "tran_trung", "huy", "loi")
QUYET_DINH_DUYET = ("cho", "duyet", "tu_choi", "het_han")


class ChatlttRun(Base):
    """Một LƯỢT của người dùng: N vòng model + M lời gọi tool."""

    __tablename__ = "chatltt_run"
    __table_args__ = (
        Index("ix_chatltt_run_conv", "conversation_id", "created_at"),
        Index("ix_chatltt_run_user_tt", "user_id", "trang_thai"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True,
                                    default=lambda: sinh_id("run_"))
    conversation_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    #: ⛔ `String(36)` — bài học `apps/ltt_voice/tables.py:66-75`: khai số ⇒ mọi
    #:    khách thành chủ số 0.
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    message_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    trang_thai: Mapped[str] = mapped_column(String(24), default="CREATED", nullable=False)
    so_vong_model: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    so_loi_goi_tool: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    #: 🔴 BA CỘT DẪN XUẤT, KHÔNG PHẢI BÚT TOÁN. Cộng từ `chatltt_execution` con,
    #:    mỗi cái vẫn ứng đúng một `request_id` trong `credit_entries`. Đối soát
    #:    vẫn là: một `request_id` ↔ một dòng sổ. Bảng này chỉ trả lời câu "lượt
    #:    này tốn bao nhiêu" mà hôm nay không ai trả lời được.
    credit_giu_tong: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_thu_tong: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_hoan_tong: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Chi phí **chính xác** tích luỹ (milli-credit) — đầu vào của C2-trong-run
    #: (R2b). Giữ ở đây vì `credit_entries` chỉ lưu credit nguyên đã làm tròn,
    #: và `test_803` chứng minh phép cộng dồn phải neo vào số **dự định**.
    mcredit_tich_luy: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    ly_do_ket: Mapped[str] = mapped_column(String(24), default="", nullable=False)
    #: Rỗng khi không giữ lease xuyên run — mặc định, vì ADR-R1 chọn phương án C.
    lease_id: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 onupdate=_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                         nullable=True)


class ChatlttStep(Base):
    """Một BƯỚC trong run: `model` hoặc `tool`."""

    __tablename__ = "chatltt_step"
    __table_args__ = (
        Index("ux_chatltt_step_thu_tu", "run_id", "thu_tu", unique=True),
        Index("ix_chatltt_step_bam", "run_id", "bam_trung"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True,
                                    default=lambda: sinh_id("st_"))
    run_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    thu_tu: Mapped[int] = mapped_column(Integer, nullable=False)
    loai: Mapped[str] = mapped_column(String(16), nullable=False)
    execution_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    tool_call_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    doi_so: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    #: ⭐ Chuỗi đối số **trước khi gộp**. `test_800` đã chứng minh runtime KHÔNG
    #:    gộp mảnh; ngày nào đó `gop_manh` gộp sai, thứ cần đọc là chuỗi này —
    #:    và lúc đó nó phải đã được lưu, vì không dựng lại được từ kết quả.
    doi_so_tho: Mapped[str] = mapped_column(Text, default="", nullable=False)

    ket_qua: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    bam_trung: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 nullable=False)


class ChatlttApproval(Base):
    """Một QUYẾT ĐỊNH duyệt. Bền qua F5, đóng tab, tiến trình khác, restart."""

    __tablename__ = "chatltt_approval"
    __table_args__ = (
        #: 🔴 `unique=True` LÀ thứ làm "duyệt hai lần" KHÔNG THỂ xảy ra — ở tầng
        #:    CSDL, không phải ở một `if` trong route. Route có thể quên; ràng
        #:    buộc không quên. Cùng luật `job_submit.dedupe_key`.
        Index("ux_chatltt_approval_step", "step_id", unique=True),
        Index("ux_chatltt_approval_idem", "idempotency_key", unique=True),
        Index("ix_chatltt_approval_user", "user_id", "quyet_dinh"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True,
                                    default=lambda: sinh_id("ap_"))
    step_id: Mapped[str] = mapped_column(String(40), nullable=False)
    run_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Đối số người dùng **nhìn thấy** khi bấm — không phải đối số lúc chạy.
    doi_so: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    policy_class: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Số credit **đã hiện ra**. Lệch với giá tính lại ⇒ từ chối và báo lại —
    #: cùng luật `tao_media.tao()` đã có: *"gia da doi: bao X, tinh lai Y"*.
    bao_gia_credit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    phien_ban_gia: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    quyet_dinh: Mapped[str] = mapped_column(String(16), default="cho", nullable=False)
    doi_so_da_sua: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quyet_boi: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 nullable=False)
    quyet_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                       nullable=True)
