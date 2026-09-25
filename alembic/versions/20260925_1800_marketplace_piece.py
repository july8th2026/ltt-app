# -*- coding: utf-8 -*-
"""Marketplace piece + cong duyet: marketplace_piece, marketplace_piece_nhat_ky.

Revision ID: edb8b0fc0ac9
Revises: 3d5c07e2ba91
Create Date: 2026-09-25

## VI SAO CO HAI BANG NAY (plan wfm, 25/09/2026)

`platform_core/workflow/marketplace.py` la cong duyet FAIL-CLOSED cho piece
npm duoc cai LUC CHAY (thay vi chi ghim luc build nhu bay piece tinh trong
`connector_runner/allowlist.json`). `marketplace_piece` la mot hang = mot cap
(ten, phien_ban) dang o mot trang thai (`cho_duyet`/`da_duyet`/`tu_choi`/
`da_cai`); `marketplace_piece_nhat_ky` la nhat ky kiem toan, cung hinh dang
`credential_nhat_ky` — ghi CA duong that bai (`cai_that_bai`), khong chi
duong thanh cong.

## KHOA DUY NHAT (ten, phien_ban)

Nang phien ban la MOT YEU CAU MOI, di qua dung cong duyet lan nua — khong co
duong "sua tai cho" mot hang da duyet de doi sang phien ban khac. Xem
docstring `MarketplacePiece` trong `platform_core/models.py`.

## ROLLBACK

`downgrade()` DROP ca hai bang. Mat lich su yeu cau/duyet marketplace — piece
DA CAI tren dia (`data/marketplace/`, ngoai CSDL) khong tu mat, nhung se
khong con hang nao trong CSDL xac nhan no da duoc DUYET; `cai_dat()` doc tu
CSDL nen se coi nhu chua co gi duoc duyet (fail closed dung huong).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "edb8b0fc0ac9"
down_revision = "3d5c07e2ba91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_piece",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ten", sa.String(200), nullable=False),
        sa.Column("phien_ban", sa.String(60), nullable=False),
        sa.Column("nguoi_yeu_cau_id", sa.String(36), nullable=False),
        sa.Column("trang_thai", sa.String(16), nullable=False,
                  server_default="cho_duyet"),
        sa.Column("nguoi_duyet_id", sa.String(36), nullable=False,
                  server_default=""),
        sa.Column("ly_do_tu_choi", sa.Text(), nullable=False,
                  server_default=""),
        sa.Column("mien", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("integrity", sa.String(200), nullable=False,
                  server_default=""),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("quyet_dinh_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cai_luc", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("ten", "phien_ban",
                            name="ux_marketplace_piece_ten_ban"),
    )
    op.create_index("ix_marketplace_piece_trang_thai", "marketplace_piece",
                    ["trang_thai"])

    op.create_table(
        "marketplace_piece_nhat_ky",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("yeu_cau_id", sa.String(36), nullable=False),
        sa.Column("hanh_dong", sa.String(24), nullable=False),
        sa.Column("nguoi_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("chi_tiet", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_marketplace_piece_nhat_ky_yeu_cau_id",
                    "marketplace_piece_nhat_ky", ["yeu_cau_id"])
    op.create_index("ix_marketplace_piece_nhat_ky_created_at",
                    "marketplace_piece_nhat_ky", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_marketplace_piece_nhat_ky_created_at",
                  table_name="marketplace_piece_nhat_ky")
    op.drop_index("ix_marketplace_piece_nhat_ky_yeu_cau_id",
                  table_name="marketplace_piece_nhat_ky")
    op.drop_table("marketplace_piece_nhat_ky")

    op.drop_index("ix_marketplace_piece_trang_thai",
                  table_name="marketplace_piece")
    op.drop_table("marketplace_piece")
