<#
.SYNOPSIS
    Rename the display names of the platform's shared voices.

.DESCRIPTION
    Same narrow bridge as dat_giong_dung_chung.ps1: read app.env into THIS
    process only, run one named tool, exit. Never prints a value from app.env.

    Only `ten_hien_thi` changes. `public_id` (vc_<32 hex>) is the API contract
    and is never touched, so callers using voice_id see no change at all.

    All 25 rows change in ONE transaction, or none do. A half-renamed library
    leaves no record of which rows were already done.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\doi_ten_giong_chung.ps1 -Xem
    powershell -ExecutionPolicy Bypass -File .\setup\doi_ten_giong_chung.ps1 -Ap

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = '',
    [switch]$Xem,
    [switch]$Ap
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\doi_ten_giong_chung.py'
foreach ($p in @($envFile, $venvPy, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Can quyen Administrator de doc $envFile" }

# Ten bien phai KHONG trung mot tham so nao cua chinh script -- PowerShell
# khong phan biet hoa thuong. Xem tools/check_ps_bien_trung_tham_so.py.
$soBien = 0
foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    $bienEnv = $d.Substring(0, $i).Trim()
    if ($bienEnv) { Set-Item -Path "Env:$bienEnv" -Value $d.Substring($i + 1); $soBien++ }
}
Write-Host "  [OK] Nap $soBien bien tu app.env (khong in gia tri)" -ForegroundColor Green
$env:PYTHONPATH = $Repo

$doiSo = @()
if ($Xem) { $doiSo += '--xem' }
if ($Ap)  { $doiSo += '--ap' }
if (-not $Xem -and -not $Ap) { $doiSo += '--xem' }

# Xem chu thich cung ten trong chay_thu_giong.ps1: voi 'Stop', mot exe ngoai ghi
# ra stderr se ket thuc script truoc khi doc duoc $LASTEXITCODE.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
