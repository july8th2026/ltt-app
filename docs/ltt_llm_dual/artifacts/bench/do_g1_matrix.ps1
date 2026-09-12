# do_g1_matrix.ps1 - cong G1 (Task 3.2): tim TRAN NGU CANH LON NHAT ma
# `qwen38-api` cau hinh day du con VUA that su trong 24 GB cua RTX 3090.
#
# "Vua" o day co BA dieu kien, khong phai mot:
#   1. /health xanh                     (llama-server nap xong)
#   2. Shared Usage = 0                 (KHONG co trong so tran sang RAM chu)
#   3. bien VRAM >= 300 MiB             (con cho cho dinh luc chay)
#
# Dieu kien 2 la thu de mat nhat: llama.cpp KHONG bao loi khi tran. /health van
# xanh, /v1/models van dung, noi dung sinh ra van hop le - chi toc do con mot
# phan tu (do 22/08: 63,3 -> 18,2 tok/s). Lan chay G1 dau tien (21:43) roi dung
# vao bay nay: nap "thanh cong" o 262144 nhung Shared Usage = 2.236 MiB.
#
# Moi cau hinh: nap -> do -> mot luot that -> giet. Khong dung toi llama-swap.

$ErrorActionPreference = 'Stop'

$Bin    = 'H:\LTT_LLM\bin\llamacpp\llama-server.exe'
$Gguf   = 'H:\LTT_LLM\models\Qwen3.8-27B-UD-Q4_K_M.gguf'
$Mmproj = 'H:\LTT_LLM\models\mmproj-F16.gguf'
$Tmpl   = 'H:/LTT_LLM/models/chat_template.jinja'
$Uuid38 = 'GPU-26623278-4fa5-82db-4306-237651b03e78'
$Port   = 8290
$Thu    = 'E:\AI\ltt_dual'
$Log    = "$Thu\g1_matrix.log"
$Ket    = "$Thu\g1_matrix.jsonl"

function Ghi([string]$d) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$t  $d" -Encoding UTF8
}

