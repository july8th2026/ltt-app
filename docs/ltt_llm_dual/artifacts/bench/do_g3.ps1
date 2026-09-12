# do_g3.ps1 - cong G3 (Task 3.2): LTT-3.5 tren RTX 5060 Ti (16.311 MiB).
#
# Hai cau hoi, va chung khac nhau:
#   1. Ngu canh 262.144 co vua card 16 GB khong, va con chua duoc >= ~2 GiB
#      khong (5060 Ti CON GANH desktop + app nen sau khi don 3090 - L-12).
#   2. Trong HAI ung vien Q6_K da tai (Task 3.1), cai nao?
#        unsloth/Qwen3.5-9B-MTP-GGUF   7.684.551.008 B
#        lmstudio-community            7.359.259.040 B
#      Lech 325 MB. KHONG chon truoc bang suy luan - do roi cham chat luong.
#
# Khac G1 o ba cho, va ba cho deu co ly do:
#   * GPU khac (UUID 5060 Ti), model khac, mmproj khac.
#   * KV **q8_0** chu khong q4_0: card 16 GB nhung model chi 9B nen con cho cho
#     KV rong rai hon; spec muc 2 chot q8_0 cho 3.5.
#   * KHONG `--spec-type draft-mtp`: spec ghi 3.5 chay khong MTP.
#
# "Vua" van la ba dieu kien nhu G1: /health xanh, khong tran (Shared quanh san
# cua chinh `-ub` dang dung), va con bien. Nguong bien o day la **2.048 MiB**
# chu khong 300 nhu G1: card nay con phai nuoi desktop.

param(
    [int]$Ctx = 262144
)

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Uuid35 = 'GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df'
$Tong35 = 16311
$Port   = 8291
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\g3.log"
$Ket    = "$Thu\g3.jsonl"

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

function Vram35 {
    foreach ($dong in (& nvidia-smi --query-gpu=uuid,memory.used --format=csv,noheader,nounits)) {
        $c = $dong -split ',\s*'
        if ($c[0] -eq $Uuid35) { return [int]$c[1] }
    }
    return -1
}

function DemGpu([int]$pid_, [string]$ten) {
    try {
        $m = Get-Counter "\GPU Process Memory(pid_$pid_*)\$ten" -ErrorAction Stop
        return [math]::Round((($m.CounterSamples | Measure-Object -Property CookedValue -Sum).Sum) / 1MB, 1)
    } catch { return -1 }
}

function DonDep {
    Get-Process llama-server -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Bin } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 4
}

$M = 'H:\LTT_LLM\models'
$DsCauHinh = @(
    @{ ten = 'unsloth';  gguf = "$M\Qwen3.5-9B-Q6_K-unsloth.gguf";  mm = "$M\mmproj-9B-F16-unsloth.gguf";   np = 4 }
    @{ ten = 'unsloth';  gguf = "$M\Qwen3.5-9B-Q6_K-unsloth.gguf";  mm = "$M\mmproj-9B-F16-unsloth.gguf";   np = 3 }
    @{ ten = 'lmstudio'; gguf = "$M\Qwen3.5-9B-Q6_K-lmstudio.gguf"; mm = "$M\mmproj-9B-BF16-lmstudio.gguf"; np = 4 }
    @{ ten = 'lmstudio'; gguf = "$M\Qwen3.5-9B-Q6_K-lmstudio.gguf"; mm = "$M\mmproj-9B-BF16-lmstudio.gguf"; np = 3 }
)

New-Item -ItemType Directory -Force -Path $Thu | Out-Null
Remove-Item -Path $Log, $Ket -Force -ErrorAction SilentlyContinue
Ghi "=== G3 === ctx=$Ctx, $($DsCauHinh.Count) cau hinh, card 5060 Ti ($Tong35 MiB)"

foreach ($ch in $DsCauHinh) {
    $nhan = "$($ch.ten)_np$($ch.np)_ctx$Ctx"
    DonDep
    $truoc = Vram35
    Ghi "---- $($nhan) | VRAM truoc = $truoc MiB"

    $a = @('-m', $ch.gguf, '--mmproj', $ch.mm,
           '--jinja', '--reasoning-format', 'deepseek',
           '-fa', '1', '-ngl', '999', '--metrics',
           '-c', "$Ctx", '-np', "$($ch.np)", '-kvu',
           '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0',
           '--host', '127.0.0.1', '--port', "$Port")

    $env:CUDA_VISIBLE_DEVICES = $Uuid35
    $t0 = Get-Date
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\g3_$nhan.out.log" -RedirectStandardError "$Thu\g3_$nhan.err.log"

    $xanh = $false
    for ($i = 0; $i -lt 300; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { break }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
    }
    $giay = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    $r = [ordered]@{ nhan = $nhan; ung_vien = $ch.ten; ctx = $Ctx; np = $ch.np
                     nap_duoc = $xanh; giay_nap = $giay; vram_truoc_mib = $truoc }

    if (-not $xanh) {
        $r.ly_do = 'khong nap duoc'
        $r.duoi_log = (Get-Content "$Thu\g3_$nhan.err.log" -Tail 12 -ErrorAction SilentlyContinue) -join ' | '
        Ghi "TRUOT   $($nhan): khong nap duoc sau $giay s"
    } else {
        $sau = Vram35
        $r.vram_sau_nap_mib = $sau
        $r.shared_usage_mib = DemGpu $p.Id 'Shared Usage'
        $r.dedicated_usage_mib = DemGpu $p.Id 'Dedicated Usage'
        $r.bien_mib = $Tong35 - $sau
        Ghi "NAP     $($nhan): $giay s | VRAM $sau | Shared $($r.shared_usage_mib) | bien $($r.bien_mib)"

        try {
            $body = @{ model = 'x'
                       messages = @(@{ role = 'user'; content = 'Tinh 12 * 17 va giai thich ngan gon.' })
                       max_tokens = 400; stream = $false } | ConvertTo-Json -Depth 5
            $t1 = Get-Date
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/v1/chat/completions" `
                        -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 300
            $m = $resp.choices[0].message
            $r.co_chu = -not ([string]::IsNullOrWhiteSpace("$($m.content)") -and [string]::IsNullOrWhiteSpace("$($m.reasoning_content)"))
            $r.token_ra = $resp.usage.completion_tokens
            $r.giay_luot = [math]::Round(((Get-Date) - $t1).TotalSeconds, 1)
            $r.tok_s = if ($r.giay_luot -gt 0) { [math]::Round($r.token_ra / $r.giay_luot, 2) } else { 0 }
            $r.vram_dinh_mib = Vram35
            Ghi "LUOT    $($nhan): $($r.token_ra) token / $($r.giay_luot) s = $($r.tok_s) tok/s | co_chu=$($r.co_chu)"
        } catch {
            $r.luot_loi = $_.Exception.Message
            Ghi "LUOT    $($nhan) LOI: $($_.Exception.Message)"
        }
        Stop-Process -Id $p.Id -Force
    }
    Add-Content -Path $Ket -Value ($r | ConvertTo-Json -Depth 5 -Compress) -Encoding UTF8
}

DonDep
Ghi "=== KET THUC G3 ==="
