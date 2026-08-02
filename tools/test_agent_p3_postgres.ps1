<# Isolated PostgreSQL migration/concurrency test for Agent P3. ASCII only. #>
[CmdletBinding()]
param(
    [string]$PgBin = 'C:\Program Files\PostgreSQL\17\bin',
    [string]$AppEnvFile = 'secrets\app.env',
    [string]$SuperuserPasswordFile = 'secrets\postgres-superuser.txt'
)

$ErrorActionPreference = 'Stop'
$envText = Get-Content -Raw -LiteralPath $AppEnvFile
if ($envText -notmatch '(?m)^LTT_DATABASE_URL=(postgresql\+?\w*://([^:]+):([^@]+)@([^:/]+):(\d+)/(\S+))\s*$') {
    throw 'Cannot parse LTT_DATABASE_URL.'
}
$dbHost = $Matches[4]
$dbPort = $Matches[5]
$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$dbName = "ltt_agent_p3_test_$stamp"
$restoreDb = "ltt_agent_p3_restore_$stamp"
if ($dbName -notmatch '^ltt_agent_p3_test_[0-9]{14}$' -or
    $restoreDb -notmatch '^ltt_agent_p3_restore_[0-9]{14}$') {
    throw 'Invalid test database name.'
}
$probeDir = Join-Path $env:TEMP "ltt_agent_p3_$stamp"
New-Item -ItemType Directory -Path $probeDir | Out-Null
$dumpFile = Join-Path $probeDir 'agent-p3.dump'
$superPassword = (Get-Content -Raw -LiteralPath $SuperuserPasswordFile).Trim()
$encodedPassword = [Uri]::EscapeDataString($superPassword)
$testUrl = "postgresql+psycopg://postgres:$encodedPassword@$dbHost`:$dbPort/$dbName"

$env:PGPASSWORD = $superPassword
try {
    & (Join-Path $PgBin 'createdb.exe') -h $dbHost -p $dbPort -U postgres $dbName
    if ($LASTEXITCODE -ne 0) { throw 'createdb failed' }
    & (Join-Path $PgBin 'createdb.exe') -h $dbHost -p $dbPort -U postgres $restoreDb
    if ($LASTEXITCODE -ne 0) { throw 'createdb restore failed' }
    $env:PGPASSWORD = $null
    $env:LTT_DATABASE_URL = $testUrl
    $env:LTT_TEST_DATABASE_URL = $testUrl

    & python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'alembic upgrade failed' }
    & python -m alembic downgrade b2c3d4e5f6a7
    if ($LASTEXITCODE -ne 0) { throw 'alembic downgrade failed' }
    & python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'alembic re-upgrade failed' }
    & python -m pytest -q tests/test_73_dong_thoi_pg.py
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL concurrency tests failed' }
    $env:PGPASSWORD = $superPassword
    # The concurrency fixture intentionally drops all tables. Recreate the
    # isolated DB so Alembic cannot be fooled by a stale version table.
    & (Join-Path $PgBin 'dropdb.exe') -h $dbHost -p $dbPort -U postgres --if-exists $dbName
    if ($LASTEXITCODE -ne 0) { throw 'dropdb before restore rehearsal failed' }
    & (Join-Path $PgBin 'createdb.exe') -h $dbHost -p $dbPort -U postgres $dbName
    if ($LASTEXITCODE -ne 0) { throw 'recreate database failed' }
    $env:PGPASSWORD = $null
    & python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'alembic upgrade before restore rehearsal failed' }
    $env:PGPASSWORD = $superPassword
    $probeSql = "INSERT INTO agent_runs(id,user_id,app_slug,goal,plan,checkpoint,status,budget_max,estimated,actual,approved_by,decision_log,version,created_at) VALUES ('p3-restore-probe','probe-user','agent','probe','{}','{}','planning',0,0,0,'','[]',1,now());"
    & (Join-Path $PgBin 'psql.exe') -h $dbHost -p $dbPort -U postgres -d $dbName -v ON_ERROR_STOP=1 -q -c $probeSql
    if ($LASTEXITCODE -ne 0) { throw 'insert restore probe failed' }
    $workflowSql = "INSERT INTO agent_workflows(id,user_id,name,goal,plan_version,nodes,edges,viewport,status,budget_max,estimated,revision,source_workflow_id,created_at,updated_at) VALUES ('p10-workflow-probe','probe-user','probe','probe',1,'[]','[]','{}','draft',0,0,1,'',now(),now());"
    & (Join-Path $PgBin 'psql.exe') -h $dbHost -p $dbPort -U postgres -d $dbName -v ON_ERROR_STOP=1 -q -c $workflowSql
    if ($LASTEXITCODE -ne 0) { throw 'insert workflow restore probe failed' }
    & (Join-Path $PgBin 'pg_dump.exe') -h $dbHost -p $dbPort -U postgres -d $dbName -Fc -f $dumpFile
    if ($LASTEXITCODE -ne 0) { throw 'P3 pg_dump failed' }
    & (Join-Path $PgBin 'pg_restore.exe') -h $dbHost -p $dbPort -U postgres -d $restoreDb --no-owner -1 $dumpFile
    if ($LASTEXITCODE -ne 0) { throw 'P3 pg_restore failed' }
    $probeCount = & (Join-Path $PgBin 'psql.exe') -h $dbHost -p $dbPort -U postgres -d $restoreDb -Atq -c "SELECT count(*) FROM agent_runs WHERE id='p3-restore-probe';"
    if ($LASTEXITCODE -ne 0 -or $probeCount.Trim() -ne '1') { throw 'P3 restore verification failed' }
    $workflowCount = & (Join-Path $PgBin 'psql.exe') -h $dbHost -p $dbPort -U postgres -d $restoreDb -Atq -c "SELECT count(*) FROM agent_workflows WHERE id='p10-workflow-probe';"
    if ($LASTEXITCODE -ne 0 -or $workflowCount.Trim() -ne '1') { throw 'P10 workflow restore verification failed' }
    Write-Output 'AGENT_P10_POSTGRES=PASS; migration up/down/up; concurrency; workflow restore'
}
finally {
    $env:LTT_DATABASE_URL = $null
    $env:LTT_TEST_DATABASE_URL = $null
    $env:PGPASSWORD = $superPassword
    & (Join-Path $PgBin 'dropdb.exe') -h $dbHost -p $dbPort -U postgres --if-exists $restoreDb | Out-Null
    & (Join-Path $PgBin 'dropdb.exe') -h $dbHost -p $dbPort -U postgres --if-exists $dbName | Out-Null
    $env:PGPASSWORD = $null
    $superPassword = $null
    $encodedPassword = $null
    $resolved = (Resolve-Path -LiteralPath $probeDir -ErrorAction SilentlyContinue).Path
    $tempRoot = (Resolve-Path -LiteralPath $env:TEMP).Path
    $safeLeaf = $resolved -and (Split-Path $resolved -Leaf) -match '^ltt_agent_p3_[0-9]{14}$'
    if ($safeLeaf -and $resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
