"""Bang cua Auto Scan Video: asv_run, asv_stage.

Revision ID: e1a7c04b93d2
Revises: a5f31c07d2b4
Create Date: 2026-09-01

Hai bang, tien to `asv_` theo `AppManifest.table_prefix`.

## VI SAO `asv_stage` LA MOT DONG CHO MOI GIAI DOAN, KHONG PHAI MOT KHOI JSON

Tien le trong kho la `AgentRun.checkpoint` — mot tai lieu JSON bi doc-sua-ghi o
moi tick cua `platform_core/agent/executor.py`. No dang chay dung, nhung **chi
vi** moi nguoi ghi deu di qua `runs.get_owned(..., lock=True)`. Tinh dung dan
nam o mot ky luat ma khong gi cuong che: them mot duong ghi quen khoa la mat cap
nhat, im lang.

Mot dong cho moi `(run_id, stage)` xoa bo nguy co thay vi canh no — hai giai
doan xong cung luc ghi hai dong khac nhau, khong the dam nhau. Rang buoc UNIQUE
o duoi la cho bat bien I18 song.

## VI SAO `owner_id` LAP LAI O CA HAI BANG

Khong chuan hoa, co y. Mot phep loc quyen so huu khong nen phu thuoc vao mot
phep JOIN ma nguoi viet truy van co the quen. Chi phi la mot cot String(36);
cai gia cua ben kia la mot lo ro du lieu giua hai khach.

⛔ `owner_id` la String(36) chu KHONG phai so. `User.id` cua nen tang la UUID
   chuoi. Khai `BigInteger` o `voice_profile` da tung lam MOI khach chung mot
   chu so huu — xem `20260831_1000_voice_owner_uuid.py`. Bay nay co that trong
   chinh kho nay.

## ROLLBACK

Them thuan tuy: khong cot nao, bang nao dang co bi doi hay xoa (O16). `downgrade`
xoa dung hai bang nay va chi so cua chung, nen quay lui la mot lenh
`alembic downgrade` cong voi viec go ba thu muc app.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e1a7c04b93d2"
#: Head luc tao: `20260901_0200_voice_dung_chung.py`.
#: ⚠️ Cay nay ghim o `c31b1ae`; mot lane khac dang them migration song song. Khi
#:    gop nhanh `phien/asv` ve, kiem `alembic heads` — neu ra HAI head thi noi
#:    chung bang mot revision hop nhat, dung sua `down_revision` cua ban ghi da
#:    chay o dau.
down_revision = "a5f31c07d2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asv_run",
        sa.Column("id", sa.String(length=48), primary_key=True),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False,
                  server_default="queued"),
        sa.Column("contract_version", sa.String(length=32), nullable=False,
                  server_default="auto_scan_mvp_v1"),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False,
                  server_default=""),
        sa.Column("credit_held", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credit_actual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_asv_run_owner_id", "asv_run", ["owner_id"])
    op.create_index("ix_asv_run_status", "asv_run", ["status"])
    op.create_index("ix_asv_run_created_at", "asv_run", ["created_at"])
    op.create_index("ix_asv_run_owner_created", "asv_run", ["owner_id", "created_at"])

    op.create_table(
        "asv_stage",
        sa.Column("id", sa.String(length=48), primary_key=True),
        sa.Column("run_id", sa.String(length=48), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False,
                  server_default="pending"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fingerprint", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.Column("outputs", sa.JSON(), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("credit_actual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        # 🔑 Bat bien I18 nam o day: mot giai doan chi co MOT dong, nen hai
        #    worker khong the tao hai ban ghi cho cung mot viec.
        #
        # ⚠️ Khai NGAY TRONG `create_table`, khong phai bang
        #    `op.create_unique_constraint(...)` sau do. SQLite khong ho tro ALTER
        #    de them rang buoc — ban dau tep nay lam theo cach kia va migration
        #    **khong chay noi tren SQLite**, tuc khong test duoc cuc bo, trong khi
        #    ca bo test cua kho chay tren SQLite. No chi dung tren PostgreSQL cua
        #    production, va do la kieu loi chi lo ra o dung cho khong ai nhin.
        sa.UniqueConstraint("run_id", "stage", name="ux_asv_stage_run_stage"),
    )
    op.create_index("ix_asv_stage_run_id", "asv_stage", ["run_id"])
    op.create_index("ix_asv_stage_owner_id", "asv_stage", ["owner_id"])
    op.create_index("ix_asv_stage_status", "asv_stage", ["status"])
    op.create_index("ix_asv_stage_job_id", "asv_stage", ["job_id"])
    op.create_index("ix_asv_stage_run_status", "asv_stage", ["run_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_asv_stage_run_status", table_name="asv_stage")
    op.drop_index("ix_asv_stage_job_id", table_name="asv_stage")
    op.drop_index("ix_asv_stage_status", table_name="asv_stage")
    op.drop_index("ix_asv_stage_owner_id", table_name="asv_stage")
    op.drop_index("ix_asv_stage_run_id", table_name="asv_stage")
    op.drop_table("asv_stage")

    op.drop_index("ix_asv_run_owner_created", table_name="asv_run")
    op.drop_index("ix_asv_run_created_at", table_name="asv_run")
    op.drop_index("ix_asv_run_status", table_name="asv_run")
    op.drop_index("ix_asv_run_owner_id", table_name="asv_run")
    op.drop_table("asv_run")
