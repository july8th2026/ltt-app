"""Bang cua LTT VOICE: voice_profile, voice_ref, voice_repr, voice_consent.

Revision ID: a1f7c3d90b12
Revises: e83b5d7c1a40
Create Date: 2026-08-30

Bon bang, tien to `voice_` theo `AppManifest.table_prefix`.

VI SAO `voice_repr` TACH KHOI `voice_profile`:
    Day la toan bo ly do san pham nay chiu duoc viec doi engine. Neu `speaker_emb`
    nam ngay trong profile thi ngay nang v3 Turbo len v3 full la ngay moi
    `voice_id` phai doi -- tuc moi tich hop cua khach gay, vi mot ly do hoan toan
    noi bo. Tach ra thi nang model = them mot dong va doi co `trang_thai`.

DUONG LUI: `downgrade()` xoa ca bon bang. An toan vi khong bang nao khac tro toi
    chung, va du lieu that (tep nguon, bieu dien) nam trong storage chu khong
    trong CSDL -- lui migration khong lam mat tep nao.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1f7c3d90b12"
down_revision = "e83b5d7c1a40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_profile",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(40), nullable=False),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("ten_hien_thi", sa.String(120), nullable=False),
        sa.Column("ngon_ngu", sa.String(16), nullable=False, server_default="vi"),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(24), nullable=False,
                  server_default="dang_ghi_danh"),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("sua_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        # Ten hien thi duy nhat TRONG PHAM VI MOT CHU. Hai khach duoc phep trung
        # ten; mot khach thi khong, vi ho se khong phan biet duoc.
        sa.UniqueConstraint("owner_id", "ten_hien_thi", name="uq_voice_owner_ten"),
    )
    op.create_index("ix_voice_profile_public_id", "voice_profile", ["public_id"],
                    unique=True)
    op.create_index("ix_voice_profile_owner_id", "voice_profile", ["owner_id"])
    op.create_index("ix_voice_profile_trang_thai", "voice_profile", ["trang_thai"])
    op.create_index("ix_voice_profile_owner", "voice_profile",
                    ["owner_id", "trang_thai"])

    op.create_table(
        "voice_ref",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("mime", sa.String(64), nullable=False, server_default=""),
        sa.Column("so_byte", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("giay", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        # Cung mot tep gui lai hai lan cho cung mot giong la MOT ban ghi. Day la
        # thu lam cho job ghi danh idempotent duoc ma khong can khoa rieng: cu
        # INSERT, va coi IntegrityError la duong chay binh thuong.
        sa.UniqueConstraint("profile_id", "sha256", name="uq_voice_ref_hash"),
    )
    op.create_index("ix_voice_ref_profile_id", "voice_ref", ["profile_id"])
    op.create_index("ix_voice_ref_sha256", "voice_ref", ["sha256"])

    op.create_table(
        "voice_repr",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("ref_id", sa.BigInteger(), nullable=False),
        sa.Column("engine", sa.String(32), nullable=False, server_default="vieneu"),
        sa.Column("model_repo", sa.String(160), nullable=False, server_default=""),
        sa.Column("model_revision", sa.String(64), nullable=False,
                  server_default=""),
        sa.Column("sdk_version", sa.String(32), nullable=False, server_default=""),
        sa.Column("storage_key", sa.String(512), nullable=False, server_default=""),
        sa.Column("fingerprint", sa.String(64), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(24), nullable=False,
                  server_default="dang_dung"),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_voice_repr_profile_id", "voice_repr", ["profile_id"])
    op.create_index("ix_voice_repr_ref_id", "voice_repr", ["ref_id"])
    op.create_index("ix_voice_repr_trang_thai", "voice_repr", ["trang_thai"])
    op.create_index("ix_voice_repr_profile", "voice_repr",
                    ["profile_id", "trang_thai"])

    op.create_table(
        "voice_consent",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        # Phien ban ban dieu khoan da HIEN RA MAN HINH luc bam. Khong co no thi
        # khong tra loi duoc "ho dong y voi cai gi".
        sa.Column("phien_ban_dieu_khoan", sa.String(64), nullable=False),
        sa.Column("ref_sha256", sa.String(64), nullable=False, server_default=""),
        sa.Column("loai", sa.String(32), nullable=False, server_default="tu_thu"),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(256), nullable=False, server_default=""),
        sa.Column("dong_y_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_voice_consent_profile_id", "voice_consent", ["profile_id"])
    op.create_index("ix_voice_consent_owner_id", "voice_consent", ["owner_id"])


def downgrade() -> None:
    op.drop_table("voice_consent")
    op.drop_table("voice_repr")
    op.drop_table("voice_ref")
    op.drop_table("voice_profile")
