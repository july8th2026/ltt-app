<#
.SYNOPSIS
    Restore a data backup produced by backup.ps1 (P7/P9).

.DESCRIPTION
    Defaults to restoring into an ISOLATED directory so a restore
    rehearsal can be verified without touching live data - this is the
    "restore rehearsal" P7 requires.

    Pass -Live to overwrite the real data directory. That path stops the
    service first and takes a safety backup of current data beforehand,
    because overwriting live publishing history is irreversible.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [string]$Root = 'C:\LTTPlatform',
    [string]$ServiceName = 'LTTStudioWeb',
    [switch]$Live
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Archive)) { throw "Archive not found: $Archive" }

if (-not $Live) {
    $target = Join-Path $Root ('restore_test_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Expand-Archive -Path $Archive -DestinationPath $target -Force
    Write-Host "  [OK] Rehearsal restore into $target" -ForegroundColor Green
    Get-ChildItem $target | ForEach-Object { Write-Host "      $($_.Name)  ($($_.Length) bytes)" }
    Write-Host "`n  Live data was NOT modified. Re-run with -Live to restore for real." -ForegroundColor Cyan
    exit 0
}

Write-Host "`n  [!] LIVE RESTORE - current data will be overwritten." -ForegroundColor Red
$confirm = Read-Host '      Type RESTORE to continue'
if ($confirm -ne 'RESTORE') { Write-Host '  Aborted.' -ForegroundColor Yellow; exit 1 }

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 5
}

# Safety net: never overwrite live data without a copy of what was there.
& (Join-Path $PSScriptRoot 'backup.ps1') -Root $Root -Stamp ('pre_restore_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))

$dataDir = Join-Path $Root 'data'
Expand-Archive -Path $Archive -DestinationPath $dataDir -Force
Write-Host '  [OK] Files restored (config, tokens, audit log)' -ForegroundColor Green

# ---- PostgreSQL ------------------------------------------------------------
# Giai nen KHONG khoi phuc CSDL: du lieu that nam trong PostgreSQL, ban sao la
# file <db>.dump do pg_dump -Fc tao. Phai pg_restore no, neu khong "khoi phuc"
# chi tra lai config/token con TAT CA nguoi dung/credit/job thi mat trang.
$envFile = Join-Path $Root 'secrets\app.env'
if (Test-Path $envFile) {
    $envText = Get-Content $envFile -Raw
    if ($envText -match '(?m)^LTT_DATABASE_URL=postgresql\+?\w*://([^:]+):([^@]+)@([^:/]+):(\d+)/(\S+)\s*$') {
        $dbUser = $Matches[1]; $dbPass = $Matches[2]
        $dbHost = $Matches[3]; $dbPort = $Matches[4]; $dbName = $Matches[5]
        $dumpFile = Join-Path $dataDir "$dbName.dump"
        if (-not (Test-Path $dumpFile)) {
            throw "Khong thay $dbName.dump trong ban sao luu. Ban sao nay KHONG co CSDL - dung lai de khong tuong da khoi phuc."
        }

        $pgRestore = $null
        foreach ($v in @('18','17','16','15','14')) {
            $c = "C:\Program Files\PostgreSQL\$v\bin\pg_restore.exe"
            if (Test-Path $c) { $pgRestore = $c; break }
        }
        if (-not $pgRestore) {
            $cmd = Get-Command pg_restore.exe -ErrorAction SilentlyContinue
            if ($cmd) { $pgRestore = $cmd.Source }
        }
        if (-not $pgRestore) { throw 'Co dump nhung khong tim thay pg_restore.exe. Dung lai.' }

        $env:PGPASSWORD = $dbPass
        # --clean --if-exists: xoa doi tuong cu roi nap lai (khoi phuc that su,
        # khong chi chen them). --no-owner: bo qua chu so huu de khong ket owner
        # cu. -1: mot transaction, loi thi rollback het (khong de CSDL nua voi).
        & $pgRestore -U $dbUser -h $dbHost -p $dbPort -d $dbName --clean --if-exists --no-owner -1 $dumpFile
        $rc = $LASTEXITCODE
        $env:PGPASSWORD = $null
        if ($rc -ne 0) {
            throw "pg_restore that bai (ma $rc). CSDL co the chua khoi phuc day du - kiem tra truoc khi chay tiep."
        }
        Remove-Item $dumpFile -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] pg_restore: $dbName" -ForegroundColor Green
    }
}

Start-Service $ServiceName
Write-Host '  Service restarted. Verify: curl http://127.0.0.1:8100/health/ready' -ForegroundColor Cyan
