"""tables/nhan_vat.py -- nhan vat / trang phuc / dang / boi canh / face
embedding -- goc cua viec nhat quan xuyen canh.

Do duoc tren CSDL cua ban goc 26/09: bon bang tuong duong o do co 0 dong --
thiet ke cong phu ma chua ai nhap mot dong. Chu du an chot 26/09 van xay
(Q-14). Neu sau nay do duoc la khach cung khong dung, day la cho cat truoc.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base
from apps.prompt_ai_ommi.tables.tai_nguyen import _uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiCharacter(Base):
    __tablename__ = "ommi_character"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    gender: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    age_range: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    face_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    body_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hair_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    outfit_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    personality: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expression_style: Mapped[str] = mapped_column(Text, default="", nullable=False)
    movement_style: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Khoi chu CHEN NGUYEN VAN vao moi canh -- day la thu giu nhan vat khong doi.
    fixed_prompt_block: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reference_variant_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class OmmiOutfit(Base):
    __tablename__ = "ommi_outfit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    character_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reference_variant_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)


class OmmiPose(Base):
    __tablename__ = "ommi_pose"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pose_block: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reference_variant_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)


class OmmiBackground(Base):
    __tablename__ = "ommi_background"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    location_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    environment_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lighting_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    color_palette: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    camera_feel: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    important_objects: Mapped[str] = mapped_column(Text, default="", nullable=False)
    fixed_prompt_block: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reference_variant_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class OmmiFaceEmbedding(Base):
    """Pha 3 CHI tao bang. Khong service, khong route -- Sec 6.5 khong co
    endpoint nao cho no. Nguoi ghi dau tien la `services/composite.py` o pha 5.
    """

    __tablename__ = "ommi_face_embedding"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    character_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    variant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    vector_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    backend: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
