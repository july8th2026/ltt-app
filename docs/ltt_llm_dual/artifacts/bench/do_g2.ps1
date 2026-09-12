# do_g2.ps1 - cong G2 (Task 3.2): draft-mtp co an toan voi nhieu slot khong.
#
# Chay llama-server o DUNG cau hinh da chot (L-14): -c 221184 -np 3, mmproj tren
# GPU, -ub mac dinh. Roi ban bench.py --kich-ban mtp_gate vao cong thu 8290.
#
# Vi sao phai co cong nay: hai bao cao cong dong tren dung dong build ho nha nay
# noi draft-mtp lan slot khi -np > 1 (#27572 tra loi RONG, #26750 Blackwell
# -32%). Ca hai hong theo TUNG LUOT chu khong theo toc do trung binh, nen khong
# mot phep do thong luong nao thay duoc chung.
#
# Cong nay KHONG do toc do. No hoi ba cau dung/sai:
#   * co luot nao tra ve rong khong (ke ca reasoning_content)?
#   * co luot nao doc ra dau cua luot KHAC khong (dau hieu lan slot)?
#   * tong spec_decode_num_accepted... co TANG khong (draft-mtp that su lam viec)?

param(
    [int]$LanGate = 200,
    [int]$Ctx     = 221184,
    [int]$Np      = 3
)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Gguf   = 'H:\LTT_LLM\models\Qwen3.8-27B-UD-Q4_K_M.gguf'
$Mmproj = 'H:\LTT_LLM\models\mmproj-F16.gguf'
$Tmpl   = 'H:/LTT_LLM/models/chat_template.jinja'
$Uuid38 = 'GPU-26623278-4fa5-82db-4306-237651b03e78'
$Python = 'C:\Python313\python.exe'
$Bench  = 'E:\AI\ltt_dual\bench\bench.py'
$Port   = 8290
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\g2.log"
$Ra     = "$Thu\g2.jsonl"

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

New-Item -ItemType Directory -Force -Path $Thu | Out-Null
Remove-Item -Path $Log, $Ra -Force -ErrorAction SilentlyContinue
Ghi "=== G2 === ctx=$Ctx np=$Np luot=$LanGate"

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 4

$a = @('-m', $Gguf, '--mmproj', $Mmproj,
       '--jinja', '--chat-template-file', $Tmpl,
       '--reasoning-format', 'deepseek',
       '-fa', '1', '-ngl', '999',
       '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2', '--metrics',
       '-c', "$Ctx", '-np', "$Np", '-kvu',
       '--cache-type-k', 'q4_0', '--cache-type-v', 'q4_0',
       '--host', '127.0.0.1', '--port', "$Port")

$env:CUDA_VISIBLE_DEVICES = $Uuid38
$p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
        -RedirectStandardOutput "$Thu\g2.server.log" -RedirectStandardError "$Thu\g2.server.err.log"
Ghi "PID     $($p.Id)"

$xanh = $false
for ($i = 0; $i -lt 300; $i++) {
    Start-Sleep -Seconds 1
    if ($p.HasExited) { break }
    try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
}
if (-not $xanh) {
    Ghi "TRUOT   khong nap duoc"
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    Ghi "=== KET THUC G2 ==="
    exit 1
}
Ghi "XANH    nap xong sau $i s"

# `--gate-anh`: mot phan nam luot deo them anh. Ho so nay CO mmproj nen deo duoc,
# va bao cao cong dong noi duong anh la mot trong hai duong de kich hoat loi nhat.
# `--luong $Np`: so luong dong thoi PHAI bang so slot cua server. Lan chay
# dau (12/09 00:11) de mac dinh 4 trong khi server co 3 slot, nen mot phan luot
# nam trong hang doi cua llama.cpp chu khong o trong slot -- van hop le nhung
# ban ghi ghi "so_luong 4" khong dung voi thu da chay.
& $Python $Bench --cong $Port --model x --kich-ban mtp_gate `
    --lan-gate $LanGate --luong $Np --gate-anh --ra $Ra 2>&1 |
    ForEach-Object { Ghi "bench: $_" }
Ghi "bench thoat ma $LASTEXITCODE"

Stop-Process -Id $p.Id -Force
Ghi "=== KET THUC G2 ==="
