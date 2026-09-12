# do_viet_sua.ps1 - thu bon cach khac phuc "nghi mai khong dut" cua LTT-3.5.
#
# Bon cau hinh SERVER (hai cai giua can co server rieng vi chung la co cua
# server, khong gui duoc theo tung request):
#
#   A  mac_dinh      khong co gi them                       <- doi chung am
#   B  mac_dinh      (cung server A) + tham so lay mau Qwen
#   C  budget512     --reasoning-budget 512
#   D  khong_nghi    --chat-template-kwargs enable_thinking=false
#
# Moi cau hinh chay 3 de x 3 luot: hai de tieng Viet DA HONG, va mot de tieng
# Anh DA XANH lam doi chung duong.

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Probe  = 'E:\AI\ltt_dual\bench\probe_viet_sua.py'
$Port   = 8291
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\viet_sua.log"
$Ra     = "$Thu\viet_sua.jsonl"
$M      = 'H:\LTT_LLM\models'
$Gguf   = "$M\Qwen3.5-9B-Q6_K-unsloth.gguf"
$Mm     = "$M\mmproj-9B-F16-unsloth.gguf"

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

function DonDep {
    Get-Process llama-server -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 4
}

function ChayServer([string[]]$them) {
    $a = @('-m', $Gguf, '--mmproj', $Mm,
           '--jinja', '--reasoning-format', 'deepseek',
           '-fa', '1', '-ngl', '999', '--metrics',
           '-c', '262144', '-np', '3', '-kvu',
           '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
           '--host', '127.0.0.1', '--port', "$Port") + $them
    $env:CUDA_VISIBLE_DEVICES = $Uuid35
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\viet_sua.out.log" `
            -RedirectStandardError  "$Thu\viet_sua.err.log"
    for ($i = 0; $i -lt 300; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { return $null }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { return $p } } catch { }
    }
    return $null
}

Remove-Item -Path $Log, $Ra -Force -ErrorAction SilentlyContinue
Ghi "=== VIET SUA ==="

# --- A + B: cung mot server, hai bo tham so lay mau -------------------------
DonDep
$p = ChayServer @()
if ($null -eq $p) {
    Ghi "TRUOT   server mac dinh khong nap duoc"
} else {
    Ghi "XANH    server mac dinh"
    foreach ($ts in @('mac_dinh', 'qwen')) {
        Ghi "---- A/B: tham so = $ts"
        & $Python $Probe --cong $Port --lan 3 --nhan 'mac_dinh' --tham-so $ts --ra $Ra 2>&1 |
            ForEach-Object { Ghi "  $_" }
    }
    Stop-Process -Id $p.Id -Force
}

# --- C: reasoning-budget ----------------------------------------------------
DonDep
$p = ChayServer @('--reasoning-budget', '512')
if ($null -eq $p) {
    $duoi = (Get-Content "$Thu\viet_sua.err.log" -Tail 6 -ErrorAction SilentlyContinue) -join ' | '
    Ghi "TRUOT   budget512 khong nap duoc | $duoi"
} else {
    Ghi "XANH    budget512"
    & $Python $Probe --cong $Port --lan 3 --nhan 'budget512' --tham-so 'qwen' --ra $Ra 2>&1 |
        ForEach-Object { Ghi "  $_" }
    Stop-Process -Id $p.Id -Force
}

# --- D: tat han che nghi ----------------------------------------------------
DonDep
$p = ChayServer @('--chat-template-kwargs', '{"enable_thinking":false}')
if ($null -eq $p) {
    $duoi = (Get-Content "$Thu\viet_sua.err.log" -Tail 6 -ErrorAction SilentlyContinue) -join ' | '
    Ghi "TRUOT   khong_nghi khong nap duoc | $duoi"
} else {
    Ghi "XANH    khong_nghi"
    & $Python $Probe --cong $Port --lan 3 --nhan 'khong_nghi' --tham-so 'qwen' --ra $Ra 2>&1 |
        ForEach-Object { Ghi "  $_" }
    Stop-Process -Id $p.Id -Force
}

DonDep
Ghi "=== KET THUC VIET SUA ==="
