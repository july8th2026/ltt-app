"""index tong hop cho cau truy van claim job (W2.6c)

Revision ID: c7d8e9f0a1b2
Revises: b1c2d3e4f5a6
Create Date: 2026-07-31 14:00:00.000000

claim() chay moi vong worker: WHERE status=? AND next_run_at<=? ORDER BY
created_at LIMIT 1. Khi bang jobs lon, khong co index dung se quet tuan tu.
Index tong hop (status, next_run_at, created_at) phuc vu dung cau nay.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_jobs_claim", "jobs",
                    ["status", "next_run_at", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_claim", table_name="jobs")
