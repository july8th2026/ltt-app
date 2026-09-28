"""
chia_se.py - OmmiShareCode: chia se mot muc thu vien/tai nguyen bang MA (Q-10).

Khong co trang "kho cong khai": ai co MA moi xem/nhan duoc. `target_kind` +
`target_id` tro toi mot ban ghi CU THE o bang khac (meta_prompt/style/snippet/
character/background/pose/image_template/storyboard_framework/sample/profile) -
xem services/chia_se.py:TARGET_KINDS.

Hinh dang cot khop dung migration `alembic/versions/20260927_1842_ommi_pha4_
kho_chung.py` (bang `ommi_share_code`, index `ix_ommi_share_code_code` unique) -
lech model<->migration la loi im lang.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    import uuid
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiShareCode(Base):
    """Ve chia se dung nhieu lan (toi da `max_uses`, hoac vo han neu None)."""

    __tablename__ = "ommi_share_code"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(12), nullable=False, unique=True,
                                      index=True)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
