# p01_sieu_du_lieu_may_b.ps1 - P01 buoc 1: ghi sieu du lieu may B. CHI DOC.
#
# THUAN ASCII (quy tac 2 cua CLAUDE.md).
#
# Chay TREN MAY B (DESKTOP-MR9CFK0), PowerShell thuong, KHONG can Administrator:
#
#     powershell -ExecutionPolicy Bypass -File .\p01_sieu_du_lieu_may_b.ps1
#
# Ket qua ghi ra .\p01_sieu_du_lieu.json ben canh script. Gui lai tep do.
#
# == NO LAM GI ==
#   doc phien ban llama-server        -> build SHA / so build
#   bam GGUF va chat_template.jinja   -> danh tinh chinh xac cua model va template
#   doc llama-swap.yaml dang chay     -> doi chieu voi ban trong kho
#   hoi /running cua llama-swap       -> ho so nao dang nap
#   hoi /props cua llama-server       -> chat_template + chat_template_tool_use DANG HOAT DONG
#   loc log llama-server              -> dong "Chat format: ..."  <- CAU HOI M-1
#
# == NO KHONG LAM GI ==
#   khong ghi mot tep nao ngoai tep ket qua
#   khong khoi dong lai dich vu nao
#   khong nap hay go model nao
#   khong goi model (khong ton credit, khong ton GPU)
#
# !! Bam GGUF 15,33 GiB mat vai phut tu dia. Muon bo qua:
#      powershell -ExecutionPolicy Bypass -File .\p01_sieu_du_lieu_may_b.ps1 -BoQuaBamGguf

param(
    [switch]$BoQuaBamGguf,
    [string]$ThuMucLlm  = "H:\LTT_LLM",
    [string]$CongSwap   = "http://127.0.0.1:8080",
    [int]   $CongEngine = 8281
)

$ErrorActionPreference = "Continue"
$ra = [ordered]@{}
$ra.thoi_diem   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$ra.may         = $env:COMPUTERNAME
$ra.ghi_chu     = "P01 buoc 1 - sieu du lieu may B. Chi doc."

function Ghi-Loi($khoi, $e) { $khoi.loi = "$e"; return $khoi }

# --- 1. Phien ban llama.cpp -------------------------------------------------
$b = [ordered]@{}
try {
    $exe = Join-Path $ThuMucLlm "bin\llamacpp\llama-server.exe"
    $b.duong_dan = $exe
    if (Test-Path $exe) {
        $b.co_mat    = $true
        $b.kich_thuoc = (Get-Item $exe).Length
        $b.sua_luc   = (Get-Item $exe).LastWriteTimeUtc.ToString("yyyy-MM-ddTHH:mm:ssZ")
        # `--version` in ra stderr; gop hai luong lai
        $b.version   = (& $exe --version 2>&1 | Out-String).Trim()
    } else { $b.co_mat = $false }
} catch { $b = Ghi-Loi $b $_ }
$ra.llama_cpp = $b

# --- 2. Bam GGUF + template -------------------------------------------------
$t = [ordered]@{}
foreach ($muc in @(
    @{ ten = "gguf";     duong = (Join-Path $ThuMucLlm "models\Qwen3.8-27B-UD-Q4_K_M.gguf"); nang = $true  },
    @{ ten = "mmproj";   duong = (Join-Path $ThuMucLlm "models\mmproj-F16.gguf");            nang = $true  },
    @{ ten = "template"; duong = (Join-Path $ThuMucLlm "models\chat_template.jinja");        nang = $false }
)) {
    $m = [ordered]@{ duong_dan = $muc.duong }
    try {
        if (Test-Path $muc.duong) {
            $f = Get-Item $muc.duong
            $m.co_mat     = $true
            $m.kich_thuoc = $f.Length
            $m.sua_luc    = $f.LastWriteTimeUtc.ToString("yyyy-MM-ddTHH:mm:ssZ")
            if ($muc.nang -and $BoQuaBamGguf) {
                $m.sha256 = "(bo qua theo -BoQuaBamGguf)"
            } else {
                $m.sha256 = (Get-FileHash -Path $muc.duong -Algorithm SHA256).Hash
            }
            # Template la van ban va no la BANG CHUNG - lay nguyen van.
            if ($muc.ten -eq "template") {
                $m.noi_dung = Get-Content -Path $muc.duong -Raw -Encoding UTF8
                $m.so_dong  = (Get-Content -Path $muc.duong).Count
            }
        } else { $m.co_mat = $false }
    } catch { $m = Ghi-Loi $m $_ }
    $t[$muc.ten] = $m
}
$ra.tep_model = $t

# --- 3. llama-swap.yaml DANG CHAY ------------------------------------------
$y = [ordered]@{}
try {
    $ung = @(
        (Join-Path $ThuMucLlm "llama-swap.yaml"),
        (Join-Path $ThuMucLlm "bin\llama-swap\llama-swap.yaml"),
        "C:\ProgramData\LTTLlamaSwap\llama-swap.yaml"
    ) | Where-Object { Test-Path $_ }
    if ($ung.Count -gt 0) {
        $y.duong_dan = $ung[0]
        $y.sha256    = (Get-FileHash -Path $ung[0] -Algorithm SHA256).Hash
        $y.sua_luc   = (Get-Item $ung[0]).LastWriteTimeUtc.ToString("yyyy-MM-ddTHH:mm:ssZ")
        # >> Nguyen van, de doi chieu TUNG CO voi ban trong kho.
        $y.noi_dung  = Get-Content -Path $ung[0] -Raw -Encoding UTF8
    } else {
        $y.tim_thay = $false
        $y.da_thu   = $ung
    }
} catch { $y = Ghi-Loi $y $_ }
$ra.llama_swap_yaml = $y

