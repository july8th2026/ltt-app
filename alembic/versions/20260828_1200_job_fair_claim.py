"""H41.9/Q2: durable per-account fair claim cursor.

Revision ID: d70a3c4e9f62
Revises: c6f92a3b8d51
"""
from alembic import op
import sqlalchemy as sa

revision = "d70a3c4e9f62"
down_revision = "c6f92a3b8d51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs", sa.Column("last_claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "jobs", sa.Column("provider_state", sa.String(length=16),
                          nullable=False, server_default=""))
    op.add_column(
        "jobs", sa.Column("provider_dispatched_at", sa.DateTime(timezone=True),
                          nullable=True))
    op.create_index(
        "ix_jobs_fairness", "jobs",
        ["admission_resource", "user_id", "last_claimed_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_fairness", table_name="jobs")
    op.drop_column("jobs", "provider_dispatched_at")
    op.drop_column("jobs", "provider_state")
    op.drop_column("jobs", "last_claimed_at")
