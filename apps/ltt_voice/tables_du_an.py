"""
tables_du_an.py — hai bảng của màn Dự án.

🗑️ **CHẠY LÔ ĐÃ GỠ 01/09/2026.** Phần dưới đây nói về hai màn dùng chung bảng;
   nay chỉ còn một. Giữ nguyên lập luận vì cột `loai` vẫn còn và vì lý do gỡ
   đáng đọc trước khi ai đó dựng lại màn ấy:

   Chạy lô tồn tại **chỉ để chạy khối lượng lớn** — và nó là màn duy nhất
   không thể nhanh lên nếu không đổi ngữ nghĩa tính tiền. Nó nộp **một job cho
   mỗi dòng**, nên một CSV 500 dòng bỏ lại đúng **3,47 lần** thông lượng mà
   `infer_batch` cho không (đo 01/09: 1,457× so với 5,059× giây tiếng trên mỗi
   giây GPU, khoảng cách lớn hơn dao động 49 lần).

   Tức nó **hứa "lô" và giao một vòng lặp**. Giữ nguyên như vậy là lựa chọn duy
   nhất chắc chắn sai; hai lựa chọn đúng là dựng lại quanh `infer_batch` (và
   chấp nhận thử-lại/tính-tiền thô hơn) hoặc gỡ.

   Đo trước khi gỡ, theo tiền lệ Q108/Q109: **0 lô, 0 dự án, 0 chủ sở hữu** —
   `voice_project` chưa có dòng nào. Mã còn trong lịch sử git.

   ⛔ Dựng lại thì **đừng chép lại bản cũ**. Bản cũ đúng ở phần *"kiểm toàn bộ
      danh sách trước khi giữ một đồng"* và sai ở phần thi hành. Phần đúng đáng
      giữ; phần sai là lý do nó không còn ở đây.

   ⚠️ Cột `loai` **giữ lại**. Nay nó chỉ mang một giá trị, nhưng bỏ nó cần một
      migration trên một bảng đang sống để đổi lấy đúng một cột `varchar(16)` —
      cái giá không đáng, và nó là chỗ móc sẵn nếu màn ấy quay lại.

🔴 VÌ SAO CHẠY LÔ DÙNG CHUNG BẢNG VỚI DỰ ÁN, KHÔNG CÓ HAI BẢNG RIÊNG.

   Nhìn thì hai màn khác hẳn nhau: Dự án là chỗ soạn, Chạy lô là một lượt chạy.
   Nhưng đem hai lược đồ đặt cạnh nhau thì chúng **trùng gần như hoàn toàn**:
   chủ sở hữu · tên · giọng mặc định · một danh sách đơn vị văn bản **có thứ
   tự**, mỗi đơn vị mang giọng riêng, trạng thái, `job_id`, khoá tệp, số giây,
   số credit.

   Hai bảng nữa nghĩa là: hai migration, hai phép tra quyền, hai `gan_ket_qua`,
   hai cửa poll trạng thái — và ngày một trong sáu thứ đó được sửa ở một bên mà
   quên bên kia là ngày chúng lệch nhau. Đó chính là thứ nguyên tắc 6 của prompt
   pack cấm: *"không copy/paste cùng một logic sang nhiều trang nếu có thể trừu
   tượng hoá hợp lý."*

   ⇒ Một cột `loai` (`du_an` | `lo`) phân biệt hai màn. Khác biệt thật nằm ở
     **hành vi**, không ở dữ liệu: Dự án sửa dần rồi đọc từng khối; Lô nhập một
     lần, kiểm hết rồi chạy hết.

🔎 ĐIỀU KIỆN TÁCH RA SAU NÀY (viết ra để nó không thành giáo điều): khi một bên
   cần **một cột mà bên kia không bao giờ dùng**, hoặc khi vòng đời lệch nhau —
   ví dụ lô tự xoá sau N ngày còn dự án thì không. Lúc đó tách là đúng, và
   `loai` cho biết chính xác phải chuyển những dòng nào.

⭐ VÌ SAO MỘT TỆP RIÊNG, KHÔNG NỐI VÀO `tables.py`.

   `tables.py` mang bốn bảng của **danh tính giọng** (`voice_profile`,
   `voice_ref`, `voice_repr`, `voice_consent`) — chúng là hợp đồng dài hạn:
   `public_id` không bao giờ đổi, consent là chứng cứ pháp lý, `voice_repr` là
   thứ giữ lời hứa "nâng engine không phá `voice_id`".

   Dự án là **một công cụ soạn thảo**. Nó có thể đổi hình dạng nhiều lần, và nó
   không mang lời hứa nào ra ngoài. Trộn hai nhóm vào một tệp là mời người sửa
   công cụ soạn thảo đi ngang qua bốn bảng không được phép lay động.

⚠️ `platform_core/registry.load_app_tables` chỉ import `apps/<slug>/tables.py`,
   nên tệp này phải được `tables.py` import lại — **một dòng, ở cuối tệp đó**.
   Thiếu dòng ấy thì server vẫn chạy (route import gián tiếp) nhưng **Alembic
   không thấy hai bảng này**, và `autogenerate` sẽ lặng lẽ đề nghị **xoá** chúng.

⛔ KHÔNG có bảng `chapter`. Ảnh tham chiếu 03 vẽ Chương → Khối, nhưng một tầng
   lồng làm đôi mọi màn hình để đổi lấy rất ít ở bản đầu. Thêm được lúc nào cũng
   được; gỡ ra thì không.

⛔ KHÔNG có bảng `block_version`. Ảnh vẽ V1/V2/V3 cho mỗi khối. Lịch sử job đã
   giữ đủ mọi lượt sinh (mỗi lượt là một `Job` có `result`), nên một bảng phiên
   bản thứ hai là một nguồn chân lý thứ hai cho cùng một sự thật — và hai nguồn
   chân lý là một chỗ để chúng lệch nhau.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String, Text

from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base

#: 🔴 KHOÁ CHÍNH: `BIGINT` trên PostgreSQL, `INTEGER` trên SQLite.
#:
#:    SQLite **chỉ** tự tăng cho cột khai đúng `INTEGER PRIMARY KEY` — một
#:    `BIGINT PRIMARY KEY` thì không, và `INSERT` không kèm `id` sẽ ném
#:    `NOT NULL constraint failed`. Production là PostgreSQL nên nó chạy ở
#:    đó và **chỉ hỏng ở máy phát triển** — tức hỏng đúng chỗ khó tin nhất,
#:    vì ai cũng cho rằng lỗi nằm ở mã mới chứ không ở kiểu cột.
#:
#: ⭐ `with_variant` là câu trả lời chính chủ. SQLAlchemy issue #2074, Michael
#:    Bayer: *"This highly unusual use case can be met right now with standard
#:    recompilation techniques."* — và `with_variant` là dạng khai báo của kỹ
#:    thuật đó, không phải một mẹo tự nghĩ.
#:
#: ⚠️ Bốn bảng ở `tables.py` (`voice_profile`, `voice_ref`, `voice_repr`,
#:    `voice_consent`) **chưa** dùng biến thể này — chúng vẫn `BigInteger`
#:    trần, nên tạo giọng không chạy trên SQLite. Đó là vùng của phiên khác;
#:    đã ghi vào bản bàn giao thay vì tự sửa.
KHOA_CHINH = BigInteger().with_variant(Integer, "sqlite")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def sinh_ma_du_an() -> str:
    """`vp_<32 hex>` — tiền tố riêng, không trùng `vc_` của giọng.

    Một id có tiền tố tự nói nó là gì trong log, và nó chặn việc vô tình truyền
    một `voice_id` vào chỗ đợi `project_id`. Cùng lối `vc_`/`upl_` đã dùng.
    """
    return "vp_" + uuid.uuid4().hex


#: Hai loại vùng chứa. Cùng bảng, khác hành vi — xem đầu tệp.
LOAI_DU_AN = "du_an"
LOAI_LO = "lo"


class VoiceProject(Base):
    """Một vùng chứa có thứ tự: Dự án (soạn dần) hoặc Lô (chạy một lượt)."""

    __tablename__ = "voice_project"
    __table_args__ = (
        Index("ix_voice_project_owner", "owner_id", "loai", "trang_thai"),
    )

    id: Mapped[int] = mapped_column(KHOA_CHINH, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, index=True,
                                           default=sinh_ma_du_an)
    #: ⛔ String(36) — `User.id` là UUID chuỗi. Xem chú thích dài ở `tables.py`:
    #:    khai `BigInteger` ở đây từng làm **mọi khách chung một chủ sở hữu**.
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    ten: Mapped[str] = mapped_column(String(200), default="")

    #: `du_an` | `lo`. Phân biệt hai màn dùng chung bảng này.
    #:
    #: ⛔ Có `index` cùng `owner_id` vì MỌI truy vấn danh sách đều lọc theo cả
    #:    hai — không có nó thì màn Dự án quét cả các lô và ngược lại.
    loai: Mapped[str] = mapped_column(String(16), default=LOAI_DU_AN, index=True)

    #: Giọng dùng cho khối nào không tự khai. Lưu **chuỗi khách chọn** dạng
    #: `m:<preset>` hoặc `v:<vc_…>` — cùng khuôn bộ chọn giọng dùng ở mọi màn,
    #: nên không phải dịch qua lại giữa hai cách biểu diễn.
    giong_mac_dinh: Mapped[str] = mapped_column(String(64), default="")

    #: `nhap` (đang soạn) -> `dang_lam` -> `xong`. Không có `deleted`: xoá một
    #: dự án đã sinh tiếng là làm mồ côi các job đã tính tiền.
    trang_thai: Mapped[str] = mapped_column(String(24), default="nhap", index=True)

    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    sua_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                              default=_now, onupdate=_now)


class VoiceBlock(Base):
    """Một khối văn bản trong dự án. Đơn vị sinh tiếng và đơn vị sửa."""

    __tablename__ = "voice_block"
    __table_args__ = (
        Index("ix_voice_block_du_an", "project_id", "thu_tu"),
    )

    id: Mapped[int] = mapped_column(KHOA_CHINH, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(KHOA_CHINH, index=True)

    #: 🔴 SỐ THỰC, không phải số nguyên — để chèn giữa hai khối **không phải
    #:    đánh số lại cả dự án**. Chèn giữa 3.0 và 4.0 thì dùng 3.5.
    #:
    #:    Đánh số lại N dòng cho mỗi lần chèn là N lượt ghi cho một thao tác
    #:    người dùng coi là tức thì, và nó là chỗ hai người sửa cùng lúc sẽ giẫm
    #:    lên nhau. Số thực đổi việc đó thành **một** lượt ghi.
    thu_tu: Mapped[float] = mapped_column(Float, default=0.0)

    text: Mapped[str] = mapped_column(Text, default="")
    #: Rỗng = theo giọng mặc định của vùng chứa. Cùng khuôn `m:`/`v:`.
    giong: Mapped[str] = mapped_column(String(64), default="")

    #: Nhãn người đọc — tên tệp đầu ra khi tải cả lô.
    #:
    #: ⭐ Chỉ Lô dùng: CSV của khách thường có cột tên riêng, và một tệp zip
    #:    chứa `1.wav`, `2.wav`… là một tệp zip vô dụng. Dự án để rỗng.
    nhan: Mapped[str] = mapped_column(String(120), default="")

    #: Câu lỗi ĐÃ DUYỆT của lượt gần nhất, nếu hỏng.
    #:
    #: ⛔ Chép từ `job_events.public_message`, KHÔNG từ `job.error` thô — chuỗi
    #:    thô có thể mang đường dẫn nội bộ. Cùng luật đã áp ở `/ket-qua/`.
    loi: Mapped[str] = mapped_column(String(500), default="")

    #: `moi` -> `dang_tao` -> `xong` | `loi`.
    #: ⭐ `can_tao_lai` là trạng thái RIÊNG, không phải `moi`: nó nghĩa là "đã có
    #:    tiếng nhưng văn bản đã đổi sau đó". Gộp vào `moi` thì mất tệp cũ khỏi
    #:    màn hình trong khi nó vẫn nghe được — và khách mất chỗ so sánh.
    trang_thai: Mapped[str] = mapped_column(String(24), default="moi", index=True)

    #: Job gần nhất đã sinh khối này. Nguồn để tra lại credit, lỗi, thời điểm.
    job_id: Mapped[str] = mapped_column(String(36), default="")
    audio_key: Mapped[str] = mapped_column(String(512), default="")
    giay: Mapped[float] = mapped_column(Float, default=0.0)
    credit: Mapped[int] = mapped_column(Integer, default=0)

    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    sua_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                              default=_now, onupdate=_now)
