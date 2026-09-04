"""Noi hai cot nhan ID CUA APP tu VARCHAR(36) len VARCHAR(64).

Revision ID: b3f6a1d70c52
Revises: 7d2c1e9f4a03
Create Date: 2026-09-05

## VI SAO: mot ky tu, va no lam luot chay TRA TIEN dau tien chet o production

    AsvRun.id          = "asvr_" + 32 hex  =  37 ky tu
    credit_entries.job_id = VARCHAR(36)

HAI cho truyen `run.id` vao mot cot 36:

    features.py:140   credit.giu_cho(..., run.id)   -> credit_entries.job_id
    jobs.py:237       jobs.submit(plan_id=run.id)   -> jobs.plan_id

Ca hai tran dung MOT ky tu. Cai thu hai an sau cai thu nhat: no chi lo ra
sau khi cai thu nhat duoc sua, vi lan chay khong di toi do.

## VI SAO KHONG AI THAY TRONG 29 PHA

Production chay **PostgreSQL**, cuong che do dai cot. Moi bai test cua Auto Scan
chay tren **SQLite**, KHONG cuong che — SQLite coi `VARCHAR(36)` la mot goi y.
Va Auto Scan chua tung chay o production (`enabled=False`), nen khong con duong
nao khac de bat duoc no.

⇒ Khach TRA TIEN dau tien bam chay se nhan mot loi CSDL tho, **truoc khi he
  thong lam bat cu viec gi**:

    psycopg.errors.StringDataRightTruncation:
        value too long for type character varying(36)

No lo ra o lan chay DAU TIEN sau khi bo nghiem thu duoc chuyen sang PostgreSQL,
trong bay giay.

## VI SAO NOI COT CHU KHONG RUT NGAN ID

`36` la do dai cua mot UUID co dau gach — tuc cot nay duoc dat kich thuoc cho
**mot** lo id, roi moi lo id khac phai vua vao no. Nhung id co TIEN TO la mot
lua chon co chu dinh va co ich: `asvr_`, `vc_`, `upl_` noi ngay id do la gi
trong log va trong bao loi, va chan viec vo tinh truyen mot id khac vao dung
cho nay. Rut ngan id de vua mot cot la de cai duoi quyet dinh cai tren.

⚠️ `64` chu khong phai `48`: cot nay nhan id cua MOI app, khong rieng Auto Scan,
   va con so tiep theo bi ep se lai la mot lan sua nua. 64 du cho mot tien to
   hop ly cong mot UUID day du (36 + 28).

## ⛔ CAC COT `job_id` KHAC KHONG DOI

`execution_leases`, `upload_sessions`, `gpu_leases` cung khai `String(36)`,
nhung chung giu id job cua NEN TANG — nhung id do la UUID that. Noi ca ba theo
la doi mot luoc do vi mot loi chua xay ra o do; khi nao co bang chung thi sua.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b3f6a1d70c52"
down_revision = "7d2c1e9f4a03"
branch_labels = None
depends_on = None


#: (bang, cot) nhan mot ID CUA APP chu khong phai job id cua nen tang.
COT = (("credit_entries", "job_id"), ("jobs", "plan_id"))


def upgrade() -> None:
    for bang, cot in COT:
        with op.batch_alter_table(bang) as batch:
            batch.alter_column(cot,
                               existing_type=sa.String(36),
                               type_=sa.String(64),
                               existing_nullable=False,
                               existing_server_default=None)


def downgrade() -> None:
    # ⚠️ Ha xuong 36 se CAT bat ky `job_id` nao dai hon — tuc lam hong chinh
    #    nhung but toan ma ban nang cap nay sinh ra de ghi duoc. Giu nguyen
    #    phep ha de alembic co duong lui, nhung nguoi chay phai biet dieu do.
    for bang, cot in COT:
        with op.batch_alter_table(bang) as batch:
            batch.alter_column(cot,
                               existing_type=sa.String(64),
                               type_=sa.String(36),
                               existing_nullable=False,
                               existing_server_default=None)