# --- 4. Tien trinh dang chay + dong lenh THAT ------------------------------
# >> Dong lenh THAT quan trong hon yaml: yaml la y dinh, dong lenh la su that.
$p = [ordered]@{}
try {
    $ds = @()
    Get-CimInstance Win32_Process -Filter "Name='llama-server.exe' OR Name='llama-swap.exe'" |
        ForEach-Object {
            $ds += [ordered]@{
                ten        = $_.Name
                pid        = $_.ProcessId
                dong_lenh  = $_.CommandLine
                bat_dau    = $_.CreationDate
            }
        }
    $p.tien_trinh = $ds
    $p.so_luong   = $ds.Count
} catch { $p = Ghi-Loi $p $_ }
$ra.tien_trinh = $p

# --- 5. llama-swap /running -------------------------------------------------
$r = [ordered]@{}
try {
    $r.dia_chi = "$CongSwap/running"
    $r.tra_ve  = (Invoke-RestMethod -Uri "$CongSwap/running" -TimeoutSec 10 -Method Get)
} catch { $r = Ghi-Loi $r $_ }
$ra.llama_swap_running = $r

# --- 6. /props cua llama-server  <- CAU HOI M-1 -----------------------------
# !! CHI hoi khi da co engine nap san. Neu khong co, DUNG lam no nap - nap mot
#    model 15 GiB chi de doc mot truong la mot viec dat va no doi trang thai may.
$q = [ordered]@{}
try {
    $q.dia_chi = "http://127.0.0.1:$CongEngine/props"
    $co = $false
    try {
        $tcp = New-Object Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $CongEngine); $co = $true; $tcp.Close()
    } catch { $co = $false }
    $q.cong_mo = $co
    if ($co) {
        $props = Invoke-RestMethod -Uri "http://127.0.0.1:$CongEngine/props" -TimeoutSec 20 -Method Get
        $q.tra_ve = $props
    } else {
        $q.ghi_chu = "Cong dong - khong co engine nao dang nap. KHONG tu nap de hoi."
    }
} catch { $q = Ghi-Loi $q $_ }
$ra.props_engine = $q

# --- 7. Log: dong "Chat format:"  <- DAY LA CAU TRA LOI CHO M-1 -------------
$l = [ordered]@{}
try {
    $thu = @(
        (Join-Path $ThuMucLlm "logs"),
        "C:\ProgramData\LTTLlamaSwap\logs",
        (Join-Path $ThuMucLlm "bin\llama-swap\logs")
    ) | Where-Object { Test-Path $_ }
    $l.thu_muc_log = $thu
    $dong = @()
    foreach ($d in $thu) {
        Get-ChildItem -Path $d -Filter *.log -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 5 |
            ForEach-Object {
                $tep = $_.FullName
                Select-String -Path $tep -Pattern "Chat format|chat template|tool.?call|jinja" `
                              -ErrorAction SilentlyContinue |
                    Select-Object -Last 40 |
                    ForEach-Object { $dong += "[$($_.Filename):$($_.LineNumber)] $($_.Line.Trim())" }
            }
    }
    $l.dong_khop = $dong
    $l.so_dong   = $dong.Count
    if ($dong.Count -eq 0) {
        $l.ghi_chu = "Khong tim thay dong nao. Co the log da xoay vong, hoac thu muc log khac - sua -ThuMucLlm."
    }
} catch { $l = Ghi-Loi $l $_ }
$ra.log_chat_format = $l

# --- 8. GPU ------------------------------------------------------------------
$g = [ordered]@{}
try {
    $g.nvidia_smi = (& nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version `
                                  --format=csv,noheader 2>&1 | Out-String).Trim()
} catch { $g = Ghi-Loi $g $_ }
$ra.gpu = $g

# --- Ghi ket qua -------------------------------------------------------------
# !! KHONG BOM (quy tac 1 cua CLAUDE.md). Out-File/Set-Content cua PS 5.1 chen BOM.
$dich = Join-Path $PSScriptRoot "p01_sieu_du_lieu.json"
$json = $ra | ConvertTo-Json -Depth 12
[IO.File]::WriteAllText($dich, $json, (New-Object Text.UTF8Encoding($false)))

Write-Host ""
Write-Host "Xong. Ket qua: $dich"
Write-Host ""
Write-Host "Tom tat nhanh:"
Write-Host ("  llama-server co mat : {0}" -f $ra.llama_cpp.co_mat)
Write-Host ("  tien trinh dang chay: {0}" -f $ra.tien_trinh.so_luong)
Write-Host ("  cong engine {0} mo  : {1}" -f $CongEngine, $ra.props_engine.cong_mo)
Write-Host ("  dong log khop       : {0}" -f $ra.log_chat_format.so_dong)
Write-Host ""
Write-Host "Gui lai tep JSON tren."
