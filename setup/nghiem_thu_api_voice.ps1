<#
.SYNOPSIS
    Nghiem thu speech.ltt qua /api/v1 (muc 12-14 + chat luong) voi app.env production.

.DESCRIPTION
    Nap app.env vao tien trinh (can Administrator) de co LTT_DATABASE_URL + pepper,
    roi chay tools\nghiem_thu_api_voice.py bang PLATFORM venv (sqlalchemy+requests).
    Tool tu mint key tam, chay ma tran quote/job, va REVOKE key trong finally.
    Khong in token.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\nghiem_thu_api_voice.ps1 `
        -TaiVe "D:\...\api_job.wav"

.NOTES
    Can Administrator. Pure ASCII. Cham production (loopback 8100) + GPU may A cho 1 job.
#>
[CmdletBinding()]
param(
    [string]$Root  = 'C:\LTTPlatform',
    [string]$Repo  = '',
    [string]$Email = '',
    [string]$TaiVe = ''
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\nghiem_thu_api_voice.py'
foreach ($p in @($envFile, $venvPy, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Can quyen Administrator de doc $envFile" }

$so = 0
foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    $bienEnv = $d.Substring(0, $i).Trim()
    if ($bienEnv) { Set-Item -Path "Env:$bienEnv" -Value $d.Substring($i + 1); $so++ }
}
Write-Host "  [OK] Nap $so bien tu app.env (khong in gia tri)" -ForegroundColor Green

$doiSo = @()
if ($Email) { $doiSo += @('--email', $Email) }
if ($TaiVe) { $doiSo += @('--tai-ve', $TaiVe) }

$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
