<#
.SYNOPSIS
    Upgrade an existing LTT AI Studio install to a new release (P9).

.DESCRIPTION
    Keeps the previous release directory so rollback.ps1 can restore it in
    seconds. Runtime data, secrets and logs live outside the release
    directory and are never touched (ADR-009).

    Sequence: stop service -> back up data -> keep previous release ->
    extract new release -> reinstall deps -> start -> verify /health/ready.
    Any failure leaves the previous release in place for rollback.ps1.

.EXAMPLE
    .\update.ps1 -SourceZip C:\Temp\ltt-release-0.9.1.zip
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SourceZip,
    [string]$Root = 'C:\LTTPlatform',
    [string]$ServiceName = 'LTTStudioWeb',
    [string]$WorkerServiceName = 'LTTStudioWorker',
    [string]$CodexServiceName = 'LTTStudioCodex',

    [string]$VoiceServiceName = 'LTTStudioVoice',
    [int]$Port = 8100
)

$ErrorActionPreference = 'Stop'
# --------------------------------------------------------------- Invoke-Ngoai
# Voi `$ErrorActionPreference = 'Stop'`, MOT EXE NGOAI ghi ra stderr se thanh
# `NativeCommandError` va KET THUC script -- ngay ca khi exe do tra ve 0.
#
# pip, python, cloudflared va pg_dump deu ghi ra stderr trong luc chay binh
# thuong (canh bao, thanh tien trinh, mot dong chan doan). Hau qua khong phai
# "bao loi sai" ma la IM LANG: dong `if ($LASTEXITCODE -ne 0)` ngay sau do
# KHONG BAO GIO CHAY, script chet giua chung, va nhat ky dung lai o dong cuoi
# in duoc. Mot loi vo hai doc len giong het mot lan treo.
#
# Bay nay da dinh BON LAN trong hai ngay (30-31/08/2026): installer sidecar,
# `Test-Py`, `tai_khoan_thu.ps1`, roi buoc lam am HF cache.
#
# Boc loi goi lai: ha xuong 'Continue' dung trong khoi, roi tra lai. Khoi la
# `scriptblock` nen bien cua ham goi van thay duoc, va `$LASTEXITCODE` giu
# nguyen tu lenh cuoi -- moi phep kiem ma san co van dung.
function Invoke-Ngoai {
    param([Parameter(Mandatory = $true)][scriptblock]$Khoi)
    $truoc = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Khoi } finally { $ErrorActionPreference = $truoc }
}

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'update.ps1 must run in an elevated Administrator PowerShell.'
}

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }

if (-not (Test-Path $SourceZip)) { throw "Release archive not found: $SourceZip" }

$release  = Join-Path $Root 'app'
$previous = Join-Path $Root 'app.previous'
$venvPy   = Join-Path $Root 'venv\Scripts\python.exe'

Write-Step 'Backing up runtime data first'
& (Join-Path $PSScriptRoot 'backup.ps1') -Root $Root
Write-Ok 'Data backup complete'

Write-Step 'Stopping service'
if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    # DUNG NGUOC CHIEU PHU THUOC, va LTTStudioVoice phai di DAU TIEN.

    #

    # Dich vu do co AppDirectory tro vao app\, nen no GIU HANDLE tren thu muc

    # do. Khong dung no thi `Move-Item $release $previous` ben duoi NEM LOI va

    # ban cap nhat dung giua chung -- hoac te hon, neu Windows cho move thi

    # dich vu chay tiep bang MA CU, im lang, cho toi lan restart sau.

    foreach ($name in @($VoiceServiceName, $CodexServiceName,

                        $WorkerServiceName, $ServiceName)) {
        $service = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($service -and $service.Status -ne 'Stopped') {
            Stop-Service $name -Force -ErrorAction Stop
            $service.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
        }
        $after = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($after -and $after.Status -ne 'Stopped') {
            throw "Service $name did not stop; refusing to rotate the release."
        }
    }
    # Give the worker a moment to release its SessionLocks cleanly.
    Start-Sleep -Seconds 5
    Write-Ok "$ServiceName stopped"
} else {
    Write-Host "  [SKIP] Service $ServiceName not installed" -ForegroundColor Yellow
}

Write-Step 'Rotating release directories'
if (Test-Path $previous) { Remove-Item $previous -Recurse -Force }
if (Test-Path $release)  { Move-Item $release $previous }
Write-Ok "Previous release preserved at $previous"

Write-Step 'Extracting new release'
Expand-Archive -Path $SourceZip -DestinationPath $release -Force
Write-Ok "Extracted to $release"

Write-Step 'Ensuring runtime configuration exists'
# Self-heal for installs made by an older installer that did not seed
# config.json. Without it the service starts and reports /health/ready
# = 503 forever. An existing config is never overwritten.
$cfg = Join-Path $Root 'data\config.json'
if (Test-Path $cfg) {
    Write-Ok 'Existing config.json kept untouched'
} else {
    $example = Join-Path $release 'config.example.json'
    if (Test-Path $example) {
        Copy-Item $example -Destination $cfg -Force
        Write-Ok "Created $cfg from config.example.json"
        Write-Host '  [ACTION REQUIRED] Edit it with your real sheet id and column names.' -ForegroundColor Yellow
    } else {
        throw 'config.example.json missing from the release.'
    }
}

