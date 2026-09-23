"""wf v2: workflow_event, waitpoint.so_nguon, status CREATED, snapshot bat bien.

Revision ID: e02cebbbd57a
Revises: e4a19c07b5d2
Create Date: 2026-09-22

Luoc do cho dong co V2 (`23_24` -> `2026-09-22-wf-v2-01a-dong-co` Task 2):

  workflow_event      nhat ky cap RUN, CHI THEM (spec Sec5.11). Cung la outbox
                       cho trigger `event` (spec Sec8.4). `UNIQUE(run_id, seq)`
                       khu trung, khong the co hai su kien cung so thu tu.
  waitpoint.so_nguon   so nguon (canh vao) cua mot BARRIER (spec Sec5.7).
  workflow_run.status  mac dinh doi tu "queued" sang "CREATED" (Task 1 da doi o
                       models.py; migration nay don du lieu CU: hang dang
                       "queued" -> "CREATED", hang dang "VALIDATING" (trang
                       thai V2 da bo) -> "QUEUED".
  node_run_snapshot    CHI THEM (spec Sec5.3) — chan o CSDL bang trigger
                       Postgres (chan UPDATE, khong chan DELETE: DELETE danh
                       cho don theo TTL). SQLite khong co trigger o day; bat
                       buoc chi-them o SQLite do listener SQLAlchemy
                       `before_flush` trong `platform_core/models.py`
                       (`SnapshotBatBien`).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "e02cebbbd57a"
down_revision = "e4a19c07b5d2"
branch_labels = None
depends_on = None

_HAM = """
CREATE OR REPLACE FUNCTION wf_snapshot_bat_bien() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'node_run_snapshot la chi-them (spec 5.3)';
END; $$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.create_table(
        "workflow_event",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("loai", sa.String(40), nullable=False),
        sa.Column("node_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("du_lieu", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "seq", name="ux_workflow_event_seq"),
    )
    op.create_index("ix_workflow_event_run_id", "workflow_event", ["run_id"])
    op.create_index("ix_workflow_event_created_at", "workflow_event",
                    ["created_at"])

    with op.batch_alter_table("waitpoint") as b:
        b.add_column(sa.Column("so_nguon", sa.Integer(), nullable=False,
                               server_default="0"))

    op.execute("UPDATE workflow_run SET status='CREATED' WHERE status='queued'")
    op.execute("UPDATE workflow_run SET status='QUEUED' "
               "WHERE status='VALIDATING'")

    if op.get_bind().dialect.name == "postgresql":
        op.execute(_HAM)
        # Chi chan UPDATE: DELETE danh cho don theo TTL (spec Sec5.11).
        op.execute("CREATE TRIGGER trg_wf_snapshot_bat_bien BEFORE UPDATE "
                   "ON node_run_snapshot FOR EACH ROW "
                   "EXECUTE FUNCTION wf_snapshot_bat_bien()")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_wf_snapshot_bat_bien "
                   "ON node_run_snapshot")
        op.execute("DROP FUNCTION IF EXISTS wf_snapshot_bat_bien()")

    op.execute("UPDATE workflow_run SET status='queued' WHERE status='CREATED'")

    with op.batch_alter_table("waitpoint") as b:
        b.drop_column("so_nguon")

    op.drop_index("ix_workflow_event_created_at", table_name="workflow_event")
    op.drop_index("ix_workflow_event_run_id", table_name="workflow_event")
    op.drop_table("workflow_event")
