<#
.SYNOPSIS
    Run LTT VOICE end-to-end on production, the way a real customer does.

.DESCRIPTION
    Narrow bridge, same shape as nap_credit_tai_khoan_thu.ps1: read app.env into
    THIS process only, run one named tool, exit. Never prints a value from
    app.env.

    The tool it runs submits a job through submit_with_credit and then WAITS for
    the real production worker to pick it up. That is the point: a script that
    called `features` directly would stay green even when the queue is broken,
    when the worker has no `voice` lane, or when LTTStudioVoice is down. Those
    three are exactly what breaks at deploy time.

    !! IT TOUCHES REAL MONEY. The job holds credit then settles it, in an
       append-only ledger. The tool prints the balance before and after and
       refuses to top itself up.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\chay_thu_ltt_voice.ps1
    powershell -ExecutionPolicy Bypass -File .\setup\chay_thu_ltt_voice.ps1 -TaiVe tmp\thu.wav

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root  = 'C:\LTTPlatform',
    [string]$Repo  = '',
    [string]$Email = 'thu.giongnoi@lttstudios.local',
    [string]$Text  = '',
    [int]$ChoGiay  = 300,
    [string]$TaiVe = ''
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\chay_thu_ltt_voice.py'
foreach ($p in @($envFile, $venvPy, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Can quyen Administrator de doc $envFile" }

# !! Bo dem ten `$demBien`, KHONG phai `$so` hay `$text`. PowerShell khong phan
#    biet hoa thuong, nen mot bo dem ten trung mot tham so se GHI DE tham so ay
#    -- da xay ra that 31/08 (hai lan: -Ten thanh "HF_HOME", -So 100 thanh 70,
#    va cai sau ghi mot but toan credit SAI SO vao mot cuon so chi ghi them).
#    Chot tinh: tools/check_ps_bien_trung_tham_so.py
$demBien = 0
foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    $bienEnv = $d.Substring(0, $i).Trim()
    if ($bienEnv) { Set-Item -Path "Env:$bienEnv" -Value $d.Substring($i + 1); $demBien++ }
}
Write-Host "  [OK] Nap $demBien bien tu app.env (khong in gia tri)" -ForegroundColor Green
$env:PYTHONPATH = $Repo

$doiSo = @('--email', $Email, '--cho-giay', "$ChoGiay")
if ($Text)  { $doiSo += @('--text',   $Text) }
if ($TaiVe) { $doiSo += @('--tai-ve', $TaiVe) }

# !! Voi 'Stop', mot exe ngoai ghi ra stderr se ket thuc script TRUOC khi doc
#    duoc $LASTEXITCODE -- tuc mat chinh ma thoat ta can.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy $tool @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
exit $ma
