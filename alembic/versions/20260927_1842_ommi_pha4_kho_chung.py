# -*- coding: utf-8 -*-
"""Pha 4 PROMPT AI: kho chung + thu vien.

Them cot `share_level` (private/code/catalog) vao ommi_meta_prompt/
ommi_prompt_snippet/ommi_style; them target_format/is_default/placeholders vao
ommi_meta_prompt; them parent_id/provider_overrides vao ommi_style; tao 6 bang
moi: ommi_share_code, ommi_image_template, ommi_storyboard_framework,
ommi_sample, ommi_profile, ommi_budget.

Revision ID: b64a39da941d
Revises: ec6f58abae71
Create Date: 2026-09-27 18:42

## VI SAO MOT MIGRATION DUY NHAT CHO CA PHA (spec S9.1)

Moi pha dung MOT migration, khong chia nho theo lan, de khong co "nua pha" nam
giua hai revision roi rac. Lan M la chu duy nhat cua alembic/versions/.

## share_level: ommi_character/ommi_background/ommi_pose KHONG nam trong ALTER nay

Plan goc (2026-09-26) liet ke ca 6 bang (meta_prompt/snippet/style/character/
background/pose) vao mot `_SHARE_LEVEL_TABLES` de ALTER. Do that tren cay lam
viec (2026-09-27): migration Pha 3 (`20260927_0902_ommi_pha3.py`, head
`ec6f58abae71` - down_revision cua migration nay) DA tao ba bang character/
pose/background VOI cot share_level san co trong CREATE TABLE (Q-14, chu du
an chot 26/09 "van xay" du chua co khach dung). ALTER lai se loi "duplicate
column". Migration nay chi ALTER ba bang con thieu cot: ommi_meta_prompt,
ommi_prompt_snippet, ommi_style. Tong vao vay la du 10 bang co share_level
(3 ALTER o day + 3 da co tu Pha 3 + 4 bang moi tao o day).

## share_level KHONG THAY THE co che catalog cu (owner_id NULL)

`ommi_meta_prompt`/`ommi_prompt_snippet`/`ommi_style` da co catalog qua
owner_id IS NULL tu truoc (giu nguyen, khong dung toi). share_level la lop
THONG TIN THEM: ban ghi catalog (owner_id NULL) duoc gan share_level="catalog"
de dong bo tin hieu; ban ghi cua nguoi dung dung "code" khi ho tu chia se qua
ommi_share_code. Bang moi (ommi_image_template, ...) khong co owner_id NULL
(owner_id luon not null theo dung "moi bang" cua spec S4.2) nen voi CHUNG,
share_level="catalog" LA co che catalog duy nhat, phoi hop voi is_builtin=True.

## ommi_image_template.placeholders (bo sung 26/09, spec Sec 7.2)

Spec S4.2 lan sau (26/09) them cot `placeholders` (JSON, not null, default
list) vao ommi_image_template - do duoc tren ban sao Studio 21 mau dung mot bo
placeholder KHAC voi meta prompt ({SUBJECT}/{STYLE}/{EXTRA}/{EQUIPMENT}, xem
Sec 7.2). Ban nhap plan Task 3 (26/09) thieu cot nay - da vieng vao day va vao
model OmmiImageTemplate (tables/thu_vien.py) de khop spec.

## ommi_budget: bang khong co ORM model o Pha 4 (no lan nao trong plan so huu)

Bang duoc tao theo dung spec S4.2, nhung khong Task nao trong plan
`2026-09-26-prompt-ai-pha4-kho-chung.md` giao viec viet class ORM cho no (Task
10 chi lam image_template/storyboard_framework/sample/profile). Day la mot
"bang chet" tam thoi (co schema, chua ai doc/ghi) - ghi lai o day de dieu phoi
giao viec o pha sau, khong tu y tao tables/ngan_sach.py ngoai danh sach tep
duoc giao cua lan nay.

## ROLLBACK

downgrade() go het cot va bang da them. Mat du lieu share_level/is_default/
target_format/placeholders/placeholders(image_template) da nhap qua
nhap_mau_goc - phai chay lai nhap_mau_goc sau khi upgrade lai (no idempotent,
an toan chay lai).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b64a39da941d"
down_revision = "ec6f58abae71"
branch_labels = None
depends_on = None

# Chi ba bang CON THIEU cot share_level. ommi_character/ommi_background/
# ommi_pose da co cot nay tu migration Pha 3 - xem docstring o tren.
_SHARE_LEVEL_TABLES = ("ommi_meta_prompt", "ommi_prompt_snippet", "ommi_style")


def upgrade() -> None:
    for table_name in _SHARE_LEVEL_TABLES:
        op.add_column(table_name, sa.Column(
            "share_level", sa.String(12), nullable=False,
            server_default="private"))

    op.add_column("ommi_meta_prompt", sa.Column(
        "target_format", sa.String(24), nullable=False,
        server_default="gemini_style"))
    op.add_column("ommi_meta_prompt", sa.Column(
        "is_default", sa.Boolean(), nullable=False,
        server_default=sa.false()))
    op.add_column("ommi_meta_prompt", sa.Column(
        "placeholders", sa.JSON(), nullable=False, server_default="[]"))

    op.add_column("ommi_style", sa.Column(
        "parent_id", sa.String(36), nullable=True))
    op.add_column("ommi_style", sa.Column(
        "provider_overrides", sa.JSON(), nullable=False, server_default="{}"))

    op.create_table(
        "ommi_share_code",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(12), nullable=False, unique=True),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_share_code_owner_id", "ommi_share_code",
                    ["owner_id"])
    op.create_index("ix_ommi_share_code_code", "ommi_share_code", ["code"],
                    unique=True)
    op.create_index("ix_ommi_share_code_target", "ommi_share_code",
                    ["target_kind", "target_id"])

    op.create_table(
        "ommi_image_template",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("icon", sa.String(16), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("n_outputs", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("aspect", sa.String(8), nullable=False, server_default="1:1"),
        sa.Column("asset_type", sa.String(16), nullable=False),
        sa.Column("asset_subtype", sa.String(32), nullable=False, server_default=""),
        sa.Column("grid_layout", sa.String(16), nullable=False, server_default=""),
        sa.Column("output_mode", sa.String(16), nullable=False, server_default="grid"),
        sa.Column("requires_ref", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("multi_ref_max", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("bg_style", sa.String(64), nullable=False, server_default=""),
        sa.Column("negative_lock", sa.Text(), nullable=False, server_default=""),
        sa.Column("placeholder_hint", sa.String(200), nullable=False, server_default=""),
        # Bo sung 26/09 (spec Sec 7.2) - bo placeholder RIENG cua image
        # template ({SUBJECT}/{STYLE}/{EXTRA}/{EQUIPMENT}), khac bo cua meta
        # prompt. Thieu cot nay thi khong kiem duoc mau nao can bien gi.
        sa.Column("placeholders", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_image_template_owner_id", "ommi_image_template",
                    ["owner_id"])
    op.create_index("ix_ommi_image_template_asset_type", "ommi_image_template",
                    ["asset_type"])

    op.create_table(
        "ommi_storyboard_framework",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("icon", sa.String(16), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("composite_header", sa.Text(), nullable=False, server_default=""),
        sa.Column("composite_rules", sa.Text(), nullable=False, server_default=""),
        sa.Column("composite_negative_footer", sa.Text(), nullable=False, server_default=""),
        sa.Column("breakdown_llm_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("default_style_id", sa.String(36), nullable=True),
        sa.Column("default_aspect", sa.String(8), nullable=False, server_default="16:9"),
        sa.Column("default_n_scenes", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_storyboard_framework_owner_id",
                    "ommi_storyboard_framework", ["owner_id"])

    op.create_table(
        "ommi_sample",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("final_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("style_id", sa.String(36), nullable=True),
        sa.Column("meta_prompt_id", sa.String(36), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("rating_reasons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("used_model", sa.String(64), nullable=False, server_default=""),
        sa.Column("actual_credit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("iter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_sample_owner_id", "ommi_sample", ["owner_id"])

    op.create_table(
        "ommi_profile",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("style_id", sa.String(36), nullable=True),
        sa.Column("meta_prompt_id", sa.String(36), nullable=True),
        sa.Column("asset_tag_filter", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_profile_owner_id", "ommi_profile", ["owner_id"])

    op.create_table(
        "ommi_budget",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False, unique=True),
        sa.Column("monthly_cap_credit", sa.Integer(), nullable=True),
        sa.Column("alert_at_pct", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_budget_owner_id", "ommi_budget", ["owner_id"],
                    unique=True)


def downgrade() -> None:
    op.drop_table("ommi_budget")
    op.drop_table("ommi_profile")
    op.drop_table("ommi_sample")
    op.drop_index("ix_ommi_storyboard_framework_owner_id",
                  table_name="ommi_storyboard_framework")
    op.drop_table("ommi_storyboard_framework")
    op.drop_index("ix_ommi_image_template_asset_type", table_name="ommi_image_template")
    op.drop_index("ix_ommi_image_template_owner_id", table_name="ommi_image_template")
    op.drop_table("ommi_image_template")
    op.drop_index("ix_ommi_share_code_target", table_name="ommi_share_code")
    op.drop_index("ix_ommi_share_code_code", table_name="ommi_share_code")
    op.drop_index("ix_ommi_share_code_owner_id", table_name="ommi_share_code")
    op.drop_table("ommi_share_code")

    op.drop_column("ommi_style", "provider_overrides")
    op.drop_column("ommi_style", "parent_id")
    op.drop_column("ommi_meta_prompt", "placeholders")
    op.drop_column("ommi_meta_prompt", "is_default")
    op.drop_column("ommi_meta_prompt", "target_format")

    for table_name in reversed(_SHARE_LEVEL_TABLES):
        op.drop_column(table_name, "share_level")
