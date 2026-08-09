<#
.SYNOPSIS
    Roll back to the previous release kept by update.ps1 (P9).

.DESCRIPTION
    Swaps app.previous back into place. Runtime data is NOT rolled back -
    reverting a database to an older state would discard real publishing
    history. If you need the data restored too, run restore.ps1 explicitly
    and deliberately.
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$ServiceName = 'LTTStudioWeb',
    [string]$WorkerServiceName = 'LTTStudioWorker',
    [string]$CodexServiceName = 'LTTStudioCodex',
    [switch]$SkipServiceControl,
    [int]$Port = 8100
)

$ErrorActionPreference = 'Stop'

$release  = Join-Path $Root 'app'
$previous = Join-Path $Root 'app.previous'
$failed   = Join-Path $Root 'app.failed'

if (-not (Test-Path $previous)) {
    throw "No previous release at $previous - nothing to roll back to."
}

Write-Host "`n=== Rolling back ===" -ForegroundColor Cyan

if (-not $SkipServiceControl -and (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue)) {
    foreach ($name in @($CodexServiceName, $WorkerServiceName, $ServiceName)) {
        Stop-Service $name -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 5
}

# Keep the bad release for post-mortem instead of deleting it.
if (Test-Path $failed) { Remove-Item $failed -Recurse -Force }
if (Test-Path $release) { Move-Item $release $failed }
Move-Item $previous $release
Write-Host "  [OK] Previous release restored (bad release kept at $failed)" -ForegroundColor Green

if ($SkipServiceControl) {
    Write-Host '  [OK] Rehearsal complete; service control and health check skipped.' -ForegroundColor Green
    exit 0
}

Start-Service $ServiceName
Start-Service $WorkerServiceName -ErrorAction SilentlyContinue
Start-Service $CodexServiceName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 8

try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health/ready" -TimeoutSec 15
    if ($resp.status -ne 'ready') { throw "readiness reported '$($resp.status)'" }
    Write-Host "  [OK] Service healthy after rollback (status: $($resp.status))" -ForegroundColor Green
} catch {
    Write-Host "  [WARNING] Rollback completed but health check failed: $_" -ForegroundColor Red
    Write-Host "  Inspect $Root\logs\service-err.log" -ForegroundColor Yellow
    exit 1
}
