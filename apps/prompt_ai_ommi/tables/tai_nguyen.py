"""
tables/tai_nguyen.py — kho tài nguyên: OmmiResource + variant + tag/collection.

Tách từ apps/prompt_ai_ommi/tables.py (2026-09-26, spec pha 1 R-4). Nội dung
lớp KHÔNG đổi một dòng nào so với bản gốc — chỉ đổi vị trí tệp.

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
    # Pha 5 — dedupe + kho sâu.
    file_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True)
    favorite: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
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


class OmmiTrash(Base):
    """Thùng rác: bản chờ purge, khôi phục được nguyên id.

    Khác `archived_at` trên `OmmiResource` (lưu trữ TẠM, bản gốc vẫn còn
    trong bảng sống): ở đây bản gốc bị XOÁ THẬT khỏi bảng sống, snapshot đủ
    để dựng lại y hệt nằm trong `payload`. Đây là "xoá" thật sự của khách,
    không phải "ẩn đi".
    """

    __tablename__ = "ommi_trash"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    purge_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)


class OmmiImageJob(Base):
    """Một lượt sinh ảnh composite — theo dõi phiên bản để revert/retry.

    `parent_id` trỏ lượt sinh trước đó khi đây là một retry; `version` tăng
    dần trong cùng một chuỗi retry của cùng `resource_id`.
    """

    __tablename__ = "ommi_image_job"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="queued")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

