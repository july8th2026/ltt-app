"""Bảng riêng của video_crawler (tiền tố `vc_`, manifest `table_prefix="vc"`).

Ba bảng, khai ở `platform_core/public_api/governance.py`:
- `vc_phien`: phiên đăng nhập nền tảng theo người dùng (spec §16) — hàng `vc_phien`.
- `vc_da_tai`: sổ dedup BỀN (owner, nền, video) — Q4 chủ dự án duyệt 22/09. `jobs.result` bị xoá sau 30 ngày nên
  "không trùng" suy từ đó chỉ nhớ 30 ngày, và hai job cùng lúc cùng video đều tải + đều thu tiền (SO_LOI L4).
  Lịch sử, kết quả, tệp vẫn nằm ở `jobs` (spec §13) — bảng này chỉ giữ khoá chống trùng.
- `vc_tai_khoan`: KHO tài khoản phụ của LTT cho nền cần đăng nhập (W4-L9) — không có gì của khách, nên nằm ở
  `governance.NOT_CUSTOMER_DATA` chứ không phải `STORES`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


class VcPhien(Base):
    """Cookie đăng nhập của MỘT người dùng cho MỘT nền. Giá trị luôn mã hoá (`secretbox`), không bao giờ rõ."""

    __tablename__ = "vc_phien"
    __table_args__ = (UniqueConstraint("owner_id", "nen_tang", name="uq_vc_phien_owner_nen"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    nen_tang: Mapped[str] = mapped_column(String(32), nullable=False)
    cookie_ma_hoa: Mapped[str] = mapped_column(Text, nullable=False)
    so_cookie: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    het_han_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_bay_gio)
    cap_nhat_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_bay_gio)


#: Trạng thái của một dòng `vc_da_tai`.
DANG_TAI = "dang_tai"
XONG = "xong"


class VcDaTai(Base):
    """Một video (owner, nền, video_id) đã/đang được tải. UNIQUE ở CSDL là chỗ quyết định ai được tải.

    `dang_tai`: một job đã GIÀNH chỗ, đang tải (job chết ⇒ quá 3 giờ thì giành lại được).
    `xong`: tải xong, `tep` là storage key — tệp đi theo `jobs` (30 ngày) nên có thể đã mất; dòng vẫn giữ để chống trùng.
    """

    __tablename__ = "vc_da_tai"
    __table_args__ = (UniqueConstraint("owner_id", "nen_tang", "video_id", name="uq_vc_da_tai_owner_nen_video"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    nen_tang: Mapped[str] = mapped_column(String(32), nullable=False)
    video_id: Mapped[str] = mapped_column(String(64), nullable=False)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tep: Mapped[str | None] = mapped_column(String(512), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(16), nullable=False, default=DANG_TAI)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_bay_gio)
    cap_nhat_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_bay_gio)


#: Trạng thái của một tài khoản kho. Chỉ `song` mới vào vòng chọn.
SONG = "song"
HET_HAN = "het_han"
BI_CHAN = "bi_chan"
TAM_NGHI = "tam_nghi"


class VcTaiKhoan(Base):
    """MỘT tài khoản PHỤ của LTT trên một nền cần đăng nhập, dùng chung cho mọi khách chưa có phiên riêng.

    ⛔ KHÔNG có `owner_id`: đây là tài sản của LTT, không phải dữ liệu của khách. Quan hệ "lượt này của khách
       nào đi qua tài khoản nào" nằm ở sự kiện job INTERNAL — khách không đọc được, và nó đã có hạn lưu trữ.

    Vì sao đếm lượt ngay trên hàng (`cua_so_luc`, `so_luot_trong_gio`) chứ không suy từ `jobs`: trần là của TÀI
    KHOẢN (nền phát hiện theo tài khoản), còn `jobs` chỉ biết khách — hai câu hỏi khác nhau. Một cửa sổ trượt
    một giờ, đặt lại khi quá hạn: đủ để chia lượt, không sinh thêm một bảng sổ phải dọn.

    `diem` theo mô hình pool của cộng đồng (`jhao104/proxy_pool`, NC §2): cộng khi thành công, trừ theo MÃ lỗi,
    chỉ loại khi xuống dưới ngưỡng — xoá ngay sau một lần lỗi là cách mất sạch kho vì một sự cố mạng thoáng qua.
    """

    __tablename__ = "vc_tai_khoan"
    # Nhãn là thứ admin gọi tên tài khoản trên trang vận hành; trùng nhãn trong một nền nghĩa là hai dòng không
    # phân biệt được trong nhật ký lẫn giao diện — và "tạm nghỉ tài khoản đó" trở thành câu hỏi không có đáp án.
    __table_args__ = (UniqueConstraint("nen_tang", "nhan", name="uq_vc_tai_khoan_nen_nhan"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nen_tang: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    nhan: Mapped[str] = mapped_column(String(64), nullable=False)
    cookie_ma_hoa: Mapped[str] = mapped_column(Text, nullable=False)
    trang_thai: Mapped[str] = mapped_column(String(16), nullable=False, default=SONG)
    diem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Hạn của cookie xác thực (đọc từ chính cookies.txt), không phải hạn do người nhập gõ.
    han: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: MÃ lỗi gần nhất (`apps/video_crawler/loi.py`) — ⛔ không bao giờ là văn bản thô của yt-dlp.
    loi_gan_nhat: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dung_gan_nhat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cua_so_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    so_luot_trong_gio: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_bay_gio)
    cap_nhat_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_bay_gio)
