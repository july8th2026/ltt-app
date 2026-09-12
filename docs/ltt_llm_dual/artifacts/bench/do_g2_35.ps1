# do_g2_35.ps1 - cong G2 cho LTT-3.5. `draft-mtp` co an toan voi 3 slot khong?
#
# VI SAO CAN TEP NAY: cong G2 da chay va DAT - nhung chi cho LTT-3.8. Ta lai
# dinh bat `draft-mtp` cho CA 3.5 (G3b do duoc +38,5% toc do, va do la ly do
# chon tep unsloth). Chay cong cho mot model roi tuyen bo "MTP an toan" la
# tuyen bo cho mot model MA CHUA DO model kia.
#
# Hai bao cao cong dong (#27572 tra loi RONG khi -np > 1, #26750 Blackwell -32%)
# hong theo TUNG LUOT chu khong theo trung binh - va 5060 Ti CHINH LA Blackwell,
# tuc model nay gan bao cao thu hai hon ca 3.8.
#
# Cau hinh dung DUNG thu se chay that: ngu canh + slot cua L-14, bo co cua L-16.
# Do cong tren mot cau hinh khac roi suy rong la mot phep do lech chieu.

param(
    [int]$LanGate = 200
)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$M      = 'H:\LTT_LLM\models'
$Python = 'C:\Python313\python.exe'
$Bench  = 'E:\AI\ltt_dual\bench\bench.py'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Port   = 8291
$Np     = 3
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\g2_35.log"
$Ra     = "$Thu\g2_35.jsonl"

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 5

Remove-Item -Path $Log, $Ra -Force -ErrorAction SilentlyContinue
Ghi "=== G2 cho LTT-3.5 === ctx=262144 np=$Np luot=$LanGate"

$a = @('-m', "$M\Qwen3.5-9B-Q6_K-unsloth.gguf",
       '--mmproj', "$M\mmproj-9B-F16-unsloth.gguf",
       '--jinja', '--reasoning-format', 'deepseek',
       '-fa', '1', '-ngl', '999', '--metrics',
       '-c', '262144', '-np', "$Np", '-kvu',
       '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
       '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
       '--reasoning-budget', '512', '--temp', '0.6', '--top-p', '0.95',
       '--top-k', '20', '--min-p', '0',
       '--host', '127.0.0.1', '--port', "$Port")

$env:CUDA_VISIBLE_DEVICES = $Uuid35
$p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
        -RedirectStandardOutput "$Thu\g2_35.out.log" -RedirectStandardError "$Thu\g2_35.err.log"

$xanh = $false
for ($i = 0; $i -lt 300; $i++) {
    Start-Sleep -Seconds 1
    if ($p.HasExited) { break }
    try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
}
if (-not $xanh) {
    $duoi = (Get-Content "$Thu\g2_35.err.log" -Tail 6 -ErrorAction SilentlyContinue) -join ' | '
    Ghi "TRUOT   khong nap duoc | $duoi"
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    Ghi "=== KET THUC G2 35 ==="
    exit 1
}
Ghi "XANH    nap xong sau $i s"

# `--luong $Np` de so luong dong thoi bang so slot: ban 4 luong vao server 3
# slot thi luot thu tu nam trong hang doi cua llama.cpp chu khong o trong slot,
# tuc do mot thu khac.
# `--gate-anh`: mot phan nam luot deo anh - duong ma bao cao cong dong noi la de
# kich hoat loi nhat.
& $Python $Bench --cong $Port --model x --kich-ban mtp_gate `
    --lan-gate $LanGate --luong $Np --gate-anh --ra $Ra 2>&1 |
    ForEach-Object { Ghi "bench: $_" }
Ghi "bench thoat ma $LASTEXITCODE"

try {
    $mt = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/metrics" -TimeoutSec 10
    $d = ($mt -split "`n" | Where-Object { $_ -like '*spec_decode_num_accepted_tokens_total*' -and $_ -notlike '#*' }) -join ' '
    Ghi "metrics spec = $d"
} catch { Ghi "khong doc duoc /metrics" }

Stop-Process -Id $p.Id -Force
Ghi "=== KET THUC G2 35 ==="
