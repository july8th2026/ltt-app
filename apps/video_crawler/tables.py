"""Bảng riêng của video_crawler (tiền tố `vc_`, manifest `table_prefix="vc"`).

Chỉ MỘT bảng: phiên đăng nhập nền tảng theo người dùng (spec §16). Lịch sử, kết quả, dedup đều nằm ở `jobs`
(spec §13) — không nhân đôi sổ của nền tảng. Khai ở `platform_core/public_api/governance.py` (hàng `vc_phien`).
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
