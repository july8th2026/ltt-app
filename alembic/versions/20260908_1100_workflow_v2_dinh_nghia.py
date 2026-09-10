"""LTT WORKFLOW V2 · Dot 2.1 — bang dinh nghia workflow.

Revision ID: a4f81c2d6b95
Revises: e7b2c94a1d38
Create Date: 2026-09-08

## VI SAO NAM BANG MOI THAY VI MO RONG `agent_workflows`

Bang cu tron BA thu vao mot hang: ban dang soan (sua duoc), ban dang chay (phai
bat bien), va phong chieu thi hanh. Ba vong doi khac nhau trong mot hang la ly
do khong the ghim mot luot chay vao dung noi dung no khoi dong cung — sua
workflow luc 10:00 thi luot chay bat dau 09:58 doi theo.

  workflow          danh tinh
  workflow_draft    SUA DUOC   · khoa lac quan `revision`
  workflow_version  BAT BIEN   · `graph` + `graph_hash` + `estimated_max`
  workflow_version_node / _edge   chi muc DAN XUAT, sinh tai `xuat_ban()`

## ⭐ HAI RANG BUOC LA THIET KE, KHONG PHAI TRANG TRI

  UNIQUE (workflow_id, seq)          so thu tu hien cho nguoi, khong nhay coc
  UNIQUE (workflow_id, graph_hash)   xuat ban trung noi dung -> TRA VE BAN CU

Ve thu hai khien "xuat ban hai lan cung noi dung" thanh **khong the**, bang
rang buoc CSDL chu khong bang ma can than. Ba he doc lap da hoi tu ve dung
khuon nay (`docs/architecture/workflow_v2_audit/12_19 muc 16`):

    Activepieces   UNIQUE(flowRunId, stepName)
    n8n            UNIQUE(deduplicationKey) WHERE ... IS NOT NULL
    Trigger.dev    UNIQUE(environmentId, idempotencyKey)

`platform_core/workflow/dinh_nghia.py:xuat_ban` co mot `SELECT` truoc INSERT,
nhung do chi la duong di thuong. Hai request song song van bi CSDL chan — dung
bai hoc cua `c9d4e1a77b02`.

## AN TOAN

Chi CREATE TABLE moi. Khong doi cot nao dang co, khong cham du lieu nao dang
co, khong nam trong duong chay nao — Dot 2 chua noi vao gi (`27_29 §28`).
`downgrade()` do duoc: cac bang deu rong cho toi Dot 3.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a4f81c2d6b95"
down_revision = "e7b2c94a1d38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        # Rong co chu y: ten mac dinh do tang service dat qua `N_()` de bo
        # trich dich thay duoc. Mot `server_default` tieng Viet o day la mot
        # chuoi giao dien nam ngoai tam voi cua i18n.
        sa.Column("name", sa.String(160), nullable=False, server_default=""),
        sa.Column("published_version_id", sa.String(36), nullable=False,
                  server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_workflow_owner_id", "workflow", ["owner_id"])
    op.create_index("ix_workflow_owner_updated", "workflow",
                    ["owner_id", "updated_at"])

    op.create_table(
        "workflow_draft",
        sa.Column("workflow_id", sa.String(36), primary_key=True),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "workflow_version",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workflow_id", sa.String(36), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("graph", sa.JSON(), nullable=False),
        sa.Column("graph_hash", sa.String(64), nullable=False),
        sa.Column("estimated_max", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False,
                  server_default=""),
        sa.UniqueConstraint("workflow_id", "seq",
                            name="uq_workflow_version_seq"),
        sa.UniqueConstraint("workflow_id", "graph_hash",
                            name="uq_workflow_version_hash"),
    )
    op.create_index("ix_workflow_version_workflow_id", "workflow_version",
                    ["workflow_id"])

    op.create_table(
        "workflow_version_node",
        sa.Column("version_id", sa.String(36), primary_key=True),
        sa.Column("node_id", sa.String(64), primary_key=True),
        sa.Column("node_type", sa.String(96), nullable=False),
        sa.Column("type_version", sa.Integer(), nullable=False,
                  server_default="1"),
    )
    op.create_index("ix_wvn_type", "workflow_version_node", ["node_type"])

    op.create_table(
        "workflow_version_edge",
        sa.Column("version_id", sa.String(36), primary_key=True),
        sa.Column("edge_id", sa.String(64), primary_key=True),
        sa.Column("source_node", sa.String(64), nullable=False),
        sa.Column("source_port", sa.String(64), nullable=False,
                  server_default=""),
        sa.Column("target_node", sa.String(64), nullable=False),
        sa.Column("target_port", sa.String(64), nullable=False,
                  server_default=""),
        sa.Column("kind", sa.String(16), nullable=False, server_default="DATA"),
        sa.Column("condition", sa.JSON(), nullable=False),
    )
    op.create_index("ix_wve_version", "workflow_version_edge", ["version_id"])


def downgrade() -> None:
    op.drop_index("ix_wve_version", table_name="workflow_version_edge")
    op.drop_table("workflow_version_edge")
    op.drop_index("ix_wvn_type", table_name="workflow_version_node")
    op.drop_table("workflow_version_node")
    op.drop_index("ix_workflow_version_workflow_id",
                  table_name="workflow_version")
    op.drop_table("workflow_version")
    op.drop_table("workflow_draft")
    op.drop_index("ix_workflow_owner_updated", table_name="workflow")
    op.drop_index("ix_workflow_owner_id", table_name="workflow")
    op.drop_table("workflow")
