"""them bang developer_api_keys cho Public API (Q92)

Credential cua KHACH, tach hoan toan khoi bang `api_keys` (credential provider
cua nen tang). Bang nay chi giu digest mot chieu; khong co cot nao chua secret.

Revision ID: a7b8c9d0e1f2
Revises: b6c7d8e9f0a1
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "b6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "developer_api_keys",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(120), nullable=False, server_default=""),
        sa.Column("key_id", sa.String(48), nullable=False),
        sa.Column("verifier_digest", sa.String(64), nullable=False),
        sa.Column("pepper_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("allowed_tools", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        # RESTRICT nhu so credit: khoa la bang chung ai da tieu gi, nen ngung
        # mot tai khoan la `is_active=False`, khong phai xoa dong.
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        # UNIQUE tren key_id la mot phan cua co che xac thuc, khong chi la chi
        # muc: no bao dam mot key_id chi tro toi dung mot dong.
        sa.UniqueConstraint("key_id", name="uq_developer_api_keys_key_id"),
    )
    op.create_index("ix_developer_api_keys_user_id", "developer_api_keys",
                    ["user_id"])
    op.create_index("ix_developer_api_keys_key_id", "developer_api_keys",
                    ["key_id"])
    op.create_index("ix_developer_api_keys_owner_created", "developer_api_keys",
                    ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_developer_api_keys_owner_created",
                  table_name="developer_api_keys")
    op.drop_index("ix_developer_api_keys_key_id", table_name="developer_api_keys")
    op.drop_index("ix_developer_api_keys_user_id", table_name="developer_api_keys")
    op.drop_table("developer_api_keys")
