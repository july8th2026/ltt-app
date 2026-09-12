# do_viet_rong.ps1 - chay probe_viet_rong.py tren LTT-3.5 (ung vien unsloth).
#
# Ho so giong het lan cham chat luong da sinh ra 6/6 luot rong, de con so o day
# giai thich duoc ban ghi kia chu khong phai mot phep do cua mot thu khac:
# -c 262144 -np 3, KV q8_0, mmproj GPU, KHONG MTP, khuon chat DUNG SAN trong
# GGUF (chinh diem H2 nghi ngo).

param(
    [string]$UngVien = 'unsloth',
    [int]$Lan = 2
)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Probe  = 'E:\AI\ltt_dual\bench\probe_viet_rong.py'
$Port   = 8291
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\viet_rong.log"
$M      = 'H:\LTT_LLM\models'

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

Remove-Item -Path $Log, "$Thu\viet_rong.jsonl" -Force -ErrorAction SilentlyContinue
Ghi "=== VIET RONG === $UngVien lan=$Lan"

$a = @('-m', $Gguf, '--mmproj', $Mm,
       '--jinja', '--reasoning-format', 'deepseek',
       '-fa', '1', '-ngl', '999', '--metrics',
       '-c', '262144', '-np', '3', '-kvu',
       '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
       '--host', '127.0.0.1', '--port', "$Port")

$env:CUDA_VISIBLE_DEVICES = $Uuid35
$p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
        -RedirectStandardOutput "$Thu\viet_rong.out.log" -RedirectStandardError "$Thu\viet_rong.err.log"

$xanh = $false
for ($i = 0; $i -lt 300; $i++) {
    Start-Sleep -Seconds 1
    if ($p.HasExited) { break }
    try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
}
if (-not $xanh) {
    Ghi "TRUOT   khong nap duoc"
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    Ghi "=== KET THUC VIET RONG ==="
    exit 1
}
Ghi "XANH    nap sau $i s"

& $Python $Probe --cong $Port --lan $Lan --ra "$Thu\viet_rong.jsonl" 2>&1 |
    ForEach-Object { Ghi "probe: $_" }
Ghi "probe thoat ma $LASTEXITCODE"

Stop-Process -Id $p.Id -Force
Ghi "=== KET THUC VIET RONG ==="
