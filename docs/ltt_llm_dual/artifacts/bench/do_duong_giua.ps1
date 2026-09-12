# do_duong_giua.ps1 - co duong nao vua giu chat luong vua giu toc do khong?
#
# TINH THE: bo co L-15 dua bo de tu 27/36 len 36/36, nhung do xen ke 5 khoi cho
# thay no lay di 11% toc do cua LTT-3.8 (63,60 -> 56,61 tok/s) va day model
# xuong DUOI nguong cong nghiem thu B (60,0). Hai dai khong chong nhau nen day
# la hieu ung that, khong phai nhieu.
#
# NHUNG L-15 co HAI nua, va chung khong giong nhau:
#   (a) tham so lay mau Qwen - trong do `presence-penalty 1.5` la mot phanh
#       chay moi buoc giai ma, tuc ton thoi gian that
#   (b) `--reasoning-budget 512` - chi cat khoi nghi, khong dung vao vong giai ma
#
# Phep do tach co (01/09) tren 3.5 goi y (a) ton ~6% con (b) KHONG ton gi. Neu
# dung, va neu (b) MOT MINH da du dua chat luong len 36/36, thi khong co cuoc
# doi chac nao ca - chi la toi da gop hai thu vao mot goi ma khong kiem tung cai.
#
# Bai do tra loi DUNG hai cau:
#   1. `--reasoning-budget 512` MOT MINH co giu duoc 36/36 khong?  (model 3.5)
#   2. No co giu LTT-3.8 tren 60,0 tok/s khong?                    (model 3.8)
#
# Cau 1 phai do bang CA BO de chu khong chi hai bai tieng Viet: mot ban va chi
# sua duoc cho hong ma lam tut cho khac thi khong phai ban va.

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid38 = 'GPU-26623278-4fa5-82db-4306-237651b03e78'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Bench  = 'E:\AI\ltt_dual\bench\bench.py'
$Cham   = 'E:\AI\ltt_dual\bench\danh_gia_llm.py'
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\duong_giua.log"
$M      = 'H:\LTT_LLM\models'

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

function DonDep {
    Get-Process llama-server -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 5
}

function Cho([int]$cong, $p) {
    for ($i = 0; $i -lt 600; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { return $false }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$cong/health" -TimeoutSec 3).status -eq 'ok') { return $true } } catch { }
    }
    return $false
}

Remove-Item -Path $Log, "$Thu\dg38_budget.jsonl" -Force -ErrorAction SilentlyContinue
Ghi "=== DUONG GIUA: chi --reasoning-budget 512 ==="

# ---- Cau 1: chat luong cua 3.5 voi CHI budget --------------------------------
DonDep
$a35 = @('-m', "$M\Qwen3.5-9B-Q6_K-unsloth.gguf", '--mmproj', "$M\mmproj-9B-F16-unsloth.gguf",
         '--jinja', '--reasoning-format', 'deepseek',
         '-fa', '1', '-ngl', '999', '--metrics',
         '-c', '262144', '-np', '3', '-kvu',
         '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
         '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
         '--reasoning-budget', '512',
         '--host', '127.0.0.1', '--port', '8291')
$env:CUDA_VISIBLE_DEVICES = $Uuid35
$p = Start-Process -FilePath $Bin -ArgumentList $a35 -PassThru -NoNewWindow `
        -RedirectStandardOutput "$Thu\dg35.out.log" -RedirectStandardError "$Thu\dg35.err.log"
if (Cho 8291 $p) {
    Ghi "XANH 3.5 (chi budget) - cham ca bo de"
    & $Python $Cham --thu-thap --url "http://127.0.0.1:8291" --model x --lan 5 `
        --ra "$Thu\dg35_thuthap5.json" 2>&1 | ForEach-Object { Ghi "  $_" }
    Stop-Process -Id $p.Id -Force
} else { Ghi "TRUOT 3.5" }

# (Pha 3.8 da chay xong o luot truoc: trung vi 65,18 tok/s - bo di de do lai
#  nhanh pha chat luong voi n lon hon.)

DonDep
Ghi "=== KET THUC DUONG GIUA 5 ==="
