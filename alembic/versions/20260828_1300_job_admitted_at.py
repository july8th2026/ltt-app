"""H41.9/Q3: durable job admission timestamp.

Revision ID: e83b5d7c1a40
Revises: d70a3c4e9f62
"""
from alembic import op
import sqlalchemy as sa

revision = "e83b5d7c1a40"
down_revision = "d70a3c4e9f62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs", sa.Column("admitted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "admitted_at")
