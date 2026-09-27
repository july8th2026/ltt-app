"""tables/canh.py -- OmmiCanh: CANH KICH BAN, nguon chan ly duy nhat cua
prompt di ra ngoai (spec S-1).

KHONG lan voi `ommi_scene`: cai do la KHUNG HINH storyboard, co
`storyboard_id`/`position`/`image_key`, va `prompt`/`camera` cua no chi la
ban SAO phuc vu viec sinh anh (spec S-2).

`id` phai tai dung duoc id cu (`payload["scenes"][].id`) de binding cua pha 1
song sot qua pha 3 ma khong can di tru (spec S-4). SQLAlchemy chi ap `default`
khi cot CHUA duoc dat, nen giu `default=_uuid` van cho truyen id vao.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base
from apps.prompt_ai_ommi.tables.tai_nguyen import _uuid


class OmmiCanh(Base):
    __tablename__ = "ommi_canh"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    brief_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Chu TU DO, giau chi tiet. Dung ep ve enum dong cua `taovideo` o day --
    # viec quy doi la cua pha 2 (`handoff_stage`), va chi tiet goc phai di vao
    # `prompt` chu khong bi bo (spec Sec 6.2b).
    camera: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lighting: Mapped[str] = mapped_column(Text, default="", nullable=False)
    mood: Mapped[str] = mapped_column(Text, default="", nullable=False)
    continuity: Mapped[str] = mapped_column(Text, default="", nullable=False)
    selected_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("brief_id", "position", name="uq_ommi_canh_vitri"),
    )
