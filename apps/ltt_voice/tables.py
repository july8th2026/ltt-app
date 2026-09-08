"""Bảng CSDL riêng của LTT VOICE. Tiền tố `voice_` theo `MANIFEST.table_prefix`.

Bốn bảng, và ranh giới giữa chúng **không phải chuyện gọn gàng** — nó là thứ giữ
lời hứa dài hạn của sản phẩm:

* `voice_profile` — **danh tính công khai**. `public_id` dạng `vc_<uuid4hex>` là
  thứ duy nhất khách và API nhìn thấy. Nó không bao giờ đổi.
* `voice_ref`     — **tệp nguồn bất biến** của khách, kèm hash và consent. Giữ
  lại để **dựng lại được** biểu diễn khi lên engine mới.
* `voice_repr`    — **biểu diễn engine**: `speaker_emb` + `ref_codes` của một
  phiên bản model cụ thể. Nhiều dòng cho một profile; đúng một dòng `active`.
* `voice_consent` — cam kết sở hữu, lưu thành **dữ liệu** chứ không phải ghi chú.

## Vì sao `voice_repr` phải tách khỏi `voice_profile`

Đây là toàn bộ lý do sản phẩm này chịu được việc đổi engine. Nếu `speaker_emb`
nằm ngay trong `voice_profile` thì ngày nâng v3 Turbo lên v3 full là ngày mọi
`voice_id` phải đổi — tức mọi tích hợp của khách gãy, vì một lý do hoàn toàn nội
bộ. Tách ra thì nâng model = **thêm một dòng** và đổi cờ `active`.

`docs/LTT_VOICE/00_PHUONG_AN_VA_LO_TRINH.md` gọi đây là QĐ-3, và
`specs/VOICE_API_NORTH_STAR.md` của prompt pack gọi nó là "stability rule".

## Vì sao consent là một BẢNG, không phải một cột `bool`

Một `bool` trả lời được "có đồng ý không" nhưng không trả lời được "đồng ý với
bản điều khoản nào, lúc nào, từ IP nào" — và đó mới là những câu hỏi được hỏi khi
có tranh chấp. Tiền lệ: `apps/vps/dieu_khoan.py` + `test_298` đối chiếu từng con
số trong điều khoản với hằng số thật.

## Vì sao ràng buộc DUY NHẤT nằm ở tầng CSDL

Hai request cùng tạo một giọng tên giống nhau là chuyện thường. Cách đúng không
phải "đọc xem có chưa rồi ghi" — giữa hai bước đó có một khoảng trống. Cách đúng
là **cứ INSERT và coi `IntegrityError` là đường chạy bình thường**. Khuôn này đã
chạy trong production ở `platform_core/gpu_lease.py` và `apps/vps/tables.py`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (BigInteger, Boolean, DateTime, Float, Index, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base

#: 🔴 `BigInteger` THUẦN KHÔNG TỰ TĂNG TRÊN SQLITE.
#:
#:    Production chạy PostgreSQL nên nó đúng ở đó, và sai **chỉ trong test** —
#:    tức sai ở đúng chỗ không ai nhìn thấy cho tới khi có người viết một phép
#:    kiểm chạm bảng này trên SQLite, rồi nhận `NOT NULL constraint failed:
#:    voice_profile.id` và tưởng mình viết sai fixture.
#:
#: ⭐ `tables_du_an.py` đã giải đúng bài này từ trước bằng `with_variant`; đây
#:    chỉ là mang lời giải ấy sang tệp anh em. Hai tệp cùng dự án mà một tệp
#:    test được còn tệp kia thì không là một chênh lệch không có lý do nào.
KHOA_CHINH = BigInteger().with_variant(Integer, "sqlite")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def sinh_public_id() -> str:
    """`vc_<32 hex>`. Tiền tố có chủ ý — cùng lối `upl_` của Public API.

    Một id có tiền tố tự nói nó là gì trong log và trong báo lỗi, và nó chặn
    việc vô tình truyền nhầm một id khác vào chỗ này.
    """
    return "vc_" + uuid.uuid4().hex


class VoiceProfile(Base):
    """Danh tính công khai của một giọng. **Không chứa gì của engine.**"""

    __tablename__ = "voice_profile"
    __table_args__ = (
        # Tên hiển thị duy nhất TRONG PHẠM VI MỘT CHỦ. Hai khách được phép đặt
        # trùng tên; một khách thì không, vì họ sẽ không phân biệt được.
        UniqueConstraint("owner_id", "ten_hien_thi", name="uq_voice_owner_ten"),
        Index("ix_voice_profile_owner", "owner_id", "trang_thai"),
    )

    id: Mapped[int] = mapped_column(KHOA_CHINH, primary_key=True,
                                    autoincrement=True)
    #: Thứ DUY NHẤT khách và API nhìn thấy. Không bao giờ đổi, kể cả khi đổi engine.
    public_id: Mapped[str] = mapped_column(String(40), unique=True, index=True,
                                           default=sinh_public_id)
    #: ⛔ String(36), KHÔNG phải số. `User.id` của nền tảng là **UUID chuỗi**
    #:    (`platform_core/models.py:73` — cố ý, để id không đoán được và không
    #:    lộ quy mô). App này ban đầu khai `BigInteger`, và hệ quả không phải
    #:    một lỗi kiểu ồn ào mà là một sự im lặng: chỗ đọc id ép `int(...)`,
    #:    ném, bị nuốt, trả **0** — nên MỌI khách đều thành chủ sở hữu số 0 và
    #:    sẽ nhìn thấy giọng của nhau. Đổi 31/08/2026 khi cả bốn bảng còn rỗng.
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    ten_hien_thi: Mapped[str] = mapped_column(String(120))
    ngon_ngu: Mapped[str] = mapped_column(String(16), default="vi")

    #: 🔴 GIỚI TÍNH CỦA GIỌNG — `"nam"` · `"nu"` · `""` (KHÔNG RÕ).
    #:
    #:    Cột này tồn tại vì **hai** thứ khác nhau cùng cần nó, và trước
    #:    07/09/2026 không thứ nào làm được:
    #:
    #:      ① `lui_giong.py` — khi một giọng hỏng, đường lùi phải giữ NGUYÊN
    #:         giới. Không biết giới thì không lùi được, và cách duy nhất còn
    #:         lại là lùi bừa. Hệ `D:\Viral` đã đi đúng con đường đó và khách
    #:         báo lỗi ngày 26/08/2026: *"giọng nam bị biến thành giọng nữ"* —
    #:         backend của họ không có bảng giới nên mọi đường lùi rơi về giọng
    #:         mặc định, vốn là nữ.
    #:      ② bộ lọc ở `_voice_chon.html` — giới là câu hỏi đầu tiên người chọn
    #:         giọng hỏi, và 20 giọng mẫu đã trả lời được từ lâu
    #:         (`giong_mau_engine.json`). Giọng nhân bản thì không, nên một bộ
    #:         lọc giới sẽ **làm biến mất** đúng những giọng của chính khách.
    #:
    #: ⛔ MẶC ĐỊNH `""` = KHÔNG RÕ, và đó là một giá trị THẬT chứ không phải một
    #:    chỗ trống chờ điền. Mọi dòng có trước migration này đều không rõ giới,
    #:    và **đoán hộ là sai**: đoán bằng F0 nghe thì hợp lý, nhưng chính
    #:    `toc_do.py` đã ghi lại một ca bộ dò cao độ nhầm quãng tám trên một
    #:    clip giọng nữ (báo 105,6 Hz). Một cột "giới" sai còn tệ hơn một cột
    #:    trống, vì nó **được tin**.
    #:
    #: ⇒ Không rõ thì `lui_giong` TỪ CHỐI lùi, và bộ lọc LUÔN HIỆN giọng đó.
    #:   Hai hành vi ấy đều là "không biết thì đừng làm gì hộ người ta".
    gioi: Mapped[str] = mapped_column(String(8), default="", nullable=False)

    ghi_chu: Mapped[str] = mapped_column(Text, default="")

    #: `dang_ghi_danh` -> `active` -> `disabled` | `revoked`.
    #: ⛔ KHÔNG có `deleted`: xoá một profile là làm mồ côi lịch sử sinh tiếng đã
    #:    tính tiền. Vô hiệu hoá thì giữ được cả hai.
    trang_thai: Mapped[str] = mapped_column(String(24), default="dang_ghi_danh",
                                            index=True)

    #: 🔴 GIỌNG NÀY CÓ PHẢI KHO DÙNG CHUNG CỦA NỀN TẢNG KHÔNG.
    #:
    #:    Trước 01/09/2026 hệ thống có đúng hai loại giọng, và **không có gì ở
    #:    giữa**:
    #:      · "Giọng mẫu"     — preset dựng sẵn của engine, ai cũng dùng được,
    #:                          nhưng ta không tạo thêm được cái nào;
    #:      · "Giọng của tôi" — nhân bản, và `giai_giong` kiểm chủ sở hữu ở
    #:                          **một chỗ duy nhất**, nên nó không thể dùng chung.
    #:
    #:    Nghĩa là một giọng nhân bản hay tới đâu cũng chỉ phục vụ được đúng
    #:    một tài khoản. Cột này mở ra loại thứ ba: giọng **nền tảng sở hữu**,
    #:    mọi khách đọc được, không khách nào sửa hay tắt được.
    #:
    #: ⛔ MẶC ĐỊNH `False`, và điều đó là bắt buộc chứ không phải cẩn thận.
    #:    Một giọng nhân bản là dữ liệu sinh trắc của một con người. Mặc định
    #:    `True` — hay một migration đặt `True` cho các dòng cũ — sẽ **công khai
    #:    giọng của khách** cho mọi tài khoản khác, và đó là loại lỗi không lấy
    #:    lại được bằng một bản vá.
    #:
    #: ⚠️ Bật cột này KHÔNG bỏ qua `VoiceConsent`. Một giọng dùng chung vẫn phải
    #:    có bút toán cam kết quyền; nó chỉ đổi **ai đọc được**, không đổi **ai
    #:    chịu trách nhiệm**.
    dung_chung: Mapped[bool] = mapped_column(Boolean, default=False,
                                             nullable=False, index=True)

    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    sua_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                              default=_now, onupdate=_now)


class VoiceRef(Base):
    """Tệp nguồn bất biến. Giữ để DỰNG LẠI biểu diễn cho engine tương lai."""

    __tablename__ = "voice_ref"
    __table_args__ = (
        # Cùng một tệp gửi lại hai lần cho cùng một giọng là **một** bản ghi.
        # Đây là thứ làm cho job ghi danh idempotent được mà không cần khoá riêng.
        UniqueConstraint("profile_id", "sha256", name="uq_voice_ref_hash"),
    )

    id: Mapped[int] = mapped_column(KHOA_CHINH, primary_key=True,
                                    autoincrement=True)
    profile_id: Mapped[int] = mapped_column(BigInteger, index=True)
    #: Khoá trong `platform_core.storage`. Bản GỐC, không phải bản đã xử lý.
    storage_key: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    mime: Mapped[str] = mapped_column(String(64), default="")
    so_byte: Mapped[int] = mapped_column(BigInteger, default=0)
    giay: Mapped[float] = mapped_column(Float, default=0.0)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class VoiceRepr(Base):
    """Biểu diễn engine. NHIỀU dòng cho một profile; đúng MỘT dòng `active`."""

    __tablename__ = "voice_repr"
    __table_args__ = (
        Index("ix_voice_repr_profile", "profile_id", "trang_thai"),
    )

    id: Mapped[int] = mapped_column(KHOA_CHINH, primary_key=True,
                                    autoincrement=True)
    profile_id: Mapped[int] = mapped_column(BigInteger, index=True)
    ref_id: Mapped[int] = mapped_column(BigInteger, index=True)

    #: `vieneu` hôm nay. Cột này tồn tại để ngày mai có engine thứ hai thì **dữ
    #: liệu** phân biệt được, chứ không phải mã phải đoán.
    engine: Mapped[str] = mapped_column(String(32), default="vieneu")
    model_repo: Mapped[str] = mapped_column(String(160), default="")
    #: SHA của revision HF. Ghim thật, không ghi "main" — v3 full sắp ra.
    model_revision: Mapped[str] = mapped_column(String(64), default="")
    sdk_version: Mapped[str] = mapped_column(String(32), default="")

    #: Khoá `.npz` chứa `speaker_emb` + `codes` trong storage.
    #: ⛔ KHÔNG BAO GIỜ ra ngoài. Khách không cần biết nó tồn tại (VOICE_API_NORTH_STAR).
    storage_key: Mapped[str] = mapped_column(String(512), default="")
    #: Vân tay của chính biểu diễn, để phát hiện dựng lại ra kết quả khác.
    fingerprint: Mapped[str] = mapped_column(String(64), default="")

    trang_thai: Mapped[str] = mapped_column(String(24), default="dang_dung",
                                            index=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class VoiceConsent(Base):
    """Cam kết sở hữu giọng. Dữ liệu, không phải ghi chú."""

    __tablename__ = "voice_consent"

    id: Mapped[int] = mapped_column(KHOA_CHINH, primary_key=True,
                                    autoincrement=True)
    profile_id: Mapped[int] = mapped_column(BigInteger, index=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)

    #: Phiên bản bản điều khoản đã hiện ra màn hình lúc bấm. Không có nó thì
    #: không trả lời được "họ đồng ý với cái gì".
    phien_ban_dieu_khoan: Mapped[str] = mapped_column(String(64))
    #: Hash tệp nguồn tại thời điểm cam kết — cột nối consent với đúng clip đó.
    ref_sha256: Mapped[str] = mapped_column(String(64), default="")
    #: `tu_thu` (giọng của chính mình) | `duoc_uy_quyen` (có giấy uỷ quyền).
    loai: Mapped[str] = mapped_column(String(32), default="tu_thu")
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    dong_y_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=_now)



class VoiceTuDien(Base):
    """Từ điển phát âm RIÊNG của một khách.

    ## Vì sao nó là một bảng, không phải một trường JSON

    Ảnh tham chiếu 01 vẽ mục ⑤ `PRONUNCIATION` với nút `Dictionary`. Và điều
    đáng nói hơn: **chuỗi tham số cho nó đã được nối sẵn từ lâu** —
    `features.chuan_bi_van_ban(tu_dien_rieng=...)` → `text_pipeline.chuan_hoa`
    → `tu_dien.ap_dung(them=...)`. Cả ba tầng nhận nó, và **không ai truyền**.

    ⭐ `tu_dien.py` đã ghi rõ ranh giới từ trước: *"Đây là bảng CHUNG cho mọi
       khách. Từ điển riêng của một người (tên công ty, tên nhân vật) đi qua
       tham số `them=` — nó không được lẫn vào đây."* Bảng này là đầu kia của
       câu ấy.

    ## Vì sao khách CẦN nó

    Upstream #168: engine đọc `ch` thành `tr` ở một số từ. Với từ phổ thông thì
    `BANG_CHUNG` lo được. Nhưng **tên riêng** — tên công ty, tên nhân vật trong
    truyện, tên sản phẩm — thì không ai đoán trước được, và chúng lặp lại trong
    **mọi** kịch bản của chính khách đó. Không có chỗ sửa thì họ phải gõ sai
    chính tả trong kịch bản để ép engine đọc đúng.

    ⛔ KHÔNG dùng để đổi giọng hay chèn lệnh. Nó chỉ là phép thay chuỗi theo
       BIÊN TỪ, y hệt `tu_dien.BANG_CHUNG`, chạy trước mọi phép chuẩn hoá khác.
    """

    __tablename__ = "voice_tu_dien"
    __table_args__ = (
        # Một khách không thể có hai mục cho cùng một từ — nếu không thì phép
        # thay phụ thuộc thứ tự đọc từ CSDL, và thứ tự ấy không ai bảo đảm.
        UniqueConstraint("owner_id", "tu", name="uq_voice_tudien_owner_tu"),
    )

    id: Mapped[int] = mapped_column(KHOA_CHINH, primary_key=True,
                                    autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)

    #: Từ cần sửa, đã hạ chữ thường. Khớp theo BIÊN TỪ (`tu_dien._mau`).
    tu: Mapped[str] = mapped_column(String(80))
    #: Viết lại thành gì. Đây là VĂN BẢN, không phải phiên âm IPA — ta đưa nó
    #: cho `sea-g2p` như một chuỗi bình thường.
    thay: Mapped[str] = mapped_column(String(160))
    #: Vì sao thêm mục này. `tu_dien.py` đòi lý do cho bảng chung, và lý do ấy
    #: cũng đúng ở đây: một bảng thay thế không có lý do sẽ không bao giờ xoá
    #: được, vì không ai dám.
    ghi_chu: Mapped[str] = mapped_column(String(200), default="")

    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                              default=_now)
    sua_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                              default=_now, onupdate=_now)


# ── Bảng của màn Dự án ───────────────────────────────────────────────────────
#
# 🔴 MỘT DÒNG NÀY LÀ BẮT BUỘC, và thiếu nó hỏng theo kiểu tệ nhất.
#
#    `platform_core/registry.load_app_tables` chỉ import đúng
#    `apps/<slug>/tables.py` — Alembic gọi nó trong `env.py` để dựng
#    `Base.metadata`. Server thì import gián tiếp qua route, nên **server vẫn
#    chạy** nếu thiếu dòng này.
#
#    Hệ quả của việc thiếu: `alembic revision --autogenerate` không thấy hai
#    bảng kia và **đề nghị XOÁ chúng**, im lặng, trong một migration mà người
#    duyệt tưởng là dọn dẹp.
#
# ⭐ Model đặt ở tệp riêng (`tables_du_an.py`) có chủ ý: bốn bảng phía trên là
#    danh tính giọng — hợp đồng dài hạn, consent pháp lý, lời hứa "nâng engine
#    không phá `voice_id`". Dự án chỉ là một công cụ soạn thảo và sẽ đổi hình
#    nhiều lần. Trộn chúng là mời người sửa công cụ đi ngang qua bốn bảng không
#    được phép lay động.
from .tables_du_an import VoiceBlock, VoiceProject  # noqa: E402,F401
