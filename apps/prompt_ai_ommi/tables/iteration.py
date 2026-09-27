"""tables/iteration.py -- OmmiIteration: mot luot goi LLM de sua kich ban,
va phan quyet cua khach ve luot do."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base
from apps.prompt_ai_ommi.tables.tai_nguyen import _uuid


class OmmiIteration(Base):
    """`was_free` ghi lai luot NAY co thu tien hay khong -- de sau con doi soat.

    `verdict="rejected"` KHONG hoan credit. Hoan thi khach bam rejected moi
    lan la LLM mien phi vo han (spec Sec 6.4).
    """

    __tablename__ = "ommi_iteration"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    brief_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    prompt_sent: Mapped[str] = mapped_column(Text, default="", nullable=False)
    output: Mapped[str] = mapped_column(Text, default="", nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    credit_charged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    was_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verdict: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("brief_id", "seq", name="uq_ommi_iteration_seq"),
    )
