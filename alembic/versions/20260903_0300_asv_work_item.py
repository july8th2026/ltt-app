"""Bang checkpoint theo don vi viec cua Auto Scan Video: asv_work_item.

Revision ID: a4c17f9b62d0
Revises: f2b8d16e05a3
Create Date: 2026-09-03

## VI SAO CAN MOT DON VI NHO HON MOT GIAI DOAN

`AsvStage` giu MOT dong cho moi `(run_id, stage)`, va no da lam dung viec cua no
suot hai muoi pha. V4 doi ba thu ma mot dong moi giai doan khong dien dat duoc:

  G5   viec dat tien theo doan phai checkpoint va dung lai duoc don vi con hop le
  G12  vong lap chinh do dai theo doan phai CO CHAN va dung lai doan da dat
  G14  sua loi phai nham vao pham vi hong NHO NHAT, khong chay lai ca run

Va cai gia cua viec khong co no da do duoc. `apps/ltt_voice` xuat mot hop dong
cong khai dang hoan chinh (`ToolSpec("speech.ltt")` -> `ltt_voice.synthesize`),
nhung mot job sinh ra MOT tep khoa theo `job_id`, con `asv_stage` chi giu MOT
`job_id` cho moi giai doan. Sinh tieng tung doan can N. Nen pha 12 cua V2 khong
uy quyen duoc, va theo doi tien do bang **su ton tai cua tep tren dia** — mot
checkpoint khong van tay, khong chi phi, khong so lan thu, khong chu so huu.

⇒ Bang nay la thu mo khoa pha 09 va pha 15. Xem
   `docs/auto_scan_video_v4/CAPABILITY_INVENTORY_V4.md` muc 3.

## ⛔ VI SAO NO KHONG PHAI MOT HANG DOI THU HAI

`V4_OPERATING_CONTRACT` A.5 cho phep them dong checkpoint va cam them mot hang
doi worker-claim. Hai thu do khac nhau o **dung nhung cot cho phep mot worker tu
chon viec**, va khong cot nao trong so do co mat o day:

    claimed_by · worker_id · locked_by · lease_until
    visible_at · available_at · priority · heartbeat_at

`tests/test_427` chot su vang mat do, kem mot phep tu kiem chay bo do tren mot
bang gia CO chung — de "khong co cot xau" khong bi nham voi "bo do hong".

Chieu khang dinh: dong o bang nay duoc ghi boi chinh handler cua giai doan, ma
handler do da dang giu mot `Job` cua nen tang. Khong cho nao doc bang nay de
quyet dinh chay gi tiep theo.

## RANG BUOC CHIU LUC

`UNIQUE(run_id, stage, item_key)` — hai worker khong tao duoc hai dong cho cung
mot don vi viec, nen "doan 47 da sinh tieng chua" co dung MOT cau tra loi.

⚠️ Khai NGAY TRONG `create_table`: SQLite khong ALTER duoc rang buoc, va ca bo
   test cua kho chay tren SQLite. Cung ghi chu voi hai migration ASV truoc.

## ROLLBACK

Them thuan tuy. Khong cot nao cua bang cu doi kieu hay doi y nghia, nen
`downgrade` la mot `drop_table` va moi dong `asv_run`/`asv_stage`/`asv_asset` da
co van doc duoc y nguyen. Mot lan chay tao truoc migration nay khong co dong item
nao, va do la trang thai hop le: giai doan nao chua chia don vi viec thi tu ghi
`credit_actual` cua chinh no nhu truoc.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a4c17f9b62d0"
down_revision = "f2b8d16e05a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asv_work_item",
        sa.Column("id", sa.String(length=48), primary_key=True),
        sa.Column("run_id", sa.String(length=48), nullable=False),
        # Chu so huu o COT, khong chi trong khoa luu tru: mot phep tra "cua ai"
        # phai la mot dieu kien WHERE, khong phai mot phep phan tich duong dan.
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("item_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False,
                  server_default="pending"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fingerprint", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.Column("outputs", sa.JSON(), nullable=False),
        # DO DUOC, khong tinh lai tu bang gia (ADR-001 D4).
        sa.Column("credit_actual", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "stage", "item_key",
                            name="ux_asv_work_item_run_stage_key"),
    )
    op.create_index("ix_asv_work_item_run_id", "asv_work_item", ["run_id"])
    op.create_index("ix_asv_work_item_owner_id", "asv_work_item", ["owner_id"])
    op.create_index("ix_asv_work_item_status", "asv_work_item", ["status"])
    op.create_index("ix_asv_work_item_run_stage_status", "asv_work_item",
                    ["run_id", "stage", "status"])
    op.create_index("ix_asv_work_item_owner_run", "asv_work_item",
                    ["owner_id", "run_id"])


def downgrade() -> None:
    op.drop_index("ix_asv_work_item_owner_run", table_name="asv_work_item")
    op.drop_index("ix_asv_work_item_run_stage_status", table_name="asv_work_item")
    op.drop_index("ix_asv_work_item_status", table_name="asv_work_item")
    op.drop_index("ix_asv_work_item_owner_id", table_name="asv_work_item")
    op.drop_index("ix_asv_work_item_run_id", table_name="asv_work_item")
    op.drop_table("asv_work_item")
