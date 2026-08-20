"""nexus: cot paid_until cho thue bao theo may/thang (Q98, Phase 5)

Them mot cot NULLABLE vao `nexus_devices`: thue bao tra toi luc nao. NULL = chua
tra thang nao. Migration khong lam vo dong nao (bang co the da co thiet bi).

Chi them, khong xoa du lieu.

Revision ID: 455d0097906f
Revises: 7445f5031805
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "455d0097906f"
down_revision = "7445f5031805"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nexus_devices", sa.Column(
        "paid_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("nexus_devices", "paid_until")
