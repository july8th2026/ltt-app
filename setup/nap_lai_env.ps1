# nap_lai_env.ps1 - nap lai secrets\app.env vao moi truong cua BON dich vu.
#
#     powershell -ExecutionPolicy Bypass -File .\setup\nap_lai_env.ps1
#
# CAN QUYEN ADMINISTRATOR (nssm ghi vao dang ky dich vu).
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! VI SAO CAN SCRIPT NAY, VA VI SAO SUA app.env ROI RESTART LA KHONG DU:
#
#    Dich vu chay qua nssm, va nssm NUONG bien moi truong vao dang ky dich vu
#    LUC CAI (`AppEnvironmentExtra`). Tien trinh `server\run.py` chi doc
#    `os.environ` - no KHONG tu doc `secrets\app.env` luc chay.
#
#    Nen sau khi them mot dong vao app.env:
#
#      Restart-Service LTTStudioWeb          -> dich vu len lai voi ENV CU
#      (khong loi nao bao, chi la cai co moi khong co tac dung)
#
#    Da dinh hai lan trong du an nay: mot lan o cong VLM may B (sua gateway.env
#    roi restart, khong an gi), mot lan o day (them LTT_PUBLIC_API_TOOLS ngay
#    23/08). Trieu chung giong het nhau: cau hinh dung, dich vu chay, tinh nang
#    khong bat.
#
# !! NHE HON `2-cai-dat.ps1`. Script cai dat lam dung viec nay o dong 398-403,
#    nhung kem theo dung dich vu, robocopy ca cay ma nguon va `alembic upgrade
#    head`. Khi thu duy nhat thay doi la app.env thi khong can bat nhieu do.
#
# !! BI MAT KHONG DI QUA DONG LENH. Script tu doc file va truyen cho nssm; no
#    khong in gia tri nao ra man hinh va khong nhan bi mat qua tham so - dong
#    lenh nhin thay duoc trong danh sach tien trinh.

[CmdletBinding()]
param(
    [string]$Root = 'C:\LTTPlatform',
    # LTTStudioVoice them 2026-08-30 (Q117). No chay tu vieneu-venv nhung van

    # lay env qua nssm nhu ba dich vu kia, nen no PHAI co trong danh sach nay:

    # quen no thi doi mot co (vi du LTT_VOICE_BACKEND) se khong co tac dung, va

    # khong loi nao bao.

    [string[]]$Services = @('LTTStudioWeb', 'LTTStudioWorker', 'LTTStudioCodex',

                            'LTTStudioVoice'),
    [switch]$KhongKhoiDongLai       # chi nap ENV, khong restart
)

$ErrorActionPreference = 'Stop'
function Head($m) { Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Loi($m)  { Write-Host "  [LOI] $m" -ForegroundColor Red }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw 'Can quyen Administrator. Mo PowerShell bang Run as administrator.' }

$envFile = Join-Path $Root 'secrets\app.env'
$nssmExe = Join-Path $Root 'tools\nssm.exe'
if (-not (Test-Path $envFile)) { throw "Khong thay $envFile" }
if (-not (Test-Path $nssmExe)) { throw "Khong thay $nssmExe" }

# Cung cach dung cap nhu `2-cai-dat.ps1` dong 398-402. Giu giong het co chu y:
# hai cach doc khac nhau la hai bo ENV khac nhau, va lech do rat kho thay.
Head "Doc $envFile"
$envPairs = @()
foreach ($line in (Get-Content $envFile)) {
    $t = $line.Trim()
    if ($t -and -not $t.StartsWith('#') -and $t.Contains('=')) { $envPairs += $t }
}
if ($envPairs.Count -eq 0) { throw 'app.env khong co dong bien nao - dung lai' }
Ok "$($envPairs.Count) bien (khong in gia tri)"

Head 'Nap vao dich vu'
foreach ($svc in $Services) {
    if (-not (Get-Service $svc -ErrorAction SilentlyContinue)) {
        Write-Host "  bo qua $svc (chua cai)" -ForegroundColor Yellow
        continue
    }
    & $nssmExe set $svc AppEnvironmentExtra ($envPairs -join "`r`n") | Out-Null
    if ($LASTEXITCODE -ne 0) { Loi "$svc : nssm set that bai"; continue }
    Ok "$svc da nhan ENV moi"
}

if ($KhongKhoiDongLai) {
    Write-Host ""
    Write-Host 'DA NAP ENV nhung CHUA khoi dong lai - dich vu van dang chay ENV CU.' -ForegroundColor Yellow
    Write-Host 'Chay lai khong kem -KhongKhoiDongLai, hoac restart tay, thi moi co tac dung.'
    exit 0
}

Head 'Khoi dong lai'
# Dung theo THU TU NGUOC voi phu thuoc roi bat lai xuoi: worker va codex phu
# thuoc vao cung CSDL nhung khong phu thuoc nhau, con web la thu nguoi dung thay.
foreach ($svc in ($Services | Sort-Object -Descending)) {
    if (-not (Get-Service $svc -ErrorAction SilentlyContinue)) { continue }
    Restart-Service $svc -Force -ErrorAction SilentlyContinue
    $s = (Get-Service $svc).Status
    if ($s -eq 'Running') { Ok "$svc : $s" } else { Loi "$svc : $s" }
}

Write-Host ""
Write-Host 'XONG. Kiem lai bang mot thu that, khong tin trang thai dich vu:' -ForegroundColor Cyan
Write-Host '  curl.exe -s https://app.lttstudios.com/api/v1/health'
