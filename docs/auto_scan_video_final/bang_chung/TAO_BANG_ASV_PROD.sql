-- TAO_BANG_ASV_PROD.sql
-- ============================================================================
-- MUC DICH: tao 5 bang `asv_*` con thieu tren production (CSDL `lttplatform`),
-- vi alembic_version da o head nhung cac migration ASV chua tung THUC THI
-- (bi day tay qua, xem docs/auto_scan_video_final/SU_CO_ASV_ASSET_PROD.md).
--
-- NGUON DDL (sinh 24/09/2026, phien lam viec `asvf-bang-prod`):
--   1. alembic/versions/20260901_1800_asv_run_va_stage.py   (asv_run, asv_stage)
--   2. alembic/versions/20260901_1930_asv_asset.py          (asv_asset)
--   3. alembic/versions/20260903_0300_asv_work_item.py      (asv_work_item)
--   4. alembic/versions/20260903_1000_asv_usage.py          (asv_usage)
--   Da grep toan bo `alembic/versions/*.py` (moi revision SAU bon tep tren)
--   tim add_column/alter_column/create_index cham bang `asv_*` -> KHONG co
--   revision nao khac dung toi cac bang nay. Bon migration goc la TOAN BO
--   lich su schema cua chung.
--
--   Doi chieu (khop tuyet doi, khong lech mot cot/chi so nao) bang
--   `sqlalchemy.schema.CreateTable`/`CreateIndex` chay truc tiep tren
--   `Base.metadata` cua model that (apps/auto_scan_video/tables.py:
--   AsvRun, AsvStage, AsvAsset, AsvWorkItem, AsvUsage), dialect PostgreSQL.
--
-- RANG BUOC NGOAI (foreign key): KHONG CO. Ca migration lan model deu KHONG
-- khai bat cu ForeignKey/ForeignKeyConstraint nao cho 5 bang nay -- day la
-- lua chon co y cua tac gia app (xem docstring dau
-- apps/auto_scan_video/tables.py va cac migration): `owner_id` tham chieu
-- KHAI NIEM toi `users.id`, `asv_stage.job_id` tham chieu KHAI NIEM toi
-- `jobs.id`, va `run_id`/`stage`/`item_key` la tham chieu noi bo giua chinh
-- 5 bang nay -- nhung KHONG cot nao trong so do duoc CSDL cuong che bang
-- FOREIGN KEY. Da do THAT tren production (chi doc, khong ghi):
--   to_regclass('users') -> 'users'   (CO)
--   to_regclass('jobs')  -> 'jobs'    (CO)
--   to_regclass('asv_run' | 'asv_stage' | 'asv_asset' | 'asv_work_item'
--               | 'asv_usage') -> NULL (ca 5 deu CHUA CO, do 24/09/2026)
-- => Vi khong co FK duoc khai bao, thu tu tao 5 bang duoi day KHONG bi CSDL
--    ep buoc, nhung van giu THEO DUNG THU TU migration/logic phu thuoc:
--    asv_run -> asv_stage -> asv_asset -> asv_work_item -> asv_usage.
--
-- SO COT (model == DDL sinh == DDL migration cong don, doi chieu 24/09):
--   asv_run        12 cot | asv_stage      14 cot | asv_asset   13 cot
--   asv_work_item  15 cot | asv_usage      15 cot
--
-- AN TOAN CHAY LAI: moi CREATE TABLE/INDEX deu co IF NOT EXISTS -- chay lai
-- tren mot CSDL da co du 5 bang la vo hai (no-op).
--
-- CAU LENH KIEM HAU KIEM (chay SAU khi COMMIT, xem chi tiet o cuoi tep va o
-- tep di kem HAU_KIEM_BANG_ASV_PROD.sql): dem cot tung bang qua
-- information_schema.columns + to_regclass ca 5 bang. HAU KIEM PHAI HOI
-- CATALOG (information_schema / to_regclass), KHONG duoc hoi lai
-- `alembic_version` -- chinh alembic_version la thu da noi doi trong su co
-- nay (no van bao "da o head" trong khi 5 bang khong ton tai).
-- ============================================================================

BEGIN;

