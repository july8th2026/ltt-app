<#
.SYNOPSIS
    Measure the long-form path using a SECOND sidecar started from THIS tree.

.DESCRIPTION
    Why this exists instead of just running setup\do_bai_dai.ps1:

    The running LTTStudioVoice service is the DEPLOYED copy under
    C:\LTTPlatform\app. New sidecar endpoints that live only in a worktree are
    simply not there -- the measurement gets HTTP 404 and reports every joined
    document as failed. That is exactly what happened on 2026-09-03.

    Deploying to production just to take a measurement is the wrong trade: it
    replaces the whole app tree, and other sessions have unmerged work. So this
    script starts a SECOND sidecar from the worktree on a spare port, points the
    measurement at it, and stops it again. Production is never touched.

    The second sidecar loads its own copy of the model (~320 MB of weights), so
    it needs a GPU with room -- check nvidia-smi first if unsure.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\do_bai_dai_worktree.ps1

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root  = 'C:\LTTPlatform',
    [string]$Repo  = '',
    [int]$Port     = 8121,
    [string]$DoDai = '',
    [switch]$BoAsr,
    [string]$Json  = 'tmp\do_bai_dai.json',
    [int]$ChoGiay  = 180
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$tool    = Join-Path $Repo 'tools\do_bai_dai.py'
$entry   = Join-Path $Repo 'voice_sidecar_main.py'
foreach ($p in @($envFile, $tool, $entry)) {
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
    $bienEnv = $d.Substring(0, $i).Trim()
    if ($bienEnv) { Set-Item -Path "Env:$bienEnv" -Value $d.Substring($i + 1); $so++ }
}
Write-Host "  [OK] Nap $so bien tu app.env (khong in gia tri)" -ForegroundColor Green

$venvPy = $env:LTT_VIENEU_PYTHON
if (-not $venvPy -or -not (Test-Path $venvPy)) {
    throw "Khong thay python cua vieneu-venv (LTT_VIENEU_PYTHON=$venvPy)"
}

# Cong RIENG cho ban worktree. Dich vu that van o cong cu, khong bi dung toi.
$env:LTT_VOICE_SIDECAR_PORT = "$Port"
$env:PYTHONPATH = $Repo

$logOut = Join-Path $Repo 'tmp\sidecar-worktree-out.log'
$logErr = Join-Path $Repo 'tmp\sidecar-worktree-err.log'
New-Item -ItemType Directory -Force -Path (Join-Path $Repo 'tmp') | Out-Null

Write-Host "  Khoi dong sidecar tu worktree tren cong $Port ..." -ForegroundColor Cyan
$sc = Start-Process -FilePath $venvPy -ArgumentList $entry -WorkingDirectory $Repo `
    -RedirectStandardOutput $logOut -RedirectStandardError $logErr `
    -PassThru -WindowStyle Hidden

$ma = 1
try {
    $san = $false
    for ($i = 0; $i -lt $ChoGiay; $i++) {
        Start-Sleep -Seconds 1
        if ($sc.HasExited) { throw "Sidecar worktree chet ngay: xem $logErr" }
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/live" -TimeoutSec 3 `
                 -UseBasicParsing -ErrorAction Stop
            if ($r.StatusCode -eq 200) { $san = $true; break }
        } catch { }
    }
    if (-not $san) { throw "Sidecar worktree khong san sang sau $ChoGiay giay" }
    Write-Host "  [OK] Sidecar worktree san sang (PID $($sc.Id))" -ForegroundColor Green

    $doiSo = @('--json', $Json)
    if ($DoDai) { $doiSo += @('--do-dai', $DoDai) }
    if ($BoAsr) { $doiSo += '--bo-asr' }

    # Xem chu thich cung ten trong cong_chat_luong_voice.ps1.
    $truoc = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $venvPy $tool @doiSo
    $ma = $LASTEXITCODE
    $ErrorActionPreference = $truoc
}
finally {
    # !! LUON dung sidecar worktree, ke ca khi phep do nem loi. Mot ban thu hai
    #    con song la mot ban giu VRAM va giu cong, va lan chay sau se thay mot
    #    cong "da co san" ma khong biet no chay ma nao.
    if ($sc -and -not $sc.HasExited) {
        Write-Host '  Dung sidecar worktree ...' -ForegroundColor Cyan
        Stop-Process -Id $sc.Id -Force -ErrorAction SilentlyContinue
    }
}
exit $ma
