<#
.SYNOPSIS
    Mint a one-time SSO ticket for the .local TEST account and print its URL.

.DESCRIPTION
    Same narrow bridge as tai_khoan_thu.ps1: read app.env into THIS process only,
    run one named tool, exit. It prints exactly one line -- the URL.

    The ticket lives 90 seconds and is single-use (platform_core/nexus/sso.py).
    Open it immediately; a printed ticket left sitting is a dead ticket.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\ve_dang_nhap_thu.ps1

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root  = 'C:\LTTPlatform',
    [string]$Repo  = '',
    [string]$Email = '',
    [string]$Goc   = ''
)

$ErrorActionPreference = 'Stop'

# --------------------------------------------------------------- Invoke-Ngoai
# Voi 'Stop', mot exe NGOAI ghi ra stderr se thanh NativeCommandError va KET
# THUC script -- ke ca khi exe do tra ve 0. Xem chu thich day du trong
# deploy\windows\install-vieneu-sidecar.ps1.
function Invoke-Ngoai {
    param([Parameter(Mandatory = $true)][scriptblock]$Khoi)
    $truoc = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Khoi } finally { $ErrorActionPreference = $truoc }
}

if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\ve_dang_nhap_thu.py'
foreach ($p in @($envFile, $venvPy, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Can quyen Administrator de doc $envFile" }

foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    $ten = $d.Substring(0, $i).Trim()
    if ($ten) { Set-Item -Path "Env:$ten" -Value $d.Substring($i + 1) }
}

$doiSo = @()
if ($Email) { $doiSo += @('--email', $Email) }
if ($Goc)   { $doiSo += @('--goc',   $Goc) }

Invoke-Ngoai { & $venvPy $tool @doiSo }
exit $LASTEXITCODE