Write-Step 'Updating dependencies'
Invoke-Ngoai { & $venvPy -m pip install -r (Join-Path $release 'requirements.txt') --quiet }
if ($LASTEXITCODE -ne 0) { throw "Loi khi chay: & $venvPy -m pip install -r (Join-Path $release 'requirement" }
Invoke-Ngoai { & $venvPy -m pip install -r (Join-Path $release 'requirements-server.txt') --quiet }
if ($LASTEXITCODE -ne 0) { throw "Loi khi chay: & $venvPy -m pip install -r (Join-Path $release 'requirement" }
Write-Ok 'Dependencies updated'

Write-Step 'Updating isolated WhisperX CUDA sidecar'
$envFileWhisper = Join-Path $Root 'secrets\app.env'
$envTextWhisper = Get-Content $envFileWhisper -Raw
$whisperPy = $null
# Reuse a configured healthy sidecar. Rebuilding a multi-GB CUDA environment
# during every release lengthens downtime and can stop an otherwise valid
# deployment when the package index is temporarily unavailable.
if ($envTextWhisper -match '(?m)^LTT_WHISPERX_PYTHON=(.+)$') {
    $candidateWhisperPy = $Matches[1].Trim()
    if (Test-Path $candidateWhisperPy) {
        & $candidateWhisperPy -c "import torch,whisperx,sys; sys.exit(0 if torch.cuda.is_available() else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $whisperPy = $candidateWhisperPy
            Write-Ok 'Existing WhisperX CUDA sidecar kept'
        }
    }
}
if (-not $whisperPy) {
    $whisperOut = @(& (Join-Path $release 'deploy\windows\install-whisperx-sidecar.ps1') `
        -Root $Root -ReleaseDir $release -PythonExe 'python')
    $whisperPy = $whisperOut[-1]
    if (-not $whisperPy) { throw 'WhisperX sidecar update failed' }
}
if ($envTextWhisper -notmatch '(?m)^LTT_WHISPERX_PYTHON=') {
    [IO.File]::AppendAllText($envFileWhisper, "`r`nLTT_WHISPERX_PYTHON=$whisperPy`r`n", (New-Object Text.UTF8Encoding($false)))
}
$envTextWhisper = [IO.File]::ReadAllText($envFileWhisper)
if ($envTextWhisper -notmatch '(?m)^LTT_HF_TOKEN=') {
    [IO.File]::AppendAllText($envFileWhisper, "`r`nLTT_HF_TOKEN=`r`n", (New-Object Text.UTF8Encoding($false)))
}
Write-Ok 'WhisperX CUDA sidecar ready'

Write-Step 'Applying database migrations'
# Bat buoc: ban phat hanh doi schema ma khong nang cap thi service boot tren
# schema cu -> loi runtime kho truy hoac hong du lieu. Chay alembic tren ban MOI
# TRUOC khi start. LTT_DATABASE_URL lay tu app.env (service doc env qua NSSM,
# tien trinh nay thi khong). Mirror dung cach setup/2-cai-dat.ps1 lam.
$envFileForMig = Join-Path $Root 'secrets\app.env'
if ((Test-Path $envFileForMig) -and ((Get-Content $envFileForMig -Raw) -match '(?m)^LTT_DATABASE_URL=(.+)$')) {
    $env:LTT_DATABASE_URL = $Matches[1].Trim()
    Push-Location $release
    Invoke-Ngoai { & $venvPy -m alembic upgrade head }
    $rc = $LASTEXITCODE
    Pop-Location
    $env:LTT_DATABASE_URL = $null
    if ($rc -ne 0) { throw 'alembic upgrade head that bai - dung lai, roll back bang .\rollback.ps1' }
    Write-Ok 'Database migrations applied'
} else {
    throw 'Khong doc duoc LTT_DATABASE_URL tu secrets\app.env - khong the chay migration. Dung lai.'
}

Write-Step 'Starting service'
Start-Service $ServiceName
Start-Service $WorkerServiceName -ErrorAction SilentlyContinue
Start-Service $CodexServiceName -ErrorAction SilentlyContinue

# Bat sau cung: no nap ~320 MB trong so len GPU va mat khoang 20 giay moi san

# sang. Bat truoc thi no tranh CPU voi web dung luc web dang khoi dong.

Start-Service $VoiceServiceName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 8

Write-Step 'Verifying health'
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health/ready" -TimeoutSec 15
    if ($resp.status -ne 'ready') { throw "readiness reported '$($resp.status)'" }
    Write-Ok "Service healthy (environment: $($resp.environment))"
    Write-Host "`nUpdate complete. If anything looks wrong, run: .\rollback.ps1" -ForegroundColor Cyan
} catch {
    Write-Host "`n  [FAILED] Health check did not pass: $_" -ForegroundColor Red
    Write-Host '  The previous release is still available. Roll back with:' -ForegroundColor Yellow
    Write-Host '    .\rollback.ps1' -ForegroundColor Yellow
    exit 1
}
