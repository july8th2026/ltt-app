"""
tables.py — bảng CSDL riêng của PROMPT AI OMMI.

Vì sao app này cần bảng thật thay vì `AppProject` JSON: kho tài nguyên và thư
viện prompt **dùng chung giữa nhiều project**. Nhét chúng vào payload của từng
project thì mỗi project giữ một bản sao, sửa một chỗ không lan sang chỗ khác,
không phân trang được, và không trả lời được câu hỏi "tài nguyên này đang dùng ở
đâu" — chính là con số app phải hiển thị.

**Mô hình sở hữu.** Module nguồn (`D:\\BOT GEMINI`) khai ba tầng PERSONAL /
LIBRARY / TEAM nhưng `scoping.py` lại lọc mọi truy vấn theo một `master_user_id`
dùng chung, nên trên thực tế mọi người dùng chung một kho. Ở đây KHÔNG có
namespace chung:

- `owner_id` có giá trị  → bản ghi riêng tư, chỉ chủ sở hữu thấy và sửa.
- `owner_id` NULL        → mẫu trong catalog, mọi người ĐỌC, chỉ admin sửa.

Người dùng "lấy" một mẫu bằng cách clone thành bản riêng của mình. Không có
đường nào cho hai người dùng thường thấy dữ liệu của nhau.

Tên bảng đều mang tiền tố `ommi_` theo `MANIFEST.table_prefix`; registry từ chối
nạp nếu lệch.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, Index, Integer, JSON, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Năm nhóm tài nguyên — khớp phần "Phân loại tài nguyên" của giao diện.
RESOURCE_KINDS = ("character", "background", "prop", "vehicle", "misc")


class OmmiResource(Base):
    """Một tài nguyên tham chiếu: nhân vật, bối cảnh, đạo cụ, phương tiện, khác.

    Gộp `asset_groups` + `characters` + `backgrounds` + `outfits` + `poses` của
    nguồn thành một bảng phân biệt bằng `kind`. Năm bảng riêng ở nguồn chỉ khác
    nhau vài cột mô tả, và mỗi lần thêm loại mới lại phải thêm một bảng + một
    router — không đáng.
    """

    __tablename__ = "ommi_resource"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # NULL = mẫu catalog do admin publish. Có giá trị = tài nguyên riêng tư.
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Mô tả dùng khi ghép prompt — tách khỏi `description` vốn để người đọc.
    prompt_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    cover_variant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        # Lọc kho luôn là (của tôi) + (loại) + (chưa lưu trữ). Không có index này
        # thì kho vài trăm tài nguyên đã phải quét toàn bảng mỗi lần mở trang.
        Index("ix_ommi_resource_owner_kind", "owner_id", "kind", "archived_at"),
    )


class OmmiResourceVariant(Base):
    """Một ảnh của tài nguyên. Một tài nguyên có nhiều biến thể (góc, trang phục).

    File nằm ở Storage; ở đây chỉ giữ khoá. Không bao giờ lưu URL đã ký vào CSDL
    vì nó hết hạn.
    """

    __tablename__ = "ommi_resource_variant"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # Lặp lại owner để lọc được mà không cần join — và để một lần quên join
    # không biến thành lỗ hổng đọc chéo.
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    thumb_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bytes_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)


class OmmiTag(Base):
    """Nhãn tự do, riêng theo người dùng."""

    __tablename__ = "ommi_tag"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_ommi_tag_owner_name"),
    )


class OmmiResourceTag(Base):
    """Quan hệ tài nguyên ↔ nhãn.

    Nguồn dùng tới bốn bảng cho việc này (`asset_tags`, `asset_group_tags`,
    `tags`, `entity_tags`); hai bảng là đủ.
    """

    __tablename__ = "ommi_resource_tag"

    resource_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tag_id: Mapped[str] = mapped_column(String(36), primary_key=True)


class OmmiCollection(Base):
    """Bộ tài nguyên dùng lại — ví dụ dàn nhân vật của một chiến dịch."""

    __tablename__ = "ommi_collection"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)


class OmmiCollectionItem(Base):
    __tablename__ = "ommi_collection_item"

    collection_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OmmiResourceUsage(Base):
    """Tài nguyên này đang được dùng ở project/cảnh nào.

    Có bảng này thì trả lời được "xoá tài nguyên này có ảnh hưởng gì không" —
    câu hỏi mà giao diện phải trả lời trước khi cho xoá.
    """

    __tablename__ = "ommi_resource_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scene_ref: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("resource_id", "project_id", "scene_ref",
                         name="uq_ommi_usage_resource_project_scene"),
    )


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
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
