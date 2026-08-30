<#
.SYNOPSIS
    Run tools/tai_khoan_thu.py with production's environment loaded.

.DESCRIPTION
    `secrets\app.env` is ACL-locked (only the service account and Administrators
    can read it), which is correct. But that also means a maintenance tool run by
    hand cannot see LTT_DATABASE_URL, so it cannot reach the database at all.

    This script is the narrow bridge: read app.env, put it in THIS process only,
    run one specific tool, exit. It never writes app.env, never touches a service,
    and never prints a value from it.

    WHY NARROW ON PURPOSE. A general "run any command with the production
    environment" helper is a much more useful tool -- and that is exactly why it
    should not exist casually: it turns every future shell into one that can read
    the token encryption key. This one names its tool in the code.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\tai_khoan_thu.ps1 -LietKe
    powershell -ExecutionPolicy Bypass -File .\setup\tai_khoan_thu.ps1 -DatLaiMatKhau

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root  = 'C:\LTTPlatform',
    [string]$Repo  = '',
    [string]$Email = '',
    [switch]$DatLaiMatKhau,
    [switch]$LietKe
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\tai_khoan_thu.py'

foreach ($p in @($envFile, $venvPy, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw "Can quyen Administrator de doc $envFile (ACL cua no la dung, dung noi long)."
}

# utf-8-sig: nuot BOM neu ai do soan tep bang cong cu chen BOM. Quy tac 1 noi dung
# GHI BOM; doc thi phai chiu duoc.
$so = 0
foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    $ten = $d.Substring(0, $i).Trim()
    $gt  = $d.Substring($i + 1)
    if ($ten) {
        # KHONG in gia tri nao: tep nay giu khoa ma hoa token va mat khau CSDL.
        Set-Item -Path "Env:$ten" -Value $gt
        $so++
    }
}
Write-Host "  [OK] Nap $so bien tu app.env vao tien trinh nay (khong in gia tri)" -ForegroundColor Green

# !! CANH BAO CHO NGUOI CHAY: cong cu nay IN MAT KHAU ra man hinh mot lan.
#
#    Dung chuyen huong toan bo (`*> file.log`) khi chay no. Ngay 2026-08-30 toi
#    da lam dung the va mat khau nam trong `C:\LTTPlatform\logs\` cho toi khi
#    xoa tay. Mot bi mat trong thu muc log la mot bi mat trong moi ban sao luu.
#
#    Muon giu ban ghi thi chuyen huong RIENG stderr (`2> file.log`) va doc mat
#    khau tren man hinh.
$doiSo = @()
if ($Email)         { $doiSo += @('--email', $Email) }
if ($DatLaiMatKhau) { $doiSo += '--dat-lai-mat-khau' }
if ($LietKe)        { $doiSo += '--liet-ke' }

& $venvPy $tool @doiSo
exit $LASTEXITCODE
