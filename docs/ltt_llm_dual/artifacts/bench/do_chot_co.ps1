# do_chot_co.ps1 - chot bo co cho llama-swap.yaml. Ba ung vien, cham CA BO de.
#
# TINH THE sau bon lo do:
#
#   khong co gi          65 tok/s   bo de 27/36   tieng Viet   0%
#   chi budget 512       65 tok/s   bo de 58/60   tieng Viet  80%   <- 2/10 SAI
#   budget + tham so     57 tok/s   bo de 36/36   tieng Viet 100%   <- TRUOT cong B
#
# Va kieu hong cua "chi budget" TE HON kieu hong cu: khong phai tra loi RONG
# (de phat hien) ma tra loi SAI, kem ca khoi nghi ro ra `content`:
#
#   'Doc lap\n</think>\n\n2/9'        <- the </think> nam trong content, dap an sai
#   '**2 thang 10**'                  <- sai han
#   '1. **Analyze the Request:**...'  <- transcript suy nghi ro ra content
#
# Mot cau tra loi sai nhin nhu that thi khach khong phat hien duoc, con mot cau
# rong thi phat hien duoc ngay. Nen 80% o day XAU HON con so 80% goi y.
#
# HAI DUONG CHUA THU, va ca hai deu co ly do de tin:
#
#   B  tham so lay mau BO `presence-penalty` (giu temp/top-p/top-k/min-p).
#      Gia thuyet: 11% mat toc do gan nhu toan bo den tu presence-penalty - no
#      la phanh chay MOI BUOC giai ma, con ba cai kia gan nhu mien phi. Neu
#      chung moi la thu giup model "hoi phuc" sau khi bi ep dong </think> thi
#      ta duoc ca hai.
#
#   C  budget 1024 thay vi 512. Cac luot SACH dung ~516-523 token, tuc phanh
#      nhay dung o mep. Noi long ra thi model thuong tu dong </think> truoc khi
#      phanh cham toi - ma tu dong thi khong co gi de ro ra.

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Python = 'C:\Python313\python.exe'
$Cham   = 'E:\AI\ltt_dual\bench\danh_gia_llm.py'
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\chot_co.log"
$M      = 'H:\LTT_LLM\models'

$DsBai = @(
    @{ n = 'A_budget512_thamso_du'
       them = @('--reasoning-budget', '512', '--temp', '0.6', '--top-p', '0.95',
                '--top-k', '20', '--min-p', '0', '--presence-penalty', '1.5') }
    @{ n = 'B_budget512_khong_penalty'
       them = @('--reasoning-budget', '512', '--temp', '0.6', '--top-p', '0.95',
                '--top-k', '20', '--min-p', '0') }
    @{ n = 'C_budget1024'
       them = @('--reasoning-budget', '1024') }
)

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

Remove-Item -Path $Log -Force -ErrorAction SilentlyContinue
Ghi "=== CHOT BO CO === 3 ung vien, cham ca bo de, lan 5"

foreach ($b in $DsBai) {
    Get-Process llama-server -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 5

    $a = @('-m', "$M\Qwen3.5-9B-Q6_K-unsloth.gguf", '--mmproj', "$M\mmproj-9B-F16-unsloth.gguf",
           '--jinja', '--reasoning-format', 'deepseek',
           '-fa', '1', '-ngl', '999', '--metrics',
           '-c', '262144', '-np', '3', '-kvu',
           '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
           '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2',
           '--host', '127.0.0.1', '--port', '8291') + $b.them

    $env:CUDA_VISIBLE_DEVICES = $Uuid35
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\cc_$($b.n).out.log" `
            -RedirectStandardError  "$Thu\cc_$($b.n).err.log"
    $xanh = $false
    for ($i = 0; $i -lt 300; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { break }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:8291/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
    }
    if (-not $xanh) { Ghi "TRUOT $($b.n)"; continue }
    Ghi "---- $($b.n)"
    & $Python $Cham --thu-thap --url "http://127.0.0.1:8291" --model x --lan 5 `
        --ra "$Thu\cc_$($b.n).json" 2>&1 | ForEach-Object { Ghi "  $_" }
    Stop-Process -Id $p.Id -Force
}

Get-Process llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
Ghi "=== KET THUC CHOT CO ==="
