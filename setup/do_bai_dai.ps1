<#
.SYNOPSIS
    Measure JOINED long-form audio quality across document lengths.

.DESCRIPTION
    Same narrow bridge as cong_chat_luong_voice.ps1: read app.env into THIS
    process only, run one named tool, exit. Never prints a value from app.env.

    The tool calls the voice sidecar directly, so it touches the GPU but NOT
    the credit ledger. Do not run it while an image batch or a video job is up.

    This answers the ONE condition tham_so_cong_khai.py still leaves open
    before TRAN_KY_TU_CONG_KHAI can be raised: is the JOINED read as good as
    the single-pass read the product sells today?

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\do_bai_dai.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\do_bai_dai.ps1 -DoDai 1400,1500,3000

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root  = 'C:\LTTPlatform',
    [string]$Repo  = '',
    [string]$DoDai = '',
    [switch]$BoAsr,
    [string]$Json  = 'tmp\do_bai_dai.json'
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
# !! PYTHON CUA `vieneu-venv`, khong phai venv nen tang. Bo do nay can
#    librosa + soundfile de tinh F0 va speaker embedding, va chung chi co
#    trong venv giong. Doc tu app.env sau khi nap ben duoi.
$venvPy = ''
$tool   = Join-Path $Repo 'tools\do_bai_dai.py'
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

$doiSo = @('--json', $Json)
if ($DoDai) { $doiSo += @('--do-dai', $DoDai) }
if ($BoAsr) { $doiSo += '--bo-asr' }

# Xem chu thich cung ten trong cong_chat_luong_voice.ps1: voi 'Stop', mot exe
# ngoai ghi ra stderr se ket thuc script truoc khi doc duoc $LASTEXITCODE.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
