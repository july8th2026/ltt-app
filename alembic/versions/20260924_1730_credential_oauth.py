# -*- coding: utf-8 -*-
"""Kho credential cua khach + lượt OAuth dang do: credential, credential_nhat_ky, oauth_state.

Revision ID: 9c1e4b77a205
Revises: c4a17f9b6d20
Create Date: 2026-09-24

## VI SAO CO BA BANG NAY (spec §9, plan wf-v2 P5c)

Truoc 24/09/2026, cho DUY NHAT mot workflow cat duoc header `Authorization` la
`params` cua node — tuc BEN TRONG `workflow_version`. Bang ay duoc nhan ban khi
khach "Save as", duoc tra nguyen ven cho trinh soan thao, va di theo moi ban
xuat. Mot bi mat nam trong mot ban ghi THIET KE DE DEM DI CHO KHAC la mot bi
mat da ro, chi la chua ai doc. Do la ly do `core.http` bi khoa cho toi khi co
bang nay.

## DAY LA DU LIEU CUA KHACH

Ca ba bang khai o `public_api/governance.py::STORES` (test_211 doi chieu):
`credential` va `credential_nhat_ky` la EVIDENCE (hang o lai sau khi thu hoi —
no la bang chung mot run da dung cai gi), `oauth_state` la OPERATIONAL 1 ngay
(mot luot OAuth do dang song 10 phut; giu lau hon la giu mot PKCE verifier
khong ai can nua).

## BI MAT NAM O DAU

`credential.bi_mat_ma_hoa` va `oauth_state.pkce_verifier_ma_hoa` la token Fernet
(`platform_core/secretbox.py`, nay la `MultiFernet` de xoay khoa duoc).
⛔ Khong cot nao trong ba bang nay duoc tra thang ra API.

## ROLLBACK

`downgrade()` DROP ca ba bang. Do la MAT DU LIEU that (bi mat cua khach), khong
phai mot thao tac dao nguoc duoc — ai chay no phai biet minh dang xoa gi. Giu
lai vi vong kiem di tru chay ca hai chieu tren SQLite.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "9c1e4b77a205"
down_revision = "c4a17f9b6d20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credential",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("kieu", sa.String(32), nullable=False),
        sa.Column("nha_cung_cap", sa.String(40), nullable=False,
                  server_default=""),
        sa.Column("ten", sa.String(120), nullable=False, server_default=""),
        sa.Column("bi_mat_ma_hoa", sa.Text(), nullable=False,
                  server_default=""),
        sa.Column("preview", sa.String(16), nullable=False, server_default=""),
        sa.Column("pham_vi", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("meta", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("het_han_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("thu_hoi_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dung_lan_cuoi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_credential_owner_id", "credential", ["owner_id"])

    op.create_table(
        "credential_nhat_ky",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("credential_id", sa.String(36), nullable=False),
        sa.Column("hanh_dong", sa.String(16), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("node_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_credential_nhat_ky_credential_id",
                    "credential_nhat_ky", ["credential_id"])
    op.create_index("ix_credential_nhat_ky_created_at",
                    "credential_nhat_ky", ["created_at"])

    op.create_table(
        "oauth_state",
        # ⭐ Khoa chinh la HASH, khong phai `state` tho: gia tri tho song trong
        #    URL cua trinh duyet va trong log cua Google. Thu ta luu chi can du
        #    de SO KHOP, khong can du de PHAT LAI.
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("pkce_verifier_ma_hoa", sa.Text(), nullable=False,
                  server_default=""),
        sa.Column("redirect_after", sa.String(500), nullable=False,
                  server_default=""),
        sa.Column("pham_vi", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("het_han_luc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dung_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_oauth_state_owner_id", "oauth_state", ["owner_id"])
    op.create_index("ix_oauth_state_het_han_luc", "oauth_state",
                    ["het_han_luc"])


def downgrade() -> None:
    op.drop_index("ix_oauth_state_het_han_luc", table_name="oauth_state")
    op.drop_index("ix_oauth_state_owner_id", table_name="oauth_state")
    op.drop_table("oauth_state")
    op.drop_index("ix_credential_nhat_ky_created_at",
                  table_name="credential_nhat_ky")
    op.drop_index("ix_credential_nhat_ky_credential_id",
                  table_name="credential_nhat_ky")
    op.drop_table("credential_nhat_ky")
    op.drop_index("ix_credential_owner_id", table_name="credential")
    op.drop_table("credential")
