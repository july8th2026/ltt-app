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
    [string]$WorkerServiceName = 'LTTStudioWorker',
    [string]$CodexServiceName = 'LTTStudioCodex',
    [int]$Port = 8100
)

$ErrorActionPreference = 'Stop'

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'update.ps1 must run in an elevated Administrator PowerShell.'
}

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
    foreach ($name in @($CodexServiceName, $WorkerServiceName, $ServiceName)) {
        $service = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($service -and $service.Status -ne 'Stopped') {
            Stop-Service $name -Force -ErrorAction Stop
            $service.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
        }
        $after = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($after -and $after.Status -ne 'Stopped') {
            throw "Service $name did not stop; refusing to rotate the release."
        }
    }
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

Write-Step 'Applying database migrations'
# Bat buoc: ban phat hanh doi schema ma khong nang cap thi service boot tren
# schema cu -> loi runtime kho truy hoac hong du lieu. Chay alembic tren ban MOI
# TRUOC khi start. LTT_DATABASE_URL lay tu app.env (service doc env qua NSSM,
# tien trinh nay thi khong). Mirror dung cach setup/2-cai-dat.ps1 lam.
$envFileForMig = Join-Path $Root 'secrets\app.env'
if ((Test-Path $envFileForMig) -and ((Get-Content $envFileForMig -Raw) -match '(?m)^LTT_DATABASE_URL=(.+)$')) {
    $env:LTT_DATABASE_URL = $Matches[1].Trim()
    Push-Location $release
    & $venvPy -m alembic upgrade head
    $rc = $LASTEXITCODE
    Pop-Location
    $env:LTT_DATABASE_URL = $null
    if ($rc -ne 0) { throw 'alembic upgrade head that bai - dung lai, roll back bang .\rollback.ps1' }
    Write-Ok 'Database migrations applied'
} else {
    throw 'Khong doc duoc LTT_DATABASE_URL tu secrets\app.env - khong the chay migration. Dung lai.'
}

Write-Step 'Starting service'
Start-Service $ServiceName
Start-Service $WorkerServiceName -ErrorAction SilentlyContinue
Start-Service $CodexServiceName -ErrorAction SilentlyContinue
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
