"""PROMPT AI OMMI: kho tai nguyen va thu vien prompt rieng theo nguoi dung

Bang dau tien do MOT APP so huu (apps/prompt_ai_ommi/tables.py) thay vi nam
trong platform_core. Moi bang mang tien to `ommi_` theo MANIFEST.table_prefix.

Mo hinh so huu: `owner_id` co gia tri = rieng tu; `owner_id` NULL = mau catalog
do admin publish, moi nguoi chi doc. Khong co namespace dung chung.

Revision ID: a1b2c3d4e5f7
Revises: f6a7b8c9d0e1
Create Date: 2026-08-05 19:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ommi_resource",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("cover_variant_id", sa.String(36), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ommi_resource_owner_id", "ommi_resource", ["owner_id"])
    op.create_index("ix_ommi_resource_kind", "ommi_resource", ["kind"])
    op.create_index("ix_ommi_resource_owner_kind", "ommi_resource",
                    ["owner_id", "kind", "archived_at"])

    op.create_table(
        "ommi_resource_variant",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("thumb_key", sa.String(512), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("bytes_size", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ommi_resource_variant_resource_id",
                    "ommi_resource_variant", ["resource_id"])
    op.create_index("ix_ommi_resource_variant_owner_id",
                    "ommi_resource_variant", ["owner_id"])

    op.create_table(
        "ommi_tag",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "name", name="uq_ommi_tag_owner_name"))
    op.create_index("ix_ommi_tag_owner_id", "ommi_tag", ["owner_id"])

    op.create_table(
        "ommi_resource_tag",
        sa.Column("resource_id", sa.String(36), primary_key=True),
        sa.Column("tag_id", sa.String(36), primary_key=True))

    op.create_table(
        "ommi_collection",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ommi_collection_owner_id", "ommi_collection", ["owner_id"])

    op.create_table(
        "ommi_collection_item",
        sa.Column("collection_id", sa.String(36), primary_key=True),
        sa.Column("resource_id", sa.String(36), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False))

    op.create_table(
        "ommi_resource_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("scene_ref", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("resource_id", "project_id", "scene_ref",
                            name="uq_ommi_usage_resource_project_scene"))
    op.create_index("ix_ommi_resource_usage_resource_id",
                    "ommi_resource_usage", ["resource_id"])
    op.create_index("ix_ommi_resource_usage_owner_id",
                    "ommi_resource_usage", ["owner_id"])
    op.create_index("ix_ommi_resource_usage_project_id",
                    "ommi_resource_usage", ["project_id"])

    op.create_table(
        "ommi_meta_prompt",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("variables", sa.JSON(), nullable=False),
        sa.Column("is_catalog", sa.Boolean(), nullable=False),
        sa.Column("cloned_from_id", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ommi_meta_prompt_owner_id", "ommi_meta_prompt", ["owner_id"])
    op.create_index("ix_ommi_meta_prompt_purpose", "ommi_meta_prompt", ["purpose"])

    op.create_table(
        "ommi_prompt_snippet",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_catalog", sa.Boolean(), nullable=False),
        sa.Column("cloned_from_id", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ommi_prompt_snippet_owner_id",
                    "ommi_prompt_snippet", ["owner_id"])

    op.create_table(
        "ommi_prompt_version",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("target_kind", sa.String(16), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("note", sa.String(300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("target_kind", "target_id", "version",
                            name="uq_ommi_prompt_version_target"))
    op.create_index("ix_ommi_prompt_version_owner_id",
                    "ommi_prompt_version", ["owner_id"])
    op.create_index("ix_ommi_prompt_version_target_id",
                    "ommi_prompt_version", ["target_id"])

    op.create_table(
        "ommi_style",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("negative", sa.Text(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("is_catalog", sa.Boolean(), nullable=False),
        sa.Column("cloned_from_id", sa.String(36), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ommi_style_owner_id", "ommi_style", ["owner_id"])


def downgrade() -> None:
    for table in ("ommi_style", "ommi_prompt_version", "ommi_prompt_snippet",
                  "ommi_meta_prompt", "ommi_resource_usage",
                  "ommi_collection_item", "ommi_collection",
                  "ommi_resource_tag", "ommi_tag", "ommi_resource_variant",
                  "ommi_resource"):
        op.drop_table(table)
