# cai_dat_dich_vu.ps1 - cai hai dich vu va mo tuong lua. CHAY TREN MAY B.
#
# !! CAN QUYEN ADMINISTRATOR. Mo PowerShell bang "Run as administrator" roi chay:
#     powershell -ExecutionPolicy Bypass -File E:\AI\ltt_render\gateway\deploy\cai_dat_dich_vu.ps1
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# HAI DIEU KHONG BAO GIO DUOC DOI O DAY (quyet dinh nen Q102):
#   1. ComfyUI CHI nghe 127.0.0.1. No khong co xac thuc: ai goi duoc cong 8188 la
#      chay duoc ma tuy y tren may nay. Dua no ra LAN hay ra Cloudflare la mo cua.
#   2. Cong render nghe LAN nhung tuong lua CHI mo cho 192.168.2.17 (may A).

[CmdletBinding()]
param(
    [string]$Goc      = "E:\AI\ltt_render",
    [string]$ComfyGoc = "E:\AI\ComfyUI",
    [string]$MayA     = "192.168.2.17",
    [int]   $Cong     = 8199,
    [switch]$Go,                             # go bo thay vi cai
    [switch]$BoQuaComfy                      # KHONG dung toi ComfyUI cua du an video
)

$ErrorActionPreference = "Stop"

function Buoc($s) { Write-Host ""; Write-Host "== $s" -ForegroundColor Cyan }
function Dat($s)  { Write-Host "  [OK]  $s" -ForegroundColor Green }
function Loi($s)  { Write-Host "  [LOI] $s" -ForegroundColor Red }

$dangAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $dangAdmin) {
    Loi "Chua co quyen Administrator. Mo PowerShell bang 'Run as administrator'."
    exit 1
}

$nssm = "E:\AI\ltt_render\scripts\nssm.exe"
if (-not (Test-Path $nssm)) { $nssm = (Get-Command nssm.exe -ErrorAction SilentlyContinue).Source }
if (-not $nssm) {
    Loi "Khong thay nssm.exe. Dat no o $Goc\scripts\nssm.exe roi chay lai."
    exit 1
}

if ($Go) {
    Buoc "Go bo"
    foreach ($d in @("LTTRenderGateway", "LTTComfyUI")) {
        if (Get-Service $d -ErrorAction SilentlyContinue) {
            & $nssm stop $d confirm | Out-Null
            & $nssm remove $d confirm | Out-Null
            Dat "da go $d"
        }
    }
    Get-NetFirewallRule -DisplayName "LTT Render Gateway*" -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule
    Dat "da go quy tac tuong lua"
    exit 0
}

# --- 1. Dich vu ComfyUI ---------------------------------------------------------
# --listen 127.0.0.1 la BAT BUOC, khong phai mac dinh cho tien.
Buoc "1. Dich vu LTTComfyUI"

