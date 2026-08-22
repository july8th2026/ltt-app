# start_comfy_h37.ps1 - khoi dong ComfyUI tren may B, CHUA LAI VRAM cho may. (H37)
#
#   powershell -ExecutionPolicy Bypass -File E:\AI\ltt_render\gateway\render_gateway\deploy\start_comfy_h37.ps1
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# !! VI SAO CO TEP NAY THAY VI SUA `E:\AI\tools\start_comfy.ps1`:
#    Tep do la cua DU AN VIDEO. Sua no la doi hanh vi cua ho ma ho khong biet.
#    Tep nay giu Y NGUYEN moi co cua ho va chi THEM `--reserve-vram`.
#
#      cua ho : main.py --port 8188 --disable-auto-launch --listen 127.0.0.1
#      cua ta : ... + --reserve-vram 3
#
# !! VI SAO CAN `--reserve-vram`: do that 21-22/08, cau hinh dich cua H37 chiem
#    23,9 / 24,6 GB = 97,5 % VRAM va O LI muc do GIUA CAC JOB (ComfyUI giu model
#    thuong tru). Tren mot may de ban dung chung voi du an video, do la khong chua
#    cho cho ai. `--reserve-vram 3` bao ComfyUI de danh 3 GB cho he dieu hanh va
#    phan mem khac; tran cua ta xuong ~21,5 GB. Cai gia la cham hon chut do phai
#    day ra day vao.
#
# !! CHI MOT INSTANCE GIU DUOC CONG 8188. Ai khoi dong truoc thi co cua nguoi do
#    co hieu luc. Neu du an video khoi dong bang script cua HO thi KHONG co
#    reserve-vram - do la dieu can noi voi ho, khong phai dieu de sua len len.

[CmdletBinding()]
param(
    [string]$Venv    = "E:\ai\venv\Scripts\python.exe",
    [string]$Comfy   = "E:\ai\ComfyUI",
    [int]$Port       = 8188,
    [double]$ChuaLai = 3.0,
    [int]$ChoGiay    = 300
)

$ErrorActionPreference = "Continue"

# !! TU GHI LOG. Tep nay duoc phong qua Win32_Process.Create de THOAT KHOI JOB
#    OBJECT cua Nexus: `exec` cua Nexus tra ve `contained: true`, tuc no GIAM CA CAY
#    TIEN TRINH - lenh ket thuc (hoac het gio) la ComfyUI chet theo. Da dinh that
#    22/08: ComfyUI len duoc toi buoc nap custom node roi bien mat.
#    Va Win32_Process.Create KHONG co shell, nen '*> tep.log' tren dong lenh chi la
#    tham so van ban. Vay nen ghi log tu day.
$LogKhoiDong = "E:i\logs\start_comfy_h37.log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogKhoiDong) | Out-Null
try { Start-Transcript -Path $LogKhoiDong -Force | Out-Null } catch { }

# --- 0. Khong gianh cong cua ai --------------------------------------------------
$dang = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($dang) {
    Write-Host "ComfyUI DA CHAY san (PID $($dang[0].OwningProcess)) - khong khoi dong lai." -ForegroundColor Yellow
    Write-Host "Neu can co --reserve-vram thi phai dung instance do TRUOC, va" -ForegroundColor Yellow
    Write-Host "phai chac chan khong ai dang chay viec tren no." -ForegroundColor Yellow
    try { Stop-Transcript | Out-Null } catch { }
    exit 0
}

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")
$env:GIT_PYTHON_REFRESH = "quiet"

$out = "E:\ai\logs\comfy_run.log"
$err = "E:\ai\logs\comfy_run_err.log"
New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
foreach ($f in @($out, $err)) { if (Test-Path $f) { Clear-Content $f } }

$doiSo = @("main.py", "--port", "$Port", "--disable-auto-launch",
           "--listen", "127.0.0.1", "--reserve-vram", "$ChuaLai")
Write-Host ("Khoi dong: python " + ($doiSo -join " ")) -ForegroundColor Cyan

$p = Start-Process -FilePath $Venv -ArgumentList $doiSo -WorkingDirectory $Comfy `
     -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
Write-Host "ComfyUI PID: $($p.Id)"
$p.Id | Out-File "E:\ai\logs\comfy.pid" -Encoding ascii

# --- 1. Cho san sang, roi XAC MINH co da co hieu luc -------------------------------
for ($i = 0; $i -lt [Math]::Ceiling($ChoGiay / 10); $i++) {
    Start-Sleep -Seconds 10
    try {
        $r = Invoke-RestMethod "http://127.0.0.1:$Port/system_stats" -TimeoutSec 5
        Write-Host ("SAN SANG sau {0} giay" -f (($i + 1) * 10)) -ForegroundColor Green
        foreach ($d in $r.devices) {
            "  {0} | VRAM tong {1:N2} GB | VRAM tu do {2:N2} GB" -f $d.name, ($d.vram_total/1GB), ($d.vram_free/1GB)
        }
        # !! XAC MINH co that su nam tren dong lenh, khong chi tin la minh da truyen.
        $cl = (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cl -and $cl -match "--reserve-vram") {
            Write-Host "  XAC MINH: --reserve-vram co tren dong lenh that." -ForegroundColor Green
            try { Stop-Transcript | Out-Null } catch { }
            exit 0
        }
        Write-Host "  CANH BAO: KHONG thay --reserve-vram tren dong lenh cua PID $($p.Id)." -ForegroundColor Red
        exit 4
    } catch { }
}
Write-Host "KHONG PHAN HOI sau $ChoGiay giay - xem $err" -ForegroundColor Red
exit 1