-- ── 1. asv_run ───────────────────────────────────────────────────────────
-- Nguon: alembic/versions/20260901_1800_asv_run_va_stage.py (revision e1a7c04b93d2)
CREATE TABLE IF NOT EXISTS asv_run (
    id                  VARCHAR(48)              NOT NULL,
    owner_id            VARCHAR(36)              NOT NULL,
    status              VARCHAR(16)              NOT NULL DEFAULT 'queued',
    contract_version    VARCHAR(32)              NOT NULL DEFAULT 'auto_scan_mvp_v1',
    settings            JSON                     NOT NULL,
    source_key          VARCHAR(255)             NOT NULL DEFAULT '',
    credit_held         INTEGER                  NOT NULL DEFAULT 0,
    credit_actual       INTEGER                  NOT NULL DEFAULT 0,
    revision            INTEGER                  NOT NULL DEFAULT 1,
    error               TEXT                     NOT NULL DEFAULT '',
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at         TIMESTAMP WITH TIME ZONE,
    CONSTRAINT asv_run_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_asv_run_owner_id      ON asv_run (owner_id);
CREATE INDEX IF NOT EXISTS ix_asv_run_status        ON asv_run (status);
CREATE INDEX IF NOT EXISTS ix_asv_run_created_at    ON asv_run (created_at);
CREATE INDEX IF NOT EXISTS ix_asv_run_owner_created ON asv_run (owner_id, created_at);

-- ── 2. asv_stage ─────────────────────────────────────────────────────────
-- Nguon: alembic/versions/20260901_1800_asv_run_va_stage.py (revision e1a7c04b93d2)
CREATE TABLE IF NOT EXISTS asv_stage (
    id                  VARCHAR(48)              NOT NULL,
    run_id              VARCHAR(48)              NOT NULL,
    owner_id            VARCHAR(36)              NOT NULL,
    stage               VARCHAR(32)              NOT NULL,
    status              VARCHAR(24)              NOT NULL DEFAULT 'pending',
    attempt             INTEGER                  NOT NULL DEFAULT 0,
    fingerprint         VARCHAR(64)              NOT NULL DEFAULT '',
    outputs             JSON                     NOT NULL,
    job_id              VARCHAR(36)              NOT NULL DEFAULT '',
    credit_actual       INTEGER                  NOT NULL DEFAULT 0,
    revision            INTEGER                  NOT NULL DEFAULT 1,
    error               TEXT                     NOT NULL DEFAULT '',
    started_at          TIMESTAMP WITH TIME ZONE,
    finished_at         TIMESTAMP WITH TIME ZONE,
    CONSTRAINT asv_stage_pkey PRIMARY KEY (id),
    CONSTRAINT ux_asv_stage_run_stage UNIQUE (run_id, stage)
);

CREATE INDEX IF NOT EXISTS ix_asv_stage_run_id      ON asv_stage (run_id);
CREATE INDEX IF NOT EXISTS ix_asv_stage_owner_id    ON asv_stage (owner_id);
CREATE INDEX IF NOT EXISTS ix_asv_stage_status      ON asv_stage (status);
CREATE INDEX IF NOT EXISTS ix_asv_stage_job_id      ON asv_stage (job_id);
CREATE INDEX IF NOT EXISTS ix_asv_stage_run_status  ON asv_stage (run_id, status);

-- ── 3. asv_asset ─────────────────────────────────────────────────────────
-- Nguon: alembic/versions/20260901_1930_asv_asset.py (revision f2b8d16e05a3)
CREATE TABLE IF NOT EXISTS asv_asset (
    id                  VARCHAR(48)              NOT NULL,
    owner_id            VARCHAR(36)              NOT NULL,
    run_id              VARCHAR(48)              NOT NULL,
    created_by_stage    VARCHAR(32)              NOT NULL DEFAULT '',
    kind                VARCHAR(16)              NOT NULL,
    storage_key         VARCHAR(512)             NOT NULL,
    size                INTEGER                  NOT NULL DEFAULT 0,
    checksum            VARCHAR(64)              NOT NULL DEFAULT '',
    parent_keys         JSON                     NOT NULL,
    schema_version      INTEGER                  NOT NULL DEFAULT 1,
    integrity           VARCHAR(16)              NOT NULL DEFAULT 'ok',
    expires_at          TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT asv_asset_pkey PRIMARY KEY (id),
    CONSTRAINT ux_asv_asset_storage_key UNIQUE (storage_key)
);

CREATE INDEX IF NOT EXISTS ix_asv_asset_owner_id    ON asv_asset (owner_id);
CREATE INDEX IF NOT EXISTS ix_asv_asset_run_id      ON asv_asset (run_id);
CREATE INDEX IF NOT EXISTS ix_asv_asset_integrity   ON asv_asset (integrity);
CREATE INDEX IF NOT EXISTS ix_asv_asset_run_stage   ON asv_asset (run_id, created_by_stage);
CREATE INDEX IF NOT EXISTS ix_asv_asset_owner_run   ON asv_asset (owner_id, run_id);

-- ── 4. asv_work_item ─────────────────────────────────────────────────────
-- Nguon: alembic/versions/20260903_0300_asv_work_item.py (revision a4c17f9b62d0)
CREATE TABLE IF NOT EXISTS asv_work_item (
    id                  VARCHAR(48)              NOT NULL,
    run_id              VARCHAR(48)              NOT NULL,
    owner_id            VARCHAR(36)              NOT NULL,
    stage               VARCHAR(32)              NOT NULL,
    item_key            VARCHAR(64)              NOT NULL,
    status              VARCHAR(24)              NOT NULL DEFAULT 'pending',
    attempt             INTEGER                  NOT NULL DEFAULT 0,
    fingerprint         VARCHAR(64)              NOT NULL DEFAULT '',
    outputs             JSON                     NOT NULL,
    credit_actual       INTEGER                  NOT NULL DEFAULT 0,
    revision            INTEGER                  NOT NULL DEFAULT 1,
    error               TEXT                     NOT NULL DEFAULT '',
    started_at          TIMESTAMP WITH TIME ZONE,
    finished_at         TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT asv_work_item_pkey PRIMARY KEY (id),
    CONSTRAINT ux_asv_work_item_run_stage_key UNIQUE (run_id, stage, item_key)
);

CREATE INDEX IF NOT EXISTS ix_asv_work_item_run_id             ON asv_work_item (run_id);
CREATE INDEX IF NOT EXISTS ix_asv_work_item_owner_id           ON asv_work_item (owner_id);
CREATE INDEX IF NOT EXISTS ix_asv_work_item_status             ON asv_work_item (status);
CREATE INDEX IF NOT EXISTS ix_asv_work_item_run_stage_status   ON asv_work_item (run_id, stage, status);
CREATE INDEX IF NOT EXISTS ix_asv_work_item_owner_run          ON asv_work_item (owner_id, run_id);

-- ── 5. asv_usage ─────────────────────────────────────────────────────────
-- Nguon: alembic/versions/20260903_1000_asv_usage.py (revision c81d3f5a90e7)
CREATE TABLE IF NOT EXISTS asv_usage (
    id                  VARCHAR(48)              NOT NULL,
    run_id              VARCHAR(48)              NOT NULL,
    owner_id            VARCHAR(36)              NOT NULL,
    stage               VARCHAR(32)              NOT NULL,
    item_key            VARCHAR(64)              NOT NULL,
    attempt             INTEGER                  NOT NULL DEFAULT 0,
    nang_luc            VARCHAR(64)              NOT NULL,
    app_chu             VARCHAR(32)              NOT NULL,
    trang_thai          VARCHAR(16)              NOT NULL,
    don_vi              VARCHAR(16)              NOT NULL DEFAULT '',
    so_luong            FLOAT                    NOT NULL DEFAULT 0,
    credit              INTEGER                  NOT NULL DEFAULT 0,
    ma_dispatch         VARCHAR(64)              NOT NULL,
    ghi_chu             JSON                     NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT asv_usage_pkey PRIMARY KEY (id),
    CONSTRAINT ux_asv_usage_run_dispatch UNIQUE (run_id, ma_dispatch)
);

CREATE INDEX IF NOT EXISTS ix_asv_usage_run_id            ON asv_usage (run_id);
CREATE INDEX IF NOT EXISTS ix_asv_usage_owner_id          ON asv_usage (owner_id);
CREATE INDEX IF NOT EXISTS ix_asv_usage_trang_thai        ON asv_usage (trang_thai);
CREATE INDEX IF NOT EXISTS ix_asv_usage_run_stage_item    ON asv_usage (run_id, stage, item_key);
CREATE INDEX IF NOT EXISTS ix_asv_usage_run_trang_thai    ON asv_usage (run_id, trang_thai);

COMMIT;

-- ============================================================================
-- HAU KIEM (chay SAU COMMIT, chi doc -- hoi CATALOG, KHONG hoi alembic_version)
-- Xem ban day du dang tach rieng o
-- docs/auto_scan_video_final/bang_chung/HAU_KIEM_BANG_ASV_PROD.sql
-- ============================================================================

-- 1) Ca 5 bang phai deu KHAC NULL:
-- SELECT to_regclass('asv_run')       AS asv_run,
--        to_regclass('asv_stage')     AS asv_stage,
--        to_regclass('asv_asset')     AS asv_asset,
--        to_regclass('asv_work_item') AS asv_work_item,
--        to_regclass('asv_usage')     AS asv_usage;

-- 2) So cot tung bang phai khop dung 12/14/13/15/15 (xem bang so sanh dau tep):
-- SELECT table_name, count(*) AS so_cot
--   FROM information_schema.columns
--  WHERE table_schema = 'public'
--    AND table_name IN ('asv_run','asv_stage','asv_asset','asv_work_item','asv_usage')
--  GROUP BY table_name
--  ORDER BY table_name;