# !! ComfyUI tren may B do DU AN VIDEO dung chung va HO tu khoi dong no bang
#    E:/AI/tools/start_comfy.ps1. Hai rui ro co that khi bien no thanh dich vu:
#      1. tranh cong 8188 voi cach khoi dong cua ho -> mot ben chet;
#      2. de XOA MAT co --reserve-vram 3 ma H37 dat sau su co D-024.
#
# ** CHU DU AN DUYET CAI THANH DICH VU - 2026-08-22 (H38).
#    Ly do: do that 22/08 cho thay ComfyUI dang chay la mot TIEN TRINH MO COI
#    (cha da thoat, sinh luc 14:11 tu mot phien SSH). Khong dich vu, khong Task
#    Scheduler, khong Startup, khong registry Run. MAY KHOI DONG LAI LA MAT.
#
#    Rui ro 2 da duoc bit ngay ben duoi: bo co o day BUOC PHAI khop
#    `start_comfy_h37.ps1`, va co `--reserve-vram 3`.
#
#    Rui ro 1 KHONG bit duoc bang script - no la thoa thuan giua nguoi voi nguoi:
#    tu nay ComfyUI do DICH VU quan ly. Ai chay `E:\AI\tools\start_comfy.ps1` tay
#    khi dich vu dang chay se thay "cong 8188 dang ban" chu khong phai ComfyUI moi.
if ($BoQuaComfy) {
    Write-Host "  [BO QUA] -BoQuaComfy: khong dung toi ComfyUI." -ForegroundColor Yellow
    Write-Host "           Luu y: khong co dich vu thi ComfyUI KHONG song qua reboot." -ForegroundColor Yellow
} else {
$pyComfy = "E:\AI\venv\Scripts\python.exe"
if (-not (Test-Path $pyComfy)) { Loi "khong thay $pyComfy"; exit 1 }

# !! BO CO PHAI KHOP `start_comfy_h37.ps1` - do la ban khai chuan.
#    Ban truoc cua dong nay la:
#        main.py --port 8188 --disable-auto-launch --listen 127.0.0.1 --cache-ram 24 64
#    SAI hai cho:
#      1. THIEU `--reserve-vram 3` - chinh cai H37 them sau su co D-024. Mat no
#         thi mat TRONG IM LANG: ComfyUI van chay, van render, chi la bien VRAM
#         mong lai va may de ban dung chung khong con cho tho.
#      2. THUA `--cache-ram 24 64` - instance dang chay that (va moi so do cua
#         H38 ngay 22/08) KHONG co co nay. Dat vao la phuc vu mot cau hinh chua
#         ai do.
#    Quy tac: bo co o day = bo co cua `start_comfy_h37.ps1`. Doi mot ben thi doi ca hai.
if (-not (Get-Service LTTComfyUI -ErrorAction SilentlyContinue)) {
    & $nssm install LTTComfyUI $pyComfy | Out-Null
}
& $nssm set LTTComfyUI AppDirectory $ComfyGoc                                  | Out-Null
& $nssm set LTTComfyUI AppParameters "main.py --port 8188 --disable-auto-launch --listen 127.0.0.1 --reserve-vram 3" | Out-Null

# !! GHIM GPU BANG UUID (P0-GPU-PIN, Task 0.2 LTT LLM Dual-Model, 2026-09-11).
#    May B co hai GPU tu 09/2026 (3090 + 5060 Ti). ComfyUI dung CHUNG card 24 GB
#    voi qwen38-* (xem llm_gateway/deploy/llama-swap.yaml) - khong ghim thi
#    ComfyUI tu do co the roi len 5060 Ti, ma 5060 Ti de danh cho model khac
#    (D-09a). UUID lay tu llm_gateway/deploy/gpu_may_b.json, vai "ltt38". Doi
#    card that thi doi trong gpu_may_b.json VA o day - hai cho khai cung mot
#    dieu, tep .ps1 nay khong doc JSON duoc (thuan ASCII, khong Python inline).
#    tests/test_1200_ghim_gpu_may_b.py doi chieu dong duoi day voi gpu_may_b.json.
& $nssm set LTTComfyUI AppEnvironmentExtra "CUDA_VISIBLE_DEVICES=GPU-26623278-4fa5-82db-4306-237651b03e78" | Out-Null

# !! GIET CA CAY TIEN TRINH khi dung dich vu.
#    `E:\ai\venv\Scripts\python.exe` la STUB 274 KB, no sinh ra
#    `C:\Users\lengo\...\Python312\python.exe` moi la ComfyUI THAT (giu model + VRAM).
#    Chi giet tien trinh cha thi dich vu bao "Stopped" trong khi ComfyUI that
#    VAN SONG VA VAN OM VRAM. Do that 22/08: PID 8564 (3,8 MB) -> PID 13912 (2.265 MB).
#
# !! KHONG DAT `AppKillProcessTree` O DAY. nssm tren may B la **2.24 (2014-08-31)**,
#    va tham so do CHUA TON TAI trong ban 2.24 - no duoc them o cac ban sau, va o
#    do no dung de TAT hanh vi mac dinh chu khong phai de bat.
#
#    Ban 2.24 VON DA giet ca cay tien trinh khi dung dich vu. Dat tham so nay lam
#    nssm in mot trang loi "Invalid parameter" giua chung script, va nguoi doc
#    tuong dich vu cai hong. Da xay ra that 23/08.
#
#    KHONG TIN, HAY DO: sau `nssm stop LTTComfyUI`, kiem
#    `nvidia-smi --query-gpu=memory.used --format=csv`. Con vai GB nghia la
#    ComfyUI that con song, va luc do moi phai tim cach khac.
& $nssm set LTTComfyUI AppStdout "$Goc\logs\comfy.log"                         | Out-Null
& $nssm set LTTComfyUI AppStderr "$Goc\logs\comfy_err.log"                     | Out-Null
& $nssm set LTTComfyUI AppRotateFiles 1                                        | Out-Null
& $nssm set LTTComfyUI AppRotateBytes 20000000                                 | Out-Null
# ComfyUI chi phuc vu anh (image.ltt). Trong cua so LLM no KHONG duoc chay: mot
# ComfyUI am giu ~223.5 MiB CUDA context, day bien 3.8 (-c 221184) xuong duoi 300 MiB.
# Trong tai residency tu `sc start` o trang thai `anh` va dung o `tra_anh`
# (platform_core/llm/residency.py). Vi vay KHONG tu khoi dong khi boot (17/09).
& $nssm set LTTComfyUI Start SERVICE_DEMAND_START                              | Out-Null
# Tran so lan khoi dong lai: khong de roi vao vong lap khoi dong vo han.
# Sau 3 lan chet trong 90 giay thi dung han va de nguoi doc log.
# !! KHONG DAT AppThrottle LON HON THOI GIAN CHO CUA SCM (~30 giay).
#    Ban dau la 90000, va hau qua la MOI LAN `net stop` + `net start` DEU THAT BAI:
#    SCM cho ~30s, NSSM van dang giu throttle 90s, SCM tuyen bo "could not be
#    started" roi gui STOP -> dich vu CHET HAN. Da xay ra that voi LTTLlmGateway
#    luc 00:12 ngay 23/08, va trieu chung danh lua nguoi doc: log ung dung ghi
#    "Uvicorn running" ngay truoc do, nen no trong het nhu loi cua ma nguon moi.
#    5000 van chan duoc vong lap crash ma khong dung vao tran cho cua SCM.
& $nssm set LTTComfyUI AppThrottle 5000                                        | Out-Null
& $nssm set LTTComfyUI AppExit Default Restart                                 | Out-Null
& $nssm set LTTComfyUI AppRestartDelay 15000                                   | Out-Null
Dat "LTTComfyUI da cau hinh (chi nghe 127.0.0.1)"
}

