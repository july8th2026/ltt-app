"""LTT WORKFLOW V2 · Dot 4 + Dot 5 — foreach, artifact, trigger.

Revision ID: e8f35c1a7d64
Revises: d7e24b9f1c53
Create Date: 2026-09-08

## `foreach_vong` + `foreach_muc` (Dot 4.3, nguong `M7`)

    M7: ForEach 100 phan tu, crash giua chung -> 100 ket qua, 0 luot lap

⭐ MOT HANG CHO MOI PHAN TU, ghi san ngay luc mo vong. Day la thu lam `M7` dat
   duoc, va no la mot quyet dinh KIEN TRUC chu khong phai mot chi tiet:

   Mot CON TRO "da toi dau" chi dung khi cac phan tu chay TUAN TU. Voi
   `parallelism > 1` thi phan tu 7 co the xong truoc phan tu 3, va mot con tro
   KHONG BIEU DAT NOI trang thai ay. Sau mot lan chet, "con phai chay gi" tro
   thanh mot cau `WHERE xong = false` — chinh xac, khong suy doan.

⛔ `max_items` NOT NULL va phai huu han: khong co chan tren thi khong tinh duoc
   tran chi phi (`WF-501`). Mot ForEach khong chan tren la mot hoa don khong
   chan tren.

## `artifact` (Dot 5.1, `G33` `G35` `G36`)

    id = "<backend>:<key>"    -- TU MO TA

🔴 Ban va cho mot lo SE NO, khong phai lo dang no. Ngay LTT bat R2 SONG SONG
   Local, `storage.get_storage()` la mot singleton toan cuc => moi khoa cu
   thanh mo ho. Mot "abc/def.png" trong `output_ref` cua buoc truoc khong noi
   no nam o dau, va KHONG CO CHO NAO DE TRA — vi tham chieu di vao JSONB, va
   JSONB khong tra bang duoc (bai hoc n8n, `05 §4.1`).

⚠️ `delete` la TUY CHON cua hop dong luu tru: backend nao co vong doi rieng
   (R2 lifecycle) thi ta KHONG tu xoa. Chong TTL cua ta len TTL cua R2 la hai
   bo dem cung nham mot tep, va bo nao chay truoc thi bo kia thao tac tren hu
   khong.

## `workflow_trigger` (Dot 5.4, `G42`)

Bai hoc Windmill: 11 CRATE trigger, khong phai 11 nhanh `if`. Nen tang khong
biet ten loai nao ca — no chi biet mot loai phai tra loi duoc `toi_han()` va
`lan_ke_tiep()`. Them loai thu nam la mot lan `dang_ky()`, khong phai mot lan
sua `platform_core`.

## BA CHI SO BO PHAN, MOT LY DO

    ix_foreach_muc_chua_xong  WHERE xong = false
    ix_artifact_expiry        WHERE ttl_class <> 'PERMANENT' AND expires_at IS NOT NULL
    ix_trigger_due            WHERE enabled AND next_fire_at IS NOT NULL

Hang da chet khong duoc nam trong chi so ma bo quet di qua moi vai giay.

## AN TOAN

Chi CREATE TABLE moi. Khong doi cot nao dang co, khong cham du lieu nao dang
co, chua noi vao duong chay nao (`27_29 §28`).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e8f35c1a7d64"
down_revision = "d7e24b9f1c53"
branch_labels = None
depends_on = None


_MUC_CHUA_XONG_PG = "xong = false"
_MUC_CHUA_XONG_LITE = "xong = 0"
_ART_PG = "ttl_class <> 'PERMANENT' AND expires_at IS NOT NULL"
_TRIG_PG = "enabled AND next_fire_at IS NOT NULL"
_TRIG_LITE = "enabled = 1 AND next_fire_at IS NOT NULL"


def upgrade() -> None:
    # ── Dot 4.3 ──────────────────────────────────────────────────────────────
    op.create_table(
        "foreach_vong",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("node_id", sa.String(64), nullable=False),
        # BAT BUOC va huu han — khong co chan tren thi khong co tran chi phi.
        sa.Column("max_items", sa.Integer(), nullable=False),
        # `M4`: hom nay 4 CUNG. V2 khai duoc, mac dinh 8.
        sa.Column("parallelism", sa.Integer(), nullable=False,
                  server_default="8"),
        sa.Column("so_muc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_foreach_vong_run_id", "foreach_vong", ["run_id"])

    op.create_table(
        "foreach_muc",
        sa.Column("vong_id", sa.String(36), primary_key=True),
        sa.Column("chi_so", sa.Integer(), primary_key=True),
        sa.Column("dau_vao", sa.JSON(), nullable=False),
        sa.Column("ket_qua", sa.JSON(), nullable=False),
        sa.Column("xong", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
    )
    op.create_index("ix_foreach_muc_chua_xong", "foreach_muc", ["vong_id"],
                    postgresql_where=sa.text(_MUC_CHUA_XONG_PG),
                    sqlite_where=sa.text(_MUC_CHUA_XONG_LITE))

    # ── Dot 5.1 ──────────────────────────────────────────────────────────────
    op.create_table(
        "artifact",
        # "<backend>:<key>" — backend nam NGAY TRONG id.
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        # LINEAGE: "tep nay tu dau ra" tra loi bang MOT cot.
        sa.Column("created_by_snapshot_id", sa.String(36), nullable=False,
                  server_default=""),
        sa.Column("kind", sa.String(16), nullable=False, server_default="file"),
        sa.Column("mime", sa.String(120), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False,
                  server_default="0"),
        sa.Column("checksum_sha256", sa.String(64), nullable=False,
                  server_default=""),
        sa.Column("ttl_class", sa.String(16), nullable=False,
                  server_default="RUN"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifact_owner_id", "artifact", ["owner_id"])
    op.create_index("ix_artifact_expiry", "artifact", ["expires_at"],
                    postgresql_where=sa.text(_ART_PG),
                    sqlite_where=sa.text(_ART_PG))

    # ── Dot 5.4 ──────────────────────────────────────────────────────────────
    op.create_table(
        "workflow_trigger",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workflow_id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("next_fire_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workflow_trigger_workflow_id", "workflow_trigger",
                    ["workflow_id"])
    op.create_index("ix_trigger_due", "workflow_trigger", ["next_fire_at"],
                    postgresql_where=sa.text(_TRIG_PG),
                    sqlite_where=sa.text(_TRIG_LITE))


def downgrade() -> None:
    op.drop_index("ix_trigger_due", table_name="workflow_trigger")
    op.drop_index("ix_workflow_trigger_workflow_id",
                  table_name="workflow_trigger")
    op.drop_table("workflow_trigger")
    op.drop_index("ix_artifact_expiry", table_name="artifact")
    op.drop_index("ix_artifact_owner_id", table_name="artifact")
    op.drop_table("artifact")
    op.drop_index("ix_foreach_muc_chua_xong", table_name="foreach_muc")
    op.drop_table("foreach_muc")
    op.drop_index("ix_foreach_vong_run_id", table_name="foreach_vong")
    op.drop_table("foreach_vong")
