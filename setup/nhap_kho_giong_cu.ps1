<#
.SYNOPSIS
    Enroll one voice on production, going through the real HTTPS door.

.DESCRIPTION
    Same narrow bridge as chay_thu_giong.ps1: read app.env into THIS process
    only, run one named tool, exit. Never prints a value from app.env.

    Unlike chay_thu_giong.ps1, the tool posts over HTTPS with the csrf_token it
    scraped from the rendered page. A script that called submit_with_credit
    directly would stay green even with CSRF broken -- and CSRF broken is
    exactly what killed every POST door of this app on 31/08.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup
hap_kho_giong_cu.ps1 -Xem
    powershell -ExecutionPolicy Bypass -File .\setup
hap_kho_giong_cu.ps1 -Nhap

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root  = 'C:\LTTPlatform',
    [string]$Repo  = '',
    [string]$Email = '',
    [string]$Chi   = '',
    [switch]$Xem,
    [switch]$Nhap,
    [int]$ChoGiay  = 600
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\nhap_kho_giong_cu.py'
# KHONG kiem $Clip nua: cong cu nay tu tim clip da noi trong tmp/giong_cu
# va TU BAO neu thieu, kem lenh sinh lai. Kiem o day se chan ca che do
# --Xem, tuc chan dung cai che do dung de biet minh dang thieu gi.
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
    # !! KHONG dat ten bien la $ten O DAY. PowerShell khong phan biet hoa
    #    thuong, nen $ten va tham so -Ten LA MOT BIEN. Vong lap nay se ghi de
    #    -Ten bang ten bien moi truong CUOI CUNG trong app.env, va giong duoc
    #    tao ra mang ten "HF_HOME". Da xay ra that 31/08, hai luot lien.
    $bienEnv = $d.Substring(0, $i).Trim()
    if ($bienEnv) { Set-Item -Path "Env:$bienEnv" -Value $d.Substring($i + 1); $so++ }
}
Write-Host "  [OK] Nap $so bien tu app.env (khong in gia tri)" -ForegroundColor Green
$env:PYTHONPATH = $Repo

$doiSo = @('--cho-giay', "$ChoGiay")
if ($Email) { $doiSo += @('--email', $Email) }
if ($Chi)   { $doiSo += @('--chi',   $Chi) }
if ($Nhap)  { $doiSo += '--nhap' }

# !! Xem chu thich cung ten trong chay_thu_giong.ps1: voi 'Stop', mot exe ngoai
#    ghi ra stderr se ket thuc script truoc khi doc duoc $LASTEXITCODE.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
