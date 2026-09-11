# do_toc_do_35.ps1 - MOC TOC DO CHINH THUC cua LTT-3.5 tren RTX 5060 Ti.
#
# Vi sao can rieng mot lan chay: con so 50,6-53,3 tok/s trong g3.jsonl la tham
# do MOT luot 400 token voi prompt vai chuc chu. No du de noi "model tra loi
# duoc", KHONG du de lam moc:
#   * mot luot thi khong co trung vi, ma nhieu lay mau o day rat that thuong
#     (bo do khong truyen temperature - xem danh_gia_llm.py);
#   * prompt vai chuc chu gan nhu khong co prefill, nen con so gan nhu thuan
#     decode, khong giong mot luot khach that;
#   * chua do C3 (ba luot dong thoi), ma do moi la thu quyet dinh suc chua.
#
# Moc cua LTT-3.8 (66,70 tok/s) do bang bench.py kich ban c1, prompt ~1.150 tu,
# lay TRUNG VI nhieu luot. Lan nay lam DUNG NHU THE cho 3.5 de hai con so so
# sanh duoc voi nhau.

param(
    [string]$UngVien = 'lmstudio',
    [int]$Lan = 5,
    [int]$Ctx = 262144,
    [int]$Np  = 3
)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Bench  = 'E:\AI\ltt_dual\bench\bench.py'
$Port   = 8291
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\toc_do_35.log"

$M = 'H:\LTT_LLM\models'
if ($UngVien -eq 'unsloth') {
    $Gguf = "$M\Qwen3.5-9B-Q6_K-unsloth.gguf";  $Mm = "$M\mmproj-9B-F16-unsloth.gguf"
} else {
    $Gguf = "$M\Qwen3.5-9B-Q6_K-lmstudio.gguf"; $Mm = "$M\mmproj-9B-BF16-lmstudio.gguf"
}

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 4

Remove-Item -Path $Log -Force -ErrorAction SilentlyContinue
Ghi "=== TOC DO 3.5 === ung vien=$UngVien ctx=$Ctx np=$Np lan=$Lan"

$a = @('-m', $Gguf, '--mmproj', $Mm,
       '--jinja', '--reasoning-format', 'deepseek',
       '-fa', '1', '-ngl', '999', '--metrics',
       '-c', "$Ctx", '-np', "$Np", '-kvu',
       '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
       '--host', '127.0.0.1', '--port', "$Port")

$env:CUDA_VISIBLE_DEVICES = $Uuid35
$p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
        -RedirectStandardOutput "$Thu\toc_do_35.out.log" -RedirectStandardError "$Thu\toc_do_35.err.log"

$xanh = $false
for ($i = 0; $i -lt 300; $i++) {
    Start-Sleep -Seconds 1
    if ($p.HasExited) { break }
    try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
}
if (-not $xanh) {
    Ghi "TRUOT   khong nap duoc"
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    Ghi "=== KET THUC ==="
    exit 1
}
Ghi "XANH    nap sau $i s"

# C1: mot luot, lap $Lan lan de co trung vi. `--uuid` tro card 5060 Ti, neu
# khong bench.py se do VRAM cua 3090 va ghi mot con so cua card khac.
Ghi "---- C1 ($Lan luot) ----"
& $Python $Bench --cong $Port --model x --uuid $Uuid35 --kich-ban c1 `
    --lan $Lan --ra "$Thu\toc_do_35_c1.jsonl" 2>&1 | ForEach-Object { Ghi "c1: $_" }

# C3: ba luot dong thoi (bang $Np). Day moi la con so suc chua.
Ghi "---- C3 ($Np luong, 3 lan) ----"
& $Python $Bench --cong $Port --model x --uuid $Uuid35 --kich-ban c4 `
    --luong $Np --lan 3 --ra "$Thu\toc_do_35_c3.jsonl" 2>&1 | ForEach-Object { Ghi "c3: $_" }

Stop-Process -Id $p.Id -Force
Ghi "=== KET THUC ==="
