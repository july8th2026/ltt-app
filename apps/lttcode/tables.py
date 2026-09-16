"""Bảng riêng của app LTTCODE. Tiền tố `lttcode_` theo `MANIFEST.table_prefix`.

`lttcode_auth_codes` — mã cấp quyền một lần của luồng "Đăng nhập LTT Studios"
trên ứng dụng desktop (PKCE S256 + loopback). Chỉ lưu **digest** của mã; mã sống
120 giây và bị tiêu bằng một câu UPDATE có điều kiện (`dang_nhap.doi_ma`).

⛔ `user_id` là `String(36)` — `User.id` của nền tảng là UUID chuỗi.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


class LttcodeAuthCode(Base):
    __tablename__ = "lttcode_auth_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    code_challenge: Mapped[str] = mapped_column(String(64), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    device: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_lttcode_auth_codes_expires_at", "expires_at"),)
