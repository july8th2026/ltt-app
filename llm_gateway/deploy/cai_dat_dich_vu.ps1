# cai_dat_dich_vu.ps1 - cai hai dich vu VLM va mo tuong lua. CHAY TREN MAY B.
#
# !! CAN QUYEN ADMINISTRATOR. Mo PowerShell bang "Run as administrator" roi chay:
#     powershell -ExecutionPolicy Bypass -File H:\LTT_LLM\gateway\deploy\cai_dat_dich_vu.ps1
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# BA DIEU KHONG BAO GIO DUOC DOI O DAY:
#   1. llama-server CHI nghe 127.0.0.1. No KHONG co xac thuc: ai goi duoc cong do
#      la dung duoc model nha khong gioi han. llama-swap cung CHI 127.0.0.1.
#   2. Chi LTTLlmGateway nghe LAN, va tuong lua CHI mo cho 192.168.2.17 (may A).
#   3. KHONG dua bat cu cong nao trong so nay ra Cloudflare.
#
# LUU Y VE THU TU: LTTLlmGateway phu thuoc LTTLlamaSwap. Nguoc lai thi cong se
# tra 502 trong vai giay dau moi lan may khoi dong lai - trong nhu hong.

[CmdletBinding()]
param(
    [string]$Goc   = "H:\LTT_LLM",
    [string]$MayA  = "192.168.2.17",
    [int]   $Cong  = 8299,
    [switch]$Go                              # go bo thay vi cai
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

# nssm dung chung voi cong render neu may B da cai no roi.
$nssm = "$Goc\bin\nssm.exe"
if (-not (Test-Path $nssm)) { $nssm = "E:\AI\ltt_render\scripts\nssm.exe" }
if (-not (Test-Path $nssm)) { $nssm = (Get-Command nssm.exe -ErrorAction SilentlyContinue).Source }
if (-not $nssm) {
    Loi "Khong thay nssm.exe. Dat no o $Goc\bin\nssm.exe roi chay lai."
    exit 1
}

if ($Go) {
    Buoc "Go bo"
    foreach ($d in @("LTTLlmGateway", "LTTLlamaSwap")) {
        if (Get-Service $d -ErrorAction SilentlyContinue) {
            & $nssm stop $d confirm | Out-Null
            & $nssm remove $d confirm | Out-Null
            Dat "da go $d"
        }
    }
    Get-NetFirewallRule -DisplayName "LTT LLM Gateway*" -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule
    Dat "da go quy tac tuong lua"
    exit 0
}

# --- 1. Dich vu llama-swap ------------------------------------------------------
# --listen 127.0.0.1 la BAT BUOC, khong phai mac dinh cho tien. llama-swap sinh ra
# llama-server, va llama-server khong co xac thuc.
Buoc "1. Dich vu LTTLlamaSwap"
$swap = "$Goc\bin\llamaswap\llama-swap.exe"
# deploy.ps1 dat yaml o `gateway\`, KHONG phai `gateway\deploy\`. Hai duong dan nay
# tung lech nhau va script se exit 1 ngay dong dau. Giu chung khop.
$yaml = "$Goc\gateway\llama-swap.yaml"
if (-not (Test-Path $swap)) { Loi "khong thay $swap - chay P1 truoc"; exit 1 }
if (-not (Test-Path $yaml)) { Loi "khong thay $yaml - chay deploy.ps1 tu may A truoc"; exit 1 }

if (-not (Get-Service LTTLlamaSwap -ErrorAction SilentlyContinue)) {
    & $nssm install LTTLlamaSwap $swap | Out-Null
}
& $nssm set LTTLlamaSwap AppDirectory "$Goc\bin\llamaswap"                      | Out-Null
& $nssm set LTTLlamaSwap AppParameters "--config `"$yaml`" --listen 127.0.0.1:8280" | Out-Null
& $nssm set LTTLlamaSwap AppStdout "$Goc\logs\llamaswap.log"                    | Out-Null
& $nssm set LTTLlamaSwap AppStderr "$Goc\logs\llamaswap_err.log"                | Out-Null
& $nssm set LTTLlamaSwap AppRotateFiles 1                                       | Out-Null
& $nssm set LTTLlamaSwap AppRotateBytes 20000000                                | Out-Null
& $nssm set LTTLlamaSwap Start SERVICE_AUTO_START                               | Out-Null
# Chong vong lap khoi dong vo han: chay duoi AppThrottle ms thi coi la "chet ngay",
# va NSSM gian dan thoi gian cho truoc khi bat lai.
#
# !! KHONG DAT SO NAY LON HON THOI GIAN CHO CUA SCM (~30 giay). Ban dau la 90000,
#    va hau qua la MOI LAN `net stop` + `net start` DEU THAT BAI:
#
#      net start  -> SCM cho ~30s -> NSSM van dang giu throttle 90s
#      -> SCM tuyen bo "could not be started" -> gui STOP -> dich vu CHET HAN
#
#    Do la chuyen da xay ra that luc 00:12 ngay 23/08: cong VLM nam im o trang
#    thai STOPPED sau mot lan deploy binh thuong. Trieu chung danh lua nguoi doc
#    -- log ung dung ghi "Uvicorn running on http://0.0.0.0:8299" ngay truoc do,
#    nen no trong het nhu loi cua ma nguon moi trien khai.
#
# 5000 van chan duoc vong lap crash (tien trinh chet trong 5 giay = chet ngay),
# ma khong bao gio dung vao tran cho cua SCM.
& $nssm set LTTLlamaSwap AppThrottle 5000                                       | Out-Null
& $nssm set LTTLlamaSwap AppExit Default Restart                                | Out-Null
& $nssm set LTTLlamaSwap AppRestartDelay 15000                                  | Out-Null
Dat "LTTLlamaSwap da cau hinh (chi nghe 127.0.0.1:8280)"

# --- 2. Dich vu cong VLM --------------------------------------------------------
Buoc "2. Dich vu LTTLlmGateway"
$pyGw = "$Goc\venv\Scripts\python.exe"
if (-not (Test-Path $pyGw)) { Loi "khong thay $pyGw - chay deploy.ps1 tu may A truoc"; exit 1 }

$envTep = "C:\ProgramData\LTTLlm\gateway.env"
if (-not (Test-Path $envTep)) { Loi "khong thay $envTep - chay deploy.ps1 tu may A truoc"; exit 1 }

# Doi HOST sang dia chi LAN de may A goi duoc. Ghi lai KHONG BOM (quy tac 1):
# PowerShell 5.1 chen BOM voi Out-File/Set-Content, va mot BOM o day lam
# python-dotenv doc sai dong dau tien.
$dong = [IO.File]::ReadAllLines($envTep) | ForEach-Object {
    if ($_ -like "LTT_LLM_HOST=*") { "LTT_LLM_HOST=0.0.0.0" } else { $_ }
}
[IO.File]::WriteAllText($envTep, ($dong -join [Environment]::NewLine), (New-Object Text.UTF8Encoding($false)))

if (-not (Get-Service LTTLlmGateway -ErrorAction SilentlyContinue)) {
    & $nssm install LTTLlmGateway $pyGw | Out-Null
}
& $nssm set LTTLlmGateway AppDirectory "$Goc\gateway"                           | Out-Null
& $nssm set LTTLlmGateway AppParameters "-m llm_gateway.main"                   | Out-Null

# !! NAP gateway.env VAO MOI TRUONG CUA DICH VU.
#    Truoc day cho nay chi dat PYTHONPATH, va gateway.env KHONG BAO GIO duoc doc.
#    Hau qua neu quen: dich vu len binh thuong, /health tra 200, nhung
#      - LTT_LLM_TOKEN rong  -> cong KHONG kiem bearer, mo toang tren LAN
#      - LTT_LLM_MODELS rong -> fail-closed, /v1/models tra rong, khach tuong hong
#      - LTT_LLM_HOST mac dinh 127.0.0.1 -> may A khong goi duoc
#    Ba trieu chung khac nhau, mot nguyen nhan, va khong cai nao bao loi.
$bien = @("PYTHONPATH=$Goc\gateway")
foreach ($caiDong in [IO.File]::ReadAllLines($envTep)) {
    $d = $caiDong.Trim()
    if ($d -and -not $d.StartsWith("#") -and $d.Contains("=")) { $bien += $d }
}
& $nssm set LTTLlmGateway AppEnvironmentExtra $bien                             | Out-Null
Dat ("nap $($bien.Count) bien moi truong tu gateway.env")
& $nssm set LTTLlmGateway AppStdout "$Goc\logs\gateway.log"                     | Out-Null
& $nssm set LTTLlmGateway AppStderr "$Goc\logs\gateway_err.log"                 | Out-Null
& $nssm set LTTLlmGateway AppRotateFiles 1                                      | Out-Null
& $nssm set LTTLlmGateway AppRotateBytes 20000000                               | Out-Null
& $nssm set LTTLlmGateway Start SERVICE_AUTO_START                              | Out-Null
& $nssm set LTTLlmGateway AppThrottle 5000                                      | Out-Null   # xem ghi chu o LTTLlamaSwap ben tren
& $nssm set LTTLlmGateway AppExit Default Restart                               | Out-Null
& $nssm set LTTLlmGateway AppRestartDelay 15000                                 | Out-Null
& $nssm set LTTLlmGateway DependOnService LTTLlamaSwap                          | Out-Null
Dat "LTTLlmGateway da cau hinh (khoi dong sau LTTLlamaSwap)"

# --- 3. Tuong lua: CHI cho may A ------------------------------------------------
Buoc "3. Tuong lua TCP $Cong"
Get-NetFirewallRule -DisplayName "LTT LLM Gateway*" -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule
New-NetFirewallRule -DisplayName "LTT LLM Gateway (chi may A)" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Cong `
    -RemoteAddress $MayA -Profile Any | Out-Null
Dat "chi $MayA duoc goi cong $Cong"

# --- 4. Kiem lai rang KHONG co gi khac lot ra LAN -------------------------------
# Day khong phai kiem tra thua. Mot dong `--listen 0.0.0.0` lot vao llama-swap.yaml
# la mo cua model nha cho ca LAN, va no se KHONG bao loi gi ca.
Buoc "4. Kiem cong 8280 va cong llama-server KHONG nghe LAN"
$lo = netstat -ano -p TCP | Select-String ":8280|:8281|:8282" | Where-Object { $_ -notmatch "127\.0\.0\.1" }
if ($lo) {
    Loi "CO CONG NGHE NGOAI LOOPBACK - dung lai va sua llama-swap.yaml:"
    $lo | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    exit 1
}
Dat "8280/8281/8282 chi nghe loopback"

Buoc "Xong"
Write-Host "  Khoi dong:  Start-Service LTTLlamaSwap; Start-Service LTTLlmGateway"
Write-Host "  Kiem tra :  curl http://127.0.0.1:$Cong/health"
