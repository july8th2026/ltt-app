"""nexus: thiet bi va ma ghep (Q93)

Hai bang, va ranh gioi giua chung la ranh gioi bao mat:

`nexus_devices` giu KHOA CONG KHAI cua mot may da duoc tin. Khong co khoa rieng
o day va se khong bao gio co — Q93 rang buoc 1: khoa rieng khong bao gio roi may
do. He qua thuc te: doc trom ca hai bang nay KHONG cho phep gia mao mot thiet bi
nao, khac han mot bang chua bearer token.

`nexus_enrollments` giu ma ghep da bam, dung mot lan, han 5 phut. Bam vi khong
co gi can doc lai ma goc — chi can kiem mot lan. Mot ban dump CSDL roi ra ngoai
cung khong cho ke cam no ghep duoc may nao.

UNIQUE tren `code_digest` va tren `public_key` la CSDL cuong che, khong de Python
doc-roi-ghi quyet dinh. Do la bai hoc H36.3: hai tien trinh cung kiem "chua ai
dung" roi cung ghi.

Chi tien: khong migration nao o day xoa du lieu.

Revision ID: b165aa3584e0
Revises: f8a9b0c1d2e3
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# Sinh ngau nhien va doi chieu voi 40 id dang co. Ban dau file nay dung
# `a1b2c3d4e5f6` — mot id trong hop ly ma TRUNG voi migration chat_ai_studio,
# tao vong lap trong do thi revision. Test khong bat duoc vi test dung
# `Base.metadata.create_all()` chu khong chay alembic; chi co chay that moi thay.
revision = "b165aa3584e0"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nexus_devices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False,
                  server_default=""),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("hardware_fingerprint", sa.String(length=128), nullable=False,
                  server_default=""),
        sa.Column("platform", sa.String(length=32), nullable=False,
                  server_default=""),
        sa.Column("agent_version", sa.String(length=32), nullable=False,
                  server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_key", name="uq_nexus_devices_public_key"),
    )
    op.create_index("ix_nexus_devices_user", "nexus_devices", ["user_id"])
    op.create_index("ix_nexus_devices_seen", "nexus_devices", ["last_seen_at"])

    op.create_table(
        "nexus_enrollments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("code_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_id", sa.String(length=36), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claimed_ip", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_digest", name="uq_nexus_enrollments_digest"),
    )
    op.create_index("ix_nexus_enrollments_user", "nexus_enrollments", ["user_id"])
    op.create_index("ix_nexus_enrollments_expires", "nexus_enrollments",
                    ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_nexus_enrollments_expires", table_name="nexus_enrollments")
    op.drop_index("ix_nexus_enrollments_user", table_name="nexus_enrollments")
    op.drop_table("nexus_enrollments")
    op.drop_index("ix_nexus_devices_seen", table_name="nexus_devices")
    op.drop_index("ix_nexus_devices_user", table_name="nexus_devices")
    op.drop_table("nexus_devices")
