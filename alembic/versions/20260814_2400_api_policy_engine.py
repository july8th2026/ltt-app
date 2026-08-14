"""them chinh sach han muc va kill switch cho khu API (EXT-14)

Moi cot so deu NULLABLE va NULL nghia la "ke thua". Khong dung 0 lam dau hieu
"chua dat": 0 la mot han muc that va co nghia (nhip 0 = tu choi tat ca), tieu no
cho "chua dat" thi khong bao gio dien dat duoc nua.

Kill switch tach khoi chinh sach vi chung tra loi hai cau hoi khac nhau: chinh
sach noi "bao nhieu", kill switch noi "khong phai luc nay". Gop lai thi ban ghi
duy nhat ve "3 gio sang tat cai nay vi sao" chi con la mot con so.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c5d6e7f8a9b0"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_policies",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.String(500), nullable=False,
                  server_default=""),
        sa.Column("rpm_read", sa.Integer(), nullable=True),
        sa.Column("rpm_write", sa.Integer(), nullable=True),
        sa.Column("rpm_create", sa.Integer(), nullable=True),
        sa.Column("max_active_jobs", sa.Integer(), nullable=True),
        sa.Column("daily_credit", sa.Integer(), nullable=True),
        sa.Column("max_upload_bytes", sa.Integer(), nullable=True),
        sa.Column("class_concurrency", sa.JSON(), nullable=False),
        sa.Column("tool_overrides", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_api_policy_name"),
    )

    op.create_table(
        "api_policy_assignments",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("subject_id", sa.String(48), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # CASCADE, khac voi cac khoa ngoai khac o day dung RESTRICT: mot dong
        # gan khong phai bang chung ve tien, no chi la mot con tro. Xoa chinh
        # sach thi han muc tut ve buoc truoc — thay doi doan truoc duoc.
        sa.ForeignKeyConstraint(["policy_id"], ["api_policies.id"],
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "subject_id", name="uq_api_policy_subject"),
    )
    op.create_index("ix_api_policy_assignments_policy_id",
                    "api_policy_assignments", ["policy_id"])
    op.create_index("ix_api_policy_lookup", "api_policy_assignments",
                    ["scope", "subject_id"])

    op.create_table(
        "api_kill_switches",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(64), nullable=False, server_default=""),
        # NOT NULL co chu dich: mot cong tat khong co ly do la mot su co khong
        # ai giai thich duoc ve sau.
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False,
                  server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # Het han = tu het hieu luc, khong can job don. Loi thuong gap nhat cua
        # mot cong tat su co la khong ai nho tat no di.
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "subject", name="uq_api_kill_subject"),
    )
    op.create_index("ix_api_kill_switches_scope", "api_kill_switches", ["scope"])
    op.create_index("ix_api_kill_scope", "api_kill_switches",
                    ["scope", "expires_at"])


def downgrade() -> None:
    op.drop_index("ix_api_kill_scope", table_name="api_kill_switches")
    op.drop_index("ix_api_kill_switches_scope", table_name="api_kill_switches")
    op.drop_table("api_kill_switches")
    op.drop_index("ix_api_policy_lookup", table_name="api_policy_assignments")
    op.drop_index("ix_api_policy_assignments_policy_id",
                  table_name="api_policy_assignments")
    op.drop_table("api_policy_assignments")
    op.drop_table("api_policies")
