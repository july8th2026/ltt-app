"""them bang public_api_idempotency cho Public API (Q92)

Chong double-charge khi client thu lai: `jobs.dedupe_key` chi khop job CHUA
ket thuc, nen retry sau khi job xong se tao job va hold thu hai.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_api_idempotency",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("key_id", sa.String(48), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("operation", sa.String(48), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default="in_progress"),
        sa.Column("job_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        # Rang buoc nay LA co che chong double-charge, khong phai chi mot chi
        # muc: hai request dua nhau cung mot khoa thi CSDL cho dung mot cai qua.
        sa.UniqueConstraint("key_id", "operation", "idempotency_key",
                            name="uq_public_api_idempotency"),
    )
    op.create_index("ix_public_api_idempotency_key_id", "public_api_idempotency",
                    ["key_id"])
    op.create_index("ix_public_api_idempotency_user_id", "public_api_idempotency",
                    ["user_id"])
    op.create_index("ix_public_api_idempotency_owner", "public_api_idempotency",
                    ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_public_api_idempotency_owner",
                  table_name="public_api_idempotency")
    op.drop_index("ix_public_api_idempotency_user_id",
                  table_name="public_api_idempotency")
    op.drop_index("ix_public_api_idempotency_key_id",
                  table_name="public_api_idempotency")
    op.drop_table("public_api_idempotency")
