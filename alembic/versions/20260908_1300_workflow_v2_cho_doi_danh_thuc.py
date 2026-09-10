"""LTT WORKFLOW V2 · Dot 2.3 + 2.4 — waitpoint va bang danh thuc.

Revision ID: c6d13a8e4b72
Revises: b5c92e3f7a41
Create Date: 2026-09-08

## DOT 2.3 — WAITPOINT (`23_24 §4.3`)

Ba quyet dinh, va ca ba deu den tu mot khiem khuyet DO DUOC o kho khac:

  nhieu-nhieu       `WF-204`: 20 node ForEach cung cho MOT job GPU. Mo hinh
                    mot-waitpoint-mot-buoc cua Activepieces khong bieu dat noi,
                    va day khong phai kich ban hiem — no la hinh dang MAC DINH
                    cua ForEach co tai nguyen chung.
  `sealed`          khong co no thi `ALL` KHONG DINH NGHIA DUOC khi so nhanh la
                    dong: "du tat ca" so voi cai gi?
  `NOT_DISPATCHED`  tin hieu le ra phai gui ma chua bao gio gui. Thieu no, mot
                    nhanh chet treo barrier VINH VIEN — no khong SUCCEEDED cung
                    khong FAILED, no VANG MAT.

## DOT 2.4 — WAKEUP (chot `Q4`, `23_24 §3`)

Bang la NGUON CHAN LY; `LISTEN/NOTIFY` chi RUT NGAN DO TRE. Ly do la mot con so
do duoc, khong phai mot so thich kien truc:

    worker restart 13,6 lan/ngay   (`01 §A.6`)

Mot `NOTIFY` phat dung luc worker dang khoi dong lai BIEN MAT khong dau vet.

    UNIQUE(run_id, node_run_id, kind, due_at)   khu trung bang RANG BUOC
    ix_wakeup_due (due_at) WHERE claimed_at IS NULL   <- CHI SO BO PHAN

🔴 `M2`: mot run cho 60 phut co MOT hang va phat sinh 0 cau SQL trong 60 phut
   do. Bo quet hoi "co hang nao toi han chua" bang MOT truy van cho TOAN HE
   THONG. `test_953` dem cau SQL that bang `before_cursor_execute` — mot vong
   lap an se hien ra thanh con so.

## VI SAO CHI SO PHAI LA BO PHAN — ca hai bang

Hang da nhat / waitpoint da xong khong con la viec. De chung trong chi so ma bo
quet di qua moi 5 giay la tra tien mai cho nhung thu da chet. Cung khuon voi
`ux_jobs_dedupe_active` (`c9d4e1a77b02`).

## AN TOAN

Chi CREATE TABLE moi. Khong doi cot nao dang co, khong cham du lieu nao dang
co, chua noi vao duong chay nao (`27_29 §28`).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c6d13a8e4b72"
down_revision = "b5c92e3f7a41"
branch_labels = None
depends_on = None


_WP_IDEM = "idempotency_key <> ''"
_WP_DUE = "status = 'PENDING' AND due_at IS NOT NULL"
_WK_DUE = "claimed_at IS NULL"


def upgrade() -> None:
    # ── 2.3 ──────────────────────────────────────────────────────────────────
    op.create_table(
        "waitpoint",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        # DELAY | JOB | WEBHOOK | HUMAN | CHILD_RUN | BARRIER
        sa.Column("kind", sa.String(16), nullable=False),
        # PENDING | COMPLETED | EXPIRED | CANCELLED
        sa.Column("status", sa.String(16), nullable=False,
                  server_default="PENDING"),
        # "se khong con tin hieu nao nua" — dieu kien de `ALL` co nghia.
        sa.Column("sealed", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        # 0 = ALL (chi ket luan duoc sau khi sealed). >0 = N-of-M.
        sa.Column("required_successes", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("release_on_first_failure", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False,
                  server_default=""),
        sa.Column("output_ref", sa.JSON(), nullable=False),
        sa.Column("output_is_error", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("idempotency_key", sa.String(120), nullable=False,
                  server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_waitpoint_run_id", "waitpoint", ["run_id"])
    op.create_index("ux_waitpoint_idem", "waitpoint",
                    ["owner_id", "idempotency_key"], unique=True,
                    postgresql_where=sa.text(_WP_IDEM),
                    sqlite_where=sa.text(_WP_IDEM))
    op.create_index("ix_waitpoint_due", "waitpoint", ["due_at"],
                    postgresql_where=sa.text(_WP_DUE),
                    sqlite_where=sa.text(_WP_DUE))

    op.create_table(
        "waitpoint_signal",
        sa.Column("waitpoint_id", sa.String(36), primary_key=True),
        sa.Column("seq", sa.Integer(), primary_key=True),
        # PENDING | SUCCEEDED | FAILED | CANCELLED | NOT_DISPATCHED
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("ref_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("result_ref", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "node_run_waitpoint",
        sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("node_id", sa.String(64), primary_key=True),
        sa.Column("waitpoint_id", sa.String(36), primary_key=True),
    )

    # ── 2.4 ──────────────────────────────────────────────────────────────────
    op.create_table(
        "wakeup",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("node_run_id", sa.String(64), nullable=False,
                  server_default=""),
        # job_done | waitpoint_due | approval | child_run | resource_free
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "node_run_id", "kind", "due_at",
                            name="uq_wakeup_khu_trung"),
    )
    op.create_index("ix_wakeup_run_id", "wakeup", ["run_id"])
    op.create_index("ix_wakeup_due", "wakeup", ["due_at"],
                    postgresql_where=sa.text(_WK_DUE),
                    sqlite_where=sa.text(_WK_DUE))


def downgrade() -> None:
    op.drop_index("ix_wakeup_due", table_name="wakeup")
    op.drop_index("ix_wakeup_run_id", table_name="wakeup")
    op.drop_table("wakeup")
    op.drop_table("node_run_waitpoint")
    op.drop_table("waitpoint_signal")
    op.drop_index("ix_waitpoint_due", table_name="waitpoint")
    op.drop_index("ux_waitpoint_idem", table_name="waitpoint")
    op.drop_index("ix_waitpoint_run_id", table_name="waitpoint")
    op.drop_table("waitpoint")
