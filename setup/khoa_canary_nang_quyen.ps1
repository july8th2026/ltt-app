# khoa_canary_nang_quyen.ps1 - LOP TRONG cua viec phat khoa canary (AGENTS.md 9.3).
#
# KHONG CHAY TAY TEP NAY. No duoc goi boi lop ngoai:
#
#     Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
#       '-File','"D:\LTTSTUDIOSAPP\setup\khoa_canary_nang_quyen.ps1"' -Verb RunAs
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! VI SAO CAN LOP THU HAI. `Start-Process -Verb RunAs` KHONG dung chung duoc
#    voi `-RedirectStandardOutput`, va no hong IM LANG. Ma khoa thi in ra
#    stdout MOT LAN duy nhat - khong bat duoc stdout la mat khoa, va phai phat
#    lai mot khoa nua (moi khoa la mot chung danh song, dung rai chung ra).
#
# !! KHOA DI VAO `tmp/` CHU KHONG RA MAN HINH LOG.
#    `tmp/` da nam trong .gitignore (dong 147). Day van la mot chung danh tren
#    dia - dung chep no di dau, va xoa khi xong.
#
# !! `EXITCODE` RONG KHAC HAN `EXITCODE=0`. Rong nghia la tien trinh khong chay.

[CmdletBinding()]
param(
    [string]$Repo = 'D:\LTTSTUDIOSAPP',
    [ValidateSet('tao-tk-canary', 'khoa-canary')]
    [string]$Viec = 'khoa-canary'
)

$ErrorActionPreference = 'Stop'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

$tmp = Join-Path $Repo 'tmp'
if (-not (Test-Path $tmp)) { New-Item -ItemType Directory -Path $tmp -Force | Out-Null }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$out = Join-Path $tmp "canary-$Viec-$stamp.out.txt"
$err = Join-Path $tmp "canary-$Viec-$stamp.err.txt"
$sum = Join-Path $tmp "canary-$Viec-$stamp.ket.txt"

"BAT DAU=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content $sum -Encoding utf8
"VIEC=$Viec"  | Add-Content $sum -Encoding utf8
"ADMIN=$isAdmin" | Add-Content $sum -Encoding utf8
"OUT=$out"    | Add-Content $sum -Encoding utf8

if (-not $isAdmin) {
    "EXITCODE=-1" | Add-Content $sum -Encoding utf8
    "LY_DO=khong co quyen Administrator - lop ngoai phai dung -Verb RunAs" |
        Add-Content $sum -Encoding utf8
    exit 1
}

$script = Join-Path $Repo 'setup\chay_voi_env.ps1'
if (-not (Test-Path $script)) {
    "EXITCODE=-2" | Add-Content $sum -Encoding utf8
    "LY_DO=khong thay $script" | Add-Content $sum -Encoding utf8
    exit 1
}

$p = Start-Process powershell `
        -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$script`"",
                      '-Viec', $Viec, '-Repo', "`"$Repo`"" `
        -RedirectStandardOutput $out -RedirectStandardError $err `
        -Wait -PassThru

"EXITCODE=$($p.ExitCode)" | Add-Content $sum -Encoding utf8
"KET THUC=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Add-Content $sum -Encoding utf8

if ($p.ExitCode -eq 0) {
    Write-Host ''
    Write-Host "XONG (EXITCODE=0). Ket qua o: $out" -ForegroundColor Green
} else {
    Write-Host ''
    Write-Host "HONG - EXITCODE=$($p.ExitCode). Xem $err" -ForegroundColor Red
}
Start-Sleep -Seconds 4
exit $p.ExitCode
