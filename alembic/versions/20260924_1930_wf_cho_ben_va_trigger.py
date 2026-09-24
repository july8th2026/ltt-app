"""waitpoint: han cho + che do het han; workflow_trigger: version/cursor/loi

Revision ID: c4a17f9b6d20
Revises: b06f7b03870a, b7d2e9c41a03
Create Date: 2026-09-24

⭐ HAI `down_revision`, va do la CHU Y, khong phai mot tai nan.

`main` dang co HAI head: `b06f7b03870a` (hop hai head upload_sessions) va
`b7d2e9c41a03` (wf_run_con cua lan P3) — ca hai deu moc tu `8f1c6a4d2b90`.
`tests/test_103_autosub_projects.py::test_platform_migrations_have_a_single_head`
(va bon test cung luat khac) dang DO vi dieu do. Ban ghi nay noi hai nhanh lai,
nen chuoi migration co MOT head tro lai.

⛔ Khong `alembic stamp`, khong `create_all`: doi voi PostgreSQL that day la
   mot lenh `ALTER TABLE ... ADD COLUMN` co `server_default` — tren
   PostgreSQL >= 11 la thao tac CHI SUA CATALOG, khong viet lai bang. Ca hai
   bang deu dang chay that.

Chi so `ix_waitpoint_het_han` la `(het_han_luc, id)` chu khong phai
`(het_han_luc)`: bo quet het han di bang KEYSET CURSOR
(`cho_doi.quet_het_han`), va mot dieu kien `(a, id) > (:a, :id)` chi dung duoc
chi so khi chi so mang dung hai cot do theo dung thu tu.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4a17f9b6d20"
down_revision: Union[str, Sequence[str], None] = ("b06f7b03870a",
                                                  "b7d2e9c41a03")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("waitpoint", sa.Column(
        "het_han_luc", sa.DateTime(timezone=True), nullable=True))
    op.add_column("waitpoint", sa.Column(
        "che_do_het_han", sa.String(length=16), nullable=False,
        server_default="fail"))
    op.create_index(
        "ix_waitpoint_het_han", "waitpoint", ["het_han_luc", "id"],
        postgresql_where=sa.text(
            "status = 'PENDING' AND het_han_luc IS NOT NULL"),
        sqlite_where=sa.text("status = 'PENDING' AND het_han_luc IS NOT NULL"))

    op.add_column("workflow_trigger", sa.Column(
        "version_mode", sa.String(length=16), nullable=False,
        server_default="published"))
    op.add_column("workflow_trigger", sa.Column(
        "pinned_version_id", sa.String(length=36), nullable=False,
        server_default=""))
    op.add_column("workflow_trigger", sa.Column(
        "con_tro", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("workflow_trigger", sa.Column(
        "last_fired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("workflow_trigger", sa.Column(
        "loi_lien_tiep", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("workflow_trigger", "loi_lien_tiep")
    op.drop_column("workflow_trigger", "last_fired_at")
    op.drop_column("workflow_trigger", "con_tro")
    op.drop_column("workflow_trigger", "pinned_version_id")
    op.drop_column("workflow_trigger", "version_mode")
    op.drop_index("ix_waitpoint_het_han", table_name="waitpoint")
    op.drop_column("waitpoint", "che_do_het_han")
    op.drop_column("waitpoint", "het_han_luc")