# --- 2. Dich vu cong render -----------------------------------------------------
Buoc "2. Dich vu LTTRenderGateway"
$pyGw = "$Goc\venv\Scripts\python.exe"
if (-not (Test-Path $pyGw)) { Loi "khong thay $pyGw - chay deploy.ps1 tu may A truoc"; exit 1 }

$envTep = "C:\ProgramData\LTTRender\gateway.env"
if (-not (Test-Path $envTep)) { Loi "khong thay $envTep - chay deploy.ps1 tu may A truoc"; exit 1 }

# Doi HOST sang dia chi LAN de may A goi duoc. Ghi lai KHONG BOM (quy tac 1).
$dong = [IO.File]::ReadAllLines($envTep) | ForEach-Object {
    if ($_ -like "LTT_RENDER_HOST=*") { "LTT_RENDER_HOST=0.0.0.0" } else { $_ }
}
# !! NOI BANG "`r`n" TUONG MINH. Do that 22/08: [Environment]::NewLine ghi ra CA
#    TEP THANH MOT DONG - gateway.env se chi con mot dong chua het moi bien, va
#    dich vu doc sai MA VAN KHOI DONG (hong im lang).
[IO.File]::WriteAllText($envTep, ($dong -join "`r`n"), (New-Object Text.UTF8Encoding($false)))

