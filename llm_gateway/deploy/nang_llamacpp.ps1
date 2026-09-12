# nang_llamacpp.ps1 - nang llama.cpp tren MAY B, co duong lui.
#
#   .\nang_llamacpp.ps1                 # nang len ban GHIM (phien_ban_ghim.json)
#   .\nang_llamacpp.ps1 -Ban latest     # lay ban MOI NHAT - phai go ra
#   .\nang_llamacpp.ps1 -Ban b10689     # nang len dung mot ban
#   .\nang_llamacpp.ps1 -HoanNguyen     # quay ve ban sao luu gan nhat
#
# ==============================================================================
# VI SAO CO SCRIPT NAY
#
# Ngay 30/08 toi nang b10580 -> b10689 bang lenh go tay qua Nexus, va dinh BON
# cai bay. Ca bon deu khong hien ra trong tai lieu chinh thuc, va ca bon deu se
# lam nguoi lam sau mat thoi gian dung y nhu the. Script nay la cho de chung
# khong con la kien thuc rieng cua mot phien chat.
#
# ==============================================================================
# BON CAI BAY, VA CACH SCRIPT NAY TRANH CHUNG
#
# 1. CHEP DE, KHONG XOA ROI CHEP.
#    Thu muc `bin\llamacpp` con giu cac DLL cudart nap tu MOT GOI RIENG
#    (cudart-llama-bin-win-cuda-*.zip). Goi `llama-*-bin-win-cuda-*.zip` KHONG
#    chua chung. Xoa ca thu muc roi giai nen ban moi vao = mat cudart =
#    llama-server khong khoi dong duoc, va thong bao loi khong he chi ve phia do.
#
# 2. DUNG DICH VU THEO DUNG THU TU, VA DUNG CA HAI.
#    `LTTLlmGateway` goi xuong `LTTLlamaSwap`. Dung gateway TRUOC, roi swap.
#    Bat thi nguoc lai. Quen dung swap thi tep .exe bi khoa va chep de that bai
#    voi "being used by another process".
#
# 3. `llama-server.exe --version` IN RA STDERR.
#    PowerShell coi stderr cua native exe la loi va tra $LASTEXITCODE = 1 du
#    lenh chay dung. Doc ma thoat do thanh "hong" la ket luan sai.
#
# 4. PHAI KHOP PHIEN BAN CUDA CUA MAY.
#    May B dung CUDA 13.3. Tai nham goi 12.4 thi llama-server nap len roi bao
#    loi DLL o thoi diem NAP MODEL, tuc sau khi moi thu trong co ve on.
#
# ==============================================================================
# ! KHONG THAY DOI GI KHAC. Script chi doi BINARY. Cau hinh model o
#   `llama-swap.yaml`, tran token o `C:\ProgramData\LTTLlm\gateway.env` - hai
#   thu do co duong rieng va script nay khong dung toi.

param(
    [string]$Ban = "",
    [switch]$HoanNguyen,
    [string]$Goc = "H:\LTT_LLM",
    [string]$Cuda = "13.3"
)

$ErrorActionPreference = "Stop"

$binDir  = Join-Path $Goc "bin\llamacpp"
$tamDir  = Join-Path $Goc "incoming"
$dichVu  = @("LTTLlmGateway", "LTTLlamaSwap")   # thu tu DUNG
$batLai  = @("LTTLlamaSwap", "LTTLlmGateway")   # thu tu BAT

function Noi($s) { Write-Output "  $s" }

function PhienBanHienTai {
    $exe = Join-Path $binDir "llama-server.exe"
    if (-not (Test-Path $exe)) { return "(chua co)" }
    # Bay 3: --version in ra stderr; gom ca hai luong roi doc.
    $out = & $exe --version 2>&1 | Out-String
    if ($out -match "build (\d+)") { return "b" + $Matches[1] }
    return "(khong doc duoc)"
}

function DungDichVu {
    foreach ($d in $dichVu) {
        $s = Get-Service $d -ErrorAction SilentlyContinue
        if ($s -and $s.Status -ne "Stopped") {
            Noi "dung $d"
            Stop-Service $d -Force
        }
    }
    Start-Sleep -Seconds 8
}

function BatDichVu {
    foreach ($d in $batLai) {
        $s = Get-Service $d -ErrorAction SilentlyContinue
        if ($s) {
            Noi "bat $d"
            Start-Service $d
            Start-Sleep -Seconds 6
        }
    }
}

# ---------------------------------------------------------------- hoan nguyen
if ($HoanNguyen) {
    $saoLuu = Get-ChildItem (Split-Path $binDir) -Directory `
        | Where-Object { $_.Name -like "llamacpp.b*" } `
        | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $saoLuu) { throw "Khong tim thay ban sao luu llamacpp.b* nao." }
    Write-Output "HOAN NGUYEN ve $($saoLuu.Name)"
    DungDichVu
    Copy-Item (Join-Path $saoLuu.FullName "*") $binDir -Recurse -Force
    BatDichVu
    Noi "phien ban hien tai: $(PhienBanHienTai)"
    exit 0
}

# ------------------------------------------------------------------ tim ban
$cu = PhienBanHienTai
Write-Output "Phien ban dang chay: $cu"

