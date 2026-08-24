# chay_lo_dai.ps1 - chay MOT LO DO DAI tren may B, tach roi khoi phien SSH.
#
#   powershell -ExecutionPolicy Bypass -File render_gateway\deploy\chay_lo_dai.ps1 `
#       -Ca G9_ben_100 -Prompts G9_prompts.json -Buoc 50
#
#   ... -Xem                # chi doc log, khong khoi dong gi
#   ... -Dung               # xoa task va dung lo
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! VI SAO KHONG CHAY THANG QUA SSH - D-055.
#
#    OpenSSH tren Windows gom moi tien trinh con vao JOB OBJECT CUA PHIEN. Phien
#    dut la ca cay chet theo. Da mat mot lo 100 anh o anh 87/100 dung nhu vay,
#    roi mat them 80 phut vi tuong no con chay.
#
#    Va `Start-Process -WindowStyle Hidden` KHONG cuu duoc: no van nam trong job
#    object do. Da thu, va ket qua la khong co tien trinh nao + hai tep log 0 byte.
#
#    Task Scheduler khoi tien trinh NGOAI job object cua phien, nen no song qua
#    viec dong ket noi. Do la ly do duy nhat script nay ton tai.
#
# !! HAI CHOT NHO MA DAT:
#
#    1. `python -u` - khong dem stdout. Thieu no thi tep log nam im 0 byte hang
#       gio va khong the phan biet "dang chay" voi "da chet".
#    2. `-Ca` KHONG duoc trung ten tep `-Prompts`. `chay_baseline.py` ghi ket qua
#       ra `bench\<Ca>.json`, nen trung ten la GHI DE CHINH TEP DAU VAO. Lo dau
#       da tu xoa de bai cua no ngay sau luot chay dau; chi khong ai thay vi tep
#       chi duoc doc mot lan luc khoi dong. Script nay TU CHOI truong hop do.

[CmdletBinding()]
param(
    [string]$MayB    = "192.168.2.66",
    [string]$User    = "lengo",
    [string]$Key     = "$env:USERPROFILE\.ssh\nexus_b",
    [string]$Goc     = "E:\AI\ltt_render",
    [string]$Ca      = "",
    [string]$Prompts = "",
    [int]$Buoc       = 50,
    [string]$Mode    = "t2i",
    [double]$RefMp   = 0,
    [int]$TranToken  = 0,
    [string]$Task    = "LTT_LoDai",
    [switch]$Xem,
    [switch]$Dung
)

$ErrorActionPreference = "Stop"

function TrenB([string]$Lenh) {
    # -EncodedCommand: base64 cua UTF-16LE. Truyen thang qua ssh la bon lop thoat
    # ky tu, moi lop mot kieu quy tac.
    $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Lenh))
    & ssh -i $Key -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 `
        "$User@$MayB" "powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand $enc"
}
function TrenBTho([string]$Lenh) {
    & ssh -i $Key -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 `
        "$User@$MayB" $Lenh
}

$LogB = "$Goc\logs\$Task.log"

if ($Dung) {
    TrenBTho "schtasks /Delete /TN $Task /F"
    TrenB "Get-Process python -ErrorAction SilentlyContinue | Where-Object { `$_.Path -like '$Goc\venv\*' } | Stop-Process -Force -ErrorAction SilentlyContinue; 'da dung'"
    exit 0
}

if ($Xem) {
    TrenB "if (Test-Path '$LogB') { Get-Content '$LogB' -Tail 12 } else { 'chua co log' }"
    exit 0
}

if (-not $Ca -or -not $Prompts) {
    Write-Host "Thieu -Ca hoac -Prompts." -ForegroundColor Red
    exit 2
}

# !! Chot chong ghi de tep dau vao. Xem chu thich dau tep.
$tenPrompts = [IO.Path]::GetFileNameWithoutExtension($Prompts)
if ($tenPrompts -eq $Ca) {
    Write-Host "DUNG: -Ca '$Ca' trung ten tep -Prompts '$Prompts'." -ForegroundColor Red
    Write-Host "  Bo chay ghi ket qua ra bench\$Ca.json => no se GHI DE chinh tep de bai." -ForegroundColor Red
    Write-Host "  Doi -Ca sang mot ten khac (vd '${Ca}_kq')." -ForegroundColor Red
    exit 3
}

$args = @(
    "-u", "$Goc\gateway\render_gateway\deploy\chay_baseline.py",
    "--ca", $Ca,
    "--prompts", "$Goc\bench\$Prompts",
    "--comfy", "http://127.0.0.1:8188",
    "--mode", $Mode,
    "--steps", "$Buoc",
    "--timeout", "900"
)
if ($RefMp -gt 0)     { $args += @("--ref-mp", "$RefMp") }
if ($TranToken -gt 0) { $args += @("--tran-token", "$TranToken") }

$cmdB = "$Goc\logs\$Task.cmd"
$noiDung = @"
@echo off
REM Sinh tu render_gateway\deploy\chay_lo_dai.ps1 - dung sua tay.
$Goc\venv\Scripts\python.exe $($args -join ' ') >> $LogB 2>&1
"@

Write-Host "== Ghi $cmdB tren may B"
# UTF8Encoding(`$false) = KHONG BOM (quy tac 1). Ghi TREN MAY B, khong ghi o day
# roi scp: mot vong it hon, va khong de lai tep tam tren may A.
$encND = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($noiDung))
TrenB "[IO.File]::WriteAllBytes('$cmdB', [Convert]::FromBase64String('$encND')); 'da ghi cmd'"

Write-Host "== Tao va chay task $Task"
TrenBTho "schtasks /Create /TN $Task /TR ""cmd /c $cmdB"" /SC ONCE /ST 23:59 /RU SYSTEM /RL HIGHEST /F"
TrenBTho "schtasks /Run /TN $Task"

Write-Host ""
Write-Host "Lo dang chay TACH ROI. Theo doi:" -ForegroundColor Green
Write-Host "  powershell -File render_gateway\deploy\chay_lo_dai.ps1 -Task $Task -Xem"
Write-Host ""
Write-Host "XONG THI XOA TASK - `/SC ONCE` van co trigger 23:59 va se ban lai:" -ForegroundColor Yellow
Write-Host "  powershell -File render_gateway\deploy\chay_lo_dai.ps1 -Task $Task -Dung"
