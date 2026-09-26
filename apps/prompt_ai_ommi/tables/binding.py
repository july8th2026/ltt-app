"""tables/binding.py — OmmiBinding: nguon chan ly the (`@IMAGE_1`...) <-> variant.

Bang nay CHUA loi N-2 (spec pha 1 muc 4.2): truoc day so the duoc dem lai o
`composer.resource_lines()` (luc build prompt) va dem KHAC DI luc build refs
giao bai (`routes/handoff.py`) — hai lan dem doc lap troi khoi nhau khong ai
biet. Tu nay CHI `services/bindings.py` duoc ghi bang nay; noi khac chi DOC.

`scene_id IS NULL` = binding cap PROJECT (dung cho preview/director prompt o
muc project, chua gan canh cu the).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiBinding(Base):
    __tablename__ = "ommi_binding"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scene_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    tag: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    variant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role: Mapped[str] = mapped_column(String(24), default="reference_image", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "scene_id", "tag", name="uq_ommi_binding_tag"),
    )
