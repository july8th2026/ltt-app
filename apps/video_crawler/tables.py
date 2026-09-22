"""Bảng riêng của video_crawler (tiền tố `vc_`, manifest `table_prefix="vc"`).

Hai bảng, khai ở `platform_core/public_api/governance.py` (hàng `vc_phien`, `vc_da_tai`):
- `vc_phien`: phiên đăng nhập nền tảng theo người dùng (spec §16).
- `vc_da_tai`: sổ dedup BỀN (owner, nền, video) — Q4 chủ dự án duyệt 22/09. `jobs.result` bị xoá sau 30 ngày nên
  "không trùng" suy từ đó chỉ nhớ 30 ngày, và hai job cùng lúc cùng video đều tải + đều thu tiền (SO_LOI L4).
  Lịch sử, kết quả, tệp vẫn nằm ở `jobs` (spec §13) — bảng này chỉ giữ khoá chống trùng.
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
