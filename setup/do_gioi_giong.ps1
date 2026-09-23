<#
.SYNOPSIS
    Build the speech corpus for tools\do_gioi_giong.py (step "sinh").

.DESCRIPTION
    Same narrow bridge as do_giong_nguon_ngoai_ngu.ps1: read app.env into THIS
    process only, run one named tool, exit. Never prints a value from app.env.

    WHY ELEVATION IS NEEDED. Speaking a line goes through the VieNeu sidecar on
    :8120, and that needs LTT_VOICE_SIDECAR_TOKEN, which lives in the
    ACL-locked secrets\app.env. Nothing else here needs a secret: the tool
    enrols each shared voice straight from its source clip under
    data\voice_goc\kho_chung, so it never opens the production database.

    READ ONLY. This writes wav files under -Ra (default C:\lttinf\asvf_dogiong)
    and nothing else. It does not write one database row.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\do_gioi_giong.ps1
    powershell -ExecutionPolicy Bypass -File .\setup\do_gioi_giong.ps1 -Chi en

.NOTES
    Needs Administrator (to read the ACL-locked app.env).
    Pure ASCII (CLAUDE.md rule 6).
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [string]$Repo = '',
    [string]$Ra = 'C:\lttinf\asvf_dogiong',
    # Empty = everything. 'vi' / 'en' / 'preset' = one slice, so that one run
    # does not hold the machine lock for the whole corpus.
    [ValidateSet('', 'vi', 'en', 'preset')]
    [string]$Chi = '',
    # 0 = everything still missing. A small number is a dry run of the path
    # before a long run takes the machine lock.
    [int]$So = 0
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$envFile = Join-Path $Root 'secrets\app.env'
$venvPy  = Join-Path $Root 'venv\Scripts\python.exe'
$tool    = Join-Path $Repo 'tools\do_gioi_giong.py'
foreach ($p in @($envFile, $venvPy, $tool)) {
    if (-not (Test-Path $p)) { throw "Khong thay $p" }
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Can quyen Administrator de doc $envFile" }

$soBien = 0
foreach ($dong in (Get-Content $envFile -Encoding UTF8)) {
    $d = $dong.Trim()
    if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
    $i = $d.IndexOf('=')
    # The variable name must NOT collide with a parameter of this script --
    # PowerShell is case-insensitive. See tools/check_ps_bien_trung_tham_so.py.
    $bienEnv = $d.Substring(0, $i).Trim()
    if ($bienEnv) { Set-Item -Path "Env:$bienEnv" -Value $d.Substring($i + 1); $soBien++ }
}
Write-Host "  [OK] Nap $soBien bien tu app.env (khong in gia tri)" -ForegroundColor Green
$env:PYTHONPATH = $Repo
$env:PYTHONIOENCODING = 'utf-8'

$doiSo = @('-u', $tool, 'sinh', '--ra', $Ra)
if ($Chi) { $doiSo += @('--chi', $Chi) }
if ($So -gt 0) { $doiSo += @('--so', "$So") }

# See the note of the same name in chay_thu_giong.ps1: with 'Stop', a native
# exe writing to stderr ends the script before $LASTEXITCODE can be read.
$truoc = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPy @doiSo
$ma = $LASTEXITCODE
$ErrorActionPreference = $truoc
Write-Host "  EXITCODE=$ma"
exit $ma