if (-not (Get-Service LTTRenderGateway -ErrorAction SilentlyContinue)) {
    & $nssm install LTTRenderGateway $pyGw | Out-Null
}
& $nssm set LTTRenderGateway AppDirectory "$Goc\gateway"                       | Out-Null
& $nssm set LTTRenderGateway AppParameters "-m render_gateway.main"            | Out-Null
# !! NAP CA gateway.env VAO MOI TRUONG DICH VU.
#    Loi that 22/08: cho nay chi dat moi PYTHONPATH, nen dich vu khoi dong ma
#    KHONG CO LTT_RENDER_TOKEN va KHONG CO LTT_RENDER_HOST. Ket qua: cong chay
#    KHONG XAC THUC. Lan do no chi nghe 127.0.0.1 (vi thieu bien HOST) nen chua
#    lo ra ngoai, va chot "nghe LAN ma khong co token thi tu choi khoi dong"
#    trong main.py da giu duoc. Nhung do la MAY, khong phai thiet ke.
$bien = @("PYTHONPATH=$Goc\gateway")
foreach ($d in (Get-Content $envTep)) {
    if ($d -match "^\s*([A-Z_]+)=(.*)$") { $bien += ($Matches[1] + "=" + $Matches[2]) }
}
& $nssm set LTTRenderGateway AppEnvironmentExtra $bien                         | Out-Null
Dat ("da nap " + $bien.Count + " bien moi truong vao dich vu")
& $nssm set LTTRenderGateway AppStdout "$Goc\logs\gateway.log"                 | Out-Null
& $nssm set LTTRenderGateway AppStderr "$Goc\logs\gateway_err.log"             | Out-Null
& $nssm set LTTRenderGateway AppRotateFiles 1                                  | Out-Null
& $nssm set LTTRenderGateway AppRotateBytes 20000000                           | Out-Null
& $nssm set LTTRenderGateway Start SERVICE_AUTO_START                          | Out-Null
# !! KHONG DAT AppThrottle LON HON THOI GIAN CHO CUA SCM (~30 giay).
#    Ban dau la 90000, va hau qua la MOI LAN `net stop` + `net start` DEU THAT BAI:
#    SCM cho ~30s, NSSM van dang giu throttle 90s, SCM tuyen bo "could not be
#    started" roi gui STOP -> dich vu CHET HAN. Da xay ra that voi LTTLlmGateway
#    luc 00:12 ngay 23/08, va trieu chung danh lua nguoi doc: log ung dung ghi
#    "Uvicorn running" ngay truoc do, nen no trong het nhu loi cua ma nguon moi.
#    5000 van chan duoc vong lap crash ma khong dung vao tran cho cua SCM.
& $nssm set LTTRenderGateway AppThrottle 5000                                  | Out-Null
& $nssm set LTTRenderGateway AppExit Default Restart                           | Out-Null
& $nssm set LTTRenderGateway AppRestartDelay 15000                             | Out-Null
if ($BoQuaComfy) {
    # Khong dat phu thuoc vao dich vu KHONG TON TAI - dat thi cong render se
    # khong bao gio khoi dong duoc.
    & $nssm reset LTTRenderGateway DependOnService 2>$null | Out-Null
    Dat "LTTRenderGateway da cau hinh (KHONG phu thuoc LTTComfyUI)"
} else {
    # KHONG phu thuoc LTTComfyUI: cong render chinh la ke ra lenh dung ComfyUI, va
    # SCM tu choi dung dich vu con dich vu phu thuoc dang chay (loi 1051,
    # render_gateway/dich_vu_comfy.py). ComfyUI nay khoi dong theo nhu cau (17/09).
    & $nssm reset LTTRenderGateway DependOnService 2>$null | Out-Null
    Dat "LTTRenderGateway da cau hinh (KHONG phu thuoc LTTComfyUI; ComfyUI chay theo nhu cau)"
}

# --- 3. Tuong lua: CHI cho may A ------------------------------------------------
Buoc "3. Tuong lua TCP $Cong"
Get-NetFirewallRule -DisplayName "LTT Render Gateway*" -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule
New-NetFirewallRule -DisplayName "LTT Render Gateway (chi may A)" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Cong `
    -RemoteAddress $MayA -Profile Any | Out-Null
Dat "chi $MayA duoc goi cong $Cong"

# Kiem lai rang KHONG co quy tac nao mo 8188 ra ngoai.
$hoTo = Get-NetFirewallRule -Direction Inbound -Action Allow -ErrorAction SilentlyContinue |
    Where-Object { $_.Enabled -eq 'True' } |
    Where-Object { ($_ | Get-NetFirewallPortFilter).LocalPort -contains '8188' }
if ($hoTo) {
    Loi "CO quy tac tuong lua mo cong 8188 (ComfyUI) ra ngoai:"
    $hoTo | ForEach-Object { Write-Host ("    " + $_.DisplayName) }
    Loi "ComfyUI KHONG co xac thuc. Go quy tac do truoc khi di tiep."
    exit 1
}
Dat "khong co quy tac nao mo 8188 ra ngoai"

# --- 4. Khoi dong ---------------------------------------------------------------
Buoc "4. Khoi dong"
if (-not $BoQuaComfy) {
    & $nssm start LTTComfyUI 2>$null | Out-Null
    Start-Sleep -Seconds 5
}
& $nssm start LTTRenderGateway 2>$null | Out-Null
Start-Sleep -Seconds 8
$ds = @("LTTRenderGateway")
if (-not $BoQuaComfy) { $ds += "LTTComfyUI" }
Get-Service $ds | Select-Object Name, Status, StartType | Format-Table -AutoSize

Write-Host ""
Write-Host "Buoc nghiem thu that (G7) - PHAI lam du ca ba:" -ForegroundColor Yellow
Write-Host "  1. Restart-Computer, roi kiem ca hai dich vu co TU LEN khong."
Write-Host "  2. Tu MAY A: goi http://192.168.2.66:$Cong/health - phai duoc."
Write-Host "  3. Tu MOT MAY KHAC trong LAN: goi CUNG dia chi do - phai BI CHAN."
Write-Host "     (Doc lai cau hinh tuong lua KHONG phai la mot phep kiem.)"
