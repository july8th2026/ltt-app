"""nexus: ve phien dieu khien (Q93 rang buoc 2 va 6)

Mot dong `nexus_sessions` VUA la ve VUA la ban ghi kiem toan. Do la chu y: neu
ve song o mot cho con nhat ky o cho khac thi se co ngay hai cho lech nhau, va
luc can doi chieu sau su co thi khong biet tin cai nao.

`ticket_digest` UNIQUE va chi giu digest — ve goc chi ton tai trong dung mot
phan hoi HTTP. Bam khac khong gian voi ma ghep (domain separation), de mot
digest lay duoc o bang nay khong dem thu duoc o bang kia.

Khong bao gio xoa, khong bao gio sua lai qua khu: ket thuc phien la GHI THEM
`ended_at` + `end_reason`. Sau su co, cau hoi duy nhat quan trong la "ai da vao
may toi, luc nao, tu dau" — va khong ai hoi no truoc khi can.

`ondelete=CASCADE` tren `device_id`: xoa mot thiet bi thi phien cua no di theo.
Luu y day KHONG phai duong thu hoi — thu hoi ghi `revoked_at` va giu nguyen dong.

Chi tien: khong migration nao o day xoa du lieu.

Revision ID: d649cfad754f
Revises: b165aa3584e0
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# Sinh ngau nhien va doi chieu voi 41 id dang co truoc khi ghi (bai hoc R10:
# mot id TRONG hop ly ma trung se tao vong lap va giet moi lenh alembic).
revision = "d649cfad754f"
down_revision = "b165aa3584e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nexus_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_digest", sa.String(length=64), nullable=False),
        sa.Column("quyen", sa.String(length=16), nullable=False),
        sa.Column("controller_ip", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_reason", sa.String(length=32), nullable=False,
                  server_default=""),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["nexus_devices.id"],
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_digest", name="uq_nexus_sessions_ticket"),
    )
    op.create_index("ix_nexus_sessions_user", "nexus_sessions", ["user_id"])
    op.create_index("ix_nexus_sessions_device", "nexus_sessions", ["device_id"])
    op.create_index("ix_nexus_sessions_issued", "nexus_sessions", ["issued_at"])


def downgrade() -> None:
    op.drop_index("ix_nexus_sessions_issued", table_name="nexus_sessions")
    op.drop_index("ix_nexus_sessions_device", table_name="nexus_sessions")
    op.drop_index("ix_nexus_sessions_user", table_name="nexus_sessions")
    op.drop_table("nexus_sessions")
