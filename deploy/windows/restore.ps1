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

Expand-Archive -Path $Archive -DestinationPath (Join-Path $Root 'data') -Force
Write-Host '  [OK] Data restored' -ForegroundColor Green

Start-Service $ServiceName
Write-Host '  Service restarted. Verify: curl http://127.0.0.1:8000/health/ready' -ForegroundColor Cyan
