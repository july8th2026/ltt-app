"""voice_lich_su — trang thai nguoi dung tren mot luot lich su (da tai / da xoa)

⭐ Hai tinh nang cua man Lich su ltt_voice can mot cho luu BEN, owner-scoped:
   · "da tai"  — vong doi, khong phai mot lan phat; localStorage mat khi doi may.
   · "da xoa"  — xoa la don TEP som (job_content.expire_content) + danh dau o
                 day; hang `jobs` KHONG bi hard-delete (bang chung so credit).

⛔ Bang RIENG cua app, KHONG them cot vao `jobs` (bang dung chung moi app). Giu
   dung ranh gioi "them app thi them thu muc, khong sua platform_core".

Revision ID: d9a1f6c2b3e5
Revises: e1a2b3c4d5f6
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d9a1f6c2b3e5"
down_revision = "e1a2b3c4d5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_lich_su",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                  primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("da_tai_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("da_xoa_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("sua_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "job_id",
                            name="uq_voice_lichsu_owner_job"),
    )


def downgrade() -> None:
    op.drop_table("voice_lich_su")
