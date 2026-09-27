# -*- coding: utf-8 -*-
"""PROMPT AI OMMI Pha 2: `ommi_handoff` — ve giao bai dung mot lan, 30 phut.

Payload da renumber (@IMG_k/@VID_k), da inline anh, da qua bat bien bien
`bat_bien_giao_bai()` (Pha 1) truoc khi ghi. `used_at` khac NULL = ve da dung,
tu choi doc lan hai. Khong co cot `owner_id`: quyen so huu kiem qua
`project_id` (join sang `AppProject` cua nen tang), khong lap lai o day.

Revision ID: b7e21f9a4c68
Revises: a4f0c9b21ee3
Create Date: 2026-09-26 15:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e21f9a4c68"
down_revision: Union[str, None] = "a4f0c9b21ee3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ommi_handoff",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("scene_id", sa.String(36), nullable=False),
        sa.Column("target_app_slug", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ommi_handoff_project_id", "ommi_handoff", ["project_id"])
    op.create_index("ix_ommi_handoff_owner_id", "ommi_handoff", ["owner_id"])
    op.create_index("ix_ommi_handoff_scene_id", "ommi_handoff", ["scene_id"])
    op.create_index("ix_ommi_handoff_expires_at", "ommi_handoff", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_ommi_handoff_expires_at", table_name="ommi_handoff")
    op.drop_index("ix_ommi_handoff_scene_id", table_name="ommi_handoff")
    op.drop_index("ix_ommi_handoff_project_id", table_name="ommi_handoff")
    op.drop_table("ommi_handoff")