# ------------------------------------------------------------------ chon ban
#
# ! MAC DINH LA BAN DUOC GHIM, KHONG PHAI BAN MOI NHAT.
#
#   Ban dau cua script nay khong truyen -Ban thi di hoi GitHub va lay release
#   dau tien co goi win-cuda-$Cuda. Tuc lenh NGAN NHAT, thu ma nguoi met moi luc
#   1 gio sang se go, lai la lenh keo mot binary CHUA AI DO vao mot may dang
#   phuc vu that. "Moi hon" khong dong nghia "tot hon": bo nho du an ghi mot ca
#   cuBLAS INVALID_VALUE la dac thu cu130, va bai hoc o do la HA CUDA chu dung
#   nang driver.
#
#   Gio: khong -Ban  => dung ban ghim trong phien_ban_ghim.json
#        -Ban latest => phai GO RA, va no van chi tai ve chu khong tu quyet.
#
if (-not $Ban) {
    $tepGhim = Join-Path $PSScriptRoot "phien_ban_ghim.json"
    if (-not (Test-Path $tepGhim)) { throw "Khong thay $tepGhim - khong biet ban nao duoc chuc phuc." }
    $ghim = Get-Content $tepGhim -Raw | ConvertFrom-Json
    $Ban  = $ghim.llama_cpp.build
    if (-not $Ban) {
        Write-Output ""
        Write-Output "DUNG LAI: phien_ban_ghim.json chua ghi build llama.cpp (dang null)."
        Write-Output ""
        Write-Output "  Khong ai biet may nay DANG chay build nao, nen khong the noi"
        Write-Output "  nang len la nang TU dau. Chay truoc:"
        Write-Output ""
        Write-Output "      python llm_gateway\deploy\nghiem_thu.py"
        Write-Output ""
        Write-Output "  No doc /health -> thuong_nguon.phien_ban.engine.build_info va in"
        Write-Output "  ra so that. Ghi so do vao phien_ban_ghim.json roi chay lai."
        Write-Output ""
        Write-Output "  Hoac go thang:  .\nang_llamacpp.ps1 -Ban b10689"
        Write-Output "  Hoac lay moi nhat co y thuc:  .\nang_llamacpp.ps1 -Ban latest"
        exit 2
    }
    Noi "dung ban GHIM tu phien_ban_ghim.json: $Ban"
}

if ($Ban -eq "latest") {
    Noi "hoi GitHub ban b#### moi nhat co goi win-cuda-$Cuda ..."
    $Ban = ""
    $rs = Invoke-RestMethod -Uri "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=15" `
                            -UseBasicParsing -TimeoutSec 60
    foreach ($r in $rs) {
        $co = $r.assets | Where-Object { $_.name -like "llama-*-bin-win-cuda-$Cuda-x64.zip" }
        if ($co) { $Ban = $r.tag_name; break }
    }
    if (-not $Ban) { throw "Khong thay ban nao co goi win-cuda-$Cuda-x64." }
    Canh "dang lay ban MOI NHAT ($Ban) - no CHUA duoc do tren may nay."
    Canh "Sau khi nang: cap nhat phien_ban_ghim.json, va do lai hieu nang truoc khi tin."
}
Noi "ban dich: $Ban"

if ($Ban -eq $cu) {
    Write-Output "Da o $Ban roi, khong co gi de lam."
    exit 0
}

# ------------------------------------------------------------------ tai ve
$url = "https://github.com/ggml-org/llama.cpp/releases/download/$Ban/llama-$Ban-bin-win-cuda-$Cuda-x64.zip"
$zip = Join-Path $tamDir "llama-$Ban-cuda$($Cuda -replace '\.','').zip"
$giaiNen = Join-Path $tamDir $Ban

if (-not (Test-Path $tamDir)) { New-Item -ItemType Directory $tamDir | Out-Null }
if (-not (Test-Path $zip)) {
    Noi "tai $url"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing -TimeoutSec 900
    Noi ("tai xong {0} MB sau {1}s" -f [int]((Get-Item $zip).Length/1MB), [int]$sw.Elapsed.TotalSeconds)
} else {
    Noi "da co goi tai san: $zip"
}

if (Test-Path $giaiNen) { Remove-Item $giaiNen -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $giaiNen -Force
$srvMoi = Get-ChildItem $giaiNen -Recurse -Filter "llama-server.exe" | Select-Object -First 1
if (-not $srvMoi) { throw "Goi khong chua llama-server.exe." }

# Bay 3: kiem ban moi CHAY DUOC truoc khi dung dich vu dang phuc vu.
$thu = & $srvMoi.FullName --version 2>&1 | Out-String
if ($thu -notmatch "build (\d+)") { throw "Ban moi khong chay duoc:`n$thu" }
Noi "ban moi chay duoc: b$($Matches[1])"

# ------------------------------------------------------------------ sao luu
$saoLuuDir = Join-Path (Split-Path $binDir) "llamacpp.$cu"
if (-not (Test-Path $saoLuuDir)) {
    Noi "sao luu $cu -> $saoLuuDir"
    Copy-Item $binDir $saoLuuDir -Recurse -Force
} else {
    Noi "ban sao luu $cu da co"
}

# ------------------------------------------------------------------ thay the
DungDichVu
# Bay 1: CHEP DE, giu lai cudart va moi tep goi moi khong co.
Noi "chep de binary moi"
Copy-Item (Join-Path $srvMoi.DirectoryName "*") $binDir -Recurse -Force
BatDichVu

$moi = PhienBanHienTai
Write-Output ""
Write-Output "XONG: $cu -> $moi"
Write-Output "Hoan nguyen bat cu luc nao:  .\nang_llamacpp.ps1 -HoanNguyen"
Write-Output ""
Write-Output "CON PHAI KIEM (script khong tu lam thay):"
Write-Output "  1. /health cua cong: thuong_nguon.ma = 200"
Write-Output "  2. mot luot sinh that (model nap duoc, khong chi la service Running)"
Write-Output "  3. mot luot CO TOOL CALL - day la duong tung vo o parser peg-native"
