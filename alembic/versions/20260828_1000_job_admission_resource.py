"""H41.9/Q114: snapshot admission resource on durable jobs.

Revision ID: b5e81f2a7c40
Revises: a4d70e93f158
"""
from alembic import op
import sqlalchemy as sa

revision = "b5e81f2a7c40"
down_revision = "a4d70e93f158"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column(
        "admission_resource", sa.String(length=96),
        nullable=False, server_default=""))
    op.add_column("jobs", sa.Column(
        "admission_slots", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_jobs_admission_resource", "jobs", ["admission_resource"])
    op.create_index(
        "ix_jobs_admission_queue", "jobs",
        ["admission_resource", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_admission_queue", table_name="jobs")
    op.drop_index("ix_jobs_admission_resource", table_name="jobs")
    op.drop_column("jobs", "admission_slots")
    op.drop_column("jobs", "admission_resource")
