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

# !! DON PSModulePath TRUOC KHI SINH TIEN TRINH CON (06/09/2026).
#
#    Trieu chung: deploy chet voi
#      Get-Acl : The 'Get-Acl' command was found in the module
#      'Microsoft.PowerShell.Security', but the module could not be loaded.
#
#    Nguyen nhan goc: tien trinh con la Windows PowerShell 5.1, va no THUA
#    HUONG `PSModulePath` cua tien trinh cha. Neu cha la PowerShell 7 (mot
#    phien Claude Code chay `pwsh`), duong dan cua PS7 ro sang:
#
#      c:\program files\powershell\7\Modules\Microsoft.PowerShell.Security
#      C:\Windows\system32\WindowsPowerShell\v1.0\Modules\...
#
#    5.1 tim thay module o CA HAI, nap ban cua PS7, va
#    `Security.types.ps1xml` dang ky trung kieu da co:
#      Error in TypeData 'System.Security.AccessControl.ObjectSecurity':
#      The member AuditToString is already present.
#    Module chet keo theo `Get-Acl`, va khoi siet quyen secrets\ (W1.5) no.
#
# !! Da xay ra THAT: deploy 20:12 ngay 06/09 chet o day SAU KHI da dung bon
#    dich vu va TRUOC khi chay migration. Hau qua: production 502 khoang
#    bon phut, va MA MOI chay tren SCHEMA CU.
#
# !! Vi sao va o DAY chu khong o `2-cai-dat.ps1`: loi khong phai cua trinh
#    cai, ma cua MOI TRUONG nguoi goi de lai. Lop bao nay la cho duy nhat
#    biet minh sap sinh mot tien trinh 5.1.
$psmp = @(
    "$env:ProgramFiles\WindowsPowerShell\Modules",
    "$env:SystemRoot\system32\WindowsPowerShell\v1.0\Modules"
) -join ';'
$env:PSModulePath = $psmp
"PSMODULEPATH=$psmp" | Add-Content $sum -Encoding utf8

# Da co quyen roi, nen o day duoc phep chuyen huong. KHONG dat `-Verb`.
$p = Start-Process powershell `
        -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$script`"" `
        -RedirectStandardOutput $out -RedirectStandardError $err `
        -Wait -PassThru

"EXITCODE=$($p.ExitCode)" | Add-Content $sum -Encoding utf8
"KET THUC=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Add-Content $sum -Encoding utf8

# !! LUOI CUOI: DEPLOY HONG => DUA DICH VU TRO LAI (28/09/2026).
#
#    BA LAN cung mot hinh dang, va hai lan dau da duoc ghi ngay trong hai tep nay:
#
#      21/08  `$ErrorActionPreference='Stop'` quanh mot lenh native (alembic in
#             INFO ra stderr) -> script thoat sau khi da dung dich vu -> 502.
#             Bai hoc ghi HAI ve; chi ve MOT (`Invoke-Ngoai`) duoc viet vao ma.
#      06/09  `PSModulePath` cua PS7 ro sang tien trinh 5.1 -> `Get-Acl` chet
#             SAU KHI da dung bon dich vu -> 502 khoang bon phut (ghi o tren).
#      28/09  `Move-Item C:\LTTPlatform\app` 'Access denied' -> EXITCODE=1, ba
#             dich vu o lai Stopped -> 502 cho toi khi mot nguoi goi Start-Service.
#
#    Moi lan deu va dung NGUYEN NHAN cu the. Khong lan nao them mot luoi cho
#    HAU QUA. Nen nguyen nhan thu tu se lai di qua dung cho nay.
#
# !! Vi sao luoi phai o LOP BOC chu khong chi o `2-cai-dat.ps1`:
#
#      `trap` trong script con bat duoc loi `throw`. No KHONG bat duoc:
#        - Ctrl-C cua nguoi dung (PipelineStoppedException, khong tin duoc),
#        - `Stop-Process` / kill tien trinh con,
#        - mot loi trong chinh khoi `trap`.
#
#      Lop boc nay thi VAN SONG trong ca ba ca do, va no THAY `$p.ExitCode`. Nen
#      day la cho duy nhat bat duoc CA LOP, khong chi cac ca biet truoc.
#
# !! Khong dung `Start-Service` vo dieu kien: neu deploy hong SAU khi da khoi
#    dong lai thanh cong thi dich vu dang chay, va goi lai chi gay nhieu. Kiem
#    trang thai truoc, chi bat cai nao dang Stopped.
if ($p.ExitCode -ne 0) {
    $canBat = @()
    foreach ($svc in @('LTTStudioWeb', 'LTTStudioWorker', 'LTTStudioVoice',
                       'LTTStudioCodex')) {
        $s = Get-Service $svc -ErrorAction SilentlyContinue
        if ($s -and $s.Status -ne 'Running') { $canBat += $svc }
    }
    if ($canBat.Count -gt 0) {
        Write-Host ''
        Write-Host "LUOI CUOI: deploy hong va $($canBat.Count) dich vu dang khong chay" -ForegroundColor Yellow
        "LUOI_CUOI=dang bat lai: $($canBat -join ', ')" | Add-Content $sum -Encoding utf8
        foreach ($svc in $canBat) {
            try {
                Start-Service $svc -ErrorAction Stop
                Write-Host "   $svc -> Running" -ForegroundColor Green
                "LUOI_CUOI_OK=$svc" | Add-Content $sum -Encoding utf8
            } catch {
                Write-Host "   $svc -> KHONG bat duoc: $($_.Exception.Message)" -ForegroundColor Red
                "LUOI_CUOI_HONG=$svc : $($_.Exception.Message)" | Add-Content $sum -Encoding utf8
            }
        }
        Write-Host '   Kiem /health/ready truoc khi lam gi khac.' -ForegroundColor Yellow
    } else {
        "LUOI_CUOI=khong can - moi dich vu dang chay" | Add-Content $sum -Encoding utf8
    }
}

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
