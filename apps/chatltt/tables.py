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

#: Trạng thái của một khối `tool_call`. (H44 P09 bước 1)
#:
#: 🔴 **MỘT chiều, không phải ba cờ rời.** Bản trước mang `ok` + `cho_duyet` và
#:    bỏ hẳn `cho_job` — nên một bước **đang chờ job** tuần tự hoá thành
#:    `ok=True, cho_duyet=False, tom_tat=""`, tức **không phân biệt được với đã
#:    xong**. Đo bằng thí nghiệm 06/09, không phải bằng đọc mã.
#:
#: ⭐ Ba cờ rời cho 8 tổ hợp mà chỉ 4 có nghĩa; một union một chiều thì **mọi**
#:    giá trị đều có nghĩa. Cùng hình dạng `ToolCallMessagePartStatus` của
#:    `assistant-ui` (đọc đặc tả 06/09, không chạm mã — xem `11_KE_HOACH_P09_UX.md`).
#:
#: ⚠️ `ok` vẫn được ghi kèm, **chỉ để đọc ngược**: 220 hội thoại thật có thể
#:    đang mang khối cũ không có `trang_thai`.
TRANG_THAI_KHOI_TOOL = ("cho_duyet", "dang_chay", "xong", "loi")


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


#: Vòng đời TRÍCH của một tệp đã gắn vào hội thoại.
#: ⭐ Bốn trạng thái, không ba: `"loi"` phải là một trạng thái **đích** chứ không
#:    phải sự vắng mặt của `"xong"`. PDF ảnh scan là ca thường; một tệp nằm im ở
#:    `"moi"` mãi mãi không nói được cho người dùng biết vì sao nó im.
TRANG_THAI_TRICH = ("moi", "dang_trich", "xong", "loi")


class ChatlttTep(Base):
    """Một TỆP đã gắn vào một hội thoại — bảng LIÊN KẾT, không giữ byte nào.

    ## Vì sao là một bảng riêng chứ không phải `Job.params`

    `Job.params` là JSON nên **về mặt kỹ thuật** nó chứa được `conversation_id`.
    P06 §7 vẫn bác, và lý do không phải kỹ thuật: `governance.py` xếp `jobs` là
    **OPERATIONAL** — tự già đi theo hạn riêng — còn `chatltt_*` là **CONTENT**.
    Treo tri thức của khách vào một bảng tự dọn là hẹn ngày người dùng mở lại
    hội thoại cũ và thấy tệp đã biến mất khỏi một cuộc trò chuyện vẫn nguyên vẹn.

    🔴 Đây là lần **thứ ba** cùng một ca. P03 đã ghi `chatltt_run` **không thể**
       là OPERATIONAL vì đúng lý do ấy. Ghi lại ở đây vì cái bẫy không nằm ở chỗ
       khó hiểu — nó nằm ở chỗ *"bảng này chỉ chứa siêu dữ liệu"* nghe rất hợp lý.

    ## Vì sao KHÔNG có cột nào chứa nội dung

    Byte nằm ở `storage`, và vé vào là `upload_sessions` như mọi tệp khác của
    nền tảng. Cửa *"phải giữ credit mới được lưu file"* tồn tại — theo đúng lời
    `upload_sessions.py` tự viết — để **không ai biến input của job thành kho
    lưu trữ miễn phí**. Một cột nhị phân ở đây đi vòng qua đúng cái cửa ấy.
    `test_822` chốt điều này ở tầng schema, chỗ không quên được.

    ## Vì sao `unique` là CẶP chứ không phải riêng `upload_id`

    Hỏi cùng một tài liệu ở hai hội thoại là việc bình thường. Ràng buộc riêng
    `upload_id` biến việc bình thường ấy thành lỗi 500 — chặt hơn không phải là
    an toàn hơn. Ràng buộc đúng là *"một tệp không xuất hiện hai lần **trong
    cùng một** hội thoại"*, và nó phải ở tầng CSDL vì bấm hai lần / F5 giữa
    chừng là ca thường (cùng luật `ux_chatltt_approval_step`).
    """

    __tablename__ = "chatltt_tep"
    __table_args__ = (
        Index("ux_chatltt_tep_conv_upload", "conversation_id", "upload_id",
              unique=True),
        Index("ix_chatltt_tep_user", "user_id", "created_at"),
        Index("ix_chatltt_tep_trich", "trang_thai_trich"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True,
                                    default=lambda: sinh_id("tep_"))
    #: ⛔ `String(36)` — cùng bài học `apps/ltt_voice/tables.py:66-75`: khai số
    #:    ⇒ mọi khách thành chủ số 0, và triệu chứng là "ai cũng thấy tệp của
    #:    người khác" chứ không phải một lỗi kiểu.
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(40), index=True,
                                                 nullable=False)
    #: Vé upload của nền tảng (`upload_sessions.id`, `String(36)`). Byte ở đó.
    upload_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    #: Tên người dùng thấy. Chép lại để hiện danh sách mà không phải join —
    #: và vì `upload_sessions` có vòng đời riêng, không hứa sống cùng hội thoại.
    ten_tep: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    kich_thuoc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    trang_thai_trich: Mapped[str] = mapped_column(String(16), default="moi",
                                                  nullable=False)
    #: Job trích văn bản (bước 3). Rỗng cho tới khi nộp.
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    so_doan: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Vì sao trích hỏng, viết cho **người dùng** đọc, không cho log.
    ly_do_loi: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 onupdate=_now, nullable=False)


