<#
.SYNOPSIS
    Buoc 1 - Kiem tra may chu da san sang chua. KHONG thay doi gi.

.DESCRIPTION
    Chay TRUOC khi cai. Chi doc, khong ghi, khong cai gi ca.
    Muc dich: phat hien van de khi con re, thay vi cai nua chung roi hong.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup\1-kiem-tra-may.ps1
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    [int]$Port = 8000
)

$ErrorActionPreference = 'Continue'
$script:Fail = 0
$script:Warn = 0

function Say($m)  { Write-Host $m }
function Head($m) { Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK]   $m" -ForegroundColor Green }
function Bad($m)  { Write-Host "  [LOI]  $m" -ForegroundColor Red;    $script:Fail++ }
function Warn($m) { Write-Host "  [CANH] $m" -ForegroundColor Yellow; $script:Warn++ }

Head 'Quyen Administrator'
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) { Ok 'Dang chay voi quyen Administrator' }
else { Bad 'CAN quyen Administrator de cai dich vu Windows. Mo PowerShell bang Run as administrator.' }

Head 'He dieu hanh'
$os = Get-CimInstance Win32_OperatingSystem
Say "  $($os.Caption) build $($os.BuildNumber)"
# Ban Evaluation het han se tu tat may moi gio - hong ca he thong ma khong
# lien quan gi den code.
$lic = cscript //nologo "$env:SystemRoot\System32\slmgr.vbs" /dli 2>$null | Out-String
if ($lic -match 'Eval') {
    $days = if ($lic -match '(\d+)\s*day') { $Matches[1] } else { '?' }
    Warn "Ban Windows EVALUATION - con khoang $days ngay. Het han may se TU TAT moi gio."
} else {
    Ok 'Giay phep Windows khong phai ban dung thu'
}

Head 'Python'
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Bad 'Khong tim thay python trong PATH. Cai Python 3.11+ va tick "Add to PATH".'
} else {
    $ver = (& python -c "import sys;print('%d.%d.%d'%sys.version_info[:3])" 2>$null)
    Say "  python $ver  ($($py.Source))"
    $parts = $ver.Split('.')
    if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
        Bad "Can Python 3.11 tro len. Dang co $ver."
    } else { Ok "Phien ban Python dat yeu cau" }
}

Head 'Bo nho va o dia'
$cs = Get-CimInstance Win32_ComputerSystem
$ramGb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
Say "  CPU : $($cs.NumberOfLogicalProcessors) vCPU"
Say "  RAM : $ramGb GB"
if ($ramGb -lt 2) { Bad "RAM $ramGb GB qua thap - can it nhat 2 GB." }
elseif ($ramGb -lt 4) { Warn "RAM $ramGb GB du chay nhung chat khi upload video." }
else { Ok "RAM du" }

$drive = (Split-Path $Root -Qualifier)
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$drive'"
if ($disk) {
    $freeGb = [math]::Round($disk.FreeSpace / 1GB, 1)
    Say "  Dia $drive : con trong $freeGb GB"
    if ($freeGb -lt 10) { Bad "Con $freeGb GB - qua it cho venv + video tam." }
    elseif ($freeGb -lt 25) { Warn "Con $freeGb GB - nen don bot cho video tam." }
    else { Ok 'Dung luong dia du' }
}

Head "Cong $Port"
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    $procId = $busy[0].OwningProcess
    $pname = (Get-Process -Id $procId -ErrorAction SilentlyContinue).ProcessName
    Warn "Cong $Port dang bi chiem boi '$pname' (PID $procId). Doi cong hoac dung tien trinh do."
} else { Ok "Cong $Port dang ranh" }

Head 'Ket noi Internet'
foreach ($h in @('pypi.org', 'api.cloudflare.com')) {
    $r = Test-NetConnection -ComputerName $h -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($r) { Ok "Ket noi duoc $h" } else { Bad "KHONG ket noi duoc $h - can cho viec cai dat" }
}

Head 'Cai dat cu'
if (Test-Path $Root) {
    Warn "$Root da ton tai. Script cai se GIU NGUYEN data/ va secrets/, chi thay code."
} else { Ok "$Root chua ton tai - se cai moi" }
foreach ($s in @('LTTStudioWeb', 'cloudflared', 'Caddy')) {
    $svc = Get-Service $s -ErrorAction SilentlyContinue
    if ($svc) { Warn "Dich vu '$s' da ton tai (dang $($svc.Status))" }
}

Head 'Ma nguon'
$here = Split-Path -Parent $PSScriptRoot
foreach ($f in @('server\run.py', 'platform_core\registry.py', 'requirements.txt',
                 'requirements-server.txt', 'config.example.json')) {
    if (Test-Path (Join-Path $here $f)) { Ok "co $f" } else { Bad "THIEU $f - folder chua day du" }
}
$appCount = (Get-ChildItem (Join-Path $here 'apps') -Directory -ErrorAction SilentlyContinue |
             Where-Object { Test-Path (Join-Path $_.FullName 'manifest.py') }).Count
if ($appCount -gt 0) { Ok "tim thay $appCount app trong apps\" }
else { Bad 'Khong tim thay app nao trong apps\' }

Write-Host ""
Write-Host ("-" * 62)
if ($script:Fail -gt 0) {
    Write-Host "KET QUA: $($script:Fail) loi, $($script:Warn) canh bao - SUA LOI TRUOC KHI CAI" -ForegroundColor Red
    exit 1
} elseif ($script:Warn -gt 0) {
    Write-Host "KET QUA: dat, co $($script:Warn) canh bao - doc lai o tren roi hay cai" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "KET QUA: may san sang. Chay tiep: .\setup\2-cai-dat.ps1" -ForegroundColor Green
    exit 0
}