function Vram38 {
    foreach ($dong in (& nvidia-smi --query-gpu=uuid,memory.used --format=csv,noheader,nounits)) {
        $c = $dong -split ',\s*'
        if ($c[0] -eq $Uuid38) { return [int]$c[1] }
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

# ctx, np, co mmproj khong
# !! DOI CHUNG PHAI DI DAU TIEN: dong dau la CHINH XAC cau hinh production
# dang phuc vu khach (204800, --parallel 1, KHONG mmproj), thu da do 03/09 va
# ghi 21.959 MiB, khong he co dau hieu tran. Neu bo dem cua CHINH no cung bao
# "Shared Usage" khac 0 thi con so do KHONG phai thuoc do tran, va nguong
# "Shared = 0" cua cong G1 la mot nguong SAI - phai bo, khong phai sua.
# Khong co dong nay thi moi con so con lai deu khong dien giai duoc.
$DsCauHinh = @(
    @{ ctx = 237568; np = 3; mm = $true }
    @{ ctx = 229376; np = 3; mm = $true }
    @{ ctx = 221184; np = 3; mm = $true }
    @{ ctx = 212992; np = 3; mm = $true }
    @{ ctx = 245760; np = 3; mm = $true; ub = 256 }
    @{ ctx = 237568; np = 3; mm = $true; ub = 256 }
)

New-Item -ItemType Directory -Force -Path $Thu | Out-Null
Remove-Item -Path $Log, $Ket -Force -ErrorAction SilentlyContinue
Ghi "=== MA TRAN G1 === $($DsCauHinh.Count) cau hinh"

foreach ($ch in $DsCauHinh) {
    $nhan = "ctx$($ch.ctx)_np$($ch.np)_mm$(if($ch.mm){'1'}else{'0'})"
    if ($ch.nommoff) { $nhan += '_nooff' }
    if ($ch.ub) { $nhan += "_ub$($ch.ub)" }
    DonDep
    $truoc = Vram38
    Ghi "---- $nhan | VRAM truoc = $truoc MiB"

    $a = @('-m', $Gguf, '--jinja', '--chat-template-file', $Tmpl,
           '--reasoning-format', 'deepseek', '-fa', '1', '-ngl', '999',
           '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2', '--metrics',
           '-c', "$($ch.ctx)", '-np', "$($ch.np)", '-kvu',
           '--cache-type-k', 'q4_0', '--cache-type-v', 'q4_0',
           '--host', '127.0.0.1', '--port', "$Port")
    if ($ch.mm) { $a += @('--mmproj', $Mmproj) }
    # `--no-mmproj-offload`: giu vision nhung de bo chieu da phuong tien
    # nam o RAM chu thay vi VRAM. Doi lai: ma hoa anh cham hon. Day la nut
    # co san cua llama.cpp, khong phai thu ta tu che.
    if ($ch.nommoff) { $a += @('--no-mmproj-offload') }
    # `-ub` (micro-batch) quyet dinh co BO DEM TINH TOAN. Ha no la cach
    # cuoi cung con lai de lay VRAM ma khong dong vao ngu canh, so slot hay
    # vision. Doi lai: prefill cham hon, nen G1 phai ghi lai prompt tok/s.
    if ($ch.ub) { $a += @('-ub', "$($ch.ub)", '-b', "$($ch.ub)") }

    $env:CUDA_VISIBLE_DEVICES = $Uuid38
    $t0 = Get-Date
    $p = Start-Process -FilePath $Bin -ArgumentList $a -PassThru -NoNewWindow `
            -RedirectStandardOutput "$Thu\$nhan.out.log" -RedirectStandardError "$Thu\$nhan.err.log"

    $xanh = $false
    for ($i = 0; $i -lt 300; $i++) {
        Start-Sleep -Seconds 1
        if ($p.HasExited) { break }
        try { if ((Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3).status -eq 'ok') { $xanh = $true; break } } catch { }
    }
    $giay = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)

    $r = [ordered]@{ nhan = $nhan; ctx = $ch.ctx; np = $ch.np; mmproj = $ch.mm
                     nap_duoc = $xanh; giay_nap = $giay; vram_truoc_mib = $truoc }

    if (-not $xanh) {
        $r.ly_do = 'khong nap duoc'
        $r.duoi_log = (Get-Content "$Thu\$nhan.err.log" -Tail 12 -ErrorAction SilentlyContinue) -join ' | '
        Ghi "TRUOT   $($nhan): khong nap duoc sau $giay s"
    } else {
        $sau  = Vram38
        $chia = DemGpu $p.Id 'Shared Usage'
        $rieng = DemGpu $p.Id 'Dedicated Usage'
        $r.vram_sau_nap_mib = $sau
        $r.shared_usage_mib = $chia
        $r.dedicated_usage_mib = $rieng
        $r.bien_mib = 24576 - $sau
        Ghi "NAP     $($nhan): $giay s | VRAM $sau | Shared $chia | Dedicated $rieng | bien $($r.bien_mib)"

        # max_tokens 400 chu khong 32: model nay co khoi <think>, va
        # `--reasoning-format deepseek` tach khoi do ra `reasoning_content`.
        # Voi 32 token no chua nghi xong => `content` RONG. Lan G1 dau tien
        # (21:43) da bao "tra loi rong" chinh vi the - do la loi cua PHEP DO,
        # khong phai cua engine. Doc ca hai truong roi moi ket luan.
        try {
            $body = @{ model = 'x'
                       messages = @(@{ role = 'user'; content = 'Tinh 12 * 17 va giai thich ngan gon.' })
                       max_tokens = 400; stream = $false } | ConvertTo-Json -Depth 5
            $t1 = Get-Date
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/v1/chat/completions" `
                        -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 300
            $m = $resp.choices[0].message
            $r.noi_dung = "$($m.content)"
            $r.reasoning = if ($m.reasoning_content) { "$($m.reasoning_content)".Substring(0, [Math]::Min(120, "$($m.reasoning_content)".Length)) } else { '' }
            $r.co_chu = -not ([string]::IsNullOrWhiteSpace("$($m.content)") -and [string]::IsNullOrWhiteSpace("$($m.reasoning_content)"))
            $r.token_ra = $resp.usage.completion_tokens
            $r.giay_luot = [math]::Round(((Get-Date) - $t1).TotalSeconds, 1)
            $r.tok_s = if ($r.giay_luot -gt 0) { [math]::Round($r.token_ra / $r.giay_luot, 2) } else { 0 }
            $r.vram_dinh_mib = Vram38
            $r.shared_dinh_mib = DemGpu $p.Id 'Shared Usage'
            Ghi "LUOT    $($nhan): $($r.token_ra) token / $($r.giay_luot) s = $($r.tok_s) tok/s | co_chu=$($r.co_chu) | Shared dinh $($r.shared_dinh_mib)"
        } catch {
            $r.luot_loi = $_.Exception.Message
            Ghi "LUOT    $nhan LOI: $($_.Exception.Message)"
        }
        Stop-Process -Id $p.Id -Force
    }
    Add-Content -Path $Ket -Value ($r | ConvertTo-Json -Depth 5 -Compress) -Encoding UTF8
}

DonDep
Ghi "=== KET THUC MA TRAN ==="
