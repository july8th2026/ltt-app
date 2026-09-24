-- HAU_KIEM_BANG_ASV_PROD.sql
-- ============================================================================
-- Chay tep nay SAU KHI da COMMIT TAO_BANG_ASV_PROD.sql, tren cung CSDL
-- `lttplatform`. CHI DOC (SELECT), khong ghi gi.
--
-- ⚠️ Hoi CATALOG (information_schema / to_regclass), TUYET DOI KHONG hoi
-- `alembic_version` de ket luan "da xong": chinh alembic_version la thu da
-- BAO SAI trong sự co nay -- no van noi "da o head" trong 20 ngay lien tuc
-- trong khi ca 5 bang khong ton tai (xem SU_CO_ASV_ASSET_PROD.md).
-- ============================================================================

-- 1) Ca 5 bang phai ton tai (khong dong nao duoc NULL).
SELECT to_regclass('public.asv_run')       AS asv_run,
       to_regclass('public.asv_stage')     AS asv_stage,
       to_regclass('public.asv_asset')     AS asv_asset,
       to_regclass('public.asv_work_item') AS asv_work_item,
       to_regclass('public.asv_usage')     AS asv_usage;

-- 2) So cot tung bang -- doi chieu voi bang so sanh model<->DDL:
--      asv_run = 12, asv_stage = 14, asv_asset = 13,
--      asv_work_item = 15, asv_usage = 15
SELECT table_name, count(*) AS so_cot
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name IN ('asv_run', 'asv_stage', 'asv_asset',
                       'asv_work_item', 'asv_usage')
 GROUP BY table_name
 ORDER BY table_name;

-- 3) Khoa chinh + rang buoc UNIQUE tung bang (phai co dung nhu migration khai):
--      asv_run        : PK(id)
--      asv_stage      : PK(id), UNIQUE(run_id, stage)
--      asv_asset      : PK(id), UNIQUE(storage_key)
--      asv_work_item  : PK(id), UNIQUE(run_id, stage, item_key)
--      asv_usage      : PK(id), UNIQUE(run_id, ma_dispatch)
SELECT tc.table_name, tc.constraint_type, tc.constraint_name,
       string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) AS cot
  FROM information_schema.table_constraints tc
  JOIN information_schema.key_column_usage kcu
    ON kcu.constraint_name = tc.constraint_name
   AND kcu.table_schema = tc.table_schema
 WHERE tc.table_schema = 'public'
   AND tc.table_name IN ('asv_run', 'asv_stage', 'asv_asset',
                          'asv_work_item', 'asv_usage')
   AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
 GROUP BY tc.table_name, tc.constraint_type, tc.constraint_name
 ORDER BY tc.table_name, tc.constraint_type;

-- 4) Danh sach index tung bang (doi chieu voi so luong trong TAO_BANG_ASV_PROD.sql:
--    asv_run 4, asv_stage 5, asv_asset 5, asv_work_item 5, asv_usage 5 --
--    KHONG tinh index cua PK/UNIQUE, Postgres tu tao rieng cho hai loai do).
SELECT tablename, indexname
  FROM pg_indexes
 WHERE schemaname = 'public'
   AND tablename IN ('asv_run', 'asv_stage', 'asv_asset',
                      'asv_work_item', 'asv_usage')
 ORDER BY tablename, indexname;

-- 5) Xac nhan KHONG co foreign key tren 5 bang nay (dung thiet ke -- xem
--    dau TAO_BANG_ASV_PROD.sql). Ket qua ky vong: 0 dong.
SELECT tc.table_name, tc.constraint_name
  FROM information_schema.table_constraints tc
 WHERE tc.table_schema = 'public'
   AND tc.table_name IN ('asv_run', 'asv_stage', 'asv_asset',
                          'asv_work_item', 'asv_usage')
   AND tc.constraint_type = 'FOREIGN KEY';

-- 6) Doi chung: cac bang duoc THAM CHIEU KHAI NIEM (khong FK cuong che) da
--    co san tren production truoc khi 5 bang ASV duoc tao.
SELECT to_regclass('public.users') AS users,
       to_regclass('public.jobs')  AS jobs;
