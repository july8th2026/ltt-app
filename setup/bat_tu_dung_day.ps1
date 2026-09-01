# bat_tu_dung_day.ps1 - bat FAILURE_ACTIONS cua SCM cho cac dich vu cua nen tang.
#
#     powershell -ExecutionPolicy Bypass -File .\setup\bat_tu_dung_day.ps1
#
# CAN QUYEN ADMINISTRATOR. Script tu kiem va bao ro neu thieu.
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# ================================ VI SAO ======================================
#
# Do 01/09 tren may A:
#
#     LTTStudioWeb     Running  Automatic  NSSM AppExit=Restart  FAILURE_ACTIONS: KHONG
#     LTTStudioWorker  Running  Automatic  NSSM AppExit=Restart  FAILURE_ACTIONS: KHONG
#     LTTStudioVoice   Running  Automatic  NSSM AppExit=Restart  FAILURE_ACTIONS: KHONG
#     LTTStudioCodex   Running  Automatic                        FAILURE_ACTIONS: KHONG
#     cloudflared      Running  Automatic                        FAILURE_ACTIONS: KHONG
#
# HAI TANG, MOT LO:
#
#   may reboot            -> OK, tat ca Automatic nen tu len lai
#   tien trinh CON chet   -> OK, NSSM AppExit=Restart dung day
#   VO BOC nssm.exe chet  -> KHONG AI DUNG DAY
#
# Tang thu ba la lo, va no khong chi la "dich vu tat". Do that tren may B ngay
# 01/09 khi dung vo boc:
#
#     + 0.0s   /health=200  Get-Service=Stopped   cong van bi giu
#     +99.0s   /health=200  Get-Service=Paused    cong van bi giu
#
# Tien trinh con SONG SOT MO COI, giu cong, va van tra loi binh thuong. Nguoi
# truc nhin trang web thay no chay; Get-Service noi da chet; va khong co gi dung
# no day nua. No chay cho toi khi chet, roi het.
#
# ================================ CAI GIA =====================================
#
# ! FAILURE_ACTIONS la CAN NHUNG KHONG DU. Do lai tren may B: SCM CO kich hoat
#    (Stopped -> Paused o giay 62,9) nhung ban moi KHONG GIANH DUOC CONG vi con
#    mo coi dang giu. Bit mot nua khong bit duoc lo.
#
#    Nua con lai da lam trong ma:
#      - `server/run.py` tu choi khoi dong khi cong da co nguoi giu, va in ra
#        PID thu pham + cach xu ly
#      - `/health/ready` khai `duoi_dich_vu.mo_coi` de su co NHIN THAY DUOC
#
# ! Do tre lui dan 15s -> 60s -> 120s, va `reset= 86400`: mot dich vu hong lien
#    tuc se KHONG bi dung day trong mot vong lap chat. Neu no hong ba lan trong
#    mot ngay thi lan thu tu SCM de yen - va do la co y, vi luc do van de khong
#    con la "tien trinh chet" ma la mot thu can nguoi nhin vao.

[CmdletBinding()]
param([string[]]$DichVu = @('LTTStudioWeb', 'LTTStudioWorker', 'LTTStudioVoice',
                            'LTTStudioCodex', 'cloudflared'))

$ErrorActionPreference = 'Stop'

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$nguoi = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $nguoi.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Can quyen Administrator." -ForegroundColor Red
    Write-Host "Mo PowerShell bang 'Run as administrator' roi chay lai lenh nay."
    Write-Host "Script nay chi DAT CHINH SACH cho lan hong sau - no KHONG khoi"
    Write-Host "dong lai dich vu nao, nen chay duoc luc dang phuc vu khach."
    exit 1
}

$doi = 0
foreach ($n in $DichVu) {
    $sv = Get-Service $n -ErrorAction SilentlyContinue
    if (-not $sv) { Write-Host ("  [BO QUA] khong co dich vu {0}" -f $n) -ForegroundColor DarkGray; continue }

    $truoc = ((sc.exe qfailure $n) -join ' ') -match 'RESTART'
    sc.exe failure $n reset= 86400 actions= restart/15000/restart/60000/restart/120000 | Out-Null
    # `failureflag 1`: tinh ca lan tien trinh THOAT VOI MA KHAC 0, khong chi lan
    # no sup do. NSSM thoat sach khi tien trinh con chet, nen thieu co nay thi
    # SCM coi nhu dich vu dung binh thuong va KHONG lam gi.
    sc.exe failureflag $n 1 | Out-Null

    $sau = ((sc.exe qfailure $n) -join ' ') -match 'RESTART'
    if ($sau) {
        $doi++
        $nhan = if ($truoc) { 'da co tu truoc' } else { 'VUA BAT' }
        Write-Host ("  [OK]   {0,-18} {1}" -f $n, $nhan) -ForegroundColor Green
    } else {
        # Khong `exit 1`: cac dich vu con lai van nen duoc dat. Nhung phai noi to.
        Write-Host ("  [LOI]  {0,-18} dat xong ma doc lai VAN KHONG THAY" -f $n) -ForegroundColor Red
    }
}

Write-Host ""
Write-Host ("Xong. {0}/{1} dich vu co FAILURE_ACTIONS." -f $doi, $DichVu.Count)
Write-Host "Kiem tay:  sc.exe qfailure LTTStudioWeb"
Write-Host ""
Write-Host "! Nho: day moi la mot nua. Con mo coi giu cong van chan duoc ban" -ForegroundColor Yellow
Write-Host "  moi bind. Nua kia nam trong ma (server/run.py + /health/ready)." -ForegroundColor Yellow
