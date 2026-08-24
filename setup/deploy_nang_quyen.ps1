# deploy_nang_quyen.ps1 - LOP TRONG cua quy trinh deploy nang quyen (AGENTS.md 9.3).
#
# KHONG CHAY TAY TEP NAY. No duoc goi boi lop ngoai:
#
#     Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
#       '-File','"D:\LTTSTUDIOSAPP\setup\deploy_nang_quyen.ps1"' -Verb RunAs
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! VI SAO PHAI TACH HAI LOP. `Start-Process` KHONG cho dung `-Verb RunAs` cung
#    voi `-RedirectStandardOutput`. Hai tham so loai tru nhau, va no HONG IM
#    LANG: khong log, khong bao loi, tien trinh thoat sau mot giay nhu the da
#    chay xong. Nen:
#
#      lop NGOAI  -> nang quyen, KHONG chuyen huong
#      lop TRONG  -> (tep nay, da co quyen) chuyen huong + ghi EXITCODE
#
# !! `EXITCODE` RONG KHAC HAN `EXITCODE=0`. Rong nghia la tien trinh khong chay.
#    Khong phan biet duoc hai thu do thi se bao "da deploy xong" trong khi chua
#    co gi xay ra - dung cai AGENTS.md muc 9.3 canh bao.

[CmdletBinding()]
param(
    [string]$Repo   = 'D:\LTTSTUDIOSAPP',
    [string]$LogDir = 'C:\LTTPlatform\logs'
)

$ErrorActionPreference = 'Stop'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$out = Join-Path $LogDir "deploy-$stamp.out.log"
$err = Join-Path $LogDir "deploy-$stamp.err.log"
$sum = Join-Path $LogDir "deploy-$stamp.ket.txt"

"BAT DAU=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content $sum -Encoding utf8
"ADMIN=$isAdmin" | Add-Content $sum -Encoding utf8
"OUT=$out"       | Add-Content $sum -Encoding utf8
"ERR=$err"       | Add-Content $sum -Encoding utf8

if (-not $isAdmin) {
    # Ghi ra roi thoat, KHONG throw: throw o day chi lam cua so bien mat va
    # nguoi doc khong biet vi sao.
    "EXITCODE=-1" | Add-Content $sum -Encoding utf8
    "LY_DO=khong co quyen Administrator - lop ngoai phai dung -Verb RunAs" |
        Add-Content $sum -Encoding utf8
    exit 1
}

$script = Join-Path $Repo 'setup\2-cai-dat.ps1'
if (-not (Test-Path $script)) {
    "EXITCODE=-2" | Add-Content $sum -Encoding utf8
    "LY_DO=khong thay $script" | Add-Content $sum -Encoding utf8
    exit 1
}

# Da co quyen roi, nen o day duoc phep chuyen huong. KHONG dat `-Verb`.
$p = Start-Process powershell `
        -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$script`"" `
        -RedirectStandardOutput $out -RedirectStandardError $err `
        -Wait -PassThru

"EXITCODE=$($p.ExitCode)" | Add-Content $sum -Encoding utf8
"KET THUC=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Add-Content $sum -Encoding utf8

if ($p.ExitCode -eq 0) {
    Write-Host ''
    Write-Host 'DEPLOY XONG (EXITCODE=0).' -ForegroundColor Green
} else {
    Write-Host ''
    Write-Host "DEPLOY HONG - EXITCODE=$($p.ExitCode). Xem $err" -ForegroundColor Red
}
Write-Host "Ket qua: $sum"
# Giu cua so mo mot chut de nguoi dung kip doc, nhung KHONG cho no cho mai mai:
# mot cua so cho `Read-Host` se treo vinh vien khi khong ai ngoi truoc may.
Start-Sleep -Seconds 6
exit $p.ExitCode
