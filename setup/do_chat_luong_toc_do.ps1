<#
.SYNOPSIS
    Do chat luong giong o BIEN SPEED (DNSMOS + ASR) voi app.env cua production.

.DESCRIPTION
    Cung mot cau noi hep nhu chay_thu_giong.ps1: doc app.env vao TIEN TRINH NAY
    thoi, chay mot tool, thoat. Khong bao gio in gia tri tu app.env.

    Nap app.env de co:
      - LTT_VOICE_SIDECAR_TOKEN : goi sidecar tong hop giong (GPU may A)
      - HF_HOME                 : noi model DNSMOS da tai (voice_sidecar/dnsmos)

    Tool ghi JSONL + in phan phoi. Ket qua la BANG CHUNG, luu duoi
    test-results\voice-acceptance\ (gitignored).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\do_chat_luong_toc_do.ps1 `
        -Ra test-results\voice-acceptance\chat_luong_toc_do.jsonl

.NOTES
    Can Administrator (de doc app.env bi ACL khoa). Pure ASCII (CLAUDE.md rule 16).
    LUU Y VAN HANH: no kich mot lo tong hop tren GPU may A. Bao phien khac truoc
    khi chay neu ho dang do do tre o tang nen tang may A.
#>
[CmdletBinding()]
param(
    [string]$Root   = 'C:\LTTPlatform',
    [string]$Repo   = '',
    [string]$Preset = '',
    [string]$Ra     = '',
    [switch]$BoAsr
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

# !! vieneu-venv, KHONG phai venv nen tang: DNSMOS can onnxruntime + soundfile
#    chi co o vieneu-venv. Harness goi sidecar qua HTTP (requests, co san day)
#    nen khong can platform_core/sqlalchemy.
$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'vieneu-venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\do_chat_luong_toc_do.py'
foreach ($p in @($envFile, $venvPy, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Can quyen Administrator de doc $envFile" }

# !! Ten bien vong lap phai KHONG trung tham so cua chinh script (PowerShell
#    khong phan biet hoa thuong). Dung $bienEnv nhu chay_thu_giong.ps1.
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
if ($Preset) { $doiSo += @('--preset', $Preset) }
if ($Ra)     { $doiSo += @('--ra', $Ra) }
if ($BoAsr)  { $doiSo += @('--bo-asr') }

# Ha ErrorActionPreference quanh loi goi ngoai: python ghi stderr vi nhieu ly do
# binh thuong (SyntaxWarning) va voi 'Stop' no thanh NativeCommandError ket thuc
# script truoc khi doc duoc exit code. Xem chay_thu_giong.ps1.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
