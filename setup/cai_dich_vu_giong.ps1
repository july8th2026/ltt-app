<#
.SYNOPSIS
    Register (or repair) ONLY the LTT VOICE sidecar service. No downtime.

.DESCRIPTION
    Runs the two steps `2-cai-dat.ps1` does for LTT VOICE -- build the isolated
    venv, then register `LTTStudioVoice` -- and nothing else.

    WHY THIS EXISTS AS A SEPARATE SCRIPT.

      On 2026-08-30 the voice service failed to register because the deploy died
      mid-way. The obvious repair is "just run 2-cai-dat.ps1 again" -- and that
      is exactly the wrong move: that script stops Web, Worker and Codex to
      rotate `app\`. Re-running a FULL INSTALL to fix ONE service takes
      production down for the duration.

      A repair must not cost more than the fault. This script touches no other
      service, never stops anything, and never rotates `app\`.

    WHAT IT DOES NOT DO: it does not copy source, does not run migrations, does
    not touch the platform venv. If `app\` is stale, this is the wrong tool --
    run a real deploy.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\cai_dich_vu_giong.ps1

.NOTES
    Needs Administrator (nssm writes to the service registry).
    Pure ASCII (CLAUDE.md rule 2).
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = '',
    [string]$VenvRoot = '',
    [switch]$BoQuaCaiVenv
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }
if (-not $VenvRoot) {
    $VenvRoot = $env:LTT_VOICE_VENV_ROOT
    if (-not $VenvRoot) { $VenvRoot = $Root }
}

$appDir  = Join-Path $Root 'app'
$secrets = Join-Path $Root 'secrets'
$logs    = Join-Path $Root 'logs'
$envFile = Join-Path $secrets 'app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$nssmExe = Join-Path $Root 'tools\nssm.exe'
$ServiceName = 'LTTStudioVoice'

function Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Step($m) { Write-Host "  [..] $m" -ForegroundColor Cyan }
function Bad($m)  { Write-Host "  [LOI] $m" -ForegroundColor Red }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw 'Can quyen Administrator: nssm ghi vao dang ky dich vu.' }
foreach ($p in @($appDir, $secrets, $nssmExe)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p - may nay chua cai nen tang?" }
}

# ------------------------------------------------------------------ venv -----
$voicePy = Join-Path $VenvRoot 'vieneu-venv\Scripts\python.exe'
if ($BoQuaCaiVenv) {
    if (-not (Test-Path $voicePy)) { throw "Khong thay $voicePy" }
    Ok 'Bo qua buoc cai venv theo yeu cau'
} else {
    Step 'Cai/kiem vieneu-venv (idempotent theo phien ban)'
    # KHONG boc try/catch: chay tay thi mot loi phai HIEN RA, khong phai bi nuot
    # roi de lai mot dich vu tro vao mot venv nua voi.
    $out = @(& (Join-Path $Repo 'deploy\windows\install-vieneu-sidecar.ps1') `
             -Root $Root -ReleaseDir $Repo -VenvRoot $VenvRoot -PythonExe 'python')
    $voicePy = ($out | Where-Object { $_ -like '*python.exe' } | Select-Object -Last 1)
    if (-not ($voicePy -and (Test-Path $voicePy))) { throw 'install-vieneu-sidecar.ps1 khong tra ve duong dan python' }
    Ok "venv san sang: $voicePy"
}

# ------------------------------------------------------------- app.env -------
$hfCache = Join-Path $VenvRoot 'hf-cache'
$envTxt = Get-Content $envFile -Raw -ErrorAction SilentlyContinue
if ($envTxt -notmatch 'LTT_VOICE_SIDECAR_TOKEN=') {
    $tok = & $venvPy -c "import secrets;print(secrets.token_urlsafe(32))"
    $them = "LTT_VOICE_SIDECAR_TOKEN=$tok`r`nLTT_VOICE_SIDECAR_PORT=8120`r`nLTT_VIENEU_PYTHON=$voicePy`r`nHF_HOME=$hfCache"
    # Khong BOM (quy tac 1 cua CLAUDE.md): `Out-File -Encoding utf8` cua PS 5.1
    # chen BOM, `json.load()` vo, va /health/ready tra 503 trong khi dich vu chay.
    [IO.File]::AppendAllText($envFile, "`r`n$them`r`n", (New-Object Text.UTF8Encoding($false)))
    Ok 'Da them LTT_VOICE_SIDECAR_TOKEN + port + HF_HOME vao app.env'
} else {
    Ok 'LTT_VOICE_SIDECAR_TOKEN da co - GIU NGUYEN'
}

$envPairs = @()
foreach ($line in (Get-Content $envFile -ErrorAction SilentlyContinue)) {
    $l = $line.Trim()
    if ($l -and -not $l.StartsWith('#') -and $l.Contains('=')) { $envPairs += $l }
}

# ------------------------------------------------------------- dich vu -------
$existing = Get-Service $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.Status -eq 'Running') { Stop-Service $ServiceName -Force; Start-Sleep -Seconds 2 }
    Ok "Dich vu $ServiceName da co - cap nhat cau hinh"
} else {
    & $nssmExe install $ServiceName $voicePy 'voice_sidecar_main.py' | Out-Null
    Ok "Da tao dich vu $ServiceName"
}
& $nssmExe set $ServiceName Application    $voicePy | Out-Null
& $nssmExe set $ServiceName AppDirectory   $appDir | Out-Null
& $nssmExe set $ServiceName AppStdout      (Join-Path $logs 'voice-out.log') | Out-Null
& $nssmExe set $ServiceName AppStderr      (Join-Path $logs 'voice-err.log') | Out-Null
& $nssmExe set $ServiceName AppRotateFiles 1 | Out-Null
& $nssmExe set $ServiceName AppRotateOnline 1 | Out-Null
& $nssmExe set $ServiceName AppRotateBytes 10485760 | Out-Null
& $nssmExe set $ServiceName Start          SERVICE_AUTO_START | Out-Null
& $nssmExe set $ServiceName AppExit Default Restart | Out-Null
& $nssmExe set $ServiceName AppRestartDelay 10000 | Out-Null
& $nssmExe set $ServiceName AppEnvironmentExtra ($envPairs -join "`r`n") | Out-Null
Ok 'Da nap bi mat vao moi truong dich vu giong noi'

Start-Service $ServiceName
Ok 'Da khoi dong - dang cho model nap (lan dau ~20 giay)'

# -------------------------------------------------------------- nghiem thu ---
# HOI DICH VU, khong tin trang thai Windows. Mot dich vu `Running` ma khong tra
# loi la dung thu Windows goi la thanh cong con nguoi dung goi la hong.
$port = 8120
$m = Select-String -Path $envFile -Pattern '^LTT_VOICE_SIDECAR_PORT=(\d+)' -ErrorAction SilentlyContinue
if ($m) { $port = [int]$m.Matches[0].Groups[1].Value }

$song = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-RestMethod "http://127.0.0.1:$port/live" -TimeoutSec 5
        if ($r.ok) { $song = $true; Ok "/live tra loi sau $($i * 2 + 2) giay"; break }
    } catch { }
}
if (-not $song) {
    Bad "Cong giong khong tra loi tren 127.0.0.1:$port"
    Bad "Xem $(Join-Path $logs 'voice-err.log')"
    exit 1
}

Write-Host ''
Write-Host 'XONG. Kiem tiep bang mot thu that:' -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File .\setup\4-nghiem-thu.ps1"
exit 0
