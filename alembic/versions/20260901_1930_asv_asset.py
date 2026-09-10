"""Bang artifact cua Auto Scan Video: asv_asset.

Revision ID: f2b8d16e05a3
Revises: e1a7c04b93d2
Create Date: 2026-09-01

## VI SAO MOT BANG RIENG THAY VI DUNG LAI `upload_sessions`

`UploadSession` la ve tai len cua KHACH: staging -> confirm -> promote cho tep
NGUON, kem kiem chu ky magic byte, quet don va doi soat. No lam viec do tot.

Cai no khong co — va khong nen co, vi no phuc vu moi app — la ngu nghia cua mot
artifact TRUNG GIAN:

    created_by_stage  giai doan nao sinh ra
    parent_keys       dan xuat tu artifact nao (LINEAGE)
    checksum          co so de tra loi "tep nay con dung khong"
    integrity         cau tra loi da luu cua phep kiem tren
    schema_version    hinh dang artifact JSON, doi theo thoi gian

Mot lan chay sinh ra tam artifact. Ep chung vao mo hinh ve tai len se lam hong
nghia cua `UploadSession` cho moi app dang dung no. Prompt 06 muc 2 doi dung dieu
nay: chi them khi ngu nghia con thieu.

## VI SAO CO `expires_at`

🔴 Kho nay da co mot lo do dung kieu do. `voice_block.audio_key` song mai cung du
   an, con tep no tro toi song 30 ngay theo han cua `jobs` — nen sau 30 ngay
   khach mo du an cu thay mot trinh phat 404 khong loi giai thich (CLAUDE.md,
   hang LTT VOICE). Mot tham chieu khong biet han cua chinh no la mot loi hua se
   het han.

## ROLLBACK

Them thuan tuy (O16). `downgrade` xoa dung bang nay va chi so cua no.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f2b8d16e05a3"
down_revision = "e1a7c04b93d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asv_asset",
        sa.Column("id", sa.String(length=48), primary_key=True),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=48), nullable=False),
        sa.Column("created_by_stage", sa.String(length=32), nullable=False,
                  server_default=""),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checksum", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.Column("parent_keys", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False,
                  server_default="1"),
        sa.Column("integrity", sa.String(length=16), nullable=False,
                  server_default="ok"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # Mot khoa luu tru chi duoc ghi nhan MOT LAN: hai dong cung tro mot tep
        # la hai cau tra loi cho cung mot cau hoi ve toan ven.
        #
        # ⚠️ Khai NGAY TRONG `create_table` — SQLite khong ALTER duoc rang buoc,
        #    va ca bo test cua kho chay tren SQLite. Xem ghi chu cung loai o
        #    `20260901_1800_asv_run_va_stage.py`.
        sa.UniqueConstraint("storage_key", name="ux_asv_asset_storage_key"),
    )
    op.create_index("ix_asv_asset_owner_id", "asv_asset", ["owner_id"])
    op.create_index("ix_asv_asset_run_id", "asv_asset", ["run_id"])
    op.create_index("ix_asv_asset_integrity", "asv_asset", ["integrity"])
    op.create_index("ix_asv_asset_run_stage", "asv_asset",
                    ["run_id", "created_by_stage"])
    op.create_index("ix_asv_asset_owner_run", "asv_asset", ["owner_id", "run_id"])


def downgrade() -> None:
    op.drop_index("ix_asv_asset_owner_run", table_name="asv_asset")
    op.drop_index("ix_asv_asset_run_stage", table_name="asv_asset")
    op.drop_index("ix_asv_asset_integrity", table_name="asv_asset")
    op.drop_index("ix_asv_asset_run_id", table_name="asv_asset")
    op.drop_index("ix_asv_asset_owner_id", table_name="asv_asset")
    op.drop_table("asv_asset")
