<# Isolated PostgreSQL dump/restore rehearsal for the Agent P3 entry gate. #>
[CmdletBinding()]
param(
    [string]$PgBin = 'C:\Program Files\PostgreSQL\17\bin',
    [string]$HostName = '127.0.0.1',
    [int]$Port = 5432,
    [string]$SuperuserPasswordFile = 'secrets\postgres-superuser.txt'
)

$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$srcDb = "ltt_agent_restore_src_$stamp"
$dstDb = "ltt_agent_restore_dst_$stamp"
if ($srcDb -notmatch '^ltt_agent_restore_src_[0-9]{14}$' -or
    $dstDb -notmatch '^ltt_agent_restore_dst_[0-9]{14}$') {
    throw 'Invalid temporary database name.'
}

$probeDir = Join-Path $env:TEMP "ltt_agent_restore_$stamp"
New-Item -ItemType Directory -Path $probeDir | Out-Null
$dumpFile = Join-Path $probeDir 'probe.dump'
$env:PGPASSWORD = (Get-Content -Raw -LiteralPath $SuperuserPasswordFile).Trim()

try {
    & (Join-Path $PgBin 'createdb.exe') -h $HostName -p $Port -U postgres $srcDb
    if ($LASTEXITCODE -ne 0) { throw 'createdb source failed' }
    & (Join-Path $PgBin 'createdb.exe') -h $HostName -p $Port -U postgres $dstDb
    if ($LASTEXITCODE -ne 0) { throw 'createdb destination failed' }

    $seedSql = "CREATE TABLE restore_probe(id integer PRIMARY KEY, marker text NOT NULL); INSERT INTO restore_probe VALUES (1, 'agent-p3-restore-ok');"
    & (Join-Path $PgBin 'psql.exe') -h $HostName -p $Port -U postgres -d $srcDb -v ON_ERROR_STOP=1 -q -c $seedSql
    if ($LASTEXITCODE -ne 0) { throw 'seed source failed' }

    & (Join-Path $PgBin 'pg_dump.exe') -h $HostName -p $Port -U postgres -d $srcDb -Fc -f $dumpFile
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $dumpFile)) {
        throw 'pg_dump failed'
    }
    & (Join-Path $PgBin 'pg_restore.exe') -h $HostName -p $Port -U postgres -d $dstDb --no-owner -1 $dumpFile
    if ($LASTEXITCODE -ne 0) { throw 'pg_restore failed' }

    $verifySql = "SELECT count(*) FROM restore_probe WHERE marker='agent-p3-restore-ok';"
    $count = & (Join-Path $PgBin 'psql.exe') -h $HostName -p $Port -U postgres -d $dstDb -Atq -c $verifySql
    if ($LASTEXITCODE -ne 0 -or $count.Trim() -ne '1') {
        throw 'restore verification failed'
    }
    Write-Output 'RESTORE_DRILL=PASS; isolated temp databases; probe rows=1'
}
finally {
    & (Join-Path $PgBin 'dropdb.exe') -h $HostName -p $Port -U postgres --if-exists $dstDb | Out-Null
    & (Join-Path $PgBin 'dropdb.exe') -h $HostName -p $Port -U postgres --if-exists $srcDb | Out-Null
    $env:PGPASSWORD = $null

    $resolved = (Resolve-Path -LiteralPath $probeDir -ErrorAction SilentlyContinue).Path
    $tempRoot = (Resolve-Path -LiteralPath $env:TEMP).Path
    $safeLeaf = $resolved -and (Split-Path $resolved -Leaf) -match '^ltt_agent_restore_[0-9]{14}$'
    if ($safeLeaf -and $resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