class ChatlttDoan(Base):
    """Một ĐOẠN văn bản trích từ một tệp — đơn vị của truy hồi và của trích dẫn.

    ## Vì sao bảng NÀY giữ chữ, còn `chatltt_tep` thì không

    Trông như mâu thuẫn, nhưng hai bảng trả lời hai câu khác nhau:

    * `chatltt_tep` nói **tệp nào thuộc hội thoại nào**. Byte gốc nằm ở
      `storage`, và giữ chúng ở CSDL là dựng một kho lưu trữ thứ hai đi vòng
      qua cửa credit của `upload_sessions`.
    * `chatltt_doan` giữ **chữ đã trích** — một biểu diễn *dẫn xuất* và *có
      trần*. Chỉ số FTS phải chạy trên chính chữ ấy; đẩy nó ra ngoài CSDL rồi
      lại kéo về mỗi lần tìm là làm chậm đúng thao tác nóng nhất.

    ⇒ Bất biến ngắn gọn: **byte gốc ở ngoài, chữ dẫn xuất ở trong.**

    ## `trang` là cột của TRÍCH DẪN, không phải của gỡ lỗi

    Bước 5 của P06 đòi mỗi câu trả lời trỏ được về `(tep_id, doan_id, trang)`.
    Không có `trang` từ lúc trích thì sau này không dựng lại được — số trang chỉ
    tồn tại trong lúc đọc tệp, không suy ra được từ chuỗi chữ.

    ⭐ `trang = 0` nghĩa là **không biết** (định dạng không có khái niệm trang,
       ví dụ `.txt`), không phải "trang đầu". Đó là lý do nó bắt đầu từ 1.

    ## Vì sao có `bam` (hash) của nội dung đoạn

    Trích lại cùng một tệp phải cho cùng kết quả. `bam` làm phép "đã trích rồi,
    đừng thu tiền lần nữa" kiểm được ở tầng dữ liệu chứ không phải bằng niềm tin
    vào một cờ trạng thái.
    """

    __tablename__ = "chatltt_doan"
    __table_args__ = (
        Index("ux_chatltt_doan_tep_thu_tu", "tep_id", "thu_tu", unique=True),
        Index("ix_chatltt_doan_conv", "conversation_id"),
        Index("ix_chatltt_doan_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True,
                                    default=lambda: sinh_id("dn_"))
    #: ⛔ `String(36)` — cùng bài học `apps/ltt_voice/tables.py:66-75`.
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    #: Chép xuống để lọc theo hội thoại mà không phải join — và vì cửa quyền
    #: không được vay bất biến của bảng bên cạnh (cùng luật `kho_tep`).
    conversation_id: Mapped[str] = mapped_column(String(40), index=True,
                                                 nullable=False)
    tep_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    thu_tu: Mapped[int] = mapped_column(Integer, nullable=False)
    #: 1-based. `0` = định dạng không có khái niệm trang.
    trang: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    noi_dung: Mapped[str] = mapped_column(Text, default="", nullable=False)
    so_ky_tu: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bam: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 nullable=False)


