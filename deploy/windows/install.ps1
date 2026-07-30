<#
.SYNOPSIS
    Install the LTT AI Studio web dashboard on a Windows Server (P9).

.DESCRIPTION
    Creates the C:\LTTPlatform layout, builds an isolated virtual
    environment, installs dependencies, and registers the app as a Windows
    service via NSSM so it survives reboots without an RDP login.

    Runtime data, secrets and logs live OUTSIDE the release directory
    (ADR-009), so update.ps1 can replace the code without touching them.

    This script does NOT configure DNS and does NOT open firewall ports -
    both are deliberate manual steps, documented in
    docs/DEPLOY_APP_LTTSTUDIOS.md.

.EXAMPLE
    .\install.ps1 -SourceZip C:\Temp\ltt-release-0.9.0.zip
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SourceZip,
    [string]$Root = 'C:\LTTPlatform',
    [string]$PythonExe = 'python',
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }

if (-not (Test-Path $SourceZip)) { throw "Release archive not found: $SourceZip" }

$release  = Join-Path $Root 'app'
$dataDir  = Join-Path $Root 'data'
$secrets  = Join-Path $Root 'secrets'
$logs     = Join-Path $Root 'logs'
$backups  = Join-Path $Root 'backups'
$venv     = Join-Path $Root 'venv'

Write-Step 'Creating directory layout'
foreach ($d in @($Root, $dataDir, $secrets, $logs, $backups)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}
Write-Ok "Layout ready under $Root"

Write-Step 'Extracting release'
if (Test-Path $release) {
    throw "$release already exists. Use update.ps1 to upgrade an existing install."
}
Expand-Archive -Path $SourceZip -DestinationPath $release -Force
Write-Ok "Extracted to $release"

Write-Step 'Creating virtual environment'
& $PythonExe -m venv $venv
if ($LASTEXITCODE -ne 0) { throw "Failed to create venv with '$PythonExe'" }
$venvPy = Join-Path $venv 'Scripts\python.exe'
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r (Join-Path $release 'requirements.txt') --quiet
& $venvPy -m pip install -r (Join-Path $release 'requirements-server.txt') --quiet
Write-Ok 'Dependencies installed'

Write-Step 'Provisioning runtime configuration'
# Without this the app starts but /health/ready reports 503 forever,
# because load_settings() cannot find data\config.json. An existing
# config is never overwritten - that would destroy an operator's real
# column mapping on every update (ADR-009).
$cfg = Join-Path $dataDir 'config.json'
if (Test-Path $cfg) {
    Write-Ok "Existing config.json kept untouched"
} else {
    $example = Join-Path $release 'config.example.json'
    if (Test-Path $example) {
        Copy-Item $example -Destination $cfg -Force
        Write-Ok "Created $cfg from config.example.json"
        Write-Host '  [ACTION REQUIRED] Edit it with your real Google Sheet id,' -ForegroundColor Yellow
        Write-Host '                    column names and app credentials.' -ForegroundColor Yellow
    } else {
        throw "config.example.json missing from the release - cannot provision config."
    }
}

Write-Step 'Securing the secrets directory'
# Only SYSTEM, Administrators and the service account may read secrets.
icacls $secrets /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" | Out-Null
Write-Ok "ACLs applied to $secrets (inheritance removed)"

Write-Step 'Checking for required secrets'
$envFile = Join-Path $secrets 'app.env'
if (-not (Test-Path $envFile)) {
    @(
        '# LTT AI Studio production secrets - NEVER commit this file.',
        '# Generate the password hash with:  python tools\hash_admin_password.py',
        'LTT_ENV=production',
        'LTT_ADMIN_USERNAME=admin',
        'LTT_ADMIN_PASSWORD_HASH=',
        'LTT_SESSION_SECRET=',
        'LTT_TOKEN_ENCRYPTION_KEY=',
        "LTT_DATA_DIR=$dataDir",
        "LTT_SECRETS_DIR=$secrets",
        "LTT_LOGS_DIR=$logs"
    ) -join "`r`n" | ForEach-Object {
        # WriteAllText with UTF8Encoding($false) = no BOM. PowerShell 5.1's
        # `-Encoding utf8` writes a BOM, and a BOM ahead of the first line of
        # a KEY=VALUE file corrupts that first key name for any parser that
        # does not strip it. The same trap took the live config.json down.
        [IO.File]::WriteAllText($envFile, $_, (New-Object Text.UTF8Encoding($false)))
    }
    Write-Host "  [ACTION REQUIRED] Fill in $envFile before starting the service." -ForegroundColor Yellow
    Write-Host "    LTT_SESSION_SECRET     : run  python -c `"import secrets;print(secrets.token_urlsafe(32))`"" -ForegroundColor Yellow
    Write-Host "    LTT_TOKEN_ENCRYPTION_KEY: same generator; keep it forever (ADR-013)" -ForegroundColor Yellow
    Write-Host "    LTT_ADMIN_PASSWORD_HASH : run  python tools\hash_admin_password.py" -ForegroundColor Yellow
} else {
    Write-Ok "Existing $envFile kept untouched"
}

Write-Step 'Registering the Windows service'
$nssm = Get-Command nssm.exe -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Host '  [SKIP] nssm.exe not on PATH - install NSSM, then re-run this step.' -ForegroundColor Yellow
    Write-Host '         choco install nssm    (or download from https://nssm.cc)' -ForegroundColor Yellow
} else {
    $svc = 'LTTStudioWeb'
    if (Get-Service -Name $svc -ErrorAction SilentlyContinue) {
        Write-Host "  [SKIP] Service $svc already exists." -ForegroundColor Yellow
    } else {
        nssm install $svc $venvPy "-m uvicorn server.run:app --host 127.0.0.1 --port $Port"
        nssm set $svc AppDirectory $release
        nssm set $svc AppStdout (Join-Path $logs 'service-out.log')
        nssm set $svc AppStderr (Join-Path $logs 'service-err.log')
        nssm set $svc AppRotateFiles 1
        nssm set $svc Start SERVICE_AUTO_START
        # Restart on failure, with a delay so a crash loop cannot spin.
        nssm set $svc AppExit Default Restart
        nssm set $svc AppRestartDelay 10000
        Write-Ok "Service $svc registered (not started yet)"
    }
}

Write-Step 'Next steps'
Write-Host @"
  1. Fill in $envFile (see ACTION REQUIRED above).
  2. Load it into the service environment:
       .\set-service-env.ps1
  3. Start the service:
       Start-Service LTTStudioWeb
  4. Verify locally BEFORE exposing it publicly:
       curl http://127.0.0.1:$Port/health/ready
  5. Configure Caddy + DNS + firewall - see docs\DEPLOY_APP_LTTSTUDIOS.md
"@ -ForegroundColor White
