"""H41.9/Q114: common execution lease for async, sync and stream.

Revision ID: c6f92a3b8d51
Revises: b5e81f2a7c40
"""
from alembic import op
import sqlalchemy as sa

revision = "c6f92a3b8d51"
down_revision = "b5e81f2a7c40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_leases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("resource", sa.String(length=96), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("holder_id", sa.String(length=128), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "resource", "slot", name="uq_execution_lease_resource_slot"),
    )
    op.create_index(
        "ix_execution_leases_resource_heartbeat", "execution_leases",
        ["resource", "heartbeat_at"])
    op.create_index(
        "ix_execution_leases_heartbeat_at", "execution_leases", ["heartbeat_at"])
    op.create_index(
        "ix_execution_leases_user_id", "execution_leases", ["user_id"])
    op.create_index(
        "ix_execution_leases_job_id", "execution_leases", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_execution_leases_job_id", table_name="execution_leases")
    op.drop_index("ix_execution_leases_user_id", table_name="execution_leases")
    op.drop_index("ix_execution_leases_heartbeat_at", table_name="execution_leases")
    op.drop_index(
        "ix_execution_leases_resource_heartbeat", table_name="execution_leases")
    op.drop_table("execution_leases")
