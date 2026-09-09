"""VPS V2: bang `vps_thao_tac` — mot mutation dai tren mot may (Pha 02).

Revision ID: c93a5d17be42
Revises: b7f21c48ae90
Create Date: 2026-09-09

## Vi sao mot bang moi chu khong tai dung `job` hay `vps_event`

`job` tra loi *"luot viec nay cua worker xong chua"* — no thu lai nhieu lan, moi
lan mot dong. `vps_event` la nhat ky: **da xay ra roi**, khong bao gio xoa.

Thao tac tra loi cau thu ba, ma khong bang nao trong hai bang tren tra loi duoc:
*"cai may nay dang bi lam gi, ai bao, toi dau roi, con bao lau nua"*. No song
xuyen qua nhieu lan thu (khac `job`) va no **ket thuc** (khac `vps_event`).

Xem `docs/vps_v2/ADR_INDEX.md` ADR-02.
"""
from alembic import op
import sqlalchemy as sa

revision = "c93a5d17be42"
down_revision = "b7f21c48ae90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vps_thao_tac",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instance_id", sa.String(36), nullable=False),
        sa.Column("loai", sa.String(16), nullable=False),
        sa.Column("boi", sa.String(190), nullable=False, server_default=""),
        # NULL chu khong phai "": chuoi rong THAM GIA vao UNIQUE, nen mot may
        # se chi co duoc **mot** thao tac khong khoa trong ca doi no. NULL thi
        # khong tinh — cung khuon voi `uq_vps_instance_vmid`.
        sa.Column("khoa_idem", sa.String(64), nullable=True),
        # `tinh_trang` chu khong `trang_thai`: `vps_instance.trang_thai` la mot
        # hinh chieu co phep quet rieng canh no, va hai cot trung ten lam phep
        # quet ay khong phan biet duoc ghi hop le voi bug. Xem `tables.py`.
        sa.Column("tinh_trang", sa.String(16), nullable=False,
                  server_default="cho"),
        sa.Column("upid", sa.Text(), nullable=False, server_default=""),
        sa.Column("lan_thu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("buoc", sa.String(64), nullable=False, server_default=""),
        sa.Column("dien_truoc", sa.String(16), nullable=False,
                  server_default=""),
        sa.Column("dien_mong_doi", sa.String(16), nullable=False,
                  server_default=""),
        sa.Column("dien_sau", sa.String(16), nullable=False, server_default=""),
        sa.Column("ma_loi", sa.String(32), nullable=False, server_default=""),
        sa.Column("chi_tiet_loi", sa.Text(), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bat_dau_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("han_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ket_thuc_luc", sa.DateTime(timezone=True), nullable=True),
        # Trong tai chong bam hai lan. Khong co no thi `mo()` phai "hoi roi moi
        # ghi", va giua hai buoc do co mot khoang ma hai request cua cung mot cu
        # bam dup lot qua duoc.
        sa.UniqueConstraint("instance_id", "khoa_idem",
                            name="uq_vps_thao_tac_idem"),
    )
    op.create_index("ix_vps_thao_tac_instance_id", "vps_thao_tac",
                    ["instance_id"])
    op.create_index("ix_vps_thao_tac_tinh_trang", "vps_thao_tac",
                    ["tinh_trang"])
    op.create_index("ix_vps_thao_tac_tao_luc", "vps_thao_tac", ["tao_luc"])
    op.create_index("ix_vps_thao_tac_may_tinhtrang", "vps_thao_tac",
                    ["instance_id", "tinh_trang"])


def downgrade() -> None:
    for ten in ("ix_vps_thao_tac_may_tinhtrang", "ix_vps_thao_tac_tao_luc",
                "ix_vps_thao_tac_tinh_trang", "ix_vps_thao_tac_instance_id"):
        op.drop_index(ten, table_name="vps_thao_tac")
    op.drop_table("vps_thao_tac")
