"""Chi muc BO PHAN duy nhat cho `dedupe_key` cua job chua ket thuc.

Revision ID: c9d4e1a77b02
Revises: f2c48b71e903
Create Date: 2026-09-07

## VI SAO

`jobs.submit()` chong double-submit bang cach `SELECT` job cung `dedupe_key`
chua ket thuc, roi moi `INSERT` neu khong thay. Giua hai cau do la mot **cua so
tranh chap that**: hai request song song (F5, hai tab, script goi API) cung thay
"chua co", cung chen — va khach bi tru tien HAI LAN cho mot yeu cau.

Ba he doc lap da hoi tu ve dung loi giai nay, cuong che bang CSDL chu khong bang
ma can than:

    Activepieces   UNIQUE(flowRunId, stepName)
    n8n            UNIQUE(deduplicationKey) WHERE deduplicationKey IS NOT NULL
    Trigger.dev    UNIQUE(environmentId, idempotencyKey)

Xem `docs/architecture/workflow_v2_audit/12_19 muc 16`.

## VI SAO PHAI LA CHI MUC BO PHAN

Hai ve, ca hai deu bat buoc:

  dedupe_key <> ''                       `dedupe_key` mac dinh la chuoi rong va
                                         phan lon job khong dung no. Mot UNIQUE
                                         day du se chan MOI job thu hai cua mot
                                         nguoi dung.

  status IN ('queued', 'running')        Xong roi thi gui lai cung yeu cau la hop
                                         le (bam "Tao lai"), va job cu van phai
                                         nam do lam bang chung cho so tien.

## ⛔ VI SAO MIGRATION NAY DUNG LAI THAY VI TU DON

Neu CSDL da co cap trung tu truoc, tao chi muc duy nhat se that bai. Cach "sua"
hien nhien la huy bot job trung — nhung **huy mot job la mot hanh dong cham so
tien** (giu cho credit, hoan tien), va mot migration khong phai cho de quyet dinh
dieu do trong im lang.

⇒ Migration nay **do truoc, dung lai va noi ro** neu thay cap trung. Operator
   quyet dinh huy cai nao, roi chay lai. Khong co du lieu nao bi mat.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c9d4e1a77b02"
down_revision = "f2c48b71e903"
branch_labels = None
depends_on = None


_DIEU_KIEN = "dedupe_key <> '' AND status IN ('queued', 'running')"

_DEM_TRUNG = sa.text(
    "SELECT user_id, dedupe_key, COUNT(*) AS so_dong "
    "FROM jobs "
    f"WHERE {_DIEU_KIEN} "
    "GROUP BY user_id, dedupe_key "
    "HAVING COUNT(*) > 1"
)


def upgrade() -> None:
    trung = list(op.get_bind().execute(_DEM_TRUNG))
    if trung:
        chi_tiet = "; ".join(
            f"user_id={row[0]} dedupe_key={row[1]!r} co {row[2]} dong"
            for row in trung[:20]
        )
        raise RuntimeError(
            "Khong tao duoc chi muc `ux_jobs_dedupe_active`: da co "
            f"{len(trung)} cap job trung `dedupe_key` va chua ket thuc. "
            "Migration KHONG tu huy job vi huy job cham so credit. "
            "Hay xem lai va huy bot bang duong quan tri, roi chay lai. "
            f"Chi tiet: {chi_tiet}"
        )

    op.create_index(
        "ux_jobs_dedupe_active",
        "jobs",
        ["user_id", "dedupe_key"],
        unique=True,
        postgresql_where=sa.text(_DIEU_KIEN),
        sqlite_where=sa.text(_DIEU_KIEN),
    )


def downgrade() -> None:
    op.drop_index("ux_jobs_dedupe_active", table_name="jobs")
