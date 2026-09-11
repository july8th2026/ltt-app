"""Scheduler V1: durable origin/priority envelope and ranking indexes.

Revision ID: e26c9a41d8b5
Revises: d15b8c30f7a4
Create Date: 2026-09-10

Both server defaults are fail-closed. During a rolling or mixed-tree interval,
an old writer can create a row without the new fields and it remains external;
it can never accidentally acquire trusted internal priority.
"""
from alembic import op
import sqlalchemy as sa

revision = "e26c9a41d8b5"
down_revision = "d15b8c30f7a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column(
        "origin", sa.String(length=24), nullable=False,
        server_default="unknown"))
    op.add_column("jobs", sa.Column(
        "priority_class", sa.String(length=16), nullable=False,
        server_default="external"))
    op.create_index(
        "ix_jobs_scheduler_queue", "jobs",
        ["admission_resource", "status", "next_run_at", "priority_class",
         "created_at"])
    op.create_index(
        "ix_jobs_priority_fairness", "jobs",
        ["admission_resource", "priority_class", "user_id", "last_claimed_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_priority_fairness", table_name="jobs")
    op.drop_index("ix_jobs_scheduler_queue", table_name="jobs")
    op.drop_column("jobs", "priority_class")
    op.drop_column("jobs", "origin")

