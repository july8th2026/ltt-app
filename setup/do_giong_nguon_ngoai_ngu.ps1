<#
.SYNOPSIS
    Put one cloned voice into the platform's shared library.

.DESCRIPTION
    Same narrow bridge as chay_thu_giong.ps1: read app.env into THIS process
    only, run one named tool, exit. Never prints a value from app.env.

    Writes one row. It never flips more than one voice per run, on purpose:
    a cloned voice is a person's biometric data.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\do_giong_nguon_ngoai_ngu.ps1

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = '',
    [int]$Vong = 2
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\do_giong_nguon_ngoai_ngu.py'
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
    # Ten bien phai KHONG trung mot tham so nao cua chinh script -- PowerShell
    # khong phan biet hoa thuong. Xem tools/check_ps_bien_trung_tham_so.py.
    $bienEnv = $d.Substring(0, $i).Trim()
    if ($bienEnv) { Set-Item -Path "Env:$bienEnv" -Value $d.Substring($i + 1); $so++ }
}
Write-Host "  [OK] Nap $so bien tu app.env (khong in gia tri)" -ForegroundColor Green
$env:PYTHONPATH = $Repo

$doiSo = @('--vong', "$Vong")

# Xem chu thich cung ten trong chay_thu_giong.ps1: voi 'Stop', mot exe ngoai ghi
# ra stderr se ket thuc script truoc khi doc duoc $LASTEXITCODE.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
