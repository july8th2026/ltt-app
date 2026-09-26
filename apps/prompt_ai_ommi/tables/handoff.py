"""tables/handoff.py — OmmiHandoff: ve giao bai dung mot lan sang app khac.

Tach rieng khoi `kich_ban.py` vi day khong phai mot phan cua "kich ban"
(brief/scene/iteration) ma la mot HOP THU tam thoi giua hai app — vong doi 30
phut, khong lien quan gi toi vong doi cua project.

`used_at` khac NULL sau lan doc dau tien (xem
`services/handoff_stage.py::doc_va_tieu_ve`). KHONG co cot `owner_id`: quyen
so huu kiem qua `project_id` (chu cua `AppProject` do), khong nhan doi o day —
hai cho khai cung mot dieu thi som muon cung lech nhau.

`_uuid`/`_now` dua vao tu `tai_nguyen.py` chu khong khai lai: chung la MOT
dinh nghia cho ca package (binding.py con ban sao rieng tu truoc khi tach —
khong nhan doi them mot ban thu ba).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base

from apps.prompt_ai_ommi.tables.tai_nguyen import _now, _uuid


class OmmiHandoff(Base):
    __tablename__ = "ommi_handoff"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scene_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_app_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
