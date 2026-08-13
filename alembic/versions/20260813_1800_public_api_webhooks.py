"""them bang webhook cho Public API (Q92)

Outbox giao dich: su kien duoc ghi TRONG transaction cua job, worker giao sau.
Nho vay webhook khong bao gio lam cham hay lam sai settlement.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_api_webhooks",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("key_id", sa.String(48), nullable=False, server_default=""),
        sa.Column("url", sa.String(2000), nullable=False),
        # MA HOA (khong phai hash): server phai tai tao duoc secret de KY.
        # Nguoc voi developer key - xem platform_core/public_api/webhooks.py.
        sa.Column("secret_enc", sa.Text(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_public_api_webhooks_user_id", "public_api_webhooks",
                    ["user_id"])
    op.create_index("ix_public_api_webhooks_owner", "public_api_webhooks",
                    ["user_id", "enabled"])

    op.create_table(
        "public_api_webhook_deliveries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("subscription_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_status_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        # Chong gui trung: mot su kien cho mot subscription dung mot lan.
        sa.UniqueConstraint("subscription_id", "event_id",
                            name="uq_public_api_webhook_event"),
    )
    op.create_index("ix_public_api_webhook_deliveries_subscription_id",
                    "public_api_webhook_deliveries", ["subscription_id"])
    op.create_index("ix_public_api_webhook_deliveries_user_id",
                    "public_api_webhook_deliveries", ["user_id"])
    op.create_index("ix_public_api_webhook_deliveries_job_id",
                    "public_api_webhook_deliveries", ["job_id"])
    op.create_index("ix_public_api_webhook_deliveries_status",
                    "public_api_webhook_deliveries", ["status"])
    op.create_index("ix_public_api_webhook_due", "public_api_webhook_deliveries",
                    ["status", "next_attempt_at"])


def downgrade() -> None:
    op.drop_index("ix_public_api_webhook_due",
                  table_name="public_api_webhook_deliveries")
    op.drop_index("ix_public_api_webhook_deliveries_status",
                  table_name="public_api_webhook_deliveries")
    op.drop_index("ix_public_api_webhook_deliveries_job_id",
                  table_name="public_api_webhook_deliveries")
    op.drop_index("ix_public_api_webhook_deliveries_user_id",
                  table_name="public_api_webhook_deliveries")
    op.drop_index("ix_public_api_webhook_deliveries_subscription_id",
                  table_name="public_api_webhook_deliveries")
    op.drop_table("public_api_webhook_deliveries")
    op.drop_index("ix_public_api_webhooks_owner", table_name="public_api_webhooks")
    op.drop_index("ix_public_api_webhooks_user_id", table_name="public_api_webhooks")
    op.drop_table("public_api_webhooks")
