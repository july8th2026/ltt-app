"""tables/brief.py -- OmmiBrief: kich ban la mot THUC THE, khong con nhet
trong `AppProject.payload`.

Vi sao tach ra: loi vao moi la 2-pane (danh sach brief <-> khung soan). Mot
danh sach doc tu JSON long trong mot cot thi khong loc, khong sap, khong phan
trang duoc -- va moi lan sua mot brief la ghi lai ca payload cua du an.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base
from apps.prompt_ai_ommi.tables.tai_nguyen import _uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiBrief(Base):
    """Mot kich ban. `free_iterations_used` la SO DEM LUOT MIEN PHI (Q-7).

    Bo dem PHAI o day, khong o phien: bo dem trong phien nghia la khach mo
    tab moi la duoc 2 luot mien phi nua -- LLM mien phi vo han.
    """

    __tablename__ = "ommi_brief"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    story_vi: Mapped[str] = mapped_column(Text, default="", nullable=False)
    goal: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    audience: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    target_duration_sec: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    target_scenes: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(8), default="16:9", nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="vi", nullable=False)
    style_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    meta_prompt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    character_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    background_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    referenced_variants: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    free_iterations_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
