"""them timeline va debug event cho job

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("correlation_id", sa.String(36),
                                    nullable=False, server_default=""))
    op.add_column("jobs", sa.Column("retry_of_id", sa.String(36),
                                    nullable=False, server_default=""))
    op.add_column("jobs", sa.Column("event_sequence", sa.Integer(),
                                    nullable=False, server_default="0"))
    # Job cũ cũng cần mã support ổn định; chính UUID job đã đủ duy nhất và không
    # lộ dữ liệu khách. Job mới do ORM sinh correlation UUID riêng.
    op.execute("UPDATE jobs SET correlation_id = id WHERE correlation_id = ''")
    op.create_index("ix_jobs_correlation_id", "jobs", ["correlation_id"])
    op.create_index("ix_jobs_retry_of_id", "jobs", ["retry_of_id"])

    op.create_table(
        "job_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("app_slug", sa.String(64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_code", sa.String(48), nullable=False),
        sa.Column("level", sa.String(12), nullable=False),
        sa.Column("visibility", sa.String(12), nullable=False),
        sa.Column("public_message", sa.String(255), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("event_key", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "event_key", name="uq_job_events_job_event_key"),
        sa.UniqueConstraint("job_id", "sequence", name="uq_job_events_job_sequence"),
    )
    op.create_index("ix_job_events_job_sequence", "job_events", ["job_id", "sequence"])
    op.create_index("ix_job_events_user_app_created", "job_events",
                    ["user_id", "app_slug", "created_at"])
    op.create_index("ix_job_events_visibility_created", "job_events",
                    ["visibility", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_job_events_visibility_created", table_name="job_events")
    op.drop_index("ix_job_events_user_app_created", table_name="job_events")
    op.drop_index("ix_job_events_job_sequence", table_name="job_events")
    op.drop_table("job_events")
    op.drop_index("ix_jobs_retry_of_id", table_name="jobs")
    op.drop_index("ix_jobs_correlation_id", table_name="jobs")
    op.drop_column("jobs", "event_sequence")
    op.drop_column("jobs", "retry_of_id")
    op.drop_column("jobs", "correlation_id")