#: Phạm vi **ÁP DỤNG** của một mẩu ghi nhớ. (H44 B4)
#:
#: ⛔ Đây KHÔNG phải phân loại nội dung. mem0 phân theo nội dung (sở thích ·
#:    chi tiết cá nhân · kế hoạch · …, bảy nhóm — đo `mem0/configs/prompts.py`
#:    ngày 06/09); bảy nhóm ấy là **nhãn để hiện**, và nhãn thì thuộc `meta`.
#:    Cột trong bảng chỉ dành cho thứ có **ràng buộc**, và thứ có ràng buộc ở
#:    đây là *"mẩu này được phép ảnh hưởng tới lượt nào"* — tức một câu hỏi về
#:    **quyền**.
#:
#: ⚠️ `du_an` khai sẵn nhưng **chưa dùng**: B5 mới là chỗ `project_id` ra đời.
#:    Khai trước vì cùng lý do `chieu_tool` giữ hai lớp rỗng — ngày đầu tiên có
#:    một mẩu thuộc project, chỗ để nó rơi vào phải đã tồn tại và đã fail-closed.
PHAM_VI = ("nguoi_dung", "du_an", "hoi_thoai")

#: Ai đã viết mẩu này. Mượn `type: Literal['user','context']` của Open WebUI
#: (đọc hành vi, **không** chạm mã — giấy phép `NOASSERTION`).
#:
#: ⭐ Trục này độc lập hoàn toàn với `PHAM_VI`, và gộp chúng là lỗi thiết kế đầu
#:    tiên ai cũng mắc: *"ai viết"* quyết định **quyền sửa** (người sửa được mọi
#:    mẩu; model chỉ được thay mẩu do chính model ghi), còn *"áp cho ai"* quyết
#:    định **lượt nào bị ảnh hưởng**. Một cột không trả lời được hai câu.
NGUON = ("nguoi", "model")

#: Trần ký tự cho MỘT mẩu. Ép ở tầng CSDL (`String`) chứ không chỉ ở service:
#: một mẩu ghi nhớ đi vào **mọi lượt sau đó**, nên một mẩu dài là một khoản
#: thuế token vĩnh viễn chứ không phải một hàng to.
TRAN_KY_TU_MOT_BAN = 500


