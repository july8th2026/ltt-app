<#
.SYNOPSIS
    K0 buoc 1: sinh tieng bang HE CU (F5-TTS da tinh chinh).

.DESCRIPTION
    Cung cay cau hep nhu cac wrapper khac: doc app.env vao RIENG tien trinh
    nay, chay mot cong cu, thoat. Khong bao gio in mot gia tri tu app.env.

    !! KHAC MOI WRAPPER KHAC: no chay PYTHON CUA HE CU
    (D:\Voiceclone_TTS\venv), khong phai venv nao cua ta. `engine_router` cua
    ho tu sinh mot tien trinh con chay `venv_f5tts` de nap checkpoint F5.

    !! Cham GPU. Dung chay cung luc voi mot lo anh, mot job video, hay bo do
    giong -- ca ba deu dung chung card.

    !! Kho cu la CHI DOC. Kich ban dem so tep trong speakers/ truoc va sau,
    va bao neu lech.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\k0_sinh_f5.ps1

.NOTES
    Can Administrator (de doc app.env bi khoa ACL).
    Thuan ASCII (CLAUDE.md quy tac 2).
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = ''
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
# Python cua HE CU. Khong doc tu app.env: no khong phai mot bi mat, va no
# khong phai mot phan cua nen tang nay.
$venvPy  = 'D:\Voiceclone_TTS\venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\k0_sinh_f5.py'
foreach ($p in @($envFile, $tool, $venvPy)) {
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

# !! KHONG dat PYTHONPATH sang kho cua ta. Kich ban tu chen duong dan kho cu
#    vao sys.path, va tron hai cay import se nap nham module cung ten -- ca hai
#    kho deu co `src/` va deu co `tools/`.
$env:PYTHONPATH = ''
Write-Host '  [!] Kho cu la CHI DOC -- dem so tep truoc/sau, bao neu lech.' -ForegroundColor Yellow

# Xem chu thich cung ten trong chay_thu_giong.ps1: voi 'Stop', mot exe ngoai ghi
# ra stderr se ket thuc script truoc khi doc duoc $LASTEXITCODE.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
