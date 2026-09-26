# -*- coding: utf-8 -*-
"""PROMPT AI OMMI pha 1 — bang ommi_binding (nguon chan ly the <-> variant).

Revision ID: a4f0c9b21ee3
Revises: edb8b0fc0ac9
Create Date: 2026-09-26

## VI SAO CO BANG NAY

So the (`@IMAGE_1`...) truoc day duoc DEM LAI moi lan build prompt
(`composer.resource_lines`) va dem KHAC DI luc build refs giao bai — hai lan
dem doc lap troi khoi nhau khong ai biet (N-2, xem
docs/PROMPT_AI/DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md). Tu nay CHI
`services/bindings.py` duoc ghi bang nay; noi khac chi DOC.

## ROLLBACK

`downgrade()` DROP bang. Bang nay hoan toan moi (khong co du lieu san xuat
nao phu thuoc no truoc migration nay), nen mat du lieu khi downgrade la
nguoi dung phai gan lai binding — khong anh huong file da luu tren Storage.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a4f0c9b21ee3"
down_revision = "edb8b0fc0ac9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ommi_binding",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("scene_id", sa.String(36), nullable=True),
        sa.Column("tag", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("variant_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("role", sa.String(24), nullable=False,
                  server_default="reference_image"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("project_id", "scene_id", "tag",
                            name="uq_ommi_binding_tag"),
    )
    op.create_index("ix_ommi_binding_owner_id", "ommi_binding", ["owner_id"])
    op.create_index("ix_ommi_binding_project_id", "ommi_binding", ["project_id"])
    op.create_index("ix_ommi_binding_scene_id", "ommi_binding", ["scene_id"])
    op.create_index("ix_ommi_binding_variant_id", "ommi_binding", ["variant_id"])


def downgrade() -> None:
    op.drop_index("ix_ommi_binding_variant_id", table_name="ommi_binding")
    op.drop_index("ix_ommi_binding_scene_id", table_name="ommi_binding")
    op.drop_index("ix_ommi_binding_project_id", table_name="ommi_binding")
    op.drop_index("ix_ommi_binding_owner_id", table_name="ommi_binding")
    op.drop_table("ommi_binding")
