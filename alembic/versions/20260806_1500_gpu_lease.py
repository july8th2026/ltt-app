"""H23: bang giu cho GPU (gpu_leases)

Revision ID: c3d4e5f6a2b3
Revises: b2c3d4e5f8a1
Create Date: 2026-08-06 15:00:00.000000

Rang buoc UNIQUE(host, gpu_uuid) la TRAI TIM cua co che: no bien viec gianh GPU
thanh nguyen tu. Hai worker cung INSERT mot GPU thi CSDL cho dung mot cai thang.
Bo rang buoc nay di thi ca co che vo nghia - hai job se cung nap model len mot
card roi OOM. Xem platform_core/gpu_lease.py.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a2b3"
down_revision: Union[str, None] = "b2c3d4e5f8a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gpu_leases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("host", sa.String(length=128), nullable=False),
        sa.Column("gpu_uuid", sa.String(length=64), nullable=False),
        sa.Column("gpu_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("worker_id", sa.String(length=128), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("vram_mb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host", "gpu_uuid", name="uq_gpu_lease_host_uuid"),
    )
    op.create_index("ix_gpu_leases_job_id", "gpu_leases", ["job_id"])
    op.create_index("ix_gpu_leases_heartbeat_at", "gpu_leases", ["heartbeat_at"])


def downgrade() -> None:
    op.drop_index("ix_gpu_leases_heartbeat_at", table_name="gpu_leases")
    op.drop_index("ix_gpu_leases_job_id", table_name="gpu_leases")
    op.drop_table("gpu_leases")
