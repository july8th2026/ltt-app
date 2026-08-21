# LTT deploy: chay setup\2-cai-dat.ps1 (copy app + migrate + restart dich vu).
#
# PHAI chay tu mot PowerShell DA NANG QUYEN (Run as Administrator).
# Neu chua nang quyen, script tu thu tao scheduled task /rl HIGHEST; cach do chi
# chay duoc khi tien trinh goi da la admin, nen thuong la phai mo cua so admin.
#
# BAI HOC 2026-08-21 (da lam sap site 1 lan):
#   Ban dau script dat $ErrorActionPreference='Stop'. Alembic in INFO ra STDERR,
#   PowerShell coi do la loi -> nem ngoai le -> script thoat NGAY SAU khi
#   2-cai-dat.ps1 da DUNG dich vu, nen dich vu khong bao gio start lai va
#   app.lttstudios.com tra 502.
#   Vi vay: KHONG dung 'Stop' quanh lenh native, va LUON co finally bao dam
#   dich vu duoc khoi dong lai du bat cu chuyen gi xay ra.
param([switch]$Elevated)
$ErrorActionPreference = 'Continue'   # KHONG doi thanh 'Stop' (xem bai hoc tren)
$repo = 'D:\LTTSTUDIOSAPP'
$log = 'C:\LTTPlatform\logs\selfdeploy.log'
$svcs = @('LTTStudioWeb', 'LTTStudioWorker', 'LTTStudioCodex')

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)

if (-not $Elevated -and -not $isAdmin) {
    Write-Host 'Chua nang quyen - thu qua scheduled task...' -ForegroundColor Cyan
    $me = $PSCommandPath; $tn = 'LTTSelfDeploy'
    Remove-Item $log -ErrorAction SilentlyContinue
    $c = schtasks /create /tn $tn /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$me`" -Elevated" /sc once /st 23:59 /rl HIGHEST /f 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'KHONG tao duoc task nang quyen:' -ForegroundColor Red
        Write-Host ($c -join ' ')
        Write-Host 'Hay mo PowerShell bang "Run as Administrator" roi chay lai script nay.' -ForegroundColor Yellow
        exit 1
    }
    schtasks /run /tn $tn | Out-Null
    Write-Host 'Dang deploy (copy app + migrate + restart)...'
    for ($i = 0; $i -lt 180; $i++) {
        Start-Sleep 2
        if ((Test-Path $log) -and ((Get-Content $log -Raw -ErrorAction SilentlyContinue) -match 'SELFDEPLOY_DONE')) { break }
    }
    schtasks /delete /tn $tn /f | Out-Null
    if (Test-Path $log) { Get-Content $log -Tail 40 } else { Write-Host 'Khong co log.' -ForegroundColor Yellow }
    exit 0
}

# --- duong nang quyen: chay deploy chinh thuc, LUON restart dich vu o cuoi ---
"=== LTT deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File $log -Encoding utf8
try {
    Set-Location $repo
    & powershell -NoProfile -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1 *>> $log
    "deploy exit rc=$LASTEXITCODE" | Out-File $log -Append -Encoding utf8
} catch {
    ("DEPLOY_EXCEPTION " + $_.Exception.Message) | Out-File $log -Append -Encoding utf8
} finally {
    # LUOI AN TOAN: du deploy thanh cong hay vo, dich vu PHAI duoc bat lai.
    foreach ($s in $svcs) {
        $sv = Get-Service $s -ErrorAction SilentlyContinue
        if ($sv -and $sv.Status -ne 'Running') {
            Start-Service $s -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep 5
    foreach ($s in $svcs) {
        $sv = Get-Service $s -ErrorAction SilentlyContinue
        if ($sv) { "$s = $($sv.Status)" | Out-File $log -Append -Encoding utf8 }
    }
    try {
        $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 -Uri 'http://127.0.0.1:8100/health/ready'
        "health/ready = $([int]$r.StatusCode)" | Out-File $log -Append -Encoding utf8
    } catch {
        ("health/ready = LOI " + $_.Exception.Message) | Out-File $log -Append -Encoding utf8
    }
    "SELFDEPLOY_DONE" | Out-File $log -Append -Encoding utf8
}
