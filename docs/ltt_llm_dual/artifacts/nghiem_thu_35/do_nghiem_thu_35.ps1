# do_nghiem_thu_35.ps1 - DO TRUOC cong nghiem thu C va E cho LTT-3.5. Thuan ASCII.
#
# VI SAO CHAY DUOC NGAY BAY GIO, va vi sao no khong rui ro:
#   LTT-3.5 nam tren RTX 5060 Ti, va SAN XUAT KHONG DUNG CARD DO. ComfyUI ghim
#   3090; llama-swap song chi co ho so 3.8 (cung 3090). Nen mot llama-server rieng
#   tren 5060 Ti o mot cong khac (8292) khong cham gi dang phuc vu khach.
#
# DO CAI GI (spec ?23):
#   C - C1 LTT-3.5 van ban + anh: tra loi dung, ghi moc
#   E - C3 LTT-3.5 (3 luong): tong tok/s, so voi 2x C1 cua chinh no
#
# !! Day la DO TRUOC, khong phai nghiem thu. Nghiem thu that chay MOT lan sau
#    Spec 2, qua llama-swap voi ho so that. Muc dich o day: biet som neu cau hinh
#    da chot KHONG dat cong, luc con sua duoc re.
#
# Cau hinh = DUNG thu se chay that: L-14 (-c 262144 -np 3) + L-16 (bo co B).

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$M      = 'H:\LTT_LLM\models'
$Python = 'C:\Python313\python.exe'
$Bench  = 'E:\AI\ltt_dual\bench\bench.py'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Port   = 8292
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\nghiem_thu_35.log"
$Ra     = "$Thu\nghiem_thu_35.jsonl"

function Ghi([string]$d) {
    $t = (Get-Date).ToString('HH:mm:ss')
    Write-Output "$t  $d"
    Add-Content -Path $Log -Value "$t  $d" -Encoding ASCII
}

Remove-Item -Path $Log, $Ra -Force -ErrorAction SilentlyContinue
Ghi "=== DO TRUOC cong C + E cho LTT-3.5 (5060 Ti, cong $Port) ==="

# Dung ban do cu neu con treo o cong nay.
Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" |
    Where-Object { $_.CommandLine -like "*--port $Port*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

$truoc = (nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $Uuid35)
Ghi "VRAM 5060 Ti truoc khi nap: $truoc MiB"

$a = @('-m', "$M\Qwen3.5-9B-Q6_K-unsloth.gguf",
       '--mmproj', "$M\mmproj-9B-F16-unsloth.gguf",
       '--jinja', '--reasoning-format', 'deepseek',
       '-fa', '1', '-ngl', '999', '--metrics',
       '-c', '262144', '-np', '3', '-kvu',
       '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
       '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
       '--reasoning-budget', '512', '--temp', '0.6', '--top-p', '0.95',
       '--top-k', '20', '--min-p', '0',
       '--host', '127.0.0.1', '--port', "$Port")

$env:CUDA_VISIBLE_DEVICES = $Uuid35
$p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
        -RedirectStandardOutput "$Thu\nghiem_thu_35.out.log" `
        -RedirectStandardError  "$Thu\nghiem_thu_35.err.log"

$xanh = $false
for ($i = 0; $i -lt 300; $i++) {
    Start-Sleep -Seconds 1
    if ($p.HasExited) { break }
    try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
}
if (-not $xanh) {
    Ghi "TRUOT: khong nap duoc sau $i s"
    Get-Content "$Thu\nghiem_thu_35.err.log" -Tail 8 -ErrorAction SilentlyContinue | ForEach-Object { Ghi "    $_" }
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    exit 1
}
Ghi "XANH sau $i giay"

$sau = (nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $Uuid35)
$tong = (nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits -i $Uuid35)
Ghi "VRAM sau khi nap: $sau / $tong MiB  (bien $([int]$tong - [int]$sau) MiB)"

Ghi "--- C1 (mot luong), 5 lan ---"
& $Python $Bench --cong $Port --model x --uuid $Uuid35 --kich-ban c1 --lan 5 --ra $Ra 2>&1 |
    ForEach-Object { Ghi "  $_" }

Ghi "--- ANH (van ban + anh), 3 lan ---"
& $Python $Bench --cong $Port --model x --uuid $Uuid35 --kich-ban anh --lan 3 --ra $Ra 2>&1 |
    ForEach-Object { Ghi "  $_" }

Ghi "--- C3 (3 luong song song), 3 lan ---"
& $Python $Bench --cong $Port --model x --uuid $Uuid35 --kich-ban c4 --luong 3 --lan 3 --ra $Ra 2>&1 |
    ForEach-Object { Ghi "  $_" }

try {
    $mt = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/metrics" -TimeoutSec 10
    $d = ($mt -split "`n" | Where-Object { $_ -like '*spec_decode*' -and $_ -notlike '#*' }) -join ' | '
    Ghi "metrics spec = $d"
} catch { Ghi "khong doc duoc /metrics" }

Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Ghi "=== XONG. Ket qua tung luot o $Ra ==="
