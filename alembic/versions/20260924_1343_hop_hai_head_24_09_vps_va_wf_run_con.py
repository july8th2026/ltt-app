"""hop hai head 24/09: ban sua VPS (upload_sessions_bigint) va wf_run_con

Hai head cung ton tai tren `main` chieu 24/09/2026 ⇒ `alembic upgrade head` tu
choi chay, tuc MOI deploy bi chan. Revision nay chi hop hai nhanh lai; no khong
doi luoc do nao.

Revision ID: 3b1a2e203c41
Revises: b06f7b03870a, b7d2e9c41a03
Create Date: 2026-09-24 13:43:40.630468
"""
from __future__ import annotations

revision = "3b1a2e203c41"
down_revision = ("b06f7b03870a", "b7d2e9c41a03")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Khong co gi de lam: day la mot nut hop nhanh."""


def downgrade() -> None:
    """Khong co gi de lui: day la mot nut hop nhanh."""
