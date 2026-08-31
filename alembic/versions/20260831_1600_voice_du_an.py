"""Bang cua man DU AN cua LTT VOICE: voice_project, voice_block.

Revision ID: c3d9f52a7e18
Revises: b2c8e41d5a90
Create Date: 2026-08-31

Hai bang, tien to `voice_` theo `AppManifest.table_prefix`.

VI SAO `thu_tu` LA SO THUC CHU KHONG PHAI SO NGUYEN:
    De chen mot khoi vao giua hai khoi KHONG phai danh so lai ca du an. Chen
    giua 3.0 va 4.0 thi dung 3.5 -- MOT luot ghi, thay vi N luot.

    Danh so lai N dong cho mot thao tac nguoi dung coi la tuc thi vua cham vua
    la cho hai nguoi sua cung luc giam len nhau. Doi lai: thu tu khong con la
    so dem, nen dung hien no ra cho khach nhu mot so thu tu -- man hinh dem lai
    tu 1 khi ve.

VI SAO KHONG CO BANG `chapter`:
    Anh tham chieu 03 ve Chuong -> Khoi, nhung mot tang long lam doi moi man
    hinh de doi lay rat it o ban dau. Them duoc luc nao cung duoc; go ra thi
    khong.

VI SAO KHONG CO BANG `block_version`:
    Lich su job da giu du moi luot sinh (moi luot la mot `Job` co `result`).
    Mot bang phien ban thu hai la mot nguon chan ly thu hai cho cung mot su
    that -- va hai nguon chan ly la mot cho de chung lech nhau.

⛔ `owner_id` la String(36), KHONG phai so. `User.id` cua nen tang la UUID
    chuoi. Khai `BigInteger` o `voice_profile` da tung lam MOI khach chung mot
    chu so huu (xem migration 20260831_1000_voice_owner_uuid.py). Dung lap lai.

DUONG LUI: `downgrade()` xoa ca hai bang. An toan vi khong bang nao khac tro
    toi chung; tep tieng cua tung khoi nam trong storage duoi khoa
    `voice/out/{owner}/{job_id}/` va thuoc vong doi cua JOB, khong thuoc vong
    doi cua khoi -- lui migration khong lam mo coi tep nao.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c3d9f52a7e18"
down_revision = "b2c8e41d5a90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_project",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=40), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("ten", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("giong_mac_dinh", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.Column("trang_thai", sa.String(length=24), nullable=False,
                  server_default="nhap"),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("sua_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_project_public_id", "voice_project",
                    ["public_id"], unique=True)
    op.create_index("ix_voice_project_owner_id", "voice_project", ["owner_id"])
    op.create_index("ix_voice_project_owner", "voice_project",
                    ["owner_id", "trang_thai"])
    op.create_index("ix_voice_project_trang_thai", "voice_project", ["trang_thai"])

    op.create_table(
        "voice_block",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        # So THUC -- xem phan dau tep.
        sa.Column("thu_tu", sa.Float(), nullable=False, server_default="0"),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("giong", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(length=24), nullable=False,
                  server_default="moi"),
        sa.Column("job_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("audio_key", sa.String(length=512), nullable=False,
                  server_default=""),
        sa.Column("giay", sa.Float(), nullable=False, server_default="0"),
        sa.Column("credit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("sua_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_block_project_id", "voice_block", ["project_id"])
    op.create_index("ix_voice_block_du_an", "voice_block",
                    ["project_id", "thu_tu"])
    op.create_index("ix_voice_block_trang_thai", "voice_block", ["trang_thai"])


def downgrade() -> None:
    op.drop_index("ix_voice_block_trang_thai", table_name="voice_block")
    op.drop_index("ix_voice_block_du_an", table_name="voice_block")
    op.drop_index("ix_voice_block_project_id", table_name="voice_block")
    op.drop_table("voice_block")

    op.drop_index("ix_voice_project_trang_thai", table_name="voice_project")
    op.drop_index("ix_voice_project_owner", table_name="voice_project")
    op.drop_index("ix_voice_project_owner_id", table_name="voice_project")
    op.drop_index("ix_voice_project_public_id", table_name="voice_project")
    op.drop_table("voice_project")