class ChatlttGhiNho(Base):
    """Một mẩu GHI NHỚ — thứ được tiêm vào ngữ cảnh của mọi lượt trong phạm vi.

    ## Vì sao KHÔNG có cột embedding, và vì sao đó không phải một thoả hiệp

    `pgvector` không có trên PostgreSQL 17.10 này (đo ở P06). Nhưng lập luận
    đúng không phải *"thiếu nên đành chịu"*: B4 §D5 chốt trần **4.000 ký tự cho
    cả khối ghi nhớ mỗi lượt**, và cả khối ấy được tiêm **trọn vẹn**. Không có
    gì để *truy hồi* — truy hồi chỉ có nghĩa khi kho lớn hơn ngữ cảnh.

    ⭐ Tức cái trần làm kho vector **thành thừa**, chứ không phải kho vector
       thiếu làm cái trần **thành thoả hiệp**. Hai câu ấy dẫn tới hai kiến trúc
       khác nhau, và câu sau là câu khiến ai đó ba tháng nữa đi cài Qdrant lên
       máy đang chạy production.

    ## 🔴 Vì sao `muc_tieu_id` là `""` chứ KHÔNG phải `NULL`

    Ràng buộc chống trùng là bộ bốn `(user_id, pham_vi, muc_tieu_id, bam)`. Với
    `pham_vi = "nguoi_dung"` thì không có mục tiêu, và phản xạ đầu tiên là để
    `NULL`. Nhưng trong SQL **`NULL` không bằng `NULL`**, nên một `UNIQUE` chứa
    cột `NULL` **không chặn trùng** — hai mẩu y hệt nhau vẫn vào được, và triệu
    chứng là kho ghi nhớ tự nhân đôi chứ không phải một lỗi ràng buộc.

    ⛔ PostgreSQL 15+ có `NULLS NOT DISTINCT`, nhưng SQLite (đường chạy test)
       **không có**. Một bất biến chỉ đúng ở một trong hai nền tảng thì phép
       kiểm sẽ xanh ở nơi nó không quan trọng — cùng hình dạng với `_tim_chuoi_con`
       của P06, và ở đó ta đã chọn *"đừng giả vờ là đường sản xuất"*.
       ⇒ Chuỗi rỗng: một giá trị **thật**, so sánh được ở cả hai nơi.

    ## Vì sao unique trên `bam` chứ không trên `noi_dung`

    Cùng lý do `chatltt_doan.bam` tồn tại, cộng một lý do vật lý: chỉ số btree
    của PostgreSQL có trần ~2.704 byte/hàng, mà 500 ký tự tiếng Việt ≈ 1.500
    byte — cộng ba cột kia thì đã sát trần. Một ràng buộc chỉ vỡ với **hàng
    dài** là một ràng buộc vỡ đúng lúc người dùng ghi mẩu quan trọng nhất.
    """

    __tablename__ = "chatltt_ghi_nho"
    __table_args__ = (
        Index("ux_chatltt_ghi_nho_khoa", "user_id", "pham_vi", "muc_tieu_id",
              "bam", unique=True),
        #: Truy vấn TIÊM: "mọi mẩu áp cho lượt này". Chạy **mỗi lượt**, nên nó
        #: là truy vấn nóng nhất của cả tính năng.
        Index("ix_chatltt_ghi_nho_tiem", "user_id", "pham_vi", "muc_tieu_id"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True,
                                    default=lambda: sinh_id("gn_"))
    #: ⛔ `String(36)` — cùng bài học `apps/ltt_voice/tables.py:66-75`.
    #:
    #: ⚠️ **Không** `index=True` ở đây, khác `chatltt_tep`/`chatltt_doan`. Chỉ số
    #:    tổ hợp `ix_chatltt_ghi_nho_tiem` bắt đầu bằng chính `user_id`, nên một
    #:    chỉ số đơn nữa là **bản sao chết**: nó tốn ghi ở mọi lần chèn và không
    #:    phục vụ truy vấn nào mà chỉ số kia không phục vụ.
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    pham_vi: Mapped[str] = mapped_column(String(16), nullable=False)
    #: `conv_id` khi `pham_vi="hoi_thoai"`, `project_id` khi `"du_an"`,
    #: **chuỗi rỗng** khi `"nguoi_dung"` — xem docstring, đừng đổi thành `NULL`.
    muc_tieu_id: Mapped[str] = mapped_column(String(40), default="",
                                             nullable=False)
    nguon: Mapped[str] = mapped_column(String(8), nullable=False)
    noi_dung: Mapped[str] = mapped_column(String(TRAN_KY_TU_MOT_BAN),
                                          nullable=False)
    #: sha256 của nội dung đã chuẩn hoá. Khoá chống trùng, không phải kiểm toàn vẹn.
    bam: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    #: Nhãn hiển thị, id lượt đã sinh ra mẩu này. ⭐ *"vì sao nó nhớ"* là một
    #: phần của lời hứa B4, và câu trả lời phải lưu được ở đâu đó.
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 onupdate=_now, nullable=False)

