# kiem_tra.ps1 - kiem moi mat xich cua cong render. CHAY TREN MAY B.
#
#   powershell -ExecutionPolicy Bypass -File E:\AI\ltt_render\gateway\deploy\kiem_tra.ps1
#
# Tep nay THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# ** NGUYEN TAC, muon cua cong_gpu.py trong du an video tren chinh may nay:
#    "CONG NAY KHONG DOAN. Moi cau hoi phai tro ve MOT SU CO THAT."
#    Khong them cau hoi vi "nghe hop ly" - cong phinh ra vi suy dien se cham dan
#    roi bi bo qua, va khi do no te hon khong co.
#
# ** VA: mot phep kiem KHONG BIET FAIL thi khong phai phep kiem. Moi cau duoi day
#    deu co the tra loi KHONG.

[CmdletBinding()]
param(
    [string]$Goc  = "E:\AI\ltt_render",
    [int]   $Cong = 8199
)

$ErrorActionPreference = "Continue"
$loi = @()
$so  = 0

function Hoi([bool]$Dat, [string]$Cau, [string]$ViSao = "") {
    $script:so++
    if ($Dat) {
        Write-Host "  [OK]  $Cau" -ForegroundColor Green
    } else {
        Write-Host "  [X]   $Cau" -ForegroundColor Red
        if ($ViSao) { Write-Host "        $ViSao" -ForegroundColor DarkYellow }
        $script:loi += $Cau
    }
    return $Dat
}

Write-Host "KIEM TRA CONG RENDER - may B"
Write-Host ("=" * 62)

# --- 1. Hai dich vu ------------------------------------------------------------
Write-Host ""
Write-Host "[1] Dich vu"
foreach ($ten in @("LTTComfyUI", "LTTRenderGateway")) {
    $d = Get-Service $ten -ErrorAction SilentlyContinue
    Hoi ($null -ne $d) "dich vu ton tai: $ten" "chay cai_dat_dich_vu.ps1 bang quyen Administrator" | Out-Null
    if ($d) {
        Hoi ($d.Status -eq 'Running')   "dang chay: $ten" ("trang thai: " + $d.Status) | Out-Null
        Hoi ($d.StartType -eq 'Automatic') "tu khoi dong: $ten" "mat dien la mat dich vu" | Out-Null
    }
}

# --- 2. ComfyUI CHI nghe loopback ----------------------------------------------
# !! SU CO CHAN TRUOC: ComfyUI khong co xac thuc. Ai goi duoc 8188 la chay duoc ma
#    tuy y tren may nay. Day la cau hoi quan trong nhat trong ca tep.
Write-Host ""
Write-Host "[2] ComfyUI chi nghe 127.0.0.1"
$nghe8188 = Get-NetTCPConnection -State Listen -LocalPort 8188 -ErrorAction SilentlyContinue
Hoi ($null -ne $nghe8188) "ComfyUI dang nghe cong 8188" | Out-Null
if ($nghe8188) {
    $ngoai = $nghe8188 | Where-Object { $_.LocalAddress -notin @('127.0.0.1', '::1') }
    Hoi ($null -eq $ngoai) "ComfyUI KHONG nghe ra ngoai loopback" `
        ("dang nghe: " + (($ngoai | ForEach-Object { $_.LocalAddress }) -join ', ') + " - SUA NGAY") | Out-Null
}
$moToang = Get-NetFirewallRule -Direction Inbound -Action Allow -ErrorAction SilentlyContinue |
    Where-Object { $_.Enabled -eq 'True' } |
    Where-Object { ($_ | Get-NetFirewallPortFilter).LocalPort -contains '8188' }
Hoi ($null -eq $moToang) "khong co quy tac tuong lua nao mo 8188" | Out-Null

# --- 3. Tuong lua cong render chi cho may A ------------------------------------
Write-Host ""
Write-Host "[3] Tuong lua cong render"
$qt = Get-NetFirewallRule -DisplayName "LTT Render Gateway*" -ErrorAction SilentlyContinue |
    Where-Object { $_.Enabled -eq 'True' -and $_.Direction -eq 'Inbound' }
Hoi ($null -ne $qt) "co quy tac cho cong $Cong" | Out-Null
if ($qt) {
    $dc = @($qt | ForEach-Object { ($_ | Get-NetFirewallAddressFilter).RemoteAddress })
    Hoi ($dc -contains '192.168.2.17') "quy tac gioi han cho 192.168.2.17" `
        ("dang cho: " + ($dc -join ', ')) | Out-Null
    Hoi (-not ($dc -contains 'Any')) "quy tac KHONG mo cho moi dia chi" | Out-Null
}

