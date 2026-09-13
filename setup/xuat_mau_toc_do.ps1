<#
.SYNOPSIS
    Xuat ban thu tieng Viet o nhieu toc do (nghe thu), voi app.env cua production.

.DESCRIPTION
    Nap app.env vao TIEN TRINH NAY (can Administrator vi app.env bi ACL khoa) de
    co LTT_VOICE_SIDECAR_TOKEN, roi chay tools\xuat_mau_toc_do.py bang vieneu-venv.
    Khong in gia tri tu app.env.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\xuat_mau_toc_do.ps1 `
        -RaDir "G:\My Drive\AI\A\Voice"

.NOTES
    Can Administrator. Pure ASCII. Kich lo tong hop GPU may A ~1 phut - bao phien
    khac neu ho dang do do tre tang nen tang may A.
#>
[CmdletBinding()]
param(
    [string]$Root   = 'C:\LTTPlatform',
    [string]$Repo   = '',
    [Parameter(Mandatory=$true)][string]$RaDir,
    [string]$Preset = ''
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'vieneu-venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\xuat_mau_toc_do.py'
foreach ($p in @($envFile, $venvPy, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Can quyen Administrator de doc $envFile" }

# Ten bien vong lap phai KHONG trung tham so cua chinh script (PowerShell khong
# phan biet hoa thuong). Dung $bienEnv nhu chay_thu_giong.ps1.
$so = 0
foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    $bienEnv = $d.Substring(0, $i).Trim()
    if ($bienEnv) { Set-Item -Path "Env:$bienEnv" -Value $d.Substring($i + 1); $so++ }
}
Write-Host "  [OK] Nap $so bien tu app.env (khong in gia tri)" -ForegroundColor Green

$doiSo = @('--ra-dir', $RaDir)
if ($Preset) { $doiSo += @('--preset', $Preset) }

$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
