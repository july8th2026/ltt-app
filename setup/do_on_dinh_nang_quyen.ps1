<#
.SYNOPSIS
    Lop NGOAI: nang quyen roi goi `do_on_dinh.ps1`, ghi log va EXITCODE.

.DESCRIPTION
    Khuon lay tu `setup\deploy_nang_quyen.ps1`, va ly do y het:

    !! `Start-Process` KHONG cho dung `-Verb RunAs` cung voi
       `-RedirectStandardOutput`. Hai tham so loai tru nhau, va no HONG IM
       LANG - cua so nang quyen dong, khong mot dong loi nao o lai.

       Do that 09/09: goi thang `do_on_dinh.ps1` bang `-Verb RunAs` ba lan.
       Lan 1 chay xong; lan 2 va 3 thoat som ma KHONG de lai gi, va tu ben
       ngoai hai truong hop "chua bam UAC" va "chay roi chet ngay" TRONG Y HET
       NHAU. Mat 20 phut de phan biet hai thu ma mot dong `EXITCODE=` tra loi
       duoc.

      lop NGOAI (tep nay) -> `-Verb RunAs`, KHONG chuyen huong
      lop TRONG           -> da co quyen, chuyen huong + ghi EXITCODE

    !! `EXITCODE` RONG KHAC HAN `EXITCODE=0`. Rong nghia la tien trinh chua
       chay xong (hoac chua chay).

.NOTES
    Pure ASCII (CLAUDE.md quy tac 2).
#>
[CmdletBinding()]
param(
    [string]$Repo = '',
    [int]$Vong = 15,
    [string]$LogDir = 'C:\LTTPlatform\logs',
    # Chuyen thang xuong lop TRONG, va lop trong moi la noi anh xa tu khoa ->
    # tep. Lop nay khong biet ten tep nao, nen no khong the duoc dung de chay
    # mot tep bat ky voi moi truong production.
    [ValidateSet('on-dinh', 'ngan-sach')]
    [string]$Do = 'on-dinh'
)

$ErrorActionPreference = 'Stop'
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
# Ten tep mang theo tu khoa: hai lo do khac nhau khong duoc lan vao nhau khi
# doc lai sau nay.
$out = Join-Path $LogDir "do_$Do-$stamp.out.log"
$err = Join-Path $LogDir "do_$Do-$stamp.err.log"
$sum = Join-Path $LogDir "do_$Do-$stamp.ket.txt"

"BAT DAU=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content $sum -Encoding utf8
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
"ADMIN=$isAdmin" | Add-Content $sum -Encoding utf8
"OUT=$out"       | Add-Content $sum -Encoding utf8
"ERR=$err"       | Add-Content $sum -Encoding utf8

if (-not $isAdmin) {
    "EXITCODE=-1" | Add-Content $sum -Encoding utf8
    throw "Lop NGOAI phai chay voi quyen Administrator."
}

$script = Join-Path $Repo 'setup\do_on_dinh.ps1'
if (-not (Test-Path $script)) {
    "EXITCODE=-2" | Add-Content $sum -Encoding utf8
    throw "Khong thay $script"
}

# !! `-u` cho python: KHONG dem stdout.
#
#    Do that 09/09: `python | Tee-Object` khong ghi mot byte nao cho toi luc
#    tien trinh KET THUC, vi Python dem stdout khi dau ra khong phai TTY. Nhin
#    tu ngoai, "dang chay binh thuong" va "treo" trong y het nhau suot 10 phut.
$p = Start-Process powershell `
    -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$script`"",
                  '-Vong', "$Vong", '-Do', "$Do" `
    -RedirectStandardOutput $out -RedirectStandardError $err `
    -NoNewWindow -Wait -PassThru

"EXITCODE=$($p.ExitCode)" | Add-Content $sum -Encoding utf8
"KET THUC=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Add-Content $sum -Encoding utf8

if ($p.ExitCode -eq 0) {
    Write-Host "DO XONG (EXITCODE=0). Xem $out" -ForegroundColor Green
} else {
    Write-Host "DO HONG - EXITCODE=$($p.ExitCode). Xem $err" -ForegroundColor Red
}
exit $p.ExitCode
