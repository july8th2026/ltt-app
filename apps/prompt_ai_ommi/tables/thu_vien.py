"""tables/thu_vien.py — thu vien prompt: meta prompt + snippet + version + style.

Tach tu apps/prompt_ai_ommi/tables.py (2026-09-26, spec pha 1 R-4). Noi dung
lop KHONG doi mot dong nao so voi ban goc — chi doi vi tri tep.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiMetaPrompt(Base):
    """Prompt meta — bộ chỉ dẫn điều khiển cách AI dựng prompt.

    Đây là thứ chủ sản phẩm yêu cầu "mỗi người một bộ riêng". `owner_id` NULL là
    mẫu catalog; người dùng clone ra bản riêng rồi sửa tuỳ ý.
    """

    __tablename__ = "ommi_meta_prompt"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), default="director",
                                         nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_catalog: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Bản clone nhớ nguồn để biết mẫu gốc đã đổi.
    cloned_from_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Admin NGỪNG DÙNG một mẫu catalog (H19.6). Khác hẳn `archived_at`:
    #   archived_at   = chủ sở hữu tự cất bản RIÊNG của mình đi;
    #   deprecated_at = admin rút một mẫu CHUNG khỏi danh sách chào mời.
    # Không tách hai cột thì "ngừng chào mẫu cũ" sẽ vô tình cất luôn bản riêng
    # của người đã clone — họ mất công cụ đang dùng mà không hiểu vì sao.
    deprecated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    deprecated_note: Mapped[str] = mapped_column(String(300), default="",
                                                 nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class OmmiPromptSnippet(Base):
    """Đoạn prompt dùng lại trong thư viện riêng."""

    __tablename__ = "ommi_prompt_snippet"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_catalog: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cloned_from_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Admin NGỪNG DÙNG một mẫu catalog (H19.6). Khác hẳn `archived_at`:
    #   archived_at   = chủ sở hữu tự cất bản RIÊNG của mình đi;
    #   deprecated_at = admin rút một mẫu CHUNG khỏi danh sách chào mời.
    # Không tách hai cột thì "ngừng chào mẫu cũ" sẽ vô tình cất luôn bản riêng
    # của người đã clone — họ mất công cụ đang dùng mà không hiểu vì sao.
    deprecated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    deprecated_note: Mapped[str] = mapped_column(String(300), default="",
                                                 nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class OmmiPromptVersion(Base):
    """Lịch sử một meta prompt hoặc snippet, để so sánh và quay lại."""

    __tablename__ = "ommi_prompt_version"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    note: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("target_kind", "target_id", "version",
                         name="uq_ommi_prompt_version_target"),
    )


class OmmiStyle(Base):
    """Phong cách hình ảnh. Riêng tư hoặc mẫu catalog, cùng mô hình như trên."""

    __tablename__ = "ommi_style"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_catalog: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cloned_from_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Admin NGỪNG DÙNG một mẫu catalog (H19.6). Khác hẳn `archived_at`:
    #   archived_at   = chủ sở hữu tự cất bản RIÊNG của mình đi;
    #   deprecated_at = admin rút một mẫu CHUNG khỏi danh sách chào mời.
    # Không tách hai cột thì "ngừng chào mẫu cũ" sẽ vô tình cất luôn bản riêng
    # của người đã clone — họ mất công cụ đang dùng mà không hiểu vì sao.
    deprecated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    deprecated_note: Mapped[str] = mapped_column(String(300), default="",
                                                 nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


