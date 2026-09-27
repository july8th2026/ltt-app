# -*- coding: utf-8 -*-
"""Pha 5 PROMPT AI OMMI: kho tai nguyen sau.

Them file_hash/favorite/rating vao ommi_resource_variant; tao bang ommi_trash
(thung rac phuc hoi duoc) va ommi_image_job (theo doi job sinh anh
composite/chia canh).

Revision ID: fa6ea619faa2
Revises: b64a39da941d
Create Date: 2026-09-27 19:30

## VI SAO BA THU NAY DI CHUNG MOT MIGRATION

Ca ba phuc vu dung MOT tinh nang cua pha 5 (kho tai nguyen sau): dedupe can
`file_hash` (theo `(owner_id, file_hash)`, khong phai `file_hash` toan cuc -
hai khach tai cung mot anh la hai ban ghi rieng vi quyen so huu khac nhau),
thung rac can bang rieng vi phai giu snapshot ban da xoa (khac `archived_at`
von la luu tru tam), va sinh anh composite can theo doi phien ban/retry qua
`ommi_image_job`. Tach ba migration se lam mot lan chay do dang (vi du co
file_hash ma khong co ommi_trash) tro thanh mot trang thai hop le gia, trong
khi ba cot/bang nay chi co y nghia CUNG NHAU.

## owner_id la NOT NULL tren CA HAI bang moi (khac ommi_resource_variant)

`ommi_resource_variant` da co `owner_id nullable=True` tu migration goc
(20260805_1900_ommi_library.py) - khong dong tren migration nay. Nhung
`ommi_trash` va `ommi_image_job` la bang du lieu MOI, nen theo dung bat bien
so huu cua module (moi bang du lieu OMMI phai loc duoc theo tung khach -
`tests/test_135_ommi_ownership.py::test_every_ommi_data_table_carries_an_owner`),
ca hai deu khai `owner_id String(36) NOT NULL` kem index rieng. Khong bang
nao trong hai bang nay la bang noi thuan (join table) - ca hai deu la du lieu
dau dong cua chinh nguoi dung.

## KHONG co rang buoc UNIQUE moi

Migration nay chi tao INDEX thuong (khong `unique=True`), nen khong co ten
`uq_*` nao can dang ky vao `tools/restore_drill_schema.py`
(`tests/test_155_ommi_metrics.py::test_moi_rang_buoc_unique_song_con_deu_nam_trong_drill`
chi doi chieu rang buoc UNIQUE tren ORM - Task nay khong dung ORM va khong
tao UNIQUE nao).

## ROLLBACK

`downgrade()` xoa dung thu tu nguoc: drop hai bang moi truoc (kem index cua
chung), roi drop index va ba cot tren `ommi_resource_variant`. Khong xoa du
lieu benh vien nao khac.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "fa6ea619faa2"
down_revision = "b64a39da941d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ommi_resource_variant") as batch:
        batch.add_column(sa.Column("file_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column(
            "favorite", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("rating", sa.Integer(), nullable=True))
    op.create_index("ix_ommi_resource_variant_file_hash",
                    "ommi_resource_variant", ["file_hash"])

    op.create_table(
        "ommi_trash",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_trash_owner_id", "ommi_trash", ["owner_id"])
    op.create_index("ix_ommi_trash_purge_after", "ommi_trash", ["purge_after"])

    op.create_table(
        "ommi_image_job",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("template_id", sa.String(36), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_image_job_owner_id", "ommi_image_job", ["owner_id"])
    op.create_index("ix_ommi_image_job_parent_id", "ommi_image_job", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_ommi_image_job_parent_id", table_name="ommi_image_job")
    op.drop_index("ix_ommi_image_job_owner_id", table_name="ommi_image_job")
    op.drop_table("ommi_image_job")

    op.drop_index("ix_ommi_trash_purge_after", table_name="ommi_trash")
    op.drop_index("ix_ommi_trash_owner_id", table_name="ommi_trash")
    op.drop_table("ommi_trash")

    op.drop_index("ix_ommi_resource_variant_file_hash",
                  table_name="ommi_resource_variant")
    with op.batch_alter_table("ommi_resource_variant") as batch:
        batch.drop_column("rating")
        batch.drop_column("favorite")
        batch.drop_column("file_hash")
