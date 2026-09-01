<#
.SYNOPSIS
    Score the OLD system's voice library with the NEW measuring suite.

.DESCRIPTION
    Same narrow bridge as chay_thu_giong.ps1: read app.env into THIS process
    only, run one named tool, exit. Never prints a value from app.env.

    The tool calls the sidecar directly, so it touches the GPU but NOT the
    credit ledger. Do not run it while an image batch or a video job is up.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\soi_kho_giong_cu.ps1

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = '',
    [switch]$BoAsr
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
# !! PYTHON CUA `vieneu-venv`, khong phai venv nen tang. Bo do nay can
#    librosa + soundfile de tinh F0, va chung chi co trong venv giong.
#    Doc tu app.env sau khi nap ben duoi -- xem doan `$venvPy` phia sau.
$venvPy  = ''
$tool    = Join-Path $Repo 'tools\soi_kho_giong_cu.py'
foreach ($p in @($envFile, $tool)) {
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

$venvPy = $env:LTT_VIENEU_PYTHON
if (-not $venvPy -or -not (Test-Path $venvPy)) {
    throw "Khong thay python cua vieneu-venv (LTT_VIENEU_PYTHON=$venvPy)"
}
$env:PYTHONPATH = $Repo

$doiSo = @()
if ($BoAsr) { $doiSo += '--bo-asr' }

# Xem chu thich cung ten trong chay_thu_giong.ps1: voi 'Stop', mot exe ngoai ghi
# ra stderr se ket thuc script truoc khi doc duoc $LASTEXITCODE.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
