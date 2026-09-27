# -*- coding: utf-8 -*-
"""PROMPT AI OMMI pha 3 -- brief, canh, iteration, nhan vat; ommi_scene.canh_id.

Revision ID: ec6f58abae71
Revises: b7e21f9a4c68
Create Date: 2026-09-27

## VI SAO CO MIGRATION NAY

Brief ra khoi `AppProject.payload` thanh thuc the CSDL rieng (`ommi_brief`),
them vong lap iterate co 2 luot mien phi dem trong CSDL (`ommi_iteration`),
va gop buoc khoa nhan vat cua `apps/prompt_canh` vao PROMPT AI (`ommi_character`
va cac bang lien quan). `ommi_canh` la CANH KICH BAN -- nguon chan ly duy nhat
cua prompt di ra ngoai (spec S-1); `ommi_scene` van la KHUNG HINH storyboard,
them `canh_id` de noi hai thu cung ten "canh" voi nhau (spec S-2).

## ROLLBACK

`downgrade()` DROP tat ca bang moi va bo cot `canh_id` khoi `ommi_scene`. Cac
bang nay hoan toan moi (khong co du lieu san xuat nao phu thuoc truoc migration
nay), nen mat du lieu khi downgrade khong anh huong gi khac ngoai pha 3.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ec6f58abae71"
down_revision = "b7e21f9a4c68"
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "ommi_brief",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("story_vi", sa.Text(), nullable=False, server_default=""),
        sa.Column("goal", sa.String(300), nullable=False, server_default=""),
        sa.Column("audience", sa.String(300), nullable=False, server_default=""),
        sa.Column("target_duration_sec", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("target_scenes", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("aspect_ratio", sa.String(8), nullable=False, server_default="16:9"),
        sa.Column("language", sa.String(8), nullable=False, server_default="vi"),
        sa.Column("style_id", sa.String(36), nullable=True),
        sa.Column("meta_prompt_id", sa.String(36), nullable=True),
        sa.Column("character_id", sa.String(36), nullable=True),
        sa.Column("background_id", sa.String(36), nullable=True),
        sa.Column("referenced_variants", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("free_iterations_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("archived_at", _TS, nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_brief_owner_id", "ommi_brief", ["owner_id"])
    op.create_index("ix_ommi_brief_project_id", "ommi_brief", ["project_id"])

    op.create_table(
        "ommi_canh",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("brief_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("negative_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("camera", sa.Text(), nullable=False, server_default=""),
        sa.Column("lighting", sa.Text(), nullable=False, server_default=""),
        sa.Column("mood", sa.Text(), nullable=False, server_default=""),
        sa.Column("continuity", sa.Text(), nullable=False, server_default=""),
        sa.Column("selected_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("brief_id", "position", name="uq_ommi_canh_vitri"),
    )
    op.create_index("ix_ommi_canh_brief_id", "ommi_canh", ["brief_id"])

    op.create_table(
        "ommi_iteration",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("brief_id", sa.String(36), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt_sent", sa.Text(), nullable=False, server_default=""),
        sa.Column("output", sa.Text(), nullable=False, server_default=""),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("credit_charged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("was_free", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verdict", sa.String(10), nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("brief_id", "seq", name="uq_ommi_iteration_seq"),
    )
    op.create_index("ix_ommi_iteration_brief_id", "ommi_iteration", ["brief_id"])

    op.create_table(
        "ommi_character",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("gender", sa.String(32), nullable=False, server_default=""),
        sa.Column("age_range", sa.String(32), nullable=False, server_default=""),
        sa.Column("face_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("body_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("hair_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("outfit_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("personality", sa.Text(), nullable=False, server_default=""),
        sa.Column("expression_style", sa.Text(), nullable=False, server_default=""),
        sa.Column("movement_style", sa.Text(), nullable=False, server_default=""),
        sa.Column("fixed_prompt_block", sa.Text(), nullable=False, server_default=""),
        sa.Column("negative_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("reference_variant_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("archived_at", _TS, nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_character_owner_id", "ommi_character", ["owner_id"])

    op.create_table(
        "ommi_outfit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("character_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("reference_variant_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_outfit_character_id", "ommi_outfit", ["character_id"])

    op.create_table(
        "ommi_pose",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("pose_block", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("reference_variant_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_pose_owner_id", "ommi_pose", ["owner_id"])

    op.create_table(
        "ommi_background",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("location_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("environment_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("lighting_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("color_palette", sa.String(200), nullable=False, server_default=""),
        sa.Column("camera_feel", sa.String(200), nullable=False, server_default=""),
        sa.Column("important_objects", sa.Text(), nullable=False, server_default=""),
        sa.Column("fixed_prompt_block", sa.Text(), nullable=False, server_default=""),
        sa.Column("negative_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("reference_variant_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("archived_at", _TS, nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_background_owner_id", "ommi_background", ["owner_id"])

    op.create_table(
        "ommi_face_embedding",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("character_id", sa.String(36), nullable=False),
        sa.Column("variant_id", sa.String(36), nullable=False),
        sa.Column("vector_json", sa.JSON(), nullable=False),
        sa.Column("backend", sa.String(32), nullable=False),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_face_embedding_character_id", "ommi_face_embedding",
                    ["character_id"])

    op.add_column("ommi_scene", sa.Column("canh_id", sa.String(36), nullable=True))
    op.create_index("ix_ommi_scene_canh_id", "ommi_scene", ["canh_id"])


def downgrade() -> None:
    op.drop_index("ix_ommi_scene_canh_id", table_name="ommi_scene")
    op.drop_column("ommi_scene", "canh_id")

    op.drop_index("ix_ommi_face_embedding_character_id", table_name="ommi_face_embedding")
    op.drop_table("ommi_face_embedding")

    op.drop_index("ix_ommi_background_owner_id", table_name="ommi_background")
    op.drop_table("ommi_background")

    op.drop_index("ix_ommi_pose_owner_id", table_name="ommi_pose")
    op.drop_table("ommi_pose")

    op.drop_index("ix_ommi_outfit_character_id", table_name="ommi_outfit")
    op.drop_table("ommi_outfit")

    op.drop_index("ix_ommi_character_owner_id", table_name="ommi_character")
    op.drop_table("ommi_character")

    op.drop_index("ix_ommi_iteration_brief_id", table_name="ommi_iteration")
    op.drop_table("ommi_iteration")

    op.drop_index("ix_ommi_canh_brief_id", table_name="ommi_canh")
    op.drop_table("ommi_canh")

    op.drop_index("ix_ommi_brief_project_id", table_name="ommi_brief")
    op.drop_index("ix_ommi_brief_owner_id", table_name="ommi_brief")
    op.drop_table("ommi_brief")
