<#
.SYNOPSIS
    Upgrade an existing LTT AI Studio install to a new release (P9).

.DESCRIPTION
    Keeps the previous release directory so rollback.ps1 can restore it in
    seconds. Runtime data, secrets and logs live outside the release
    directory and are never touched (ADR-009).

    Sequence: stop service -> back up data -> keep previous release ->
    extract new release -> reinstall deps -> start -> verify /health/ready.
    Any failure leaves the previous release in place for rollback.ps1.

.EXAMPLE
    .\update.ps1 -SourceZip C:\Temp\ltt-release-0.9.1.zip
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SourceZip,
    [string]$Root = 'C:\LTTPlatform',
    [string]$ServiceName = 'LTTStudioWeb',
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }

if (-not (Test-Path $SourceZip)) { throw "Release archive not found: $SourceZip" }

$release  = Join-Path $Root 'app'
$previous = Join-Path $Root 'app.previous'
$venvPy   = Join-Path $Root 'venv\Scripts\python.exe'

Write-Step 'Backing up runtime data first'
& (Join-Path $PSScriptRoot 'backup.ps1') -Root $Root
Write-Ok 'Data backup complete'

Write-Step 'Stopping service'
if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service $ServiceName -Force -ErrorAction SilentlyContinue
    # Give the worker a moment to release its SessionLocks cleanly.
    Start-Sleep -Seconds 5
    Write-Ok "$ServiceName stopped"
} else {
    Write-Host "  [SKIP] Service $ServiceName not installed" -ForegroundColor Yellow
}

Write-Step 'Rotating release directories'
if (Test-Path $previous) { Remove-Item $previous -Recurse -Force }
if (Test-Path $release)  { Move-Item $release $previous }
Write-Ok "Previous release preserved at $previous"

Write-Step 'Extracting new release'
Expand-Archive -Path $SourceZip -DestinationPath $release -Force
Write-Ok "Extracted to $release"

Write-Step 'Ensuring runtime configuration exists'
# Self-heal for installs made by an older installer that did not seed
# config.json. Without it the service starts and reports /health/ready
# = 503 forever. An existing config is never overwritten.
$cfg = Join-Path $Root 'data\config.json'
if (Test-Path $cfg) {
    Write-Ok 'Existing config.json kept untouched'
} else {
    $example = Join-Path $release 'config.example.json'
    if (Test-Path $example) {
        Copy-Item $example -Destination $cfg -Force
        Write-Ok "Created $cfg from config.example.json"
        Write-Host '  [ACTION REQUIRED] Edit it with your real sheet id and column names.' -ForegroundColor Yellow
    } else {
        throw 'config.example.json missing from the release.'
    }
}

Write-Step 'Updating dependencies'
& $venvPy -m pip install -r (Join-Path $release 'requirements.txt') --quiet
& $venvPy -m pip install -r (Join-Path $release 'requirements-server.txt') --quiet
Write-Ok 'Dependencies updated'

Write-Step 'Starting service'
Start-Service $ServiceName
Start-Sleep -Seconds 8

Write-Step 'Verifying health'
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health/ready" -TimeoutSec 15
    if ($resp.status -ne 'ready') { throw "readiness reported '$($resp.status)'" }
    Write-Ok "Service healthy (environment: $($resp.environment))"
    Write-Host "`nUpdate complete. If anything looks wrong, run: .\rollback.ps1" -ForegroundColor Cyan
} catch {
    Write-Host "`n  [FAILED] Health check did not pass: $_" -ForegroundColor Red
    Write-Host '  The previous release is still available. Roll back with:' -ForegroundColor Yellow
    Write-Host '    .\rollback.ps1' -ForegroundColor Yellow
    exit 1
}