# --- 4. Cong render tra loi -----------------------------------------------------
Write-Host ""
Write-Host "[4] Cong render tra loi"
$env_ = "C:\ProgramData\LTTRender\gateway.env"
$tok = ""
if (Test-Path $env_) {
    foreach ($d in [IO.File]::ReadAllLines($env_)) {
        # Tach bang dau '=' dau tien, KHONG dem ky tu bang tay: "LTT_RENDER_TOKEN="
        # dai 17 chu khong phai 18, va dem sai thi token mat ky tu dau - loi chi lo
        # ra thanh "401 sai token" o may A, rat lau sau, o mot cho khac han.
        if ($d -like "LTT_RENDER_TOKEN=*") { $tok = $d.Split('=', 2)[1] }
    }
}
Hoi ($tok -ne "") "gateway.env co token" "khong co token thi cong tu choi nghe LAN" | Out-Null

# BOM trong tep cau hinh da tung lam sap production du an nay (quy tac 1).
if (Test-Path $env_) {
    $b = [IO.File]::ReadAllBytes($env_)
    $coBom = ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)
    Hoi (-not $coBom) "gateway.env KHONG co BOM" "BOM lam json/env doc sai - xem quy tac 1" | Out-Null
}

try {
    $h = @{ "Authorization" = "Bearer $tok" }
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Cong/health" -Headers $h -TimeoutSec 10
    Hoi $true "/health tra loi" | Out-Null
    Write-Host ("        phien ban gateway: " + $r.version)
    Write-Host ("        ComfyUI song: " + $r.comfy_alive + " | ban: " + $r.busy + " | RAM trong: " + $r.ram_free_gb + " GB")
    Hoi ($r.comfy_alive -eq $true) "cong render noi duoc toi ComfyUI" | Out-Null
} catch {
    Hoi $false "/health tra loi" ("loi: " + $_.Exception.Message) | Out-Null
}

# --- 5. Ma tren may B khop voi repo --------------------------------------------
# !! SU CO KINH DIEN CUA DU AN NAY: sua tep truc tiep tren may chay, quen sua o
#    repo, lan cap nhat sau mat trang va MAT AM THAM.
Write-Host ""
Write-Host "[5] Ma khop voi repo"
$bang = "$Goc\scripts\hash_mong_doi.txt"
if (Test-Path $bang) {
    $lech = @()
    foreach ($dong in [IO.File]::ReadAllLines($bang)) {
        if (-not $dong) { continue }
        $p = $dong.Split('=', 2)
        $tep = Join-Path "$Goc\gateway" ($p[0] -replace '/', '\')
        if (-not (Test-Path -LiteralPath $tep)) { $lech += ("THIEU " + $p[0]); continue }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $tep).Hash.ToLower() -ne $p[1]) {
            $lech += ("KHAC  " + $p[0])
        }
    }
    Hoi ($lech.Count -eq 0) "moi tep khop hash voi repo" (($lech -join " | ")) | Out-Null
} else {
    Hoi $false "co bang hash de doi chieu" "chay deploy.ps1 tu may A" | Out-Null
}

# --- 6. Dong ho -----------------------------------------------------------------
# !! SU CO THAT: cum Nexus da dut mot lan vi may B lech 83 phut, moi request bi tu choi.
Write-Host ""
Write-Host "[6] Dong bo dong ho"
$t = Get-ScheduledTask -TaskName NexusClockSync -ErrorAction SilentlyContinue
Hoi ($null -ne $t) "co tac vu NexusClockSync" "lech dong ho >300s la cum Nexus tu chan" | Out-Null

# --- 7. venv rieng, khong dung chung voi ComfyUI ---------------------------------
Write-Host ""
Write-Host "[7] venv rieng"
Hoi (Test-Path "$Goc\venv\Scripts\python.exe") "cong render co venv rieng" | Out-Null
if (Test-Path "E:\AI\venv\Scripts\python.exe") {
    $co = & "E:\AI\venv\Scripts\python.exe" -c "import importlib.util,sys; sys.stdout.write('1' if importlib.util.find_spec('fastapi') else '0')" 2>$null
    Hoi ($co -ne "1") "venv cua ComfyUI KHONG bi cai them fastapi" `
        "co ai do pip install vao venv ComfyUI - do la venv cua ca stack video 342 GB" | Out-Null
}

# --- Ket luan -------------------------------------------------------------------
Write-Host ""
Write-Host ("=" * 62)
if ($loi.Count -gt 0) {
    Write-Host ("  CHAN - " + $loi.Count + "/" + $so + " cau hoi TRUOT:") -ForegroundColor Red
    $loi | ForEach-Object { Write-Host ("    - " + $_) }
    exit 1
}
Write-Host ("  $so/$so - moi mat xich deu song") -ForegroundColor Green
Write-Host ""
Write-Host "CON MOT CAU MA TEP NAY KHONG TU TRA LOI DUOC:" -ForegroundColor Yellow
Write-Host "  Tu MOT MAY KHAC trong LAN (khong phai 192.168.2.17), goi"
Write-Host "  http://192.168.2.66:$Cong/health - no PHAI bi chan."
Write-Host "  Doc lai cau hinh tuong lua khong phai la mot phep kiem."
exit 0
