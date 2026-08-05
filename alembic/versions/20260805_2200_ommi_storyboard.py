"""PROMPT AI OMMI: storyboard, canh va phien ban theo canh

Revision ID: b2c3d4e5f8a1
Revises: a1b2c3d4e5f7
Create Date: 2026-08-05 22:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f8a1"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ommi_storyboard",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("meta_prompt_id", sa.String(36), nullable=True),
        sa.Column("style_id", sa.String(36), nullable=True),
        sa.Column("aspect_ratio", sa.String(12), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ommi_storyboard_owner_id", "ommi_storyboard", ["owner_id"])
    op.create_index("ix_ommi_storyboard_project_id", "ommi_storyboard", ["project_id"])

    op.create_table(
        "ommi_scene",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("storyboard_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("camera", sa.String(200), nullable=False),
        sa.Column("continuity", sa.Text(), nullable=False),
        sa.Column("resource_ids", sa.JSON(), nullable=False),
        sa.Column("image_key", sa.String(512), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ommi_scene_owner_id", "ommi_scene", ["owner_id"])
    op.create_index("ix_ommi_scene_storyboard_id", "ommi_scene", ["storyboard_id"])
    op.create_index("ix_ommi_scene_board_position", "ommi_scene",
                    ["storyboard_id", "position"])

    op.create_table(
        "ommi_scene_version",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("scene_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("image_key", sa.String(512), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scene_id", "version", name="uq_ommi_scene_version"))
    op.create_index("ix_ommi_scene_version_owner_id", "ommi_scene_version", ["owner_id"])
    op.create_index("ix_ommi_scene_version_scene_id", "ommi_scene_version", ["scene_id"])


def downgrade() -> None:
    for table in ("ommi_scene_version", "ommi_scene", "ommi_storyboard"):
        op.drop_table(table)
